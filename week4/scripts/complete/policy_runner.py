"""policy_runner.py: ให้ Python คุมหุ่นด้วย policy เอง (งาน 4.7) ฉบับสมบูรณ์  ✅ ส่ง lowcmd (sim เท่านั้น)

    Passive --s--> Stand (interpolate ไปท่า default 3 s) --g--> Policy (soft start 0.5 s)
    ทุก state --p--> Passive · LowState หาย > 100 ms → Passive · Policy: เอียง > 0.85 rad → Passive
เทียบ g1_ctrl: Passive = State_Passive, Stand = State_FixStand (แต่ใช้ gain ตอนเทรน), Policy = State_RLBase

สองจังหวะเหมือน g1_ctrl: loop 500 Hz ส่ง lowcmd · ทุก 10 รอบ (50 Hz) ใน Policy: obs → ONNX → q_des ใหม่
⚠️ sim เท่านั้น (safety_guard) · เท้าแตะพื้น · ไม่ยอมรันถ้ามีโปรแกรมอื่นส่ง lowcmd (g1_ctrl)
รัน:  conda activate g1_sdk && python week4/scripts/complete/policy_runner.py
      MuJoCo: Pause → Load key 0 (stand_ready) → Run · แล้วพิมพ์ s (Enter) รอ 3 s แล้ว g (Enter)
"""

import math
import sys
import threading
import time
from pathlib import Path

import numpy as np

from obs import GaitPhase, Policy, PolicyConfig, action_to_q_des, build_obs, projected_gravity

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "week2" / "scripts" / "complete"))
from common import (CONTROL_DT, STATE_TIMEOUT_S, fill_damping, init_dds, set_header,  # noqa: E402  # pyrefly: ignore[missing-import]
                    start_state_reader, wait_for_state)
from unitree_sdk2py.core.channel import ChannelPublisher, ChannelSubscriber  # noqa: E402
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowCmd_  # noqa: E402
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowCmd_  # noqa: E402
from unitree_sdk2py.utils.crc import CRC  # noqa: E402

STAND_S = 3.0
SOFT_START_S = 0.5
TILT_LIMIT = 0.85
POLICY_EVERY = 10


def other_lowcmd_active(seconds: float = 0.5) -> bool:
    """ฟัง rt/lowcmd สั้นๆ ถ้ามีคนส่งอยู่ (g1_ctrl?) คืน True  ต้องเรียกหลัง init_dds() และก่อนสร้าง publisher ของเรา"""
    seen = []
    sub = ChannelSubscriber("rt/lowcmd", LowCmd_)
    sub.Init(lambda m: seen.append(1), 10)
    time.sleep(seconds)
    sub.Close()
    return len(seen) > 0


def tilt(quat) -> float:
    """มุมเอียงจากแนวตั้ง (torso_tilt_exceeds ใน State_RLBase.cpp)"""
    g = projected_gravity(quat)
    return math.acos(float(np.clip(-g[2], -1.0, 1.0)))


class KeyInput:
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


class Runner:
    def __init__(self, cfg: PolicyConfig):
        self.cfg = cfg
        self.ids = cfg.joint_ids_map
        self.mode = None
        self.policy = Policy(cfg.onnx_path)
        self.gp = GaitPhase(cfg)
        self.last_action = np.zeros(23, np.float32)
        self.q_policy = None             # q_des ล่าสุดจาก policy (ลำดับ policy)
        self.q_start = None
        self.t_enter = 0.0
        self.ticks = 0

    def current_q(self, msg) -> np.ndarray:
        return np.array([msg.motor_state[s].q for s in self.ids], np.float32)

    def enter(self, mode, msg, t, why=""):
        print(f"FSM: {self.mode or '-'} -> {mode}{f'  ({why})' if why else ''}", flush=True)
        self.mode = mode
        self.q_start = self.current_q(msg)
        self.t_enter = t
        self.ticks = 0
        if mode == "Policy":
            self.gp.reset()
            self.last_action = np.zeros(23, np.float32)       # เหมือน env->reset() ของ g1_ctrl
            self.q_policy = self.q_start.copy()

    def write_joints(self, cmd, q):
        """ใส่ q, kp, kd (จาก deploy.yaml) ให้ 23 slot ตาม joint_ids_map"""
        for i, s in enumerate(self.ids):
            m = cmd.motor_cmd[s]
            m.q = float(q[i])
            m.dq = 0.0
            m.tau = 0.0
            m.kp = float(self.cfg.stiffness[i])
            m.kd = float(self.cfg.damping[i])

    def run(self, cmd, msg, t):
        set_header(cmd, msg)
        fill_damping(cmd, msg)                                # slot ว่าง + Passive = หนืด
        if self.mode == "Stand":
            a = min(1.0, (t - self.t_enter) / STAND_S)
            self.write_joints(cmd, self.q_start + a * (self.cfg.default_joint_pos - self.q_start))
        elif self.mode == "Policy":
            if self.ticks % POLICY_EVERY == 0:                # 50 Hz: คิด action ใหม่
                obs = build_obs(msg, (0.0, 0.0, 0.0), self.last_action, self.gp.step((0.0, 0.0, 0.0)), self.cfg)
                action = self.policy.act(obs)
                self.q_policy = action_to_q_des(action, self.cfg)
                self.last_action = action                     # raw action (ไม่ใช่ q_des)
            # อีก 9 รอบ: ส่ง q_policy เดิมซ้ำ (เหมือน g1_ctrl ที่ FSM 1 kHz อ่าน processed_actions ล่าสุด)
            b = min(1.0, (t - self.t_enter) / SOFT_START_S)  # soft start
            self.write_joints(cmd, self.q_start + b * (self.q_policy - self.q_start))
        self.ticks += 1

    def check(self, key, msg, age, t):
        if age > STATE_TIMEOUT_S and self.mode != "Passive":
            return "Passive", f"LowState หาย {age * 1e3:.0f} ms"
        if self.mode == "Policy" and tilt(msg.imu_state.quaternion) > TILT_LIMIT:
            return "Passive", "เอียงเกิน 0.85 rad"
        if key == "p" and self.mode != "Passive":
            return "Passive", "คีย์ p"
        if key == "s" and self.mode == "Passive":
            return "Stand", ""
        if key == "g" and self.mode == "Stand":
            if t - self.t_enter < STAND_S:
                print("ยังยืนไม่ครบ 3 s รอก่อน", flush=True)
                return None, ""
            return "Policy", ""
        return None, ""


def main():
    cfg = PolicyConfig()
    runner = Runner(cfg)
    init_dds()                                            # safety_guard: lo + domain 1 เท่านั้น
    if other_lowcmd_active():
        raise SystemExit("มีโปรแกรมอื่นส่ง rt/lowcmd อยู่ (g1_ctrl?) ปิดก่อน")
    reader, _sub = start_state_reader()
    pub = ChannelPublisher("rt/lowcmd", LowCmd_)
    pub.Init()
    cmd = unitree_hg_msg_dds__LowCmd_()
    crc = CRC()
    keys = KeyInput()
    msg = wait_for_state(reader)
    runner.enter("Passive", msg, 0.0)
    print("คีย์: s = Stand, g = Policy (หลัง Stand 3 s), p = Passive  (พิมพ์แล้ว Enter)", flush=True)

    t0 = time.monotonic()
    next_t = t0
    next_report = 0.0
    while True:
        t = time.monotonic() - t0
        msg, age = reader.get()
        runner.run(cmd, msg, t)
        cmd.crc = crc.Crc(cmd)
        pub.Write(cmd)
        nxt, why = runner.check(keys.pop(), msg, age, t)
        if nxt:
            runner.enter(nxt, msg, t, why)
        if t >= next_report:
            next_report = t + 1.0
            print(f"[{t:6.1f}s] {runner.mode:<7} tilt {math.degrees(tilt(msg.imu_state.quaternion)):5.1f}°", flush=True)
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
        print("\nออกแล้ว: sim ใช้คำสั่งสุดท้ายต่อ (ถ้าออกตอน Stand/Policy ข้อต่อยังค้าง kp อยู่)")
