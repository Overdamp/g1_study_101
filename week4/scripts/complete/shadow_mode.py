"""shadow_mode.py: รันคู่กับ g1_ctrl ใน sim แล้วเทียบ q_des (งาน 4.4–4.5, 4.8) ฉบับสมบูรณ์  ❌ ไม่ส่งอะไร (subscribe อย่างเดียว)

ขั้นตอน (week4/docs/shadow_mode.md):
  1. ~/g1_study/start_sim.sh
  2. g1_ctrl (ไม่ใส่ --network) → Pause MuJoCo → Load key 0 → u → v → Run   (เท้าแตะพื้น, ไม่กดปุ่มเดิน)
  3. รอผ่าน soft start แล้วรันสคริปต์นี้
  4. python analyze_shadow.py shadow.csv

--break (4.8): order (ใช้ slot 0..22 แทน joint_ids_map) · nodefault (ไม่ลบ default) · gravsign (กลับเครื่องหมาย gravity)
               lastaction_qdes (last_action = q_des) · rate_1k (เรียก policy ทุก 1 ms)
รัน:  conda activate g1_sdk && python week4/scripts/complete/shadow_mode.py --seconds 15 --out shadow.csv
"""

import argparse
import threading
import time

import numpy as np
from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowCmd_, LowState_

from obs import GaitPhase, Policy, PolicyConfig, action_to_q_des, build_obs

DOMAIN = 1
IFACE = "lo"


class Latest:
    def __init__(self):
        self.msg = None
        self.lock = threading.Lock()

    def handler(self, msg):
        with self.lock:
            self.msg = msg

    def get(self):
        with self.lock:
            return self.msg


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seconds", type=float, default=15.0)
    p.add_argument("--out", default="shadow.csv")
    p.add_argument("--break", dest="break_mode", default="none",
                   choices=("none", "order", "nodefault", "gravsign", "lastaction_qdes", "rate_1k"))
    args = p.parse_args()
    cfg = PolicyConfig()
    pol = Policy(cfg.onnx_path)

    # 4.8: วิธีทำให้พังแต่ละแบบ (ปกติ None = ใช้ค่าที่ถูก)
    joint_ids = list(range(23)) if args.break_mode == "order" else None
    default = np.zeros(23, np.float32) if args.break_mode == "nodefault" else None
    dt = 0.001 if args.break_mode == "rate_1k" else cfg.step_dt

    ChannelFactoryInitialize(DOMAIN, IFACE)
    state_in, cmd_in = Latest(), Latest()
    sub_s = ChannelSubscriber("rt/lowstate", LowState_)
    sub_s.Init(state_in.handler, 10)
    sub_c = ChannelSubscriber("rt/lowcmd", LowCmd_)          # ฟังคำสั่งของ g1_ctrl (ไม่มี publisher ในไฟล์นี้)
    sub_c.Init(cmd_in.handler, 10)

    t_wait = time.monotonic()
    while state_in.get() is None or cmd_in.get() is None:
        if time.monotonic() - t_wait > 3.0:
            print(f"รอ... lowstate {'✓' if state_in.get() else '✗'}  lowcmd {'✓' if cmd_in.get() else '✗ (g1_ctrl รันอยู่ไหม?)'}",
                  flush=True)
            t_wait = time.monotonic()
        time.sleep(0.05)
    print(f"เริ่มเก็บ {args.seconds:.0f} s (break={args.break_mode})", flush=True)

    gp = GaitPhase(cfg)
    last_action = np.zeros(23, dtype=np.float32)
    rows = []
    t0 = time.monotonic()
    next_t = t0
    while True:
        t = time.monotonic() - t0
        if t >= args.seconds:
            break
        msg, lc = state_in.get(), cmd_in.get()
        obs = build_obs(msg, (0.0, 0.0, 0.0), last_action, gp.step((0.0, 0.0, 0.0)), cfg, joint_ids, default)
        if args.break_mode == "gravsign":
            obs[3:6] *= -1
        action = pol.act(obs)
        q_ours = action_to_q_des(action, cfg)
        q_g1 = np.array([lc.motor_cmd[s].q for s in cfg.joint_ids_map], dtype=np.float32)
        last_action = q_ours if args.break_mode == "lastaction_qdes" else action
        rows.append(np.concatenate([[t], q_ours, q_g1, obs]))

        next_t += dt
        sleep_s = next_t - time.monotonic()
        if sleep_s > 0:
            time.sleep(sleep_s)
        else:
            next_t = time.monotonic()

    header = ",".join(["t"] + [f"ours_{i}" for i in range(23)] + [f"g1_{i}" for i in range(23)] + [f"obs_{i}" for i in range(80)])
    np.savetxt(args.out, np.array(rows), delimiter=",", header=header, comments="", fmt="%.6f")
    err = np.abs(np.array(rows)[:, 1:24] - np.array(rows)[:, 24:47])
    print(f"เซฟ {len(rows)} แถว → {args.out}   (mean |error| ทั้งหมด {err.mean():.4f} rad, max {err.max():.3f})")


if __name__ == "__main__":
    main()
