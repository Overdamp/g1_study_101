"""read_lowstate.py: ตัวเต็มของสัปดาห์ 1 (งาน 1.2–1.7) ใช้ได้ทั้ง sim และหุ่นจริง (อ่านอย่างเดียว)

ครบทุกงาน: Hz (1.3) · ตาราง 23 ข้อต่อ (1.5) · IMU + mode_machine (1.6) · --network / --domain (1.7)
เพิ่มเติม:
  - ป้ายบรรทัดแรก SIM / REAL ROBOT (กันสับสนว่ากำลังดูข้อมูลจากไหน)
  - เตือนถ้า LowState ขาดช่วง (gap) และนับมอเตอร์ที่ vol = 0 (หุ่นจริง: มอเตอร์ไม่ตอบ)
  - --once: พิมพ์ครั้งเดียวแล้วจบ (ใช้เช็คเร็วๆ)

รัน (sim, ค่าเริ่มต้น):   python week1/scripts/complete/read_lowstate.py
รัน (หุ่นจริง, แขวนรอก):  python week1/scripts/complete/read_lowstate.py --network enp43s0
งาน 1.8:                  python week1/scripts/complete/read_lowstate.py --domain 0      (sim อยู่ domain 1)

⚠️ สคริปต์นี้ไม่ส่งคำสั่งใดๆ (ไม่มี publisher) จึงปลอดภัยกับหุ่นจริง
"""

import argparse
import math
import threading
import time

from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_

G1_23DOF_JOINTS = {
    0: "left_hip_pitch_joint", 1: "left_hip_roll_joint", 2: "left_hip_yaw_joint",
    3: "left_knee_joint", 4: "left_ankle_pitch_joint", 5: "left_ankle_roll_joint",
    6: "right_hip_pitch_joint", 7: "right_hip_roll_joint", 8: "right_hip_yaw_joint",
    9: "right_knee_joint", 10: "right_ankle_pitch_joint", 11: "right_ankle_roll_joint",
    12: "waist_yaw_joint",
    15: "left_shoulder_pitch_joint", 16: "left_shoulder_roll_joint", 17: "left_shoulder_yaw_joint",
    18: "left_elbow_joint", 19: "left_wrist_roll_joint",
    22: "right_shoulder_pitch_joint", 23: "right_shoulder_roll_joint", 24: "right_shoulder_yaw_joint",
    25: "right_elbow_joint", 26: "right_wrist_roll_joint",
}
EXPECTED_MODE_MACHINE = 4
GAP_WARN_S = 0.1          # LowState ขาดเกิน 100 ms (= timeout ของ g1_ctrl) → เตือน
CLEAR = "\033[H\033[2J"


class LowStateReader:
    def __init__(self):
        self.count = 0
        self.latest = None
        self.last_t = None           # เวลาของข้อความล่าสุด
        self.max_gap = 0.0           # ช่องว่างที่ยาวที่สุดระหว่างข้อความ ตั้งแต่รายงานครั้งก่อน
        self.lock = threading.Lock()

    def handler(self, msg: LowState_):
        now = time.monotonic()
        with self.lock:
            if self.last_t is not None:
                self.max_gap = max(self.max_gap, now - self.last_t)
            self.last_t = now
            self.count += 1
            self.latest = msg

    def snapshot(self):
        """อ่านทุกอย่างแล้วรีเซ็ตตัวนับ ภายใน lock ครั้งเดียว"""
        with self.lock:
            out = (self.count, self.latest, self.max_gap, self.last_t)
            self.count = 0
            self.max_gap = 0.0
        return out


def parse_args():
    p = argparse.ArgumentParser(description="อ่าน rt/lowstate ของ G1 23-DoF (อ่านอย่างเดียว)")
    p.add_argument("--network", default="lo",
                   help="interface: lo = sim (ค่าเริ่มต้น), enp43s0 = หุ่นจริง (ต้องระบุเอง)")
    p.add_argument("--domain", type=int, default=None,
                   help="DDS domain (ค่าเริ่มต้น: 1 ถ้า lo, 0 ถ้าการ์ดอื่น)")
    p.add_argument("--period", type=float, default=0.5, help="รอบการพิมพ์ [s]")
    p.add_argument("--once", action="store_true", help="รอข้อความแรก พิมพ์ครั้งเดียวแล้วจบ")
    args = p.parse_args()
    if args.domain is None:
        args.domain = 1 if args.network == "lo" else 0     # sim เป็นค่าเริ่มต้น หุ่นจริงต้องตั้งใจระบุ
    return args


def banner(args) -> str:
    target = "SIM" if args.network == "lo" else "REAL ROBOT"
    warn = ""
    if args.network == "lo" and args.domain != 1:
        warn = "   !! sim ของเราอยู่ domain 1"
    elif args.network != "lo" and args.domain != 0:
        warn = "   !! หุ่นจริงอยู่ domain 0"
    return f"DDS: {target} | network {args.network} | domain {args.domain}{warn}"


def format_report(msg: LowState_, hz: float, max_gap: float, head: str) -> str:
    lines = [head, f"LowState {hz:6.1f} Hz   max gap {max_gap * 1e3:5.1f} ms" +
             ("   !! gap ใหญ่" if max_gap > GAP_WARN_S else ""), ""]

    lines.append(f"{'slot':>4}  {'joint':<28} {'q[rad]':>8} {'q[deg]':>7} {'dq[rad/s]':>10} {'tau':>6} {'temp':>5} {'vol':>5}")
    lines.append("-" * 82)
    zero_vol = []
    for slot, name in G1_23DOF_JOINTS.items():
        m = msg.motor_state[slot]
        if m.vol == 0:
            zero_vol.append(slot)
        lines.append(f"{slot:>4}  {name:<28} {m.q:+8.3f} {math.degrees(m.q):+7.1f} {m.dq:+10.3f}"
                     f" {m.tau_est:+6.2f} {m.temperature[0]:>5} {m.vol:5.1f}")

    # vol = 0 ทุกตัว = sim (unitree_mujoco ไม่รายงาน vol) · บางตัว = มอเตอร์ไม่ตอบ (vault: Incident Motors 25-26)
    if len(zero_vol) == len(G1_23DOF_JOINTS):
        lines.append("vol = 0 ทุกตัว → ข้อมูลจาก sim")
    elif zero_vol:
        lines.append(f"!! vol = 0 ที่ slot {zero_vol} → มอเตอร์อาจ offline")

    imu = msg.imu_state
    roll, pitch, yaw = (math.degrees(a) for a in imu.rpy)
    mm = msg.mode_machine
    lines.append("")
    lines.append(f"IMU  roll {roll:+6.1f}°  pitch {pitch:+6.1f}°  yaw {yaw:+7.1f}°   "
                 f"gyro [{imu.gyroscope[0]:+.2f} {imu.gyroscope[1]:+.2f} {imu.gyroscope[2]:+.2f}] rad/s   temp {imu.temperature}°C")
    lines.append(f"mode_machine {mm}  mode_pr {msg.mode_pr}  tick {msg.tick}" +
                 ("" if mm == EXPECTED_MODE_MACHINE else f"   !! คาดว่า {EXPECTED_MODE_MACHINE} (23-DoF)"))
    return "\n".join(lines)


def main():
    args = parse_args()
    head = banner(args)
    print(head, flush=True)

    ChannelFactoryInitialize(args.domain, args.network)
    reader = LowStateReader()
    sub = ChannelSubscriber("rt/lowstate", LowState_)
    sub.Init(reader.handler, 10)

    t_last = time.monotonic()
    while True:
        time.sleep(args.period)
        n, msg, max_gap, last_t = reader.snapshot()
        now = time.monotonic()
        hz = n / (now - t_last)
        t_last = now

        if msg is None:
            print(f"{hz:6.1f} Hz  (no LowState yet: ดู week1/docs/debug_checklist.md)", flush=True)
            continue
        if n == 0:
            # เคยได้ข้อมูลแล้วแต่ตอนนี้หยุดมา (sim ปิด / สายหลุด)
            print(f"!! LowState หยุดมา {now - last_t:.1f} s (ข้อมูลล่าสุดค้างอยู่)", flush=True)
            continue

        report = format_report(msg, hz, max_gap, head)
        if args.once:
            print("\n".join(report.splitlines()[1:]))    # ป้าย DDS พิมพ์ไปแล้วตอนเริ่ม ไม่พิมพ์ซ้ำ
            return
        print(CLEAR + report, flush=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
