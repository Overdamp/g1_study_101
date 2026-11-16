"""hold_elbow_skeleton.py: ศอกซ้ายค้างที่มุมตอนเริ่ม ข้อต่ออื่น damping (งาน 2.4, 2.8)  ✅ ส่ง lowcmd (sim เท่านั้น)

ต่อยอดจาก damping: เพิ่ม "snapshot มุมศอกตอนเริ่ม" แล้วใช้ kp/kd ตอนเทรนกับศอกข้อเดียว
ทดลอง: ลากศอกแล้วปล่อย → ต้องกลับมาที่เดิม (คลาด < 2°)
ทายก่อน: ตอนปล่อยนิ่ง ศอกจะห่างจากเป้ากี่องศา และทำไมไม่เป็น 0  (pd_control.md: error = tau_gravity / kp)

รัน:  conda activate g1_sdk && python week2/scripts/skelatons/hold_elbow_skeleton.py
      python ... --break no_crc      (งาน 2.8 ก)
      python ... --break mode0       (งาน 2.8 ข)
"""

# TODO [2.4] imports เหมือน damping + argparse + math

DOMAIN = 1
IFACE = "lo"
CONTROL_DT = 0.002
NUM_MOTORS = 29
MODE_PR = 0
PRINT_PERIOD = 0.5

LEFT_ELBOW = 18
ELBOW_KP = None          # TODO [2.4] gain แขนตอนเทรน (BeyondMimic)
ELBOW_KD = None          # TODO [2.4]
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


def parse_args():
    # TODO [2.8] argparse: --break มีตัวเลือก "none" (ค่าเริ่มต้น), "no_crc", "mode0"
    return None


# TODO [2.4] class StateReader  (ก็อปจาก send_zero)


class HoldElbow:
    """เก็บเป้าหมายของศอก: จดครั้งเดียวตอนเริ่ม (เหมือน enter() ของ FSM สัปดาห์ 3)"""

    def __init__(self):
        self.q_target = None     # [rad] None = ยังไม่ได้จด

    def build_cmd(self, cmd, state, t, break_mode):
        # TODO [2.4] ครั้งแรกที่มี state: จด q_target = มุมศอกตอนนี้
        #            ทำไมไม่ตั้งเป้าเป็น 0 rad ไปเลย? (ทายว่าจะเกิดอะไรถ้าทำแบบนั้น แล้วค่อยลองใน 2.8 ง)
        # TODO [2.4] ทุก slot: damping แบบเดียวกับ damping_skeleton (q = มุมปัจจุบัน, kp 0, kd PASSIVE_KD)
        # TODO [2.4] เฉพาะ LEFT_ELBOW: q = q_target, kp = ELBOW_KP, kd = ELBOW_KD, dq = 0
        # TODO [2.8 ข] ถ้า break_mode == "mode0": ตั้ง mode ของศอกเป็น 0  (sim สนใจไหม? sim_vs_real.md)
        pass


def main():
    safety_guard(IFACE, DOMAIN)
    # TODO [2.4] args = parse_args()
    # TODO [2.4] โครงเหมือน send_zero แต่ใช้ HoldElbow().build_cmd(...)
    # TODO [2.8 ก] ถ้า args.break == "no_crc": ข้ามบรรทัดคำนวณ crc  (ใช้ watch_lowcmd ดูค่า crc ด้วย)
    # TODO [2.4] ทุก PRINT_PERIOD: พิมพ์ q_target, q ตอนนี้ (องศา) และ error = q_target − q (องศา)
    #            (print ใน loop 500 Hz ไม่ได้ ให้ใช้ตัวนับรอบ หรือเช็คเวลา)
    # TODO [2.8 ค] ระหว่างค้างอยู่ กด Ctrl+C → ดูแขนใน sim  ทายก่อนว่าจะห้อยลงหรือค้างอยู่
    print("hold_elbow: ยังไม่ได้เติม [2.4]")


if __name__ == "__main__":
    main()
