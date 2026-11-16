"""shadow_mode_skeleton.py: รันคู่กับ g1_ctrl ใน sim แล้วเทียบ q_des (งาน 4.4–4.5, 4.8)  ❌ ไม่ส่งอะไร (subscribe อย่างเดียว)

ขั้นตอน (week4/docs/shadow_mode.md):
  1. ~/g1_study/start_sim.sh
  2. g1_ctrl (ไม่ใส่ --network) → Pause MuJoCo → Load key 0 → u → v → Run   (เท้าแตะพื้น, ไม่กดปุ่มเดิน)
  3. รอผ่าน soft start แล้วรันสคริปต์นี้ ~15 s
  4. วิเคราะห์ด้วย analyze_shadow_skeleton.py

ทุก 20 ms (50 Hz): obs → ONNX → q_des(เรา) เทียบกับ q ใน lowcmd ที่ g1_ctrl ส่ง (23 slot ตาม joint_ids_map)
รัน:  conda activate g1_sdk && python week4/scripts/skelatons/shadow_mode_skeleton.py --seconds 15 --out shadow.csv
"""

import argparse
import threading
import time

import numpy as np

from obs_skeleton import GaitPhase, PolicyConfig, action_to_q_des, build_obs

DOMAIN = 1
IFACE = "lo"


class Latest:
    """เก็บ message ล่าสุดของ topic หนึ่ง (แพทเทิร์นสัปดาห์ 1)  ให้ไว้แล้ว"""

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
                   choices=("none", "lastaction_qdes", "rate_1k"),
                   help="4.8 (ง) last_action = q_des แทน raw · (จ) เรียก policy ทุก 1 ms")
    args = p.parse_args()
    cfg = PolicyConfig()

    # TODO [4.4] ChannelFactoryInitialize(DOMAIN, IFACE)
    state_in, cmd_in = Latest(), Latest()
    # TODO [4.4] subscribe "rt/lowstate" (LowState_) → state_in.handler
    # TODO [4.4] subscribe "rt/lowcmd"   (LowCmd_)   → cmd_in.handler     ← อ่านคำสั่งของ g1_ctrl (ไม่มี publisher ในไฟล์นี้)
    # TODO [4.4] InferenceSession(cfg.onnx_path)
    session = None
    if session is None:
        print("shadow_mode: ยังไม่ได้เติม [4.4]")
        return

    gp = GaitPhase(cfg)
    last_action = np.zeros(23, dtype=np.float32)
    rows = []
    dt = 0.001 if args.break_mode == "rate_1k" else cfg.step_dt
    # TODO [4.4] รอจนทั้ง state_in และ cmd_in มีข้อความ (ถ้า cmd_in ว่างนาน: g1_ctrl ไม่ได้รัน?)
    # TODO [4.4] t0, next_t = เวลาเริ่ม (monotonic)
    while True:
        # TODO [4.4] หยุดเมื่อเกิน args.seconds
        # TODO [4.4] msg = state_in.get();  lc = cmd_in.get()
        # TODO [4.4] obs = build_obs(msg, (0,0,0), last_action, gp.step((0,0,0)), cfg)    ← cmd = 0 (shadow_mode.md: อ่านคีย์บอร์ดของ g1_ctrl ไม่ได้)
        # TODO [4.4] action = ONNX(obs);  q_ours = action_to_q_des(action, cfg)
        # TODO [4.4] q_g1 = [lc.motor_cmd[slot].q for slot in cfg.joint_ids_map]
        # TODO [4.4] last_action = action   (4.8 ง: ใช้ q_ours แทน แล้วดูผล)
        # TODO [4.4] rows.append([t, *q_ours, *q_g1, *obs])
        # TODO [4.4] นัดเวลารอบถัดไปแบบสะสม (next_t += dt)
        # 4.5: ระหว่างเก็บ ลากลำตัวใน MuJoCo ให้ก้ม/เอียงเล็กน้อย (< 0.85 rad) ดู obs[3:6]
        break

    # TODO [4.4] เซฟ CSV: header  t, ours_0..22, g1_0..22, obs_0..79  (np.savetxt หรือ csv)
    print(f"เซฟ {len(rows)} แถว → {args.out}")


if __name__ == "__main__":
    main()
