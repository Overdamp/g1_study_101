"""hold_elbow.py: ศอกซ้ายค้างที่มุมตอนเริ่ม ข้อต่ออื่น damping (งาน 2.4, 2.8)  ✅ ส่ง lowcmd (sim เท่านั้น)

ทดลอง: ลากศอกแล้วปล่อย → กลับมาที่เดิม (ไม่ถึงพอดี เพราะแรงโน้มถ่วง: error ≈ tau_gravity / kp)
--break สำหรับงาน 2.8:
  no_crc  ไม่คำนวณ CRC        → sim ยังทำตามไหม? (หุ่นจริงจะทิ้งข้อความ)
  mode0   mode ของศอก = 0      → sim ยังทำตามไหม? (หุ่นจริงมอเตอร์จะไม่ทำตาม)
  zero    เป้าหมาย = 0 rad ทันที แทนมุมปัจจุบัน → ดูการกระตุก (เทียบกับเริ่มจากมุมปัจจุบัน)
2.8 (ค): ระหว่างค้าง กด Ctrl+C แล้วดูแขน (โปรแกรมนี้ตั้งใจไม่ส่ง damping ก่อนออก เพื่อให้เห็นพฤติกรรมของ sim)

รัน:  conda activate g1_sdk && python week2/scripts/complete/hold_elbow.py [--kp 14.3 --kd 0.9] [--break none]
"""

import argparse
import math

from common import Every, LEFT_ELBOW, fill_damping, run_control_loop, set_header

ELBOW_KP = 14.3          # gain แขนตอนเทรน (BeyondMimic)
ELBOW_KD = 0.9
MAX_KP = 60.0


class HoldElbow:
    """จดเป้าหมายครั้งเดียวตอนได้ state แรก (เหมือน enter() ของ FSM) แล้วค้างไว้"""

    def __init__(self, kp: float, kd: float, break_mode: str):
        self.kp, self.kd, self.break_mode = kp, kd, break_mode
        self.q_target = None
        self.report = Every(0.5)

    def build_cmd(self, cmd, state, t):
        q_now = state.motor_state[LEFT_ELBOW].q
        if self.q_target is None:
            # ตั้งเป้า = มุมปัจจุบัน: ตอนเปิด kp แรงบิดเริ่มที่ ~0 ไม่กระตุก
            # ถ้าตั้ง 0 rad ทั้งที่ศอกอยู่ 1.2 rad → 14.3 × 1.2 ≈ 17 Nm ทันที (ลอง --break zero)
            self.q_target = 0.0 if self.break_mode == "zero" else q_now
            print(f"เริ่ม: ศอก {math.degrees(q_now):+.1f}°  เป้า {math.degrees(self.q_target):+.1f}°", flush=True)

        set_header(cmd, state)
        fill_damping(cmd, state)                     # ทุกข้อต่อหนืด แล้วค่อยเขียนทับเฉพาะศอก

        m = cmd.motor_cmd[LEFT_ELBOW]
        m.q = self.q_target
        m.dq = 0.0
        m.kp = self.kp
        m.kd = self.kd
        m.tau = 0.0
        m.mode = 0 if self.break_mode == "mode0" else 1

        if self.report(t):
            err = math.degrees(self.q_target - q_now)
            tau = state.motor_state[LEFT_ELBOW].tau_est
            print(f"t={t:5.1f}  เป้า {math.degrees(self.q_target):+6.1f}°  ตอนนี้ {math.degrees(q_now):+6.1f}°  "
                  f"error {err:+5.2f}°  tau_est {tau:+5.2f} Nm  (kp·error = {self.kp * (self.q_target - q_now):+5.2f})",
                  flush=True)


def main():
    parser = argparse.ArgumentParser(description="ค้างศอกซ้าย (sim)")
    parser.add_argument("--kp", type=float, default=ELBOW_KP)
    parser.add_argument("--kd", type=float, default=ELBOW_KD)
    parser.add_argument("--break", dest="break_mode", choices=("none", "no_crc", "mode0", "zero"), default="none")
    args = parser.parse_args()
    if not 0 <= args.kp <= MAX_KP or not 0 <= args.kd <= 5:
        raise SystemExit(f"kp ต้อง 0–{MAX_KP}, kd ต้อง 0–5")

    hold = HoldElbow(args.kp, args.kd, args.break_mode)
    print(f"hold_elbow: kp {args.kp} kd {args.kd} break={args.break_mode} (Ctrl+C เพื่อหยุด)")
    try:
        run_control_loop(hold.build_cmd, use_crc=(args.break_mode != "no_crc"))
    except KeyboardInterrupt:
        print("\nหยุดแล้ว: ไม่ได้ส่ง damping ก่อนออก → sim ใช้คำสั่งสุดท้าย (ศอกยังค้าง kp อยู่) ดูใน MuJoCo")


if __name__ == "__main__":
    main()
