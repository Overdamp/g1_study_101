"""m5_mjcf.py: แก้ MJCF 2 วิธี (โค้ด MjSpec / แก้ไฟล์ XML เอง) + ทดลอง frictionloss กับศอกห้อย (งาน M5) ฉบับสมบูรณ์

รัน:  python3 m5_mjcf.py --sweep                        (ศอกห้อยค้างที่กี่องศา เมื่อ frictionloss ของแขน = 0, 0.1, 0.2, 0.5, 1)
      python3 m5_mjcf.py --save my_g1 --arm-fric 0 --step 0.05
          → เขียน weekM_mujoco/models/my_g1.xml  แล้วเปิดดูด้วย  python3 -m mujoco.viewer --mjcf=../../models/my_g1.xml
      python3 m5_mjcf.py --xml ../../models/my_g1.xml     (ทดลองศอกห้อยกับไฟล์ที่แก้เองด้วยมือ)

ทายก่อนรัน --sweep: (1) frictionloss = 0 ศอกจะไปหยุดที่มุมมากหรือน้อยกว่า +64.8° (ค่า 0.2 เดิม ที่ 4 s)\n                    (2) ถ้ารอนาน 90 s มุมที่ค่า 0.2 จะเปลี่ยนไหม (งาน 1.4 คุณวัดได้ +69.3°)
"""

import argparse
from pathlib import Path

import mujoco
import numpy as np

from g1mj import ElasticBand, build_model, motor_q, save_xml

SLOT = 18


def hang(m, d, duration=4.0, marks=()):
    """ห้อยด้วยหนังยาง ไม่มีแรงจากมอเตอร์ (เหมือน m3) · คืน (มุมศอกสุดท้าย [deg], {เวลา: มุม} ตาม marks)"""
    band = ElasticBand()
    seen = {}
    marks = sorted(marks)
    while d.time < duration:
        band.apply(m, d)
        mujoco.mj_step(m, d)
        while marks and d.time >= marks[0]:
            seen[marks.pop(0)] = np.degrees(motor_q(m, d)[SLOT])
    return np.degrees(motor_q(m, d)[SLOT]), seen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--arm-fric", type=float, default=None)
    ap.add_argument("--step", type=float, default=0.0, help="ใส่ขั้นบันได สูง [m]")
    ap.add_argument("--save", default=None, help="ชื่อไฟล์ใน weekM_mujoco/models/")
    ap.add_argument("--xml", type=Path, default=None, help="ทดลองศอกห้อยกับไฟล์ XML นี้")
    args = ap.parse_args()

    if args.xml:
        m = mujoco.MjModel.from_xml_path(str(args.xml))
        d = mujoco.MjData(m)
        dof = m.joint("left_elbow_joint").dofadr[0]
        ang, _ = hang(m, d)
        print(f"{args.xml.name}: frictionloss ศอก {m.dof_frictionloss[dof]:.2f} armature {m.dof_armature[dof]:.3f} "
              f"→ ศอกที่ 4 s = {ang:+.1f}°")
        return

    if args.sweep:
        marks = (1, 4, 15, 30, 60, 90)
        print("มุมศอกซ้าย [deg] ตอนห้อย (ไม่มีแรงจากมอเตอร์) ที่เวลาต่างๆ  · ใช้เวลารันราว 10–20 วินาที")
        print(f"{'arm frictionloss':>17} " + " ".join(f"{t:>6}s" for t in marks))
        for fl in (0.0, 0.1, 0.2, 0.5, 1.0):
            _, m, d = build_model(arm_frictionloss=fl)
            _, seen = hang(m, d, duration=marks[-1] + 0.01, marks=marks)
            print(f"{fl:>17.1f} " + " ".join(f"{seen[t]:>+6.1f}°" for t in marks))
        print("\n- frictionloss 0: แกว่งไม่หยุด (damping ของข้อต่อแค่ 0.05) ตัวเลขเป็นแค่ภาพ ณ เวลานั้น ไม่ใช่จุดสมดุล")
        print("- frictionloss > 0: ช่วงแรกค้างก่อนถึงจุดสมดุล แต่ MuJoCo ทำแรงเสียดทานเป็น soft constraint")
        print("  ข้อต่อจึงค่อยๆ ไหล (creep) เข้าหาจุดสมดุลของแรงโน้มถ่วง ~69° ทุกค่า (0.1 ไหลลงมาจากด้านบนด้วย)")
        print("  ค่า 0.2 (ค่าจริงของโมเดล): ~64° ที่ 4 s → ~69° ที่ 90 s = ที่มาของ +69.3° ในงาน 1.4")
        return

    spec, m, d = build_model(arm_frictionloss=args.arm_fric, step_h=args.step)
    if args.save:
        out = save_xml(spec, args.save)
        print(f"เขียน {out}  ({out.stat().st_size / 1024:.0f} KB)")
        print(f"เปิดดู:  python3 -m mujoco.viewer --mjcf={out}")
        print("ลองแก้ด้วยมือ: เปิดไฟล์ หา left_elbow_joint แก้ frictionloss แล้วรัน  python3 m5_mjcf.py --xml", out)
    else:
        ang, _ = hang(m, d)
        print(f"arm frictionloss {args.arm_fric} step {args.step} → ศอกที่ 4 s = {ang:+.1f}°")


if __name__ == "__main__":
    main()
