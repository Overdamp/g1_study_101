"""damping.py: ทุกข้อต่อ kp = 0, kd = kd ของ Passive × scale (งาน 2.3)  ✅ ส่ง lowcmd (sim เท่านั้น)

= State_Passive ของ g1_ctrl ลากแขนใน MuJoCo แล้วรู้สึก "หนืด":
  ลากช้า → dq เล็ก → แรงต้าน kd·dq เล็ก → ลากง่าย
  ลากเร็ว → dq ใหญ่ → แรงต้านใหญ่ → ลากยาก
ปล่อยมือแล้วแขนยังห้อยลงช้าๆ เพราะไม่มีสปริง (kp = 0) ดึงกลับที่ไหน

รัน:  conda activate g1_sdk && python week2/scripts/complete/damping.py [--kd-scale 1.0]
      ลอง --kd-scale 0.2 และ 3.0 เทียบความรู้สึกตอนลาก
"""

import argparse

from common import Every, LEFT_ELBOW, PASSIVE_KD, fill_damping, run_control_loop, set_header


def main():
    parser = argparse.ArgumentParser(description="damping ทุกข้อต่อ (sim)")
    parser.add_argument("--kd-scale", type=float, default=1.0, help="คูณ kd ของ Passive (0–3)")
    args = parser.parse_args()
    if not 0.0 <= args.kd_scale <= 3.0:
        raise SystemExit("--kd-scale ต้องอยู่ในช่วง 0–3")

    report = Every(1.0)

    def build_cmd(cmd, state, t):
        set_header(cmd, state)
        fill_damping(cmd, state, args.kd_scale)
        if report(t):
            s = state.motor_state[LEFT_ELBOW]
            print(f"t={t:5.1f}  ศอกซ้าย q {s.q:+.3f} dq {s.dq:+6.2f} rad/s  "
                  f"kd {PASSIVE_KD[LEFT_ELBOW] * args.kd_scale:.2f}  แรงต้าน ≈ {-PASSIVE_KD[LEFT_ELBOW] * args.kd_scale * s.dq:+.2f} Nm",
                  flush=True)

    print(f"damping: kd × {args.kd_scale} (Ctrl+C เพื่อหยุด)")
    try:
        run_control_loop(build_cmd)
    except KeyboardInterrupt:
        print("\nหยุดแล้ว: sim ใช้คำสั่ง damping สุดท้ายต่อไป (ยังหนืดอยู่จนกว่าจะมีคำสั่งใหม่)")


if __name__ == "__main__":
    main()
