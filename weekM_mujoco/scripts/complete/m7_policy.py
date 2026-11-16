"""m7_policy.py: รัน policy v0 (ONNX) ใน MuJoCo ล้วน ไม่ผ่าน DDS / g1_ctrl (งาน M7) ฉบับสมบูรณ์

รัน:  python3 m7_policy.py                                   (เปิดหน้าต่าง เดินหน้า 0.5 m/s)
      python3 m7_policy.py --headless --cmd 0.5 0 0 --duration 10
      python3 m7_policy.py --headless --step 0.03            (ขั้นบันได 3 cm ที่ x = 1 m)
      python3 m7_policy.py --headless --step 0.05            (5 cm: ผ่านไหม? → โยงกับ stairs_blind)
      python3 m7_policy.py --headless --timestep 0.005       (physics 200 Hz แบบตอนเทรน mjlab)

ใช้ obs.py จากสัปดาห์ 4 (ไม่เขียนซ้ำ): build_obs, GaitPhase, action_to_q_des, Policy
ลำดับต่อ 1 policy step (50 Hz) เหมือน g1_ctrl + bridge:
  sensordata → to_lowstate() → build_obs (80) → ONNX → action (23) → q_des → PD ทุก physics step × decimation
"""

import argparse
import sys
from pathlib import Path

import numpy as np

from g1mj import build_model, foot_forces, load_deploy, pd_ctrl, projected_gravity, run, set_pose, to_lowstate

sys.path.insert(0, str(Path.home() / "g1_study/week4/scripts/complete"))
from obs import GaitPhase, Policy, PolicyConfig, action_to_q_des, build_obs   # noqa: E402

TILT_LIMIT = 0.85          # rad: เกณฑ์ล้มเดียวกับ g1_ctrl (bad_orientation)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--duration", type=float, default=None)
    ap.add_argument("--cmd", type=float, nargs=3, default=[0.5, 0.0, 0.0], metavar=("VX", "VY", "WZ"))
    ap.add_argument("--step", type=float, default=0.0, help="ความสูงขั้นบันได [m] ที่ x = 1 m")
    ap.add_argument("--timestep", type=float, default=None, help="physics timestep [s] (ปกติ 0.002)")
    ap.add_argument("--arm-fric", type=float, default=None)
    args = ap.parse_args()
    if args.duration is None:
        args.duration = 10.0 if args.headless else None

    _, m, d = build_model(step_h=args.step, timestep=args.timestep, arm_frictionloss=args.arm_fric)
    cfg = PolicyConfig()
    pol = Policy(cfg.onnx_path)
    dep = load_deploy()                                   # kp/kd/ท่า default เรียงตาม slot
    decimation = round(cfg.step_dt / m.opt.timestep)      # 0.02 / 0.002 = 10
    print(f"physics {1 / m.opt.timestep:.0f} Hz · policy {1 / cfg.step_dt:.0f} Hz · decimation {decimation} · cmd {args.cmd}")

    set_pose(m, d, dep.q_default, base_z=0.80)            # วางเหนือพื้นนิดหน่อย ให้ตกลงมาเอง
    cmd = np.array(args.cmd, dtype=np.float32)
    gait = GaitPhase(cfg)
    last_action = np.zeros(23, dtype=np.float32)
    q_des = dep.q_default.copy()
    state = {"k": 0, "fell": None, "max_x": 0.0}

    def step_fn(m, d):
        if state["k"] % decimation == 0:                  # ทุก 10 physics step = 1 policy step
            obs = build_obs(to_lowstate(m, d), cmd, last_action, gait.step(cmd), cfg)
            action = pol.act(obs)
            last_action[:] = action                       # obs รอบหน้าใช้ action ดิบ (ไม่ใช่ q_des)
            q_des[cfg.joint_ids_map] = action_to_q_des(action, cfg)
        state["k"] += 1
        d.ctrl[:] = pd_ctrl(m, d, q_des, dep.kp, dep.kd)  # PD ทุก physics step ด้วย q_des เดิม (zero-order hold)
        g = projected_gravity(d.qpos[3:7])
        if state["fell"] is None and np.arccos(np.clip(-g[2], -1, 1)) > TILT_LIMIT:
            state["fell"] = d.time
            print(f"[t={d.time:.2f}] ล้ม (เอียงเกิน {TILT_LIMIT} rad) ที่ x = {d.qpos[0]:.2f} m", flush=True)
        state["max_x"] = max(state["max_x"], d.qpos[0])

    def report(m, d):
        fl, fr = foot_forces(m, d)
        w, x, y, z = d.qpos[3:7]
        yaw = np.degrees(np.arctan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z)))   # มุมหันจาก quaternion
        print(f"t={d.time:5.2f}  x={d.qpos[0]:+5.2f} y={d.qpos[1]:+5.2f} z={d.qpos[2]:.3f} yaw={yaw:+6.1f}°  "
              f"vx={d.qvel[0]:+.2f}  เท้า L {fl:5.0f} R {fr:5.0f} N", flush=True)

    run(m, d, step_fn, duration=args.duration, headless=args.headless, every=1.0, every_fn=report)

    print(f"\nสรุป: ไปได้ไกลสุด x = {state['max_x']:.2f} m"
          + (f" · ล้มที่ t = {state['fell']:.2f} s" if state["fell"] is not None else " · ไม่ล้ม ✅")
          + (f" · ขั้นบันได {args.step * 100:.0f} cm ที่ x = 1 m" if args.step > 0 else ""))


if __name__ == "__main__":
    main()
