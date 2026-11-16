"""mini_fsm_skeleton.py: FSM เล็กๆ ใน Python: Passive ↔ Hold → Wave (งาน 3.2–3.4)  ✅ ส่ง lowcmd (sim เท่านั้น)

โครงเดียวกับ CtrlFSM ของ g1_ctrl (week3/docs/fsm_concepts.md):
    ทุก 2 ms:  current.run(cmd, state, t)   → ส่ง lowcmd
               เช็ค current.checks ตามลำดับ → ถ้าเงื่อนไขไหนจริง: exit() → เปลี่ยน state → enter()

state ที่ต้องมี:
    Passive  kp 0, kd > 0, q = มุมปัจจุบัน          (state แรก + ที่พักฉุกเฉิน)
    Hold     ทุกข้อต่อค้างท่าตอนเข้า (gain ตอนเทรน)  [3.2]
    Wave     ศอกแกว่ง sine ±20° รอบมุมตอนเข้า แอมพลิจูดค่อยๆ เพิ่มใน 1 s   [3.4]
transition (พิมพ์ตัวอักษรแล้ว Enter ใน terminal นี้):
    Passive --o--> Hold --w--> Wave
    Hold/Wave --p--> Passive
    ทุก state: LowState หายเกิน 100 ms → Passive   [3.3]

ใช้ของจาก week2 (เพื่อให้สัปดาห์นี้โฟกัสที่ FSM): StateReader, fill_damping, set_header, safety_guard ...
ถ้าอยากใช้ของที่เขียนเองในสัปดาห์ 2 ก็เปลี่ยน path ใน import ได้

รัน:  conda activate g1_sdk && python week3/scripts/skelatons/mini_fsm_skeleton.py   (เปิด sim ไว้ก่อน)
⚠️ ห้ามรันพร้อม g1_ctrl หรือสคริปต์อื่นที่ส่ง lowcmd
"""

import sys
import threading
from pathlib import Path

# ---------------------------------------------------------------------------
# imports
# ---------------------------------------------------------------------------
WEEK2 = Path(__file__).resolve().parents[3] / "week2" / "scripts" / "complete"
sys.path.insert(0, str(WEEK2))
# TODO [3.2] จาก common (week2): init_dds, start_state_reader, wait_for_state, set_header, fill_damping,
#            CONTROL_DT, NUM_MOTORS, LEFT_ELBOW, STATE_TIMEOUT_S
# TODO [3.2] จาก unitree_sdk2py: ChannelPublisher, LowCmd_ (ชุด hg), unitree_hg_msg_dds__LowCmd_, CRC
# TODO [3.2] time, math

# gain ตอนเทรน (BeyondMimic) เรียงตาม slot 0..28 · slot ที่ไม่มีข้อต่อ (13,14,20,21,27,28) = 0
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


# ---------------------------------------------------------------------------
# อ่านคีย์บอร์ด: ให้ไว้แล้ว (ไม่ใช่เนื้อหาของสัปดาห์นี้)
# ---------------------------------------------------------------------------
class KeyInput:
    """thread อ่านบรรทัดจาก stdin  pop() คืนตัวอักษรที่กด "ครั้งเดียว" (edge แบบ .on_pressed ของ g1_ctrl)"""

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
    """แม่แบบ (เทียบ BaseState / FSMState ใน g1_ctrl)"""
    name = "State"

    def __init__(self):
        self.checks = []         # list ของ (ฟังก์ชันคืน bool, ชื่อ state ปลายทาง)  ← registered_checks

    def enter(self, cmd, state):
        """ครั้งเดียวตอนเข้า: ตั้ง gain, จดท่า/เวลาเริ่ม"""
        pass

    def run(self, cmd, state, t):
        """ทุกรอบ: คำนวณคำสั่งรอบนี้"""
        pass

    def exit(self):
        pass


class Passive(State):
    name = "Passive"

    def run(self, cmd, state, t):
        # TODO [3.2] set_header + fill_damping (q = มุมปัจจุบันทุกรอบ ทำไมสำคัญ? fsm_concepts.md)
        pass


class Hold(State):
    name = "Hold"

    def __init__(self):
        super().__init__()
        self.q_hold = None       # มุมทุกข้อต่อตอนเข้า

    def enter(self, cmd, state):
        # TODO [3.2] จด q ปัจจุบันของทุก slot ลง self.q_hold  (ทำครั้งเดียว ทำไมต้องอยู่ใน enter ไม่ใช่ run?)
        pass

    def run(self, cmd, state, t):
        # TODO [3.2] set_header · ทุก slot: mode 1, q = q_hold[i], dq 0, tau 0, kp = TRAIN_KP[i], kd = TRAIN_KD[i]
        # คำถาม: ถ้าเปลี่ยนไปใช้ "q ของ state ล่าสุด" แทน q_hold ทุกรอบ จะเกิดอะไร
        pass


class Wave(State):
    name = "Wave"

    def __init__(self):
        super().__init__()
        self.q_hold = None
        self.t_enter = None

    def enter(self, cmd, state):
        # TODO [3.4] จด q_hold (ทุก slot) และ t_enter = None (ให้ run รอบแรกเป็นคนจดเวลา) หรือจดเวลาตอนนี้เลย
        pass

    def run(self, cmd, state, t):
        # TODO [3.4] เหมือน Hold แต่ศอกซ้าย:  q = q_hold[ศอก] + A(τ) · sin(2π f τ)   τ = เวลาตั้งแต่เข้า
        # TODO [3.4] A(τ) = WAVE_AMP (rad) × min(1, τ / WAVE_RAMP_S)   ← "เข้าแบบนุ่ม" (แนวคิด Soft Start)
        # ทายก่อน: ถ้าไม่มี ramp (A คงที่ตั้งแต่ τ = 0) กราฟ q ของศอกตอนเข้าจะกระโดดไหม ทำไม (sin(0) = 0)
        #          แล้วถ้าใช้ cos แทน sin ล่ะ
        pass


# ---------------------------------------------------------------------------
# FSM
# ---------------------------------------------------------------------------
class MiniFSM:
    def __init__(self, keys: KeyInput):
        self.keys = keys
        self.states = {}             # ชื่อ → object
        self.current = None
        self.last_key = None         # คีย์ที่กดในรอบนี้ (pop ครั้งเดียวต่อรอบ แล้วให้ทุกเงื่อนไขใช้ร่วมกัน)
        self.state_age = 0.0         # อายุของ LowState ล่าสุด [s] (ใช้กับ timeout)

    def add(self, st: State):
        self.states[st.name] = st

    def key_is(self, k):
        """คืนฟังก์ชันเงื่อนไข "กดคีย์ k รอบนี้"  (เทียบ key_is ใน main.cpp ของ g1_ctrl)"""
        return lambda: self.last_key == k

    def setup_transitions(self):
        # TODO [3.2] Passive: (key 'o' → Hold)
        # TODO [3.2] Hold:    (key 'p' → Passive), (key 'w' → Wave)
        # TODO [3.4] Wave:    (key 'p' → Passive)
        # TODO [3.3] ทุก state: (LowState หายเกิน STATE_TIMEOUT_S → Passive)  ใส่ "ท้ายสุด" หรือ "แรกสุด" ดี? ทำไม
        #            (g1_ctrl ใส่ timeout ต่อท้ายทุก state ใน FSMState ctor)
        pass

    def change(self, name, cmd, state):
        # TODO [3.2] ถ้า name == ชื่อปัจจุบัน ไม่ต้องทำอะไร
        # TODO [3.2] print(f"FSM: {เดิม} -> {ใหม่}") · current.exit() · current = ... · current.enter(cmd, state)
        pass

    def tick(self, cmd, state, t, age):
        """1 รอบของ FSM (เทียบ CtrlFSM::run_())"""
        # TODO [3.2] self.last_key = self.keys.pop();  self.state_age = age
        # TODO [3.2] self.current.run(cmd, state, t)
        # TODO [3.2] วน self.current.checks: ตัวแรกที่จริง → self.change(...) แล้ว break (เปลี่ยนได้ครั้งเดียวต่อรอบ)
        # คำถาม: g1_ctrl เรียก run() ก่อนเช็ค transition แปลว่ารอบที่กดคีย์ คำสั่งที่ส่งออกไปเป็นของ state ไหน
        pass


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    keys = KeyInput()
    fsm = MiniFSM(keys)
    for st in (Passive(), Hold(), Wave()):
        fsm.add(st)
    fsm.setup_transitions()

    # TODO [3.2] init_dds()  (มี safety_guard ในตัว: lo + domain 1 เท่านั้น)
    # TODO [3.2] reader, sub = start_state_reader() · publisher rt/lowcmd · cmd = LowCmd เปล่า · crc
    # TODO [3.2] state = wait_for_state(reader)
    # TODO [3.2] fsm.current = Passive แล้วเรียก enter  (state แรกต้องเป็น Passive เสมอ เหมือน states[0] ของ g1_ctrl)
    print("คีย์: o = Hold, w = Wave (จาก Hold), p = Passive  (พิมพ์แล้วกด Enter)")

    # loop 500 Hz
    while True:
        # TODO [3.2] msg, age = reader.get()
        # TODO [3.3] ถ้า msg เก่า (age > timeout) ยังต้องเรียก fsm.tick ไหม? ใช้ state ไหนสร้างคำสั่ง?
        #            (ใบ้: ใช้ state ล่าสุดที่มี แต่ FSM ต้องเปลี่ยนเป็น Passive เอง)
        # TODO [3.2] fsm.tick(cmd, msg, t, age) → crc → Write
        # TODO [3.2] นัดเวลารอบถัดไปแบบสะสม (เหมือน run_control_loop ใน week2 common.py)
        # ทดสอบ 3.3: อยู่ใน Hold แล้วปิด sim → ทายก่อนว่าจะพิมพ์อะไร แล้วเปิด sim ใหม่ → อยู่ state ไหน
        print("mini_fsm: ยังไม่ได้เติม [3.2]")
        break   # TODO [3.2] ลบเมื่อใส่ sleep แล้ว


if __name__ == "__main__":
    main()
