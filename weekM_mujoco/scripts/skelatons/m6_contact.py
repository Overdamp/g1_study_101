"""m6_contact.py: contact, แรงที่เท้า, IMU sensor (งาน M6) โครงให้เติม

รัน:  python3 m6_contact.py --headless
      python3 m6_contact.py --headless --length 1.8
      python3 m6_contact.py                  (หน้าต่าง: กด C เห็นจุดสัมผัส · F เห็นลูกศรแรง)
ก่อนเริ่ม: เติม foot_forces ใน g1mj_skeleton.py

ทายก่อนรัน: (1) ตอนนิ่ง แรงเท้า L + R + แรงหนังยาง = ?  (2) accelerometer แกน z ตอนยืนนิ่ง = +9.81 หรือ −9.81
เฉลย: ../complete/m6_contact.py
"""

import argparse

import mujoco
import numpy as np

from g1mj_skeleton import G, ElasticBand, foot_forces, load, load_deploy, pd_ctrl, run, set_pose


def contacts_table(m, d) -> None:
    print(f"\n== contact ทั้งหมด ({d.ncon} จุด)")
    f6 = np.zeros(6)
    for i in range(d.ncon):
        c = d.contact[i]
        # TODO 1: ชื่อ body ของ c.geom1 / c.geom2 (m.body(m.geom_bodyid[g]).name), c.pos, c.dist [mm]
        # TODO 2: mujoco.mj_contactForce(m, d, i, f6) → f6[0] = แรงตั้งฉาก
        # คำถาม: เท้าแต่ละข้างมีกี่จุด อยู่ตรงไหนของเท้า (ดู c.pos) จุดหน้าหรือหลังรับแรงมากกว่า
        pass


def imu_check(m, d) -> None:
    print("\n== IMU")
    # TODO 3: เทียบ d.sensor("imu_quat").data กับ d.qpos[3:7] และ d.sensor("imu_gyro").data กับ d.qvel[3:6]
    #         (ผลต่าง max) → แล้ว mujoco.mj_forward(m, d) → เทียบใหม่  ทำไมก่อน/หลังต่างกัน
    # TODO 4: พิมพ์ d.sensor("imu_acc").data → ยืนนิ่งได้ +g หรือ −g ทำไม
    pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--duration", type=float, default=None)
    ap.add_argument("--length", type=float, default=1.4)
    args = ap.parse_args()
    if args.duration is None:
        args.duration = 3.0 if args.headless else None

    m, d = load()
    dep = load_deploy()
    set_pose(m, d, dep.q_default, base_z=0.79)
    band = ElasticBand(length=args.length)
    mg = m.body_subtreemass[0] * G

    def step_fn(m, d):
        band.apply(m, d)
        d.ctrl[:] = pd_ctrl(m, d, dep.q_default, dep.kp, dep.kd)

    def report(m, d):
        # TODO 5: fl, fr = foot_forces(m, d) → พิมพ์ fl, fr, band.f[2], ผลรวม เทียบ mg
        pass

    run(m, d, step_fn, duration=args.duration, headless=args.headless,
        key_callback=band.key, every=0.5, every_fn=report)
    contacts_table(m, d)
    imu_check(m, d)


if __name__ == "__main__":
    main()
