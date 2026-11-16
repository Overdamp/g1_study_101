"""t1_2_hello.py: พิมพ์ทุกครั้งที่ได้ LowState (งาน 1.2)

subscriber ที่เล็กที่สุด มี 4 ขั้น:
  1. เข้า DDS (domain + interface)
  2. สร้าง subscriber (ชื่อ topic + type)
  3. ฝาก callback
  4. ทำให้ main ไม่จบ

⚠️ ข้อความจะไหลรัวมาก (~900 บรรทัดต่อวินาที) เพราะ print ทุกข้อความ งาน 1.3 จะแก้ปัญหานี้
รัน:  conda activate g1_sdk && python week1/scripts/complete/t1_2_hello.py   (Ctrl+C เพื่อหยุด)
"""

import time

from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_    # G1 = ชุด hg (ใช้ go จะเงียบไม่มี error)


def on_lowstate(msg: LowState_):
    # SDK เรียกฟังก์ชันนี้ทุกครั้งที่มีข้อความ จาก thread ของ SDK เอง (ไม่ใช่ thread ของ main)
    print("ได้ข้อความแล้ว")


def main():
    ChannelFactoryInitialize(1, "lo")                      # ขั้น 1: sim = domain 1 บน lo (หุ่นจริง: 0, "enp43s0")
    sub = ChannelSubscriber("rt/lowstate", LowState_)      # ขั้น 2: ชื่อ + type ต้องตรงกับฝั่งที่ส่ง
    sub.Init(on_lowstate, 10)                              # ขั้น 3: ส่งตัวฟังก์ชัน (ไม่มีวงเล็บ), คิว 10 = เรียกจาก thread แยก
    while True:                                            # ขั้น 4: ถ้า main จบ โปรแกรมปิด callback ไม่ทันทำงาน
        time.sleep(1)                                      # `sub` ต้องยังอยู่ (ถ้าถูกเก็บกวาด การรับจะหยุด)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
