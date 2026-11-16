"""m3_band.py: step loop + viewer + หนังยาง (งาน M3) ฉบับสมบูรณ์ = unitree_mujoco แบบไม่มี DDS และไม่มีมอเตอร์

รัน:  python3 m3_band.py                         (เปิดหน้าต่าง: Space หยุด · 9 เปิด/ปิดหนังยาง · 7/↑ สั้นลง · 8/↓ ยาวขึ้น)
      python3 m3_band.py --headless --duration 5
      python3 m3_band.py --headless --duration 5 --stiffness 400     (ลองเปลี่ยนค่าสปริง)

ทายก่อนรัน: ความสูงของฐาน (pelvis = qpos[2]) ตอนนิ่ง = ?  (มวล 34.14 kg, k = 200 N/m, จุดแขวน z = 3 m, length 0)
"""

import argparse

import numpy as np

from g1mj import ElasticBand, G, load, motor_q, run, slot_table

SLOT_ELBOW_L = 18


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--duration", type=float, default=None)
    ap.add_argument("--stiffness", type=float, default=200.0)
    ap.add_argument("--damping", type=float, default=100.0)
    args = ap.parse_args()
    if args.headless and args.duration is None:
        args.duration = 5.0

    m, d = load()
    band = ElasticBand(stiffness=args.stiffness, damping=args.damping)
    mass = m.body_subtreemass[0]
    z_pred = band.point[2] - mass * G / band.stiffness
    print(f"มวล {mass:.2f} kg → แรงโน้มถ่วง {mass * G:.0f} N → สปริงยืด {mass * G / band.stiffness:.2f} m "
          f"→ pelvis คาดว่านิ่งที่ z ≈ {z_pred:.2f} m (ถ้าความยาวสาย = 0)")
    print("  ※ main.cc วัดระยะจาก qpos[0:3] (= pelvis) แต่ออกแรงที่ torso_link → ใช้ pelvis z เทียบกับที่ทาย")
    tab = slot_table(m)

    def step_fn(m, d):
        band.apply(m, d)            # ไม่มี ctrl: มอเตอร์ให้แรงบิด 0 (ctrl เริ่มที่ 0)

    def report(m, d):
        q = motor_q(m, d)
        print(f"t={d.time:5.2f}  pelvis z={d.qpos[2]:.3f}  torso z={d.body('torso_link').xpos[2]:.3f}  แรงหนังยาง={band.f[2]:6.1f} N  "
              f"ศอกซ้าย={np.degrees(q[SLOT_ELBOW_L]):+6.1f}°  เข่าซ้าย={np.degrees(q[3]):+6.1f}°", flush=True)

    run(m, d, step_fn, duration=args.duration, headless=args.headless,
        key_callback=band.key, every=0.5, every_fn=report)
    print(f"\nจบ: ศอกซ้าย {np.degrees(motor_q(m, d)[SLOT_ELBOW_L]):+.1f}° (งาน 1.4 ใน sim จริงวัดได้ +69.3°: frictionloss ทำให้ค้างก่อนจุดสมดุล ตำแหน่งที่ค้างจึงขึ้นกับการแกว่งช่วงแรก) · "
          f"{tab.names[SLOT_ELBOW_L]} range {np.degrees(m.jnt_range[tab.joint_id[SLOT_ELBOW_L]]).round(0)}°")


if __name__ == "__main__":
    main()
