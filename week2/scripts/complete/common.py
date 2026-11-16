"""common.py: ส่วนที่ทุกสคริปต์สัปดาห์ 2 ใช้ร่วมกัน (ฉบับสมบูรณ์)

ใน skeleton ให้ "ก็อปโครงจาก send_zero" ไปทุกไฟล์ เพื่อให้เขียนเองจนเข้าใจทุกบรรทัด
ฉบับสมบูรณ์ดึงส่วนที่ซ้ำกันมารวมไว้ที่นี่ (refactor) แต่ละสคริปต์จึงเหลือแค่ build_cmd() ที่ต่างกันจริงๆ
เทียบกับ skeleton ได้ตรงๆ:  StateReader, safety_guard, loop 500 Hz + CRC  อยู่ในไฟล์นี้

⚠️ sim เท่านั้น: safety_guard() หยุดโปรแกรมถ้าไม่ใช่ lo + domain 1
"""

import threading
import time

from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelPublisher, ChannelSubscriber
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowCmd_   # สร้าง LowCmd ที่ทุก field = 0
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowCmd_, LowState_  # G1 ใช้ชุด hg
from unitree_sdk2py.utils.crc import CRC

# ---------------------------------------------------------------------------
# ค่าคงที่
# ---------------------------------------------------------------------------
DOMAIN = 1               # sim
IFACE = "lo"             # sim
CONTROL_DT = 0.002       # [s] ส่งคำสั่งทุก 2 ms = 500 Hz (เหมือนตัวอย่าง G1 ของ Unitree)
NUM_MOTORS = 29          # slot 0..28 (motor_cmd มี 35 ช่อง ใช้แค่ 29 แรก ช่อง 13,14,20,21,27,28 ไม่มีข้อต่อบน 23-DoF)
MODE_PR = 0              # ข้อเท้าแบบ pitch/roll (Mode.PR ในตัวอย่าง)
LEFT_ELBOW = 18
STATE_TIMEOUT_S = 0.1    # LowState หายเกิน 100 ms → หยุด (ค่าเดียวกับ g1_ctrl ที่เข้า Passive)

# kd ของ Passive ใน g1_ctrl (config.yaml → FSM: Passive: kd) เรียงตาม slot 0..28
PASSIVE_KD = [
    4.0, 4.0, 4.0, 6.0, 2.5, 2.5,          # ขาซ้าย   0-5
    4.0, 4.0, 4.0, 6.0, 2.5, 2.5,          # ขาขวา    6-11
    4.5, 4.5, 4.5,                         # เอว      12-14
    2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5,     # แขนซ้าย  15-21
    2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5,     # แขนขวา   22-28
]


# ---------------------------------------------------------------------------
# ความปลอดภัย
# ---------------------------------------------------------------------------
def safety_guard(iface: str, domain: int) -> None:
    """หยุดโปรแกรมทันทีถ้าไม่ใช่ sim ห้ามส่ง rt/lowcmd ไปหุ่นจริงจากแบบฝึกหัด"""
    if iface != "lo" or domain != 1:
        raise SystemExit(f"[safety] iface={iface!r} domain={domain}: แบบฝึกหัดนี้ใช้ได้กับ sim (lo, domain 1) เท่านั้น")


def init_dds() -> None:
    """เช็คความปลอดภัยก่อน แล้วค่อยเข้า DDS (ลำดับนี้สำคัญ: ตรวจก่อนเชื่อมต่อ)"""
    safety_guard(IFACE, DOMAIN)
    ChannelFactoryInitialize(DOMAIN, IFACE)


# ---------------------------------------------------------------------------
# อ่าน LowState (แพทเทิร์นเดียวกับสัปดาห์ 1)
# ---------------------------------------------------------------------------
class StateReader:
    """เก็บ LowState ล่าสุด + เวลาที่ได้รับ ให้ thread ของ loop ควบคุมอ่านแบบปลอดภัย"""

    def __init__(self):
        self.latest = None               # None = ยังไม่เคยได้ข้อความ
        self.stamp = 0.0                 # time.monotonic() ตอนได้ข้อความล่าสุด
        self.lock = threading.Lock()

    def handler(self, msg: LowState_):
        # เรียกจาก thread ของ SDK ~1 kHz: แค่เก็บ ไม่ทำงานหนัก ไม่ print
        with self.lock:
            self.latest = msg
            self.stamp = time.monotonic()

    def get(self):
        """คืน (msg ล่าสุด, อายุของข้อมูล [s])"""
        with self.lock:
            return self.latest, time.monotonic() - self.stamp


def start_state_reader():
    """subscribe rt/lowstate คืน (reader, subscriber)

    ต้องเก็บ subscriber ไว้ในตัวแปรตลอดอายุโปรแกรม ถ้าปล่อยให้ถูก garbage collect การรับข้อมูลจะหยุด
    """
    reader = StateReader()
    sub = ChannelSubscriber("rt/lowstate", LowState_)
    sub.Init(reader.handler, 10)
    return reader, sub


def wait_for_state(reader: StateReader, warn_after_s: float = 3.0):
    """รอจนได้ LowState แรก (ก่อนหน้านั้นไม่รู้ mode_machine และไม่รู้ท่าปัจจุบัน ห้ามส่ง)"""
    t0 = time.monotonic()
    warned = False
    while True:
        msg, _ = reader.get()
        if msg is not None:
            return msg
        if not warned and time.monotonic() - t0 > warn_after_s:
            print("[wait] ยังไม่มี LowState: sim เปิดไหม / multicast lo / CYCLONEDDS_URI ?", flush=True)
            warned = True
        time.sleep(0.01)


# ---------------------------------------------------------------------------
# ตัวช่วยสร้างคำสั่ง
# ---------------------------------------------------------------------------
def set_header(cmd, state) -> None:
    """field ระดับข้อความ"""
    cmd.mode_pr = MODE_PR
    cmd.mode_machine = state.mode_machine   # อ่านจากหุ่น ไม่ hard-code (ตัวอย่าง Unitree ทำแบบนี้)


def fill_damping(cmd, state, kd_scale: float = 1.0) -> None:
    """ทุก slot = Passive: kp 0, kd > 0, q = มุมปัจจุบัน

    q = มุมปัจจุบัน ไม่มีผลตอนนี้ (kp = 0) แต่ถ้าโค้ดถัดไปเปิด kp ของ slot ไหน จะเริ่มจากท่าจริง ไม่กระตุก
    (เหตุผลเดียวกับ State_Passive::run() ใน g1_ctrl)
    """
    for i in range(NUM_MOTORS):
        m = cmd.motor_cmd[i]
        m.mode = 1                          # 1 = เปิดมอเตอร์ (หุ่นจริงต้องมี sim ไม่สนใจ)
        m.q = state.motor_state[i].q
        m.dq = 0.0
        m.tau = 0.0
        m.kp = 0.0
        m.kd = PASSIVE_KD[i] * kd_scale


# ---------------------------------------------------------------------------
# loop ควบคุม 500 Hz
# ---------------------------------------------------------------------------
def run_control_loop(build, use_crc: bool = True):
    """เรียก build(cmd, state, t) ทุก 2 ms แล้วคำนวณ CRC และส่ง

    build คืน False เมื่ออยากหยุด (คืน None/True = ทำต่อ)
    หยุดเองถ้า LowState หายเกิน STATE_TIMEOUT_S (เหมือน timeout ของ g1_ctrl)
    ⚠️ หยุดแล้ว sim จะใช้คำสั่งสุดท้ายต่อไปเรื่อยๆ (sim_vs_real.md)
    """
    init_dds()
    reader, _sub = start_state_reader()            # _sub: เก็บไว้กันถูก garbage collect
    pub = ChannelPublisher("rt/lowcmd", LowCmd_)
    pub.Init()
    cmd = unitree_hg_msg_dds__LowCmd_()
    crc = CRC()

    wait_for_state(reader)
    t0 = time.monotonic()
    next_t = t0
    while True:
        state, age = reader.get()
        if age > STATE_TIMEOUT_S:
            print(f"[stop] LowState หายไป {age * 1e3:.0f} ms (sim ปิด?) หยุดส่งคำสั่ง", flush=True)
            return

        if build(cmd, state, time.monotonic() - t0) is False:
            return

        if use_crc:
            cmd.crc = crc.Crc(cmd)                 # ขั้นสุดท้ายก่อนส่ง: แก้ field ไหนหลังจากนี้ CRC จะผิด
        pub.Write(cmd)

        # นัดเวลารอบถัดไปแบบสะสม (ไม่ใช่ sleep(CONTROL_DT) เฉยๆ) กันเวลาเลื่อนสะสม (บทเรียนจาก 1.3)
        next_t += CONTROL_DT
        sleep_s = next_t - time.monotonic()
        if sleep_s > 0:
            time.sleep(sleep_s)
        else:
            next_t = time.monotonic()              # ตามไม่ทัน (เช่นเครื่องช้าชั่วคราว) เริ่มนับใหม่ ไม่เร่งส่งชดเชย


class Every:
    """ช่วยพิมพ์เป็นระยะใน loop 500 Hz: ถ้า every(t) เป็น True ค่อย print"""

    def __init__(self, period_s: float):
        self.period = period_s
        self.next = 0.0

    def __call__(self, t: float) -> bool:
        if t >= self.next:
            self.next = t + self.period
            return True
        return False
