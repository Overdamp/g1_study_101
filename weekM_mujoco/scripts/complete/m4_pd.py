"""m4_pd.py: เขียน PD เองใน MuJoCo = bridge ของ unitree_mujoco ฉบับย่อ (งาน M4) ฉบับสมบูรณ์

รัน:  python3 m4_pd.py                                  (ห้อย + PD ค้างท่า default ของ policy)
      python3 m4_pd.py --drop 3                         (ปิดหนังยางที่ t = 3 s → ยืนเองได้ไหม?)
      python3 m4_pd.py --elbow-step --headless          (step ศอกซ้าย ±0.3 rad แบบสัปดาห์ 2 + วัด rise time)
      python3 m4_pd.py --elbow-step --headless --kd-scale 0     (ตัด D ทิ้ง)

สิ่งที่ฝึก: ctrl = แรงบิด (motor actuator) · PD คำนวณทุก physics step (500 Hz) แบบ bridge · ctrlrange clamp
"""

import argparse

import numpy as np

from g1mj import ElasticBand, load, load_deploy, motor_q, motor_tau, pd_ctrl, run, set_pose

SLOT = 18                 # ศอกซ้าย
AMP, PERIOD = 0.3, 2.0    # step ±0.3 rad สลับทุก 1 s (แบบ step_elbow สัปดาห์ 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--duration", type=float, default=None)
    ap.add_argument("--drop", type=float, default=None, help="ปิดหนังยางที่เวลานี้ [s]")
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
    set_pose(m, d, dep.q_default, base_z=1.0)        # เริ่มในท่า default จะได้ไม่กระชาก
    band = ElasticBand()
    log = []                                          # (t, q_des, q, tau) ของศอก

    def step_fn(m, d):
        if args.drop is not None and band.enable and d.time >= args.drop:
            band.enable = False
            print(f"[t={d.time:.2f}] ปิดหนังยาง", flush=True)
        band.apply(m, d)
        if args.elbow_step:
            sign = 1.0 if (d.time % PERIOD) < PERIOD / 2 else -1.0
            q_des[SLOT] = dep.q_default[SLOT] + sign * AMP
        d.ctrl[:] = pd_ctrl(m, d, q_des, kp, kd)      # bridge: ctrl = tau + kp(q_des − q) + kd(dq_des − dq)
        log.append((d.time, q_des[SLOT], motor_q(m, d)[SLOT], d.ctrl[SLOT]))

    def report(m, d):
        err = np.abs(motor_q(m, d) - q_des)[dep.ids]
        tilt = np.degrees(np.arccos(np.clip(d.body("pelvis").xmat[8], -1, 1)))   # มุมแกน z ลำตัวกับแนวดิ่ง
        print(f"t={d.time:5.2f}  pelvis z={d.qpos[2]:.3f}  เอียง {tilt:5.1f}°  |q−q_des| max {np.degrees(err.max()):5.2f}°  "
              f"ศอก q_des {q_des[SLOT]:+.2f} q {motor_q(m, d)[SLOT]:+.3f}  tau {motor_tau(m, d)[SLOT]:+6.2f} Nm", flush=True)

    run(m, d, step_fn, duration=args.duration, headless=args.headless,
        key_callback=band.key, every=0.5, every_fn=report)

    if args.elbow_step and log:
        analyze(np.array(log), kp[SLOT], kd[SLOT], m.actuator_ctrlrange[SLOT])


def analyze(log, kp, kd, ctrlrange) -> None:
    """วัดแต่ละ step: rise time 10→90%, overshoot  (วิธีเดียวกับ analyze_step.py สัปดาห์ 2)"""
    t, qd, q, tau = log.T
    edges = np.flatnonzero(np.diff(qd) != 0) + 1
    print(f"\n== step ศอกซ้าย kp {kp:.1f} kd {kd:.2f}  (ctrlrange {ctrlrange})")
    for k, i in enumerate(edges):
        j = edges[k + 1] if k + 1 < len(edges) else len(t)
        q0, q1 = q[i - 1], qd[i]
        frac = (q[i:j] - q0) / (q1 - q0)                       # 0 → 1
        try:
            t10 = t[i + np.argmax(frac >= 0.1)]
            t90 = t[i + np.argmax(frac >= 0.9)]
            rise = (t90 - t10) * 1e3 if frac.max() >= 0.9 else float("nan")
        except ValueError:
            rise = float("nan")
        over = (frac.max() - 1) * 100
        sat = np.mean(np.abs(tau[i:j]) >= ctrlrange[1] - 1e-6) * 100
        print(f"  step {k + 1} @ {t[i]:.2f}s  {q0:+.3f}→{q1:+.3f}  rise {rise:6.1f} ms  overshoot {over:+5.1f}%  "
              f"ค้างที่ {frac[-1] * 100:5.1f}%  tau ชนลิมิต {sat:.0f}% ของเวลา")


if __name__ == "__main__":
    main()
