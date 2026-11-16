"""step_elbow_skeleton.py: step ศอกซ้าย +amp แล้วบันทึกการตอบสนองลง CSV (งาน 2.5–2.6)  ✅ ส่ง lowcmd (sim เท่านั้น)

ต่อยอดจาก hold_elbow: เป้าหมายเปลี่ยนตามเวลา
    0 ─ SETTLE s     : ค้างที่มุมเริ่ม (q0)
    SETTLE ─ +HOLD s : เป้า = q0 + amp   (กระโดดทันที = step)
    หลังจากนั้น      : เป้า = q0 อีกครั้ง แล้วจบ (ส่ง damping ต่อ 1 s ก่อนออก)
ระหว่างนั้นบันทึก t, q_des, q, dq, tau_est, kp, kd ของศอกทุกรอบ

งาน 2.6: รันหลายครั้งด้วย kp ต่างกัน
    python ... --kp 5    --kd 0.3  --out step_kp5.csv
    python ... --kp 14.3 --kd 0.9  --out step_kp14.csv
    python ... --kp 40   --kd 2.5  --out step_kp40.csv
    python ... --kp 14.3 --kd 0    --out step_kd0.csv
ทายก่อนทุกครั้ง: rise time / overshoot จะเป็นยังไงเมื่อเทียบกับ kp 14.3
รัน:  conda activate g1_sdk && python week2/scripts/skelatons/step_elbow_skeleton.py --kp 14.3 --kd 0.9 --out step_kp14.csv
"""

# TODO [2.5] imports เหมือน hold_elbow + argparse + csv + math

DOMAIN = 1
IFACE = "lo"
CONTROL_DT = 0.002
NUM_MOTORS = 29
MODE_PR = 0
LEFT_ELBOW = 18
SETTLE_S = 2.0
HOLD_S = 3.0

# ขีดจำกัดของแบบฝึกหัด: เขียนไว้ให้แล้ว (กันพิมพ์ผิดแล้วแขนเหวี่ยงแรง)
MAX_AMP_DEG = 45.0
MAX_KP = 60.0
MAX_KD = 5.0
PASSIVE_KD = [
    4.0, 4.0, 4.0, 6.0, 2.5, 2.5,
    4.0, 4.0, 4.0, 6.0, 2.5, 2.5,
    4.5, 4.5, 4.5,
    2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5,
    2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5,
]


def safety_guard(iface: str, domain: int) -> None:
    """เขียนไว้ให้แล้ว ห้ามลบ ห้ามแก้"""
    if iface != "lo" or domain != 1:
        raise SystemExit(f"[safety] iface={iface!r} domain={domain}: แบบฝึกหัดนี้ใช้ได้กับ sim (lo, domain 1) เท่านั้น")


def check_limits(amp_deg: float, kp: float, kd: float) -> None:
    """เขียนไว้ให้แล้ว: ปฏิเสธค่าที่เกินขีดจำกัดของแบบฝึกหัด"""
    if abs(amp_deg) > MAX_AMP_DEG or not 0 <= kp <= MAX_KP or not 0 <= kd <= MAX_KD:
        raise SystemExit(f"[safety] amp {amp_deg}° (≤{MAX_AMP_DEG}), kp {kp} (≤{MAX_KP}), kd {kd} (≤{MAX_KD})")


def parse_args():
    # TODO [2.5] argparse: --kp (14.3), --kd (0.9), --amp-deg (30), --out (step.csv)
    return None


# TODO [2.5] class StateReader  (ก็อปจาก send_zero)


class StepElbow:
    def __init__(self, kp, kd, amp_rad):
        self.kp, self.kd, self.amp = kp, kd, amp_rad
        self.q0 = None
        self.rows = []           # แต่ละแถว: (t, q_des, q, dq, tau_est, kp, kd)

    def target(self, t):
        """เป้าหมายของศอก ณ เวลา t  (คืน None เมื่อจบการทดสอบแล้ว)"""
        # TODO [2.5] ตามตารางเวลาใน docstring ด้านบน
        return None

    def build_cmd(self, cmd, state, t):
        # TODO [2.5] ครั้งแรก: จด q0
        # TODO [2.5] ทุก slot damping (เหมือน hold_elbow) ยกเว้นศอก: q = target(t), kp, kd
        # TODO [2.5] เก็บแถวลง self.rows  (tau_est อยู่ใน motor_state[...] field ไหน? ดู _MotorState_.py)
        # คำถาม: q_des ที่บันทึก ควรเป็นค่าที่ "ส่งรอบนี้" ใช่ไหม แล้ว q ที่บันทึกเป็นของรอบไหน
        pass

    def save(self, path):
        # TODO [2.5] เขียน CSV มี header: t,q_des,q,dq,tau_est,kp,kd
        pass


def main():
    safety_guard(IFACE, DOMAIN)
    # TODO [2.5] args = parse_args();  check_limits(args.amp_deg, args.kp, args.kd)
    # TODO [2.5] โครง loop เหมือน send_zero ใช้ StepElbow.build_cmd
    # TODO [2.5] เมื่อ target(t) เป็น None: ส่ง damping ต่ออีก 1 s แล้ว save() แล้วจบ
    # TODO [2.5] ถ้ากด Ctrl+C กลางทาง: ยัง save() สิ่งที่เก็บได้ (try / finally)
    print("step_elbow: ยังไม่ได้เติม [2.5]")


if __name__ == "__main__":
    main()
