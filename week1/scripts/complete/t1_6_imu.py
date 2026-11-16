"""t1_6_imu.py: ตาราง 23 ข้อต่อ + IMU (roll/pitch/yaw เป็นองศา) + mode_machine (งาน 1.6)

เพิ่มจาก t1_5: format_imu()
  - imu_state.rpy = [roll, pitch, yaw] rad · gyroscope = rad/s
  - mode_machine ของ G1 23-DoF = 4 ถ้าไม่ตรง → คนละรุ่น/ผิด scene (g1_ctrl จะไม่ยอมรัน: "Unmatched robot type")
ทดลอง: ลากลำตัวหุ่นใน MuJoCo ให้ก้ม/เอียง ดูว่า pitch/roll เปลี่ยนถูกแกน · yaw ตอนเริ่มเป็นเท่าไหร่?

รัน:  conda activate g1_sdk && python week1/scripts/complete/t1_6_imu.py
"""

import math
import threading
import time

from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_

from t1_5_table import CLEAR, PRINT_PERIOD, format_table   # ใช้ตารางจาก 1.5 ซ้ำ (ไฟล์อยู่โฟลเดอร์เดียวกัน)

EXPECTED_MODE_MACHINE = 4


class LowStateReader:
    def __init__(self):
        self.count = 0
        self.latest = None
        self.lock = threading.Lock()

    def handler(self, msg: LowState_):
        with self.lock:
            self.count += 1
            self.latest = msg


def format_imu(msg: LowState_) -> str:
    imu = msg.imu_state
    roll, pitch, yaw = (math.degrees(a) for a in imu.rpy)
    gx, gy, gz = imu.gyroscope
    mm = msg.mode_machine
    warn = "" if mm == EXPECTED_MODE_MACHINE else f"   !! คาดว่า {EXPECTED_MODE_MACHINE} (23-DoF)"
    return (f"IMU  roll {roll:+6.1f}°  pitch {pitch:+6.1f}°  yaw {yaw:+7.1f}°   "
            f"gyro [{gx:+.2f} {gy:+.2f} {gz:+.2f}] rad/s\n"
            f"mode_machine {mm}  mode_pr {msg.mode_pr}  tick {msg.tick}{warn}")


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
        hz = n / (now - t_last)
        t_last = now

        if msg is None:
            print(f"{hz:.1f} Hz  (no LowState yet)", flush=True)
            continue
        print(CLEAR + format_table(msg, hz) + "\n\n" + format_imu(msg), flush=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
