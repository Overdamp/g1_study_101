"""policy_runner_skeleton.py: ให้ Python คุมหุ่นด้วย policy เอง (งาน 4.7 ท้าทาย)  ✅ ส่ง lowcmd (sim เท่านั้น)

ต่อยอด mini FSM สัปดาห์ 3:  Passive --s--> Stand (interpolate ไปท่า default 3 s) --g--> Policy (soft start 0.5 s)
                            ทุก state --p--> Passive · LowState หาย > 100 ms → Passive · เอียง > 0.85 rad → Passive
เทียบกับ g1_ctrl: Passive = State_Passive, Stand = State_FixStand, Policy = State_RLBase

สองจังหวะ (เหมือน g1_ctrl):
  loop 500 Hz  : ส่ง lowcmd (q_des ล่าสุด, kp/kd จาก deploy.yaml)
  ทุก 10 รอบ (50 Hz) ใน state Policy: obs → ONNX → q_des ใหม่

⚠️ sim เท่านั้น (safety_guard) · เท้าแตะพื้น (ไม่แขวน) · ห้ามรันพร้อม g1_ctrl (มีตัวเช็คให้แล้ว)
รัน:  conda activate g1_sdk && python week4/scripts/skelatons/policy_runner_skeleton.py
      ใน MuJoCo: Pause → Load key 0 (stand_ready) → Run แล้วพิมพ์ s (Enter) รอ 3 s แล้ว g (Enter)
"""

import sys
import threading
import time
from pathlib import Path

import numpy as np

from obs_skeleton import GaitPhase, PolicyConfig, action_to_q_des, build_obs, projected_gravity

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "week2" / "scripts" / "complete"))
# TODO [4.7] from common import init_dds, start_state_reader, wait_for_state, set_header, fill_damping, CONTROL_DT, STATE_TIMEOUT_S
# TODO [4.7] ChannelPublisher, ChannelSubscriber, LowCmd_, unitree_hg_msg_dds__LowCmd_, CRC

STAND_S = 3.0
SOFT_START_S = 0.5
TILT_LIMIT = 0.85        # rad (เท่า g1_ctrl)
POLICY_EVERY = 10        # 500 Hz / 10 = 50 Hz


def other_lowcmd_active(seconds: float = 0.5) -> bool:
    """ให้ไว้แล้ว (ความปลอดภัย): ฟัง rt/lowcmd สั้นๆ ถ้ามีคนส่งอยู่ (g1_ctrl?) คืน True  ต้องเรียกหลัง init_dds()"""
    from unitree_sdk2py.core.channel import ChannelSubscriber
    from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowCmd_
    seen = []
    sub = ChannelSubscriber("rt/lowcmd", LowCmd_)
    sub.Init(lambda m: seen.append(1), 10)
    time.sleep(seconds)
    sub.Close()
    return len(seen) > 0


def tilt(quat) -> float:
    """มุมเอียงจากแนวตั้ง [rad] จาก projected gravity (เท่า torso_tilt_exceeds ใน State_RLBase.cpp)"""
    # TODO [4.7] g = projected_gravity(quat);  return acos(clip(−g[2], −1, 1))
    return 0.0


class Runner:
    def __init__(self, cfg: PolicyConfig):
        self.cfg = cfg
        self.mode = "Passive"
        self.session = None              # TODO [4.7] InferenceSession(cfg.onnx_path)
        self.gp = GaitPhase(cfg)
        self.last_action = np.zeros(23, np.float32)
        self.q_des = None                # 23 ค่า (ลำดับ policy) ที่ส่งอยู่
        self.q_start = None              # ท่าตอนเข้า state (ใช้ interpolate / soft start)
        self.t_enter = 0.0
        self.tick_count = 0

    def enter(self, mode, msg, t):
        # TODO [4.7] พิมพ์ log การเปลี่ยน state · จด q_start = q ปัจจุบัน 23 ข้อต่อ (ตาม joint_ids_map), t_enter = t
        # TODO [4.7] ถ้าเข้า Policy: gp.reset(), last_action = 0, q_des = q_start (ยังไม่มี action)
        self.mode = mode

    def run(self, cmd, msg, t):
        # TODO [4.7] set_header + fill_damping ทุกรอบก่อน (slot ที่ไม่มีข้อต่อ = damping)
        # TODO [4.7] Passive: แค่นั้นพอ
        # TODO [4.7] Stand:  α = min(1, (t − t_enter)/STAND_S);  q = q_start + α(default − q_start)
        #                    ใส่ q, kp = stiffness, kd = damping ให้ 23 slot ตาม joint_ids_map
        # TODO [4.7] Policy: ทุก POLICY_EVERY รอบ → obs (cmd 0) → action → q_policy = action_to_q_des; last_action = action
        #                    soft start: β = min(1, (t − t_enter)/SOFT_START_S);  q_des = q_start + β(q_policy − q_start)
        #                    ใส่ q_des, kp, kd ให้ 23 slot
        # คำถาม: ระหว่าง policy step (9 รอบที่ไม่เรียก ONNX) ส่ง q_des อะไร
        pass

    def check_transitions(self, key, msg, age, t):
        """คืนชื่อ state ถัดไป (หรือ None)"""
        # TODO [4.7] age > STATE_TIMEOUT_S → "Passive"   (ทุก state)
        # TODO [4.7] mode == "Policy" และ tilt(quaternion) > TILT_LIMIT → "Passive"
        # TODO [4.7] key 'p' → Passive · Passive + 's' → Stand · Stand + 'g' → Policy (เฉพาะเมื่อ Stand ครบ 3 s แล้ว)
        return None


def main():
    cfg = PolicyConfig()
    runner = Runner(cfg)
    # TODO [4.7] init_dds()  (มี safety_guard: lo + domain 1 เท่านั้น)
    # TODO [4.7] if other_lowcmd_active(): print("มีโปรแกรมอื่นส่ง lowcmd อยู่ (g1_ctrl?) ปิดก่อน"); return
    # TODO [4.7] reader, sub = start_state_reader() · publisher rt/lowcmd · cmd = LowCmd เปล่า · crc · wait_for_state
    # TODO [4.7] KeyInput (ก็อปจาก week3 mini_fsm) · runner.enter("Passive", ...)
    print("คีย์: s = Stand, g = Policy (หลัง Stand 3 s), p = Passive")
    while True:
        # TODO [4.7] msg, age = reader.get() · key = keys.pop()
        # TODO [4.7] runner.run(...) → crc → Write · nxt = runner.check_transitions(...) → ถ้ามี: runner.enter(nxt, ...)
        # TODO [4.7] นัดเวลา 500 Hz แบบสะสม
        # ทายก่อน: ถ้าลืม soft start (β = 1 ทันที) step แรกของ Policy ข้อต่อไหนจะกระตุกมากสุด (vault Soft Start.md)
        print("policy_runner: ยังไม่ได้เติม [4.7]")
        break


if __name__ == "__main__":
    main()
