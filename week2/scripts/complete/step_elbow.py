"""step_elbow.py: step ศอกซ้าย +amp แล้วบันทึกการตอบสนองลง CSV (งาน 2.5–2.6)  ✅ ส่ง lowcmd (sim เท่านั้น)

ตารางเวลา:
    0 ─ 2 s   : ค้างที่มุมเริ่ม q0           (ให้นิ่งก่อน)
    2 ─ 5 s   : เป้า = q0 + amp  (กระโดดทันที = step)
    5 ─ 7 s   : เป้า = q0 อีกครั้ง (step กลับ)
    7 ─ 8 s   : damping ทุกข้อต่อ แล้วจบ + เซฟ CSV
บันทึกทุกรอบ (500 Hz): t, q_des, q, dq, tau_est, kp, kd ของศอก

งาน 2.6 (รันทีละครั้ง ทายก่อนทุกครั้ง):
    python step_elbow.py --kp 5    --kd 0.3 --out step_kp5.csv
    python step_elbow.py --kp 14.3 --kd 0.9 --out step_kp14.csv
    python step_elbow.py --kp 40   --kd 2.5 --out step_kp40.csv
    python step_elbow.py --kp 14.3 --kd 0   --out step_kd0.csv
แล้ววิเคราะห์ด้วย analyze_step.py

รัน:  conda activate g1_sdk && python week2/scripts/complete/step_elbow.py --kp 14.3 --kd 0.9 --amp-deg 30 --out step_kp14.csv
"""

import argparse
import csv
import math

from common import LEFT_ELBOW, fill_damping, run_control_loop, set_header

SETTLE_S = 2.0
HOLD_S = 3.0
RETURN_S = 2.0
DAMP_S = 1.0
MAX_AMP_DEG = 45.0
MAX_KP = 60.0
MAX_KD = 5.0


def check_limits(amp_deg: float, kp: float, kd: float) -> None:
    if abs(amp_deg) > MAX_AMP_DEG or not 0 <= kp <= MAX_KP or not 0 <= kd <= MAX_KD:
        raise SystemExit(f"[safety] amp {amp_deg}° (≤{MAX_AMP_DEG}), kp {kp} (≤{MAX_KP}), kd {kd} (≤{MAX_KD})")


class StepElbow:
    def __init__(self, kp: float, kd: float, amp_rad: float):
        self.kp, self.kd, self.amp = kp, kd, amp_rad
        self.q0 = None
        self.rows = []
        self.announced = set()       # phase ที่ print ไปแล้ว

    def target(self, t: float):
        """เป้าหมายของศอก ณ เวลา t ถ้าจบช่วง step แล้วคืน None"""
        if t < SETTLE_S:
            return self.q0
        if t < SETTLE_S + HOLD_S:
            return self.q0 + self.amp
        if t < SETTLE_S + HOLD_S + RETURN_S:
            return self.q0
        return None

    def build_cmd(self, cmd, state, t):
        s = state.motor_state[LEFT_ELBOW]
        if self.q0 is None:
            self.q0 = s.q
            print(f"q0 = {math.degrees(self.q0):+.1f}°  เป้า step = {math.degrees(self.q0 + self.amp):+.1f}°", flush=True)

        set_header(cmd, state)
        fill_damping(cmd, state)

        q_des = self.target(t)
        if q_des is None:
            # ช่วงท้าย: damping ล้วน (ไม่ทิ้งศอกไว้กับ kp) แล้วจบ
            if self._announce("damping"):
                print("จบการทดสอบ → damping 1 s", flush=True)
            return t < SETTLE_S + HOLD_S + RETURN_S + DAMP_S      # False = หยุด loop

        m = cmd.motor_cmd[LEFT_ELBOW]
        m.q = q_des
        m.dq = 0.0
        m.kp = self.kp
        m.kd = self.kd
        m.tau = 0.0
        # q_des คือค่าที่ "ส่งรอบนี้" ส่วน q/dq/tau_est มาจาก LowState ล่าสุด (เก่ากว่าเล็กน้อย ≤ ~1–2 ms)
        self.rows.append((t, q_des, s.q, s.dq, s.tau_est, self.kp, self.kd))

        if t >= SETTLE_S and self._announce("step"):
            print("step!", flush=True)
        if t >= SETTLE_S + HOLD_S and self._announce("return"):
            print("กลับ q0", flush=True)
        return True

    def _announce(self, phase: str) -> bool:
        """คืน True ครั้งแรกที่เข้า phase นี้ (ไว้ print ครั้งเดียว)"""
        if phase in self.announced:
            return False
        self.announced.add(phase)
        return True

    def save(self, path: str) -> None:
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["t", "q_des", "q", "dq", "tau_est", "kp", "kd"])
            w.writerows(self.rows)
        print(f"เซฟ {len(self.rows)} แถว → {path}")


def main():
    parser = argparse.ArgumentParser(description="step ศอกซ้าย + บันทึก CSV (sim)")
    parser.add_argument("--kp", type=float, default=14.3)
    parser.add_argument("--kd", type=float, default=0.9)
    parser.add_argument("--amp-deg", type=float, default=30.0)
    parser.add_argument("--out", default="step.csv")
    args = parser.parse_args()
    check_limits(args.amp_deg, args.kp, args.kd)

    test = StepElbow(args.kp, args.kd, math.radians(args.amp_deg))
    print(f"step_elbow: kp {args.kp} kd {args.kd} amp {args.amp_deg}° → {args.out}")
    try:
        run_control_loop(test.build_cmd)
    except KeyboardInterrupt:
        print("\nหยุดกลางทาง (Ctrl+C): เซฟเท่าที่เก็บได้ ⚠️ ศอกอาจยังค้าง kp อยู่ใน sim รัน damping.py ถ้าต้องการปล่อย")
    finally:
        test.save(args.out)                          # เซฟเสมอ แม้หยุดกลางทาง


if __name__ == "__main__":
    main()
