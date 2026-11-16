"""m5_mjcf.py: แก้ MJCF 2 วิธี + ทดลอง frictionloss กับศอกห้อย (งาน M5) โครงให้เติม

รัน:  python3 m5_mjcf.py --sweep
      python3 m5_mjcf.py --save my_g1 --arm-fric 0 --step 0.05      → weekM_mujoco/models/my_g1.xml
      python3 -m mujoco.viewer --mjcf=../../models/my_g1.xml        (เปิดดูไฟล์ที่เขียน)
      python3 m5_mjcf.py --xml ../../models/my_g1.xml                (หลังแก้ไฟล์ด้วยมือ)

build_model / save_xml ให้ไว้แล้วใน g1mj_skeleton.py: อ่านดูว่า MjSpec แก้ joint / เพิ่ม geom อย่างไร

ทายก่อนรัน --sweep: (1) frictionloss 0 ศอกจะไปหยุดที่มุมมาก/น้อยกว่า +64.8° (ค่า 0.2 ที่ 4 s)
                    (2) รอ 90 s ค่าที่ 0.2 เปลี่ยนไหม
เฉลย: ../complete/m5_mjcf.py
"""

import argparse
from pathlib import Path

import mujoco
import numpy as np

from g1mj_skeleton import ElasticBand, build_model, motor_q, save_xml

SLOT = 18


def hang(m, d, duration=4.0, marks=()):
    """ห้อยด้วยหนังยาง ไม่มีแรงมอเตอร์ · คืน (มุมศอกสุดท้าย [deg], {เวลา: มุม [deg]} ตาม marks)"""
    band = ElasticBand()
    seen = {}
    marks = sorted(marks)
    # TODO 1: วนจน d.time >= duration: band.apply → mujoco.mj_step
    #         ถ้า d.time ผ่าน marks[0] แล้ว → seen[marks.pop(0)] = np.degrees(motor_q(m, d)[SLOT])
    return np.degrees(motor_q(m, d)[SLOT]), seen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--arm-fric", type=float, default=None)
    ap.add_argument("--step", type=float, default=0.0)
    ap.add_argument("--save", default=None)
    ap.add_argument("--xml", type=Path, default=None)
    args = ap.parse_args()

    if args.xml:
        # TODO 2: m = mujoco.MjModel.from_xml_path(str(args.xml)); d = mujoco.MjData(m)
        #         พิมพ์ frictionloss ของศอก (m.dof_frictionloss[m.joint("left_elbow_joint").dofadr[0]]) และผล hang
        return

    if args.sweep:
        marks = (1, 4, 15, 30, 60, 90)
        for fl in (0.0, 0.1, 0.2, 0.5, 1.0):
            # TODO 3: _, m, d = build_model(arm_frictionloss=fl) → hang(m, d, marks[-1] + 0.01, marks) → พิมพ์ 1 แถว
            pass
        # คำถาม: ค่าที่ 90 s ของทุก frictionloss ไปทางไหน ทำไม (ใบ้: MuJoCo ทำ frictionloss เป็น soft constraint)
        return

    spec, m, d = build_model(arm_frictionloss=args.arm_fric, step_h=args.step)
    if args.save:
        out = save_xml(spec, args.save)
        print(f"เขียน {out}  เปิดดู: python3 -m mujoco.viewer --mjcf={out}")
        # แบบฝึก: เปิดไฟล์ หา left_elbow_joint แก้ frictionloss ด้วยมือ แล้วรัน --xml
    else:
        print(f"ศอกที่ 4 s = {hang(m, d)[0]:+.1f}°")


if __name__ == "__main__":
    main()
