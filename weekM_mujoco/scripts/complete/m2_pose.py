"""m2_pose.py: qpos, ท่าทาง, ความสูงที่เท้าแตะพื้น, quaternion → projected gravity (งาน M2) ฉบับสมบูรณ์

รัน:  python3 m2_pose.py                 (พิมพ์ผล)
      python3 m2_pose.py --view          (เปิดหน้าต่างดูท่า default ที่ความสูงที่หาได้)
      python3 m2_pose.py --pitch 10 --view   (ก้ม 10°)

สิ่งที่ฝึก: เขียน qpos ตรงๆ ("วาง" หุ่น) → mj_forward → อ่าน xpos / sensor / contact
"""

import argparse

import numpy as np

from g1mj import load, load_deploy, motor_q, projected_gravity, set_pose, slot_table, view_static


def floor_contacts(m, d) -> int:
    """จำนวน contact ระหว่างพื้น (floor) กับหุ่น"""
    f = m.geom("floor").id
    return sum(1 for i in range(d.ncon) if f in (d.contact[i].geom1, d.contact[i].geom2))


def touch_height(m, d, q, lo=0.5, hi=1.2, iters=40) -> float:
    """binary search ความสูงฐาน (qpos[2]) ที่เท้าเพิ่งแตะพื้นพอดี
    MuJoCo รายงาน contact เมื่อระยะ < margin (0 ในโมเดลนี้) → มี contact = จมหรือแตะแล้ว"""
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        set_pose(m, d, q, base_z=mid)
        if floor_contacts(m, d) > 0:
            lo = mid            # ยังแตะอยู่ → ยกขึ้น
        else:
            hi = mid            # ลอยแล้ว → ลดลง
    return hi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pitch", type=float, default=0.0, help="ก้ม [deg] (หมุนรอบแกน y ของโลก)")
    ap.add_argument("--zero", action="store_true", help="ใช้ท่า q = 0 ทุกข้อต่อ แทนท่า default")
    ap.add_argument("--view", action="store_true")
    args = ap.parse_args()

    m, d = load()
    dep = load_deploy()
    tab = slot_table(m)
    q = np.zeros(m.nu) if args.zero else dep.q_default
    print("ท่า:", "q = 0" if args.zero else "default ของ policy v0 (deploy.yaml)")
    for s in (0, 3, 4, 15, 18):
        print(f"  slot {s:>2} {tab.names[s]:<26} q = {np.degrees(q[s]):+6.1f}°  → d.qpos[{tab.qadr[s]}]")

    z = touch_height(m, d, q)
    set_pose(m, d, q, base_z=z)
    print(f"\nความสูงฐาน (pelvis) ที่เท้าแตะพื้น: {z:.4f} m")
    for b in ("pelvis", "torso_link", "left_ankle_roll_link", "right_ankle_roll_link"):
        print(f"  {b:<22} xpos = {np.round(d.body(b).xpos, 3)}")
    print(f"  qpos[0:7] = {np.round(d.qpos[:7], 4)}  (x y z | qw qx qy qz)")
    print(f"  motor_q ตรงกับที่ตั้ง: {np.allclose(motor_q(m, d), q)}")

    if args.pitch:
        th = np.radians(args.pitch)
        quat = np.array([np.cos(th / 2), 0.0, np.sin(th / 2), 0.0])     # หมุนรอบแกน y: บวก = หัวก้มลง
        set_pose(m, d, q, base_z=z + 0.1, base_quat=quat)
        qs = d.sensor("imu_quat").data
        g = projected_gravity(qs)
        R = d.body("pelvis").xmat.reshape(3, 3)                          # คอลัมน์ = แกนของลำตัวในกรอบโลก
        print(f"\nก้ม {args.pitch:+.1f}°: imu_quat = {np.round(qs, 4)}  (= qpos[3:7] เพราะ site imu อยู่ที่ pelvis ไม่หมุน)")
        print(f"  projected_gravity (สูตร week4) = {np.round(g, 4)}")
        print(f"  Rᵀ·(0,0,−1) จาก xmat         = {np.round(R.T @ [0, 0, -1.0], 4)}")
        print(f"  คาด gx = sin({args.pitch:g}°) = {np.sin(th):+.4f}, gz = −cos = {-np.cos(th):+.4f}")

    if args.view:
        print("\nเปิดหน้าต่าง (ไม่ step ฟิสิกส์ หุ่นจึงลอยค้าง) · ปิดหน้าต่างเพื่อจบ")
        view_static(m, d)


if __name__ == "__main__":
    main()
