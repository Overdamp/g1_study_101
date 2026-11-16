"""policy_once.py: ป้อน obs "ยืนนิ่งสมบูรณ์แบบ" เข้า policy (งาน 4.3) ฉบับสมบูรณ์  ❌ ไม่ต่อ DDS

1. step แรก (last_action = 0) → action, q_des − default
2. วน 20 step ป้อน last_action = action รอบก่อน → action ลู่เข้าค่าคงที่ไหม
3. ทดลองจาก onnx_basics.md: obs = 0 ทั้งหมด · เรียกซ้ำ obs เดิม · gravity x = 0.1

รัน:  conda activate g1_sdk && python week4/scripts/complete/policy_once.py
"""

import math

import numpy as np

from obs import GaitPhase, Policy, PolicyConfig, action_to_q_des, build_obs, fake_lowstate

NAMES = ["L_hip_p", "L_hip_r", "L_hip_y", "L_knee", "L_ank_p", "L_ank_r",
         "R_hip_p", "R_hip_r", "R_hip_y", "R_knee", "R_ank_p", "R_ank_r", "waist_y",
         "L_sh_p", "L_sh_r", "L_sh_y", "L_elbow", "L_wrist",
         "R_sh_p", "R_sh_r", "R_sh_y", "R_elbow", "R_wrist"]


def main():
    cfg = PolicyConfig()
    pol = Policy(cfg.onnx_path)
    msg = fake_lowstate(cfg)
    gp = GaitPhase(cfg)

    obs = build_obs(msg, (0, 0, 0), np.zeros(23, np.float32), gp.step((0, 0, 0)), cfg)
    action = pol.act(obs)
    q_des = action_to_q_des(action, cfg)
    print("== step แรก (ยืนท่า default นิ่ง ตั้งตรง, last_action = 0)")
    print(f"  {'joint':<8} {'action':>8} {'Δq_des [°]':>11}")
    for n, a, dq in zip(NAMES, action, q_des - cfg.default_joint_pos):
        print(f"  {n:<8} {a:+8.3f} {math.degrees(dq):+11.2f}")
    i = int(np.argmax(np.abs(action)))
    print(f"  max |action| = {abs(action[i]):.3f} ที่ {NAMES[i]}  → q_des ห่าง default สูงสุด "
          f"{math.degrees(np.max(np.abs(q_des - cfg.default_joint_pos))):.1f}°")

    print("\n== 20 step ต่อเนื่อง (obs อื่นคงที่, last_action = action รอบก่อน)")
    last = action
    for k in range(20):
        a = pol.act(build_obs(msg, (0, 0, 0), last, gp.step((0, 0, 0)), cfg))
        if k in (0, 4, 9, 19):
            print(f"  step {k + 2:2d}: max|action| {np.max(np.abs(a)):.3f}   เปลี่ยนจากรอบก่อน {np.max(np.abs(a - last)):.4f}")
        last = a

    print("\n== ทดลองเพิ่ม")
    zero = pol.act(np.zeros(80, np.float32))
    print(f"  obs = 0 ทั้งหมด → max|action| {np.max(np.abs(zero)):.3f}  (ไม่เป็น 0: มี normalizer + bias ใน network และ gravity 0 ไม่ใช่ท่ายืน)")
    again = pol.act(obs)
    print(f"  เรียกซ้ำ obs เดิม → ต่างจากครั้งแรก {np.max(np.abs(again - action)):.1e}  (deterministic)")
    tilt = obs.copy()
    tilt[3] = 0.1                                   # gravity x: เหมือนก้มไปข้างหน้าเล็กน้อย
    d = pol.act(tilt) - action
    top = np.argsort(-np.abs(d))[:3]
    print("  gravity x = 0.1 → ข้อต่อที่ action เปลี่ยนมากสุด: " + ", ".join(f"{NAMES[j]} {d[j]:+.3f}" for j in top))


if __name__ == "__main__":
    main()
