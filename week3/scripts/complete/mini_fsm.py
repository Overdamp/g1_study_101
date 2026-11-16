"""mini_fsm.py: FSM เล็กๆ ใน Python: Passive ↔ Hold → Wave + timeout (งาน 3.2–3.4) ฉบับสมบูรณ์  ✅ ส่ง lowcmd (sim เท่านั้น)

โครงเดียวกับ CtrlFSM ของ g1_ctrl:
    ทุก 2 ms:  current.run()  → ส่ง lowcmd  → เช็ค current.checks ตามลำดับ → ถ้าจริง: exit() → เปลี่ยน → enter()

    Passive --o--> Hold --w--> Wave
       ▲            │           │
       └─────p──────┴─────p─────┘      ทุก state: LowState หาย > 100 ms → Passive

คีย์: พิมพ์ตัวอักษรแล้วกด Enter ใน terminal นี้
รัน:  conda activate g1_sdk && python week3/scripts/complete/mini_fsm.py      (เปิด sim ไว้ก่อน)
⚠️ ห้ามรันพร้อม g1_ctrl หรือสคริปต์อื่นที่ส่ง lowcmd
"""

import math
import sys
import threading
import time
from pathlib import Path

# ใช้ของจาก week2 (StateReader, safety_guard, damping ...) สัปดาห์นี้โฟกัสที่ FSM
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "week2" / "scripts" / "complete"))
from common import (CONTROL_DT, LEFT_ELBOW, NUM_MOTORS, STATE_TIMEOUT_S, fill_damping, init_dds,  # noqa: E402  # pyrefly: ignore[missing-import]
                    set_header, start_state_reader, wait_for_state)
from unitree_sdk2py.core.channel import ChannelPublisher  # noqa: E402
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowCmd_  # noqa: E402
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowCmd_  # noqa: E402
from unitree_sdk2py.utils.crc import CRC  # noqa: E402

# gain ตอนเทรน (BeyondMimic) เรียงตาม slot 0..28 · slot ที่ไม่มีข้อต่อ = 0
TRAIN_KP = [
    40.2, 99.1, 40.2, 99.1, 28.5, 28.5,
    40.2, 99.1, 40.2, 99.1, 28.5, 28.5,
    40.2, 0.0, 0.0,
    14.3, 14.3, 14.3, 14.3, 14.3, 0.0, 0.0,
    14.3, 14.3, 14.3, 14.3, 14.3, 0.0, 0.0,
]
TRAIN_KD = [
    2.6, 6.3, 2.6, 6.3, 1.8, 1.8,
    2.6, 6.3, 2.6, 6.3, 1.8, 1.8,
    2.6, 0.0, 0.0,
    0.9, 0.9, 0.9, 0.9, 0.9, 0.0, 0.0,
    0.9, 0.9, 0.9, 0.9, 0.9, 0.0, 0.0,
]
WAVE_AMP_DEG = 20.0
WAVE_FREQ_HZ = 0.5
WAVE_RAMP_S = 1.0


class KeyInput:
    """thread อ่านบรรทัดจาก stdin · pop() คืนตัวอักษรที่กด "ครั้งเดียว" (edge แบบ .on_pressed ของ g1_ctrl)"""

    def __init__(self):
        self._key = None
        self._lock = threading.Lock()
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        for line in sys.stdin:
            with self._lock:
                self._key = line.strip()[:1] or None

    def pop(self):
        with self._lock:
            k, self._key = self._key, None
            return k


# ---------------------------------------------------------------------------
# state
# ---------------------------------------------------------------------------
class State:
    name = "State"

    def __init__(self):
        self.checks = []                 # [(ฟังก์ชันคืน bool, ชื่อปลายทาง)]  ← registered_checks

    def enter(self, cmd, state):
        pass

    def run(self, cmd, state, t):
        pass

    def exit(self):
        pass


def hold_pose(cmd, state, q_hold):
    """ทุก slot ค้างที่ q_hold ด้วย gain ตอนเทรน (slot ว่าง kp = kd = 0)"""
    set_header(cmd, state)
    for i in range(NUM_MOTORS):
        m = cmd.motor_cmd[i]
        m.mode = 1
        m.q = q_hold[i]
        m.dq = 0.0
        m.tau = 0.0
        m.kp = TRAIN_KP[i]
        m.kd = TRAIN_KD[i]


class Passive(State):
    name = "Passive"

    def run(self, cmd, state, t):
        # kp 0, kd > 0 และ q = มุมปัจจุบันทุกรอบ → state ถัดไปที่เปิด kp จะเริ่มจากท่าจริง ไม่กระตุก
        set_header(cmd, state)
        fill_damping(cmd, state)


class Hold(State):
    name = "Hold"

    def __init__(self):
        super().__init__()
        self.q_hold = None

    def enter(self, cmd, state):
        # จดครั้งเดียวตอนเข้า: ถ้าจดใน run ทุกรอบ เป้าจะวิ่งตามท่าปัจจุบัน = ไม่มีแรงดึงกลับ (ลากแล้วไม่กลับ)
        self.q_hold = [state.motor_state[i].q for i in range(NUM_MOTORS)]

    def run(self, cmd, state, t):
        hold_pose(cmd, state, self.q_hold)


class Wave(State):
    name = "Wave"

    def __init__(self):
        super().__init__()
        self.q_hold = None
        self.t_enter = None

    def enter(self, cmd, state):
        self.q_hold = [state.motor_state[i].q for i in range(NUM_MOTORS)]
        self.t_enter = None              # run รอบแรกจะจดเวลา (enter ไม่ได้รับ t)

    def run(self, cmd, state, t):
        if self.t_enter is None:
            self.t_enter = t
        tau = t - self.t_enter
        # แอมพลิจูดค่อยๆ เพิ่มจาก 0 ใน WAVE_RAMP_S (แนวคิด Soft Start)
        # sin(0) = 0 อยู่แล้วตำแหน่งจึงไม่กระโดด แต่ "ความเร็ว" ตอนเริ่มจะกระโดดจาก 0 เป็น A·2πf ถ้าไม่มี ramp
        # ถ้าใช้ cos จะกระโดดทั้งตำแหน่ง (cos 0 = 1 → เป้าเลื่อนทันที A)
        amp = math.radians(WAVE_AMP_DEG) * min(1.0, tau / WAVE_RAMP_S)
        q = list(self.q_hold)
        q[LEFT_ELBOW] = self.q_hold[LEFT_ELBOW] + amp * math.sin(2 * math.pi * WAVE_FREQ_HZ * tau)
        hold_pose(cmd, state, q)


# ---------------------------------------------------------------------------
# FSM
# ---------------------------------------------------------------------------
class MiniFSM:
    def __init__(self, keys: KeyInput):
        self.keys = keys
        self.states = {}
        self.current = None
        self.last_key = None
        self.state_age = 0.0

    def add(self, st: State):
        self.states[st.name] = st

    def key_is(self, k):
        return lambda: self.last_key == k

    def setup_transitions(self):
        timeout = (lambda: self.state_age > STATE_TIMEOUT_S, "Passive")
        # timeout ไว้ "แรกสุด" ของทุก state: ถ้าเกิดพร้อมกับการกดคีย์ ความปลอดภัยต้องชนะ
        # (g1_ctrl ใส่ timeout ต่อท้าย แต่ปุ่มของมันมีแค่ทางไป state ที่ปลอดภัยกว่าหรือ FixStand ที่ไม่มีทางกดพร้อมกันได้จริง)
        self.states["Passive"].checks = [(self.key_is("o"), "Hold")]
        self.states["Hold"].checks = [timeout, (self.key_is("p"), "Passive"), (self.key_is("w"), "Wave")]
        self.states["Wave"].checks = [timeout, (self.key_is("p"), "Passive")]

    def change(self, name, cmd, state):
        if self.current is not None and name == self.current.name:
            return
        print(f"FSM: {self.current.name if self.current else '-'} -> {name}", flush=True)
        if self.current is not None:
            self.current.exit()
        self.current = self.states[name]
        self.current.enter(cmd, state)

    def tick(self, cmd, state, t, age):
        """1 รอบ (เทียบ CtrlFSM::run_()): run ก่อน แล้วค่อยเช็ค transition
        → รอบที่กดคีย์ คำสั่งที่ส่งออกไปยังเป็นของ state เดิม state ใหม่เริ่มมีผลรอบถัดไป"""
        self.last_key = self.keys.pop()
        self.state_age = age
        self.current.run(cmd, state, t)
        for cond, target in self.current.checks:
            if cond():
                self.change(target, cmd, state)
                break                        # เปลี่ยนได้ครั้งเดียวต่อรอบ


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    keys = KeyInput()
    fsm = MiniFSM(keys)
    for st in (Passive(), Hold(), Wave()):
        fsm.add(st)
    fsm.setup_transitions()

    init_dds()                                       # safety_guard ในตัว: lo + domain 1 เท่านั้น
    reader, _sub = start_state_reader()
    pub = ChannelPublisher("rt/lowcmd", LowCmd_)
    pub.Init()
    cmd = unitree_hg_msg_dds__LowCmd_()
    crc = CRC()

    state = wait_for_state(reader)
    fsm.change("Passive", cmd, state)                # state แรกต้องเป็น Passive เสมอ
    print("คีย์: o = Hold, w = Wave (จาก Hold), p = Passive  (พิมพ์แล้วกด Enter, Ctrl+C ออก)", flush=True)

    t0 = time.monotonic()
    next_t = t0
    next_report = 0.0
    while True:
        msg, age = reader.get()
        t = time.monotonic() - t0
        # LowState หาย: ยังเรียก tick ต่อ (ใช้ state ล่าสุดที่มี) เพื่อให้ FSM เห็น age และเปลี่ยนเป็น Passive เอง
        # (ไม่หยุดโปรแกรม: พอ sim กลับมา เราอยู่ใน Passive ที่ปลอดภัย ไม่กลับไป Hold เอง)
        fsm.tick(cmd, msg, t, age)
        cmd.crc = crc.Crc(cmd)
        pub.Write(cmd)

        if t >= next_report:
            next_report = t + 1.0
            q = msg.motor_state[LEFT_ELBOW].q
            stale = f"  !! LowState หาย {age * 1e3:.0f} ms" if age > STATE_TIMEOUT_S else ""
            print(f"[{t:6.1f}s] {fsm.current.name:<7} ศอกซ้าย {math.degrees(q):+6.1f}°{stale}", flush=True)

        next_t += CONTROL_DT
        sleep_s = next_t - time.monotonic()
        if sleep_s > 0:
            time.sleep(sleep_s)
        else:
            next_t = time.monotonic()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nออกแล้ว: sim จะใช้คำสั่งสุดท้ายต่อ (ถ้าออกตอน Hold/Wave ศอกยังค้าง kp อยู่ รัน week2 damping.py เพื่อปล่อย)")
