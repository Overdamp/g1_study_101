"""t1_5_table.py: ตาราง 23 ข้อต่อ (ชื่อ, q, dq, อุณหภูมิ) อัพเดททุก 0.5 s (งาน 1.5)

เปลี่ยนจาก t1_4:
  - callback เก็บ "ทั้งก้อน msg" แทนค่าเดียว (เร็วกว่าแกะ 23×3 ค่า ~900 ครั้ง/วินาที ทั้งที่ใช้แค่ 2 ครั้ง)
  - dict slot → ชื่อ แล้ววน .items() ได้ครบ 23 ข้อต่อพอดี ข้าม slot ว่าง (13,14,20,21,27,28) ไปเอง
  - วาดตารางทับที่เดิมด้วย ANSI escape
ทดลอง: ลากแขน/ขาใน MuJoCo ดูว่าแถวที่ถูกต้องเปลี่ยน

รัน:  conda activate g1_sdk && python week1/scripts/complete/t1_5_table.py
"""

import threading
import time

from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_

# slot ใน msg.motor_state → ชื่อข้อต่อ (vault: Joint Map and Slots.md)
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
    18: "left_elbow_joint",
    19: "left_wrist_roll_joint",
    22: "right_shoulder_pitch_joint",
    23: "right_shoulder_roll_joint",
    24: "right_shoulder_yaw_joint",
    25: "right_elbow_joint",
    26: "right_wrist_roll_joint",
}
PRINT_PERIOD = 0.5       # [s]
CLEAR = "\033[H\033[2J"  # ANSI: cursor ไปมุมบนซ้าย + ล้างจอ → วาดทับที่เดิม


class LowStateReader:
    def __init__(self):
        self.count = 0
        self.latest = None
        self.lock = threading.Lock()

    def handler(self, msg: LowState_):
        # เก็บ reference ของทั้งก้อน: ปลอดภัยเพราะ SDK สร้าง msg ใหม่ทุกครั้ง ไม่เขียนทับตัวเดิม
        with self.lock:
            self.count += 1
            self.latest = msg


def format_table(msg: LowState_, hz: float) -> str:
    lines = [
        f"LowState {hz:6.1f} Hz",
        f"{'slot':>4}  {'joint':<28} {'q[rad]':>8} {'dq[rad/s]':>10} {'temp':>5}",
        "-" * 60,
    ]
    for slot, name in G1_23DOF_JOINTS.items():
        m = msg.motor_state[slot]
        # temperature เป็น array 2 ค่า (int16[2]) แสดงตัวแรก · ใน sim = 0 (ไม่จำลองความร้อน)
        lines.append(f"{slot:>4}  {name:<28} {m.q:+8.3f} {m.dq:+10.3f} {m.temperature[0]:>5}")
    return "\n".join(lines)


def main():
    ChannelFactoryInitialize(1, "lo")
    reader = LowStateReader()
    sub = ChannelSubscriber("rt/lowstate", LowState_)
    sub.Init(reader.handler, 10)

    t_last = time.monotonic()
    while True:
        time.sleep(PRINT_PERIOD)
        with reader.lock:
            n = reader.count
            reader.count = 0
            msg = reader.latest
        now = time.monotonic()
        hz = n / (now - t_last)             # ยังถูกต้องเพราะหารด้วย dt จริง (~0.5 s)
        t_last = now

        if msg is None:
            print(f"{hz:.1f} Hz  (no LowState yet: sim / domain / multicast?)", flush=True)
            continue
        print(CLEAR + format_table(msg, hz), flush=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
