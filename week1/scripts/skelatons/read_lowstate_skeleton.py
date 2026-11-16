"""read_lowstate_skeleton.py: โครงสำหรับฝึกเขียน read_lowstate เอง (งาน 1.2 ถึง 1.7)

วิธีใช้
  1. ทำทีละขั้นตามป้าย [1.2] → [1.3] → [1.4] → [1.5] → [1.6] → [1.7]
     แต่ละขั้น: เปิด comment ที่เป็น TODO แล้วเขียนโค้ดจริงแทน  (ไม่เปิดเฉลย)
  2. ก่อนรันแต่ละขั้น ทายก่อนว่าจะเห็นอะไร  หลังรันเทียบกับที่ทาย
  3. ไฟล์นี้รันได้ตั้งแต่แรก (ยังไม่ทำอะไร) และไม่มีตัวแดงใน IDE
     ค่าที่ต้องเติมใส่ไว้เป็น None  พร้อม  # TODO
รัน:  conda activate g1_sdk && python week1/scripts/skelatons/read_lowstate_skeleton.py   (เปิด sim ไว้ก่อน)
"""

# ---------------------------------------------------------------------------
# imports  (เปิดทีละตัวเมื่อถึงขั้นที่ต้องใช้)
# ---------------------------------------------------------------------------
# TODO [1.2] import 2 อย่างจาก unitree_sdk2py.core.channel  (ตัวเริ่ม DDS + ตัว subscribe)
# TODO [1.2] import type ของ LowState สำหรับ G1           (ชุด hg หรือ go?)
# TODO [1.2] import โมดูลที่มี sleep                        ([1.3] ใช้ monotonic จากโมดูลเดียวกัน)
# TODO [1.3] import โมดูลที่มี Lock
# TODO [1.4] import โมดูลที่แปลง rad -> องศา
# TODO [1.7] import โมดูลมาตรฐานสำหรับอ่าน argument จาก command line


# ---------------------------------------------------------------------------
# ค่าคงที่
# ---------------------------------------------------------------------------
# slot ใน msg.motor_state -> ชื่อข้อต่อ (เป็นข้อมูล ไม่ใช่ logic ให้ไว้เลย)
# slot 13, 14, 20, 21, 27, 28 ไม่มีข้อต่อบน 23-DoF
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

LEFT_ELBOW = None              # TODO [1.4] slot ของศอกซ้าย
PRINT_PERIOD = None            # TODO [1.5] คาบการพิมพ์ [s]
EXPECTED_MODE_MACHINE = None   # TODO [1.6] mode_machine ที่ถูกต้องของ G1 23-DoF  (ดู vault: LowState and LowCmd.md)


# ---------------------------------------------------------------------------
# ข้อมูลที่ใช้ร่วมกันระหว่าง 2 thread
# ---------------------------------------------------------------------------
class LowStateReader:
    """ข้อมูลที่ SDK thread (handler) กับ main thread ใช้ร่วมกัน"""

    def __init__(self):
        # TODO [1.3] self.count     ตัวนับข้อความ เริ่มที่เท่าไหร่
        # TODO [1.3] self.lock      lock 1 ตัว
        # TODO [1.4] self.elbow_q   มุมศอกล่าสุด  ค่าเริ่มต้น 0 หรือ None? ทำไม
        # TODO [1.5] self.latest    LowState ล่าสุดทั้งก้อน  ค่าเริ่มต้นเหมือนข้อบน
        #            (พอมี self.latest แล้ว self.elbow_q ยังจำเป็นไหม?)
        pass

    def handler(self, msg):
        # ถูกเรียก ~900 ครั้ง/วินาที จาก thread ของ SDK  ต้องสั้นและเร็ว
        # TODO [1.2] print ข้อความสั้นๆ ให้รู้ว่า callback ถูกเรียก  (ผ่าน 1.2 แล้วลบทิ้ง ทำไม?)
        # TODO [1.3] ใน lock: เพิ่มตัวนับ
        # TODO [1.4] ใน lock เดียวกัน: เก็บ q ของศอกซ้าย       msg.???[LEFT_ELBOW].???
        # TODO [1.5] ใน lock เดียวกัน: เก็บทั้ง msg
        pass


# ---------------------------------------------------------------------------
# การแสดงผล (เรียกจาก main เท่านั้น ไม่เรียกใน handler)
# ---------------------------------------------------------------------------
def format_table(msg, hz):
    """[1.5] คืนตาราง 23 ข้อต่อเป็น string ก้อนเดียว"""
    lines = []
    # TODO [1.5] บรรทัดหัว: Hz และชื่อคอลัมน์ (slot, joint, q[rad], dq[rad/s], temp)
    # TODO [1.5] วน G1_23DOF_JOINTS ได้ (slot, name)  ดึง motor_state[slot]  แล้วเพิ่ม 1 บรรทัด
    #            ใบ้ f-string:  :>4 ชิดขวา   :<28 ชิดซ้าย   :+8.3f เครื่องหมาย + ทศนิยม 3
    #            temperature ไม่ใช่ตัวเลขเดียว  (เปิด _MotorState_.py ดู)
    return "\n".join(lines)


def format_imu(msg):
    """[1.6] คืนบรรทัดสรุป IMU + mode_machine"""
    # TODO [1.6] ข้อมูล IMU อยู่ใน field ไหนของ LowState_  แล้วข้างในมีอะไร  (เปิด _LowState_.py, _IMUState_.py)
    # TODO [1.6] ดึง roll, pitch, yaw (หน่วย rad) แปลงเป็นองศา
    # TODO [1.6] ดึง mode_machine  ถ้าไม่ตรง EXPECTED_MODE_MACHINE ให้แสดงคำเตือน
    #            (ถ้าไม่ตรง แปลว่าอะไร?  ลองนึกถึงตอนส่ง lowcmd ในสัปดาห์ 2)
    # ทายก่อนรัน: ตอนหุ่นห้อยนิ่ง roll / pitch / yaw จะประมาณกี่องศา  yaw จะเป็น 0 ไหม
    return ""


# ---------------------------------------------------------------------------
# command line
# ---------------------------------------------------------------------------
def parse_args():
    """[1.7] อ่าน --network และ --domain (ชื่อเดียวกับ g1_ctrl --network) จาก command line"""
    # TODO [1.7] สร้าง ArgumentParser
    # TODO [1.7] --network ค่าเริ่มต้น = interface ของ sim
    # TODO [1.7] --domain ค่าเริ่มต้น = domain ของ sim  (type ต้องเป็นอะไร? ถ้าไม่ระบุจะได้ type อะไร)
    # TODO [1.7] return ผลที่ parse แล้ว
    #
    # หุ่นจริง:  python read_lowstate_skeleton.py --network enp43s0 --domain 0
    #   ⚠️ อ่านอย่างเดียว ปลอดภัย  แต่ห้ามเพิ่มการส่ง rt/lowcmd ในไฟล์นี้
    #   ก่อนต่อหุ่นจริง: ตั้ง IP 192.168.123.123/24 บน enp43s0  และ ping 192.168.123.161 ให้ผ่าน
    return None


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    # TODO [1.7] args = parse_args()  แล้วใช้ args แทนค่าที่ hard-code ในขั้น 1

    # ขั้น 1  TODO [1.2] เริ่ม DDS:  sim = domain ? บน interface ?
    reader = LowStateReader()
    # ขั้น 2  TODO [1.2] สร้าง subscriber:  ชื่อ topic ? กับ type ?
    # ขั้น 3  TODO [1.2] ฝาก reader.handler ไว้กับ subscriber  (มีวงเล็บหรือไม่?)  คิว 10

    # ขั้น 4  ทำให้ main ไม่จบ + รายงานผล
    # TODO [1.3] จำเวลาเริ่มต้นด้วยนาฬิกาที่ไม่ถอยหลัง
    while True:
        # TODO [1.2] sleep 1 วินาที                    ([1.5] เปลี่ยนเป็น PRINT_PERIOD)

        # TODO [1.3] ใน lock: อ่านตัวนับเก็บในตัวแปรท้องถิ่น แล้วรีเซ็ตเป็น 0
        # TODO [1.4]          อ่านมุมศอกเก็บไว้ด้วย
        # TODO [1.5]          อ่าน msg ล่าสุดเก็บไว้ด้วย
        # (ออกจาก lock ให้เร็วที่สุด  งานช้าทำข้างล่างนี้)

        # TODO [1.3] dt = เวลาที่ผ่านไปจริง,  hz = จำนวน / dt,  อัพเดทเวลาล่าสุด
        # TODO [1.4] ถ้ายังไม่มีข้อมูล (None) พิมพ์บอกแล้ว continue  ไม่งั้นพิมพ์ Hz + ศอกเป็นองศา
        # TODO [1.5] แทนที่ข้อบนด้วยการพิมพ์ format_table(...)  (ล้างจอ: "\033[H\033[2J")
        # TODO [1.6] พิมพ์ format_imu(...) ต่อท้ายตาราง

        break   # TODO [1.2] ลบบรรทัดนี้เมื่อใส่ sleep แล้ว  (ตอนนี้กันไม่ให้ loop หมุนเปล่าจน CPU 100%)


if __name__ == "__main__":
    main()
