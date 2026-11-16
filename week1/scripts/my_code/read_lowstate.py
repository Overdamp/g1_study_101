import threading   # Lock: กันสอง thread (SDK กับ main) แย่งใช้ตัวแปรเดียวกัน
import time        # sleep และวัดเวลาจริง

from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
# G1 ใช้ message ชุด unitree_hg (ถ้าใช้ unitree_go จะไม่ได้ข้อมูลและไม่มี error)
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_

# ---------------------------------------------------------------------------
# slot map: slot ใน msg.motor_state -> ชื่อข้อต่อ
# ใช้ dict เพราะ slot ไม่ต่อเนื่อง: 13, 14, 20, 21, 27, 28 ไม่มีข้อต่อบน 23-DoF
# (เป็นช่องของเอว roll/pitch และข้อมือ pitch/yaw ซึ่งมีแค่บน 29-DoF)
# วน loop ตาม dict นี้ = ได้ครบ 23 ข้อต่อพอดี และข้ามช่องว่างไปเองโดยไม่ต้องเขียน if
# ---------------------------------------------------------------------------
G1_23DOF_JOINTS = {
    0: "left_hip_pitch_joint",
    1: "left_hip_roll_joint",
    2: "left_hip_yaw_joint",
    3: "left_knee_joint",
    4: "left_ankle_pitch_joint",
    5: "left_ankle_roll_joint",
    6: "right_hip_pitch_joint",
    7: "right_hip_roll_joint",
    8: "right_hip_yaw_joint",
    9: "right_knee_joint",
    10: "right_ankle_pitch_joint",
    11: "right_ankle_roll_joint",
    12: "waist_yaw_joint",
    15: "left_shoulder_pitch_joint",
    16: "left_shoulder_roll_joint",
    17: "left_shoulder_yaw_joint",
    18: "left_elbow_joint",          # งาน 1.4
    19: "left_wrist_roll_joint",
    22: "right_shoulder_pitch_joint",
    23: "right_shoulder_roll_joint",
    24: "right_shoulder_yaw_joint",
    25: "right_elbow_joint",
    26: "right_wrist_roll_joint",
}

PRINT_PERIOD = 0.5   # [s] อัพเดทตารางทุก 0.5 s (2 ครั้ง/วินาที) ไม่ใช่ทุกข้อความ (~905 ครั้ง/วินาที)


class LowStateReader:
    """ข้อมูลที่ callback (SDK thread) กับ main (main thread) ใช้ร่วมกัน"""

    def __init__(self):
        self.count = 0                 # จำนวนข้อความตั้งแต่รีเซ็ตครั้งล่าสุด ใช้คำนวณ Hz
        self.latest = None             # LowState ล่าสุดทั้งก้อน ถ้าเป็น None = ยังไม่เคยได้ข้อความ
        self.lock = threading.Lock()

    def handler(self, msg: LowState_):
        # เรียก ~905 ครั้ง/วินาที จาก thread ของ SDK ต้องเร็วที่สุด
        # เปลี่ยนจาก 1.4: เก็บ "ทั้งก้อน" แทนที่จะแกะค่าทีละตัว
        #   - ถ้าแกะใน handler: 23 ข้อต่อ × 3 ค่า × 905 ครั้ง = ~62,000 การอ่าน/วินาที แต่ใช้จริงแค่ 2 ครั้ง
        #   - ถ้าเก็บทั้งก้อน: ทำแค่ 1 การ assign (เก็บ reference) ส่วน main ค่อยแกะตอนที่จะใช้จริง
        # เก็บ reference ได้อย่างปลอดภัย เพราะ SDK สร้าง object msg ใหม่ทุกครั้ง ไม่ได้เขียนทับตัวเดิม
        # (ตัวอย่าง g1_low_level_example.py ก็ใช้วิธีนี้: self.low_state = msg)
        with self.lock:
            self.count += 1
            self.latest = msg


def format_table(msg: LowState_, hz: float) -> str:
    """สร้างตารางเป็น string ก้อนเดียว (แยกออกมาจาก main ให้อ่านง่ายและเอาไปใช้ซ้ำได้)"""
    lines = []
    lines.append(f"LowState {hz:6.1f} Hz")
    # จัดคอลัมน์ใน f-string:  :>4  = ชิดขวา กว้าง 4   :<28 = ชิดซ้าย กว้าง 28
    #                         :+8.3f = กว้าง 8 ทศนิยม 3 แสดงเครื่องหมาย +/− เสมอ (ทำให้เลขตรงแนว)
    lines.append(f"{'slot':>4}  {'joint':<28} {'q[rad]':>8} {'dq[rad/s]':>10} {'temp':>5}")
    lines.append("-" * 60)

    for slot, name in G1_23DOF_JOINTS.items():   # .items() ได้คู่ (key, value) = (slot, ชื่อ)
        m = msg.motor_state[slot]                # MotorState_ ของมอเตอร์ช่องนั้น
        # temperature เป็น array 2 ค่า (int16[2]) ใน IDL ไม่ได้บอกว่าแต่ละช่องคืออะไร
        # บนหุ่นจริงมักใช้ [0] เป็นอุณหภูมิหลัก ใน sim จะเป็น 0 ทั้งคู่ (MuJoCo ไม่ได้จำลองความร้อน)
        lines.append(
            f"{slot:>4}  {name:<28} {m.q:+8.3f} {m.dq:+10.3f} {m.temperature[0]:>5}"
        )
    return "\n".join(lines)                       # รวมทุกบรรทัดเป็น string เดียว คั่นด้วยขึ้นบรรทัดใหม่


def main():
    ChannelFactoryInitialize(1, "lo")             # domain 1 บน lo = sim  (หุ่นจริง: 0, "enp43s0")

    reader = LowStateReader()
    sub = ChannelSubscriber("rt/lowstate", LowState_)
    sub.Init(reader.handler, 10)                  # ฝาก callback (ไม่มีวงเล็บ) คิว 10 = เรียกจาก thread แยก

    t_last = time.monotonic()
    while True:
        time.sleep(PRINT_PERIOD)                  # จุดเดียวที่เปลี่ยนจาก 1 s เป็น 0.5 s

        # ใน lock: หยิบของออกมาให้เร็วที่สุด แล้วออกทันที
        with reader.lock:
            n = reader.count
            reader.count = 0
            msg = reader.latest

        # นอก lock: งานหนักทั้งหมด (คำนวณ จัดรูปแบบ print)
        now = time.monotonic()
        dt = now - t_last
        t_last = now
        hz = n / dt                               # ยังถูกต้อง เพราะหารด้วย dt จริง (~0.5 s) ไม่ใช่ 1 คงที่

        if msg is None:
            print(f"{hz:.1f} Hz  (no LowState yet: sim เปิดไหม / domain / multicast?)")
            continue                              # ข้ามไปรอบถัดไป ไม่พยายามสร้างตาราง

        # \033[H\033[2J = ANSI escape: เลื่อน cursor ไปมุมบนซ้าย แล้วล้างจอ
        # ทำให้ตารางวาดทับที่เดิม ไม่เลื่อนยาวลงไปเรื่อยๆ
        print("\033[H\033[2J" + format_table(msg, hz), flush=True)


if __name__ == "__main__":
    main()