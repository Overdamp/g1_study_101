"""send_zero_skeleton.py: ส่ง LowCmd ที่ทุกค่าเป็น 0 ทุก 2 ms (งาน 2.1–2.2)  ✅ ส่ง lowcmd (sim เท่านั้น)

ไฟล์นี้คือ "โครงหลัก" ของทุกโปรแกรมที่ส่งคำสั่งในสัปดาห์ 2:
  อ่าน LowState (สัปดาห์ 1)  +  สร้าง LowCmd  +  ส่งทุก 2 ms  +  CRC
ไฟล์ถัดไป (damping / hold / step) ก็อปโครงนี้แล้วเปลี่ยนแค่ build_cmd()

ทายก่อนรัน: ส่ง kp = kd = tau = 0 ทุกข้อต่อ หุ่นใน sim จะเปลี่ยนไหม  (ดู sim_vs_real.md)
รัน:  conda activate g1_sdk && python week2/scripts/skelatons/send_zero_skeleton.py
"""

# ---------------------------------------------------------------------------
# imports
# ---------------------------------------------------------------------------
# TODO [2.2] ตัวเริ่ม DDS, ตัว subscribe, ตัว publish  (จาก unitree_sdk2py.core.channel)
# TODO [2.2] type ของ LowState และ LowCmd ชุด hg
# TODO [2.2] ฟังก์ชันสร้าง LowCmd เปล่า (ทุก field = 0)  จาก unitree_sdk2py.idl.default
# TODO [2.2] class คำนวณ CRC  จาก unitree_sdk2py.utils.crc
# TODO [2.2] threading, time

DOMAIN = 1
IFACE = "lo"
CONTROL_DT = 0.002       # [s] 500 Hz  (ตัวอย่างของ Unitree ใช้ 2 ms)
NUM_MOTORS = 29          # slot 0..28 ที่ใช้กับ 23-DoF (motor_cmd มี 35 ช่อง แต่ใช้แค่ 29 แรก)
MODE_PR = 0              # ข้อเท้าแบบ pitch/roll  (Mode.PR ในตัวอย่าง)


# ---------------------------------------------------------------------------
# ความปลอดภัย: เขียนไว้ให้แล้ว ห้ามลบ ห้ามแก้
# ---------------------------------------------------------------------------
def safety_guard(iface: str, domain: int) -> None:
    """หยุดโปรแกรมทันทีถ้าไม่ใช่ sim (lo + domain 1) ห้ามส่ง rt/lowcmd ไปหุ่นจริงจากแบบฝึกหัด"""
    if iface != "lo" or domain != 1:
        raise SystemExit(f"[safety] iface={iface!r} domain={domain}: แบบฝึกหัดนี้ใช้ได้กับ sim (lo, domain 1) เท่านั้น")


# ---------------------------------------------------------------------------
# อ่าน LowState (ก็อปแพทเทิร์นจากสัปดาห์ 1)
# ---------------------------------------------------------------------------
class StateReader:
    def __init__(self):
        # TODO [2.2] self.latest = None, self.lock
        pass

    def handler(self, msg):
        # TODO [2.2] ใน lock: เก็บ msg ล่าสุด
        pass

    def get(self):
        """คืน LowState ล่าสุด (หรือ None)"""
        # TODO [2.2] ใน lock: return self.latest
        return None


# ---------------------------------------------------------------------------
# สร้างคำสั่ง  ← ไฟล์ถัดไปเปลี่ยนแค่ฟังก์ชันนี้
# ---------------------------------------------------------------------------
def build_cmd(cmd, state, t):
    """เติมค่าลง cmd (LowCmd) ตาม state ล่าสุด และเวลา t [s] ตั้งแต่เริ่ม"""
    # TODO [2.2] cmd.mode_pr = MODE_PR
    # TODO [2.2] cmd.mode_machine = ค่าจาก state  (ทำไมไม่พิมพ์ 4 ลงไปเลย? ดู lowcmd_structure.md)
    # TODO [2.2] วน slot 0..NUM_MOTORS-1: mode = 1, q = dq = tau = kp = kd = 0
    # คำถาม: ถ้า kp = kd = 0 แล้ว q ที่ใส่มีผลไหม
    pass


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    safety_guard(IFACE, DOMAIN)

    # TODO [2.2] เริ่ม DDS
    reader = StateReader()
    # TODO [2.2] subscribe rt/lowstate → reader.handler
    # TODO [2.2] สร้าง publisher "rt/lowcmd" ชนิด LowCmd แล้ว Init()
    # TODO [2.2] cmd = LowCmd เปล่า,  crc = CRC()

    # รอ LowState แรกก่อน (ยังไม่รู้ mode_machine ห้ามส่ง)
    # TODO [2.2] วนรอจน reader.get() ไม่เป็น None  (ถ้ารอเกิน 3 s ให้พิมพ์เตือน: sim เปิดไหม?)

    # loop ส่งคำสั่ง 500 Hz
    # TODO [2.2] t0 = เวลาเริ่ม (monotonic),  next_t = t0
    while True:
        # TODO [2.2] state = reader.get()
        # TODO [2.2] build_cmd(cmd, state, เวลาตั้งแต่ t0)
        # TODO [2.2] cmd.crc = crc.Crc(cmd)       ← ต้องเป็นขั้นสุดท้ายก่อนส่ง ทำไม?
        # TODO [2.2] publisher.Write(cmd)
        # TODO [2.2] next_t += CONTROL_DT แล้ว sleep จนถึง next_t  (ทำไมไม่ sleep(CONTROL_DT) เฉยๆ? นึกถึง 1.3)
        # ทางเลือก: ใช้ RecurrentThread จาก unitree_sdk2py.utils.thread แบบในตัวอย่าง G1
        print("send_zero: ยังไม่ได้เติม [2.2]")
        break   # TODO [2.2] ลบเมื่อใส่ sleep แล้ว

    # ทดสอบ: รัน watch_lowcmd_skeleton.py คู่กัน ต้องเห็น ~500 Hz และ kp = 0
    # ปิดด้วย Ctrl+C  → ทายก่อน: sim จะทำอะไรต่อหลังเราหยุดส่ง (sim_vs_real.md ข้อ 3)


if __name__ == "__main__":
    main()
