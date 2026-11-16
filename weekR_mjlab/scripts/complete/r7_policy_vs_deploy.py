"""R7: obs ที่ env (ตอนเทรน) สร้าง = obs ที่ฝั่ง deploy สร้างไหม? + รัน P3b ใน env ฉบับสมบูรณ์

  python r7_policy_vs_deploy.py              # vx 0.5, 4 s
  python r7_policy_vs_deploy.py --vx 0.0     # สั่งยืน → phase เป็น 0

ทำอะไร
  ทุก step: เอาสถานะของ env 0 (q, dq, quat, gyro, คำสั่ง, action ก่อนหน้า) มาใส่ "LowState ปลอม"
  แล้วสร้าง obs ด้วย week4/scripts/complete/obs.py (ตัวเดียวกับที่ใช้ shadow mode กับ g1_ctrl)
  เทียบกับ obs["actor"] ที่ env ส่งให้ policy · ต่างกันมาก = sim2real bug (ลำดับ joint, สัญลักษณ์, phase ...)

สิ่งที่ควรเห็น
  - ทุก term ต่างกันแค่ ~1e-7 (float32) ยกเว้น phase: deploy เดินนาฬิกาก่อนคำนวณ → นำ env 1 step (0.1 rad)
  - joint order: policy index i ↔ SDK slot joint_ids_map[i] ตรงกับลำดับ joint ใน env
"""
import argparse
import contextlib
import io
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch

import rlib

sys.path.insert(0, str(Path.home() / "g1_study/week4/scripts/complete"))
import obs as w4  # noqa: E402  (week4 obs.py: build_obs, GaitPhase, PolicyConfig)


def lowstate_from_env(env, i: int, pcfg) -> SimpleNamespace:
    """สถานะของ env ที่ i → object หน้าตาเหมือน LowState (motor_state[slot].q/dq, imu_state)"""
    d = env.scene["robot"].data
    q, dq = d.joint_pos[i].tolist(), d.joint_vel[i].tolist()      # เรียงตามลำดับ joint ของ env (= policy index)
    motors = [SimpleNamespace(q=0.0, dq=0.0) for _ in range(35)]
    for k, slot in enumerate(pcfg.joint_ids_map):
        motors[slot].q, motors[slot].dq = q[k], dq[k]
    imu = SimpleNamespace(quaternion=d.root_link_quat_w[i].tolist(),     # (w, x, y, z)
                          gyroscope=d.root_link_ang_vel_b[i].tolist())   # กรอบลำตัว = gyro
    return SimpleNamespace(motor_state=motors, imu_state=imu)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vx", type=float, default=0.5)
    ap.add_argument("--seconds", type=float, default=4.0)
    args = ap.parse_args()

    cfg = rlib.load_cfg(rlib.FLAT, 4)
    rlib.fix_command(cfg, args.vx)
    cfg.observations["actor"].enable_corruption = False
    cfg.events.pop("push_robot", None)
    with contextlib.redirect_stdout(io.StringIO()):
        env = rlib.make_env(cfg)

    # ตรวจลำดับ joint ก่อน: env กับ deploy.yaml ต้องเรียงเหมือนกัน
    pcfg = w4.PolicyConfig()
    names = env.scene["robot"].joint_names
    print("joint order env:", names[:3], "...", names[-2:], f"({len(names)} ตัว)")
    print("default ตรง deploy.yaml:",
          np.allclose(env.scene["robot"].data.default_joint_pos[0].cpu().numpy(), pcfg.default_joint_pos, atol=1e-4))

    actor = rlib.ActorMLP(device=env.device)
    sl = rlib.term_slices(env, "actor")
    obs, _ = env.reset()
    gait = w4.GaitPhase(pcfg)
    steps = int(args.seconds / env.step_dt)
    max_diff = {k: 0.0 for k in sl}
    vx_sum = 0.0
    gait.reset()                                         # deploy: นาฬิกาเริ่ม 0 ตอนเริ่มรัน policy

    for t in range(steps):
        # --- obs ฝั่ง deploy จากสถานะเดียวกัน
        ls = lowstate_from_env(env, 0, pcfg)
        cmd = env.command_manager.get_command("twist")[0].tolist()
        last = env.action_manager.action[0].tolist()
        ph = gait.step(cmd)                              # deploy: phase += dt ก่อน แล้วค่อยคำนวณ sin/cos
        mine = w4.build_obs(ls, cmd, last, ph, pcfg)
        theirs = obs["actor"][0].cpu().numpy()           # env: phase = (episode_length_buf × dt) mod period
        for k, (s, e) in sl.items():
            max_diff[k] = max(max_diff[k], float(np.abs(mine[s:e] - theirs[s:e]).max()))

        with torch.no_grad():
            obs, _, term, _, _ = env.step(actor(obs["actor"]))
        vx_sum += env.scene["robot"].data.root_link_lin_vel_b[:, 0].mean().item()

    print(f"\nเทียบ obs {steps} step (env 0) · max |deploy − env| ต่อ term:")
    rlib.print_table([(k, f"[{s},{e})", f"{max_diff[k]:.1e}", "✓" if max_diff[k] < 1e-4 else "✗")
                      for k, (s, e) in sl.items()], ["term", "ช่วง", "max diff", ""])
    n = env.step_dt / pcfg.gait_period
    print(f"\nphase ✗ ไม่ใช่ bug ของสคริปต์: step แรก env ให้ phase = 0 (episode_length_buf = 0)"
          f"\n   แต่ GaitPhase แบบ deploy เดินนาฬิกาก่อน → phase = dt/period = {n:.4f} รอบ"
          f"\n   ต่างกัน 1 step ตลอด (0.02 s = {n * 100:.1f}% ของคาบ) → sin ต่างได้สูงสุด 2·sin(π·{n:.4f}) = {2 * np.sin(np.pi * n):.3f}"
          if args.vx != 0 else "\nสั่งยืน: phase = 0 ทั้งสองฝั่ง")
    print(f"\nP3b vx จริงเฉลี่ย (กรอบหุ่น) {vx_sum / steps:+.2f} m/s (สั่ง {args.vx}) · ล้มใน step สุดท้าย: {int(term.sum())} env")
    env.close()


if __name__ == "__main__":
    main()
