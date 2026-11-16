"""m6_contact.py: contact, แรงที่เท้า, IMU sensor (งาน M6) ฉบับสมบูรณ์

รัน:  python3 m6_contact.py --headless                 (หนังยางยาว 1.4 m: หนังยางรับน้ำหนักส่วนหนึ่ง เท้ารับส่วนที่เหลือ)
      python3 m6_contact.py --headless --length 1.8    (หนังยางรับน้อยลง: เท้ารับมากขึ้น ยังยืนได้ไหม?)
      ※ ElasticBand ใน main.cc ไม่มีเงื่อนไข 'สายหย่อน': ถ้า length ยาวกว่าระยะถึงจุดแขวน สปริงจะ 'ดันลง' (แรงติดลบ)
      python3 m6_contact.py                            (เปิดหน้าต่าง: กด C ให้เห็นจุดสัมผัส F ให้เห็นลูกศรแรง)

ทายก่อนรัน: ตอนนิ่ง แรงเท้าซ้าย + แรงเท้าขวา + แรงหนังยาง = ?   แล้ว accelerometer แกน z อ่านได้ +9.81 หรือ −9.81
"""

import argparse

import mujoco
import numpy as np

from g1mj import G, ElasticBand, foot_forces, load, load_deploy, pd_ctrl, run, set_pose


def contacts_table(m, d) -> None:
    print(f"\n== contact ทั้งหมด ({d.ncon} จุด)")
    f6 = np.zeros(6)
    for i in range(d.ncon):
        c = d.contact[i]
        b1, b2 = m.body(m.geom_bodyid[c.geom1]).name, m.body(m.geom_bodyid[c.geom2]).name
        mujoco.mj_contactForce(m, d, i, f6)
        print(f"  {i:>2} {b1:<10} ↔ {b2:<22} pos {np.round(c.pos, 3)}  ระยะ {c.dist * 1e3:+.2f} mm  "
              f"แรงตั้งฉาก {f6[0]:6.1f} N")


def imu_check(m, d) -> None:
    print("\n== IMU (site 'imu' อยู่ที่ pelvis)")
    for label in ("หลัง mj_step", "หลัง mj_forward"):
        q_s, w_s = d.sensor("imu_quat").data, d.sensor("imu_gyro").data
        print(f"  [{label}] imu_quat − qpos[3:7] max {np.abs(q_s - d.qpos[3:7]).max():.1e}   "
              f"imu_gyro − qvel[3:6] max {np.abs(w_s - d.qvel[3:6]).max():.1e}")
        mujoco.mj_forward(m, d)
    print("  → mj_step คำนวณ sensor ก่อน integrate: sensordata ช้ากว่า qpos/qvel 1 step (2 ms) · mj_forward ทำให้ตรงกัน")
    print("    (ความเร็วเชิงมุมของ free joint qvel[3:6] อยู่ในกรอบลำตัว จึงเท่ากับ gyro ได้ตรงๆ)")
    a_s = d.sensor("imu_acc").data
    print(f"  imu_acc {np.round(a_s, 3)}  |a| = {np.linalg.norm(a_s):.3f}")
    print("  → accelerometer วัด 'แรงที่ดันตัว' (ไม่รวมแรงโน้มถ่วง) ยืนนิ่ง = +g ชี้ขึ้น · ตกอิสระ = 0")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--duration", type=float, default=None)
    ap.add_argument("--length", type=float, default=1.4, help="ความยาวหนังยาง [m] (ยาว = หย่อน)")
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
        fl, fr = foot_forces(m, d)
        print(f"t={d.time:4.1f}  เท้า L {fl:6.1f}  R {fr:6.1f}  หนังยาง {band.f[2]:6.1f}  รวม {fl + fr + band.f[2]:6.1f} N "
              f"(mg = {mg:.1f})  pelvis z {d.qpos[2]:.3f}", flush=True)

    run(m, d, step_fn, duration=args.duration, headless=args.headless,
        key_callback=band.key, every=0.5, every_fn=report)
    contacts_table(m, d)
    imu_check(m, d)


if __name__ == "__main__":
    main()
