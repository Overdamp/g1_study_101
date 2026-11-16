"""m7_policy.py: รัน policy v0 (ONNX) ใน MuJoCo ล้วน ไม่ผ่าน DDS / g1_ctrl (งาน M7) โครงให้เติม

รัน:  python3 m7_policy.py                              (หน้าต่าง เดินหน้า 0.5 m/s)
      python3 m7_policy.py --headless --step 0.03       (ขั้นบันได 3 cm ที่ x = 1 m)
      python3 m7_policy.py --headless --timestep 0.005  (physics 200 Hz แบบตอนเทรน)
ก่อนเริ่ม: เติม to_lowstate ใน g1mj_skeleton.py · ใช้ obs.py ของสัปดาห์ 4 (ไม่ต้องเขียน obs ใหม่)

ทายก่อนรัน: (1) decimation = ?  (2) ขั้นบันไดสูงสุดที่ v0 (เทรนพื้นเรียบ ไม่มี height scan) ผ่านได้ = ? cm
เฉลย: ../complete/m7_policy.py
"""

import argparse
import sys
from pathlib import Path

import numpy as np

from g1mj_skeleton import build_model, load_deploy, pd_ctrl, projected_gravity, run, set_pose, to_lowstate

sys.path.insert(0, str(Path.home() / "g1_study/week4/scripts/complete"))   # หรือชี้ไปที่ obs ของคุณเอง
from obs import GaitPhase, Policy, PolicyConfig, action_to_q_des, build_obs   # noqa: E402

TILT_LIMIT = 0.85


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--duration", type=float, default=None)
    ap.add_argument("--cmd", type=float, nargs=3, default=[0.5, 0.0, 0.0])
    ap.add_argument("--step", type=float, default=0.0)
    ap.add_argument("--timestep", type=float, default=None)
    args = ap.parse_args()
    if args.duration is None:
        args.duration = 10.0 if args.headless else None

    _, m, d = build_model(step_h=args.step, timestep=args.timestep)
    cfg = PolicyConfig()
    pol = Policy(cfg.onnx_path)
    dep = load_deploy()
    decimation = 1   # TODO 1: = round(cfg.step_dt / m.opt.timestep)

    set_pose(m, d, dep.q_default, base_z=0.80)
    cmd = np.array(args.cmd, dtype=np.float32)
    gait = GaitPhase(cfg)
    last_action = np.zeros(23, dtype=np.float32)
    q_des = dep.q_default.copy()
    state = {"k": 0, "fell": None}

    def step_fn(m, d):
        if state["k"] % decimation == 0:
            # TODO 2: obs = build_obs(to_lowstate(m, d), cmd, last_action, gait.step(cmd), cfg)
            # TODO 3: action = pol.act(obs); last_action[:] = action
            # TODO 4: q_des[cfg.joint_ids_map] = action_to_q_des(action, cfg)
            #         (policy เรียง 23 ตัวตามลำดับของมัน → joint_ids_map บอกว่าแต่ละตัวคือ slot ไหน)
            pass
        state["k"] += 1
        # TODO 5: d.ctrl[:] = pd_ctrl(m, d, q_des, dep.kp, dep.kd)   ← ทุก physics step (ไม่ใช่แค่ทุก policy step)
        # TODO 6: ตรวจล้ม: g = projected_gravity(d.qpos[3:7]); มุมเอียง = arccos(−g[2]) > TILT_LIMIT → จำเวลา
        pass

    def report(m, d):
        print(f"t={d.time:5.2f}  x={d.qpos[0]:+5.2f} y={d.qpos[1]:+5.2f} z={d.qpos[2]:.3f}  vx={d.qvel[0]:+.2f}", flush=True)

    run(m, d, step_fn, duration=args.duration, headless=args.headless, every=1.0, every_fn=report)
    print("ล้มที่", state["fell"])
    # คำถาม: ถ้าย้าย pd_ctrl เข้าไปไว้ใน if (คำนวณทุก policy step แล้วค้าง ctrl) จะต่างกันอย่างไร ลองดู


if __name__ == "__main__":
    main()
