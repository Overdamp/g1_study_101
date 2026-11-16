"""m2_pose.py: qpos, ท่าทาง, ความสูงที่เท้าแตะพื้น, quaternion → projected gravity (งาน M2) โครงให้เติม

รัน:  python3 m2_pose.py                 (พิมพ์ผล)
      python3 m2_pose.py --view          (เปิดหน้าต่างดูท่า)
      python3 m2_pose.py --pitch 10      (ก้ม 10°)
ก่อนเริ่ม: เติม set_pose / projected_gravity ใน g1mj_skeleton.py

ทายก่อนรัน: ท่า default ของ policy ฐาน (pelvis) ต้องสูงเท่าไรเท้าถึงแตะพื้นพอดี  (ใบ้: ใน XML pelvis เริ่มที่ 0.793)
เฉลย: ../complete/m2_pose.py
"""

import argparse

import numpy as np

from g1mj_skeleton import load, load_deploy, motor_q, projected_gravity, set_pose, slot_table, view_static


def floor_contacts(m, d) -> int:
    """จำนวน contact ที่ geom หนึ่งเป็น floor"""
    f = m.geom("floor").id
    # TODO 1: นับ i ใน range(d.ncon) ที่ f อยู่ใน (d.contact[i].geom1, d.contact[i].geom2)
    return 0


def touch_height(m, d, q, lo=0.5, hi=1.2, iters=40) -> float:
    """binary search ความสูงฐานที่เท้าเพิ่งแตะพื้น"""
    # TODO 2: วน iters รอบ: mid = (lo+hi)/2 → set_pose(m, d, q, base_z=mid)
    #         ถ้า floor_contacts > 0 (ยังแตะ/จม) → lo = mid  ไม่งั้น → hi = mid
    return hi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pitch", type=float, default=0.0)
    ap.add_argument("--zero", action="store_true", help="ท่า q = 0 ทุกข้อต่อ")
    ap.add_argument("--view", action="store_true")
    args = ap.parse_args()

    m, d = load()
    dep = load_deploy()
    tab = slot_table(m)
    q = np.zeros(m.nu) if args.zero else dep.q_default
    # TODO 3: พิมพ์ q ของ slot 0, 3, 4, 15, 18 เป็นองศา พร้อมบอกว่าเขียนลง d.qpos[?] (tab.qadr)

    z = touch_height(m, d, q)
    set_pose(m, d, q, base_z=z)
    print(f"ความสูงฐานที่เท้าแตะพื้น: {z:.4f} m")
    # TODO 4: พิมพ์ d.body(name).xpos ของ pelvis, torso_link, left_ankle_roll_link, right_ankle_roll_link
    # TODO 5: ตรวจ motor_q(m, d) == q (np.allclose) → ยืนยันว่า slot_table + sensor ถูก

    if args.pitch:
        th = np.radians(args.pitch)
        # TODO 6: quaternion หมุนรอบแกน y มุม th = (cos(th/2), 0, sin(th/2), 0) → set_pose(..., base_z=z+0.1, base_quat=...)
        # TODO 7: g = projected_gravity(d.sensor("imu_quat").data)
        # TODO 8: เทียบกับ R.T @ (0,0,−1) โดย R = d.body("pelvis").xmat.reshape(3, 3)  ต้องเท่ากัน
        #         คาดว่า gx = sin(th) → ก้มแล้ว gx บวกหรือลบ? ตรงกับที่ policy เห็นใน week4 ไหม
        pass

    if args.view:
        view_static(m, d)


if __name__ == "__main__":
    main()
