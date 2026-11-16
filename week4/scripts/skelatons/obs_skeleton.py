"""obs_skeleton.py: สร้าง observation 80 ตัวจาก LowState ให้ตรงกับ g1_ctrl (งาน 4.2, 4.6, 4.8)

ไฟล์นี้เป็น "ไลบรารี" ที่ policy_once / shadow_mode / policy_runner import ไปใช้
รันตรงๆ = รันเทสต์ (ไม่ต่อ DDS):  python week4/scripts/skelatons/obs_skeleton.py

อ้างอิง: week4/docs/observations.md (สูตรทุก term + โค้ด C++ ที่ต้องทำให้ตรง)
ลำดับ obs (80): base_ang_vel 3 · projected_gravity 3 · velocity_commands 3 · gait_phase 2 ·
               joint_pos_rel 23 · joint_vel_rel 23 · last_action 23
"""

import math
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import yaml

V0 = Path.home() / "nvidia/unitree/unitree_rl_mjlab/deploy/robots/g1_23dof/config/policy/velocity/v0"


class PolicyConfig:
    """ค่าจาก deploy.yaml ที่ต้องใช้สร้าง obs และแปลง action (ให้ไว้แล้ว)"""

    def __init__(self, policy_dir: Path = V0):
        d = yaml.safe_load(open(policy_dir / "params" / "deploy.yaml"))
        act = d["actions"]["JointPositionAction"]
        self.joint_ids_map = list(d["joint_ids_map"])                 # policy index → SDK slot
        self.default_joint_pos = np.array(d["default_joint_pos"], dtype=np.float32)
        self.action_scale = np.array(act["scale"], dtype=np.float32)
        self.action_offset = np.array(act["offset"], dtype=np.float32)
        self.stiffness = np.array(d["stiffness"], dtype=np.float32)
        self.damping = np.array(d["damping"], dtype=np.float32)
        self.step_dt = float(d["step_dt"])                            # 0.02 s (50 Hz)
        self.gait_period = float(d["observations"]["gait_phase"]["params"]["period"])   # 0.6 s
        self.cmd_ranges = d["commands"]["base_velocity"]["ranges"]
        self.obs_terms = list(d["observations"])                      # ลำดับ term
        self.onnx_path = policy_dir / "exported" / "policy.onnx"


# ---------------------------------------------------------------------------
# term ทีละตัว
# ---------------------------------------------------------------------------
def projected_gravity(quat) -> np.ndarray:
    """quat = (w, x, y, z) ของ IMU → แรงโน้มถ่วง (0,0,−1) ในกรอบลำตัว"""
    # TODO [4.2] สูตรใน observations.md:  gx = −2(xz − wy),  gy = −2(yz + wx),  gz = −(1 − 2(x² + y²))
    # TODO [4.8 ค] (ทำให้พัง) ลองกลับเครื่องหมายทั้งเวกเตอร์ แล้วดู q_des ใน shadow mode
    return np.zeros(3, dtype=np.float32)


def joint_pos_rel(msg, cfg: PolicyConfig) -> np.ndarray:
    # TODO [4.2] วน cfg.joint_ids_map: q ของ slot นั้น − default_joint_pos[i]   (23 ค่า เรียงตาม policy)
    # TODO [4.8 ก] ลองใช้ slot 0..22 ตรงๆ แทน joint_ids_map  ·  [4.8 ข] ลองไม่ลบ default
    return np.zeros(23, dtype=np.float32)


def joint_vel_rel(msg, cfg: PolicyConfig) -> np.ndarray:
    # TODO [4.2] dq ของแต่ละ slot ตาม joint_ids_map (default velocity = 0 จึงไม่ต้องลบ)
    return np.zeros(23, dtype=np.float32)


def clamp_command(cmd, cfg: PolicyConfig) -> np.ndarray:
    """(vx, vy, wz) clamp ตาม commands.base_velocity.ranges"""
    # TODO [4.2] clip แต่ละแกนด้วย lin_vel_x / lin_vel_y / ang_vel_z
    return np.zeros(3, dtype=np.float32)


class GaitPhase:
    """นาฬิกาจังหวะก้าว (เทียบ gait_phase_from_command ใน observations.h)"""

    def __init__(self, cfg: PolicyConfig):
        self.dt = cfg.step_dt
        self.period = cfg.gait_period
        self.phase = 0.0                 # 0..1

    def reset(self):
        self.phase = 0.0

    def step(self, cmd) -> np.ndarray:
        """เรียก 1 ครั้งต่อ policy step คืน (sin, cos) หรือ (0, 0) ถ้า |cmd| < 0.1"""
        # TODO [4.6] phase = (phase + dt / period) mod 1   ← เดินทุก step แม้ obs จะเป็น 0
        # TODO [4.6] ถ้า norm(cmd) < 0.1 คืน (0, 0) ไม่งั้น (sin 2πφ, cos 2πφ)
        # คำถาม: ทำไมต้องเดิน phase ก่อนเช็ค cmd (ลองสลับลำดับแล้วคิดว่าจะต่างจาก g1_ctrl ยังไง)
        return np.zeros(2, dtype=np.float32)


# ---------------------------------------------------------------------------
# รวมทั้งหมด
# ---------------------------------------------------------------------------
def build_obs(msg, cmd, last_action, phase_obs, cfg: PolicyConfig) -> np.ndarray:
    """คืน np.float32 shape (80,) เรียงตามลำดับ term ใน deploy.yaml"""
    # TODO [4.2] base_ang_vel = gyroscope (3)
    # TODO [4.2] ต่อ: ang_vel, projected_gravity(quaternion), clamp_command(cmd), phase_obs,
    #            joint_pos_rel, joint_vel_rel, last_action      → np.concatenate(...).astype(np.float32)
    # ทุก term scale = 1, clip = null ใน v0 (ถ้า policy อื่นมี scale ≠ 1 ต้องคูณ)
    return np.zeros(80, dtype=np.float32)


def action_to_q_des(action, cfg: PolicyConfig) -> np.ndarray:
    """raw action (23) → q_des (23) เรียงตาม policy  (actions.md)"""
    # TODO [4.3] offset + scale × action   (clip = null)
    return np.zeros(23, dtype=np.float32)


# ---------------------------------------------------------------------------
# เทสต์ (ให้ไว้แล้ว): รันไฟล์นี้ตรงๆ
# ---------------------------------------------------------------------------
def fake_lowstate(cfg: PolicyConfig, quat=(1.0, 0.0, 0.0, 0.0)):
    """LowState ปลอม: ยืนท่า default นิ่งสนิท ใช้ SimpleNamespace แทน message จริง (field ชื่อเดียวกัน)"""
    motors = [SimpleNamespace(q=0.0, dq=0.0) for _ in range(35)]
    for i, slot in enumerate(cfg.joint_ids_map):
        motors[slot].q = float(cfg.default_joint_pos[i])
    imu = SimpleNamespace(quaternion=list(quat), gyroscope=[0.0, 0.0, 0.0], rpy=[0.0, 0.0, 0.0])
    return SimpleNamespace(motor_state=motors, imu_state=imu, mode_machine=4)


def run_tests():
    cfg = PolicyConfig()
    ok = True

    def check(name, cond):
        nonlocal ok
        ok &= bool(cond)
        print(f"  {'PASS' if cond else 'FAIL'}  {name}")

    print("projected_gravity")
    check("identity → (0,0,−1)", np.allclose(projected_gravity((1, 0, 0, 0)), [0, 0, -1], atol=1e-6))
    p = 0.2
    g = projected_gravity((math.cos(p / 2), 0, math.sin(p / 2), 0))
    check("pitch +0.2 → gx ≈ +sin(0.2)", abs(g[0] - math.sin(p)) < 1e-5)
    r = projected_gravity((math.cos(p / 2), math.sin(p / 2), 0, 0))
    check("roll +0.2 → gy ≈ −sin(0.2)", abs(r[1] + math.sin(p)) < 1e-5)

    print("build_obs (ยืนท่า default นิ่ง)")
    msg = fake_lowstate(cfg)
    obs = build_obs(msg, (0.0, 0.0, 0.0), np.zeros(23, np.float32), np.zeros(2, np.float32), cfg)
    check("shape (80,) float32", obs.shape == (80,) and obs.dtype == np.float32)
    check("gravity = (0,0,−1) ที่ index 3–5", np.allclose(obs[3:6], [0, 0, -1], atol=1e-6))
    check("joint_pos_rel ≈ 0 (index 11–33)", np.allclose(obs[11:34], 0, atol=1e-6))
    msg.motor_state[18].q += 0.1                                  # ขยับศอกซ้าย
    obs2 = build_obs(msg, (0.0, 0.0, 0.0), np.zeros(23, np.float32), np.zeros(2, np.float32), cfg)
    check("ศอกซ้าย (slot 18) อยู่ที่ obs index 11+16 = 27", abs(obs2[27] - 0.1) < 1e-6)
    check("command clamp: vx 2.0 → 1.0", abs(clamp_command((2.0, 0, 0), cfg)[0] - 1.0) < 1e-6)

    print("gait_phase")
    gp = GaitPhase(cfg)
    check("cmd 0 → (0,0)", np.allclose(gp.step((0, 0, 0)), 0))
    gp.reset()
    v = [gp.step((0.5, 0, 0)) for _ in range(30)]
    check("cmd 0.5: ครบ 30 step = 1 รอบ (กลับมา sin≈0, cos≈1)", np.allclose(v[-1], [0, 1], atol=1e-5))

    print("action_to_q_des")
    check("action 0 → default pose", np.allclose(action_to_q_des(np.zeros(23), cfg), cfg.default_joint_pos))
    print("ผ่านทั้งหมด ✅" if ok else "ยังมี FAIL: เติม TODO แล้วรันใหม่")


if __name__ == "__main__":
    run_tests()
