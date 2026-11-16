"""t1_4_elbow.py: พิมพ์มุมศอกซ้าย (slot 18) เป็นองศา + Hz ทุก 1 s (งาน 1.4)

ต่อยอดจาก t1_3: callback เก็บ "มุมล่าสุด" เพิ่มจากตัวนับ
ทดลอง: ใน MuJoCo ดับเบิลคลิกแขนท่อนล่าง แล้ว Ctrl + คลิกขวาค้างลาก ดูตัวเลขเปลี่ยน
ผลที่วัดได้: ห้อยนิ่ง ≈ +69.3° (ไม่มีใครคุม ข้อต่อหยุดที่ friction ชนะแรงโน้มถ่วง)

รัน:  conda activate g1_sdk && python week1/scripts/complete/t1_4_elbow.py
"""

import math
import threading
import time

from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_

LEFT_ELBOW = 18          # ค่าคงที่แทนเลขลอยๆ · ศอกขวา = 25


class LowStateReader:
    def __init__(self):
        self.count = 0
        self.elbow_q = None              # None = ยังไม่มีข้อมูล (ถ้าใช้ 0 จะแยกไม่ออกว่า "มุม 0°" หรือ "ยังไม่มี")
        self.lock = threading.Lock()

    def handler(self, msg: LowState_):
        with self.lock:
            self.count += 1
            # motor_state = list 35 ช่องของ MotorState_ · .q = มุม [rad]
            self.elbow_q = msg.motor_state[LEFT_ELBOW].q


def main():
    ChannelFactoryInitialize(1, "lo")
    reader = LowStateReader()
    sub = ChannelSubscriber("rt/lowstate", LowState_)
    sub.Init(reader.handler, 10)

    t_last = time.monotonic()
    while True:
        time.sleep(1)
        with reader.lock:
            n = reader.count
            reader.count = 0
            q = reader.elbow_q              # สำเนาเป็นของ main แล้ว callback เขียนทับไม่ได้

        now = time.monotonic()
        hz = n / (now - t_last)
        t_last = now

        if q is None:
            print(f"{hz:6.1f} Hz  (no LowState yet)", flush=True)   # math.degrees(None) → TypeError
        else:
            print(f"{hz:6.1f} Hz  elbow_L = {math.degrees(q):+6.1f} deg", flush=True)   # :+ = แสดงเครื่องหมายเสมอ


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
