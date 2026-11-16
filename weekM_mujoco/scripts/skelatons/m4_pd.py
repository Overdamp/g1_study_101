"""m4_pd.py: เขียน PD เองใน MuJoCo = bridge ฉบับย่อ (งาน M4) โครงให้เติม

รัน:  python3 m4_pd.py                            (ห้อย + PD ค้างท่า default)
      python3 m4_pd.py --drop 3                   (ปิดหนังยางที่ 3 s)
      python3 m4_pd.py --elbow-step --headless    (step ศอกซ้าย ±0.3 rad + วัด rise time)
ก่อนเริ่ม: เติม pd_ctrl ใน g1mj_skeleton.py

ทายก่อนรัน: (1) --drop 3: หุ่นยืนเองได้ไหมด้วย PD ค้างท่า default (gain เดียวกับตอนเทรน)
            (2) --elbow-step --kd-scale 0: overshoot มากขึ้นหรือน้อยลง กี่ %
เฉลย: ../complete/m4_pd.py
"""

import argparse

import numpy as np

from g1mj_skeleton import ElasticBand, load, load_deploy, motor_q, motor_tau, pd_ctrl, run, set_pose

SLOT = 18
AMP, PERIOD = 0.3, 2.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--duration", type=float, default=None)
    ap.add_argument("--drop", type=float, default=None)
    ap.add_argument("--elbow-step", action="store_true")
    ap.add_argument("--kp-scale", type=float, default=1.0)
    ap.add_argument("--kd-scale", type=float, default=1.0)
    args = ap.parse_args()
    if args.duration is None:
        args.duration = 6.0 if args.headless else None

    m, d = load()
    dep = load_deploy()
    kp, kd = dep.kp * args.kp_scale, dep.kd * args.kd_scale
    q_des = dep.q_default.copy()
    set_pose(m, d, dep.q_default, base_z=1.0)
    band = ElasticBand()
    log = []

    def step_fn(m, d):
        # TODO 1: ถ้า args.drop และ d.time >= args.drop → band.enable = False (พิมพ์ครั้งเดียว)
        band.apply(m, d)
        # TODO 2: ถ้า --elbow-step: q_des[SLOT] = default ± AMP สลับทุก PERIOD/2 วินาที (ใช้ d.time % PERIOD)
        # TODO 3: d.ctrl[:] = pd_ctrl(m, d, q_des, kp, kd)
        # TODO 4: log.append((d.time, q_des[SLOT], motor_q(m, d)[SLOT], d.ctrl[SLOT]))
        pass

    def report(m, d):
        # TODO 5: พิมพ์ pelvis z, มุมเอียง (np.degrees(np.arccos(d.body("pelvis").xmat[8]))), ศอก q_des / q / tau
        pass

    run(m, d, step_fn, duration=args.duration, headless=args.headless,
        key_callback=band.key, every=0.5, every_fn=report)

    if args.elbow_step and log:
        t, qd, q, tau = np.array(log).T
        edges = np.flatnonzero(np.diff(qd) != 0) + 1
        # TODO 6: แต่ละ edge i: frac = (q[i:j] − q[i−1]) / (qd[i] − q[i−1])
        #         rise = เวลาจาก frac ≥ 0.1 ถึง frac ≥ 0.9 · overshoot = (max(frac) − 1)·100 · ค้างที่ frac[−1]
        # คำถาม: ทำไม step ขาลงไม่ถึง 100% (ใบ้: แรงโน้มถ่วง + frictionloss 0.2 กับ kp 14.3 → error ค้าง = ? rad)
        print(f"{len(edges)} edges")


if __name__ == "__main__":
    main()
