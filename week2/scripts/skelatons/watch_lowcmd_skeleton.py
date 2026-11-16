"""watch_lowcmd_skeleton.py: ฟัง rt/lowcmd แล้วพิมพ์สรุป (งาน 2.2, 2.8)  ❌ ไม่ส่งอะไร

ใช้คู่กับไฟล์ที่ส่งคำสั่ง เพื่อพิสูจน์ว่าคำสั่งออกไปจริง ถี่แค่ไหน ค่าถูกไหม
โครงเดียวกับ read_lowstate.py สัปดาห์ 1 เปลี่ยนแค่ topic และ type

รัน:  conda activate g1_sdk && python week2/scripts/skelatons/watch_lowcmd_skeleton.py
"""

# ---------------------------------------------------------------------------
# imports
# ---------------------------------------------------------------------------
# TODO [2.2] ตัวเริ่ม DDS + ตัว subscribe  (เหมือนสัปดาห์ 1)
# TODO [2.2] type ของ LowCmd สำหรับ G1  (ชุดเดียวกับ LowState_)
# TODO [2.2] threading, time

DOMAIN = 1
IFACE = "lo"
WATCH_SLOT = 18          # ศอกซ้าย
PRINT_PERIOD = 1.0       # [s]


class LowCmdWatcher:
    """เก็บ LowCmd ล่าสุด + นับจำนวน (แพทเทิร์นเดียวกับ LowStateReader สัปดาห์ 1)"""

    def __init__(self):
        # TODO [2.2] self.count, self.latest (None), self.lock
        pass

    def handler(self, msg):
        # TODO [2.2] ใน lock: นับ + เก็บ msg ล่าสุด  (ห้าม print ที่นี่)
        pass


def summarize(msg, hz):
    """คืน string สรุป 1 บรรทัด"""
    # TODO [2.2] Hz, mode_machine, mode_pr
    # TODO [2.2] ของ WATCH_SLOT: mode, q (เป็นองศาด้วย), kp, kd, tau
    # TODO [2.8] crc ของข้อความ (ดูว่าเปลี่ยนทุกครั้งไหม / เป็น 0 ไหมตอนลืมคำนวณ)
    # คำถาม: ถ้าเห็น kp ของทุก slot เป็น 0 แปลว่าโปรแกรมฝั่งส่งอยู่ในโหมดไหน
    return ""


def main():
    # TODO [2.2] เริ่ม DDS (DOMAIN, IFACE)
    watcher = LowCmdWatcher()
    # TODO [2.2] subscribe "rt/lowcmd" ด้วย type ที่ถูก แล้วฝาก watcher.handler (คิว 10)

    while True:
        # TODO [2.2] sleep(PRINT_PERIOD)
        # TODO [2.2] ใน lock: อ่าน count (แล้วรีเซ็ต) + msg ล่าสุด
        # TODO [2.2] ถ้ายังไม่มี msg พิมพ์ "no lowcmd" (ใครควรเป็นคนส่ง?) ไม่งั้นพิมพ์ summarize(...)
        # ทายก่อน: ถ้ายังไม่มีโปรแกรมไหนส่งเลย จะเห็นอะไร  แล้วตอนรัน send_zero คู่กันจะได้กี่ Hz
        print("watch_lowcmd: ยังไม่ได้เติม [2.2]")
        break   # TODO [2.2] ลบเมื่อใส่ sleep แล้ว


if __name__ == "__main__":
    main()
