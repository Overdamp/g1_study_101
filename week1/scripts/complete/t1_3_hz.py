"""t1_3_hz.py: นับข้อความต่อวินาที (Hz) พิมพ์ทุก 1 s (งาน 1.3)

แพทเทิร์นหลักของทั้งคอร์ส:
  callback (SDK thread)  → แค่ "เก็บ/นับ" ให้เร็วที่สุด ไม่ print
  main (main thread)     → ตื่นเป็นระยะ อ่านค่า แล้วค่อยทำงานช้า (คำนวณ, print)
ทั้งสองฝั่งแตะตัวแปรเดียวกัน จึงต้องใช้ Lock (อ่าน docs/threading_and_lock.md)

ผลที่วัดได้ใน sim: ~905 Hz (sim ตั้งไว้ 1000 Hz แต่ทุกรอบ "ทำงาน แล้วนอน 1 ms")
รัน:  conda activate g1_sdk && python week1/scripts/complete/t1_3_hz.py
"""

import threading
import time

from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_


class LowStateCounter:
    """ตัวนับที่ทั้ง callback และ main ใช้ร่วมกัน"""

    def __init__(self):
        self.count = 0                  # จำนวนข้อความตั้งแต่รีเซ็ตครั้งล่าสุด
        self.lock = threading.Lock()    # กุญแจดอกเดียว: ถือได้ทีละ thread

    def handler(self, msg: LowState_):
        with self.lock:                 # จองก่อนแก้ ถ้า main ถืออยู่ต้องรอ
            self.count += 1             # self.count (ถ้าเขียน count เฉยๆ → UnboundLocalError)


def main():
    ChannelFactoryInitialize(1, "lo")
    counter = LowStateCounter()
    sub = ChannelSubscriber("rt/lowstate", LowState_)
    sub.Init(counter.handler, 10)       # ส่ง method ของ object

    t_last = time.monotonic()           # นาฬิกาที่เดินหน้าอย่างเดียว เหมาะกับการวัดช่วงเวลา
    while True:
        time.sleep(1)                   # ไม่ได้ 1.000 s พอดี จึงต้องวัด dt จริงข้างล่าง

        with counter.lock:              # "อ่าน + รีเซ็ต" เป็นขั้นตอนเดียว callback แทรกไม่ได้
            n = counter.count
            counter.count = 0
        # ออกจาก lock แล้ว: งานที่ช้ากว่าทำข้างนอก callback นับต่อได้ทันที

        now = time.monotonic()
        dt = now - t_last
        t_last = now
        print(f"{n / dt:7.1f} Hz  ({n} msgs in {dt:.3f} s)", flush=True)
        # 0.0 Hz → sim ไม่ได้เปิด / domain / multicast (docs/debug_checklist.md)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
