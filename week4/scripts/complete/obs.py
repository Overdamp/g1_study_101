"""obs.py: สร้าง observation 80 ตัวจาก LowState ให้ตรงกับ g1_ctrl (งาน 4.2, 4.3, 4.6) ฉบับสมบูรณ์

ไลบรารีที่ policy_once / shadow_mode / policy_runner ใช้ · รันตรงๆ = เทสต์ 11 ข้อ (ไม่ต่อ DDS)
อ้างอิง C++: deploy/include/unitree_articulation.h (update), isaaclab/envs/mdp/observations/observations.h,
            isaaclab/envs/mdp/actions/joint_actions.h  · docs: week4/docs/observations.md, actions.md

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
    """ค่าจาก deploy.yaml ที่ใช้สร้าง obs และแปลง action"""

    def __init__(self, policy_dir: Path = V0):
        d = yaml.safe_load(open(policy_dir / "params" / "deploy.yaml"))
        act = d["actions"]["JointPositionAction"]
        self.joint_ids_map = list(d["joint_ids_map"])                 # policy index → SDK slot
        self.default_joint_pos = np.array(d["default_joint_pos"], dtype=np.float32)
        self.action_scale = np.array(act["scale"], dtype=np.float32)
        self.action_offset = np.array(act["offset"], dtype=np.float32)
        self.stiffness = np.array(d["stiffness"], dtype=np.float32)
        self.damping = np.array(d["damping"], dtype=np.float32)
        self.step_dt = float(d["step_dt"])
        self.gait_period = float(d["observations"]["gait_phase"]["params"]["period"])
        self.cmd_ranges = d["commands"]["base_velocity"]["ranges"]
        self.obs_terms = list(d["observations"])
        self.onnx_path = policy_dir / "exported" / "policy.onnx"
        # v0: ทุก term scale = 1, clip = null, history_length = 1 → ตรวจไว้ ถ้า policy อื่นไม่ใช่แบบนี้ ไฟล์นี้ต้องแก้
        for name, t in d["observations"].items():
            if t.get("history_length", 1) != 1 or t.get("clip") is not None or any(s != 1.0 for s in t["scale"]):
                raise ValueError(f"obs term {name}: รองรับแค่ scale 1 / no clip / history 1 (แบบ v0)")


# ---------------------------------------------------------------------------
# term ทีละตัว
# ---------------------------------------------------------------------------
def projected_gravity(quat) -> np.ndarray:
    """(w, x, y, z) → R(q)ᵀ · (0, 0, −1)  = แรงโน้มถ่วงในกรอบลำตัว  (C++: root_quat_w.conjugate() * GRAVITY_VEC_W)"""
    w, x, y, z = (float(v) for v in quat)
    return np.array([
        -2.0 * (x * z - w * y),
        -2.0 * (y * z + w * x),
        -(1.0 - 2.0 * (x * x + y * y)),
    ], dtype=np.float32)


def joint_pos_rel(msg, cfg: PolicyConfig, joint_ids=None, default=None) -> np.ndarray:
    """q[slot] − default  เรียงตาม policy (joint_ids_map)
    joint_ids / default ใช้ทำให้พังในงาน 4.8 (ปกติไม่ต้องใส่)"""
    ids = cfg.joint_ids_map if joint_ids is None else joint_ids
    dflt = cfg.default_joint_pos if default is None else default
    q = np.array([msg.motor_state[s].q for s in ids], dtype=np.float32)
    return q - dflt


def joint_vel_rel(msg, cfg: PolicyConfig, joint_ids=None) -> np.ndarray:
    ids = cfg.joint_ids_map if joint_ids is None else joint_ids
    return np.array([msg.motor_state[s].dq for s in ids], dtype=np.float32)


def clamp_command(cmd, cfg: PolicyConfig) -> np.ndarray:
    r = cfg.cmd_ranges
    return np.array([
        np.clip(cmd[0], *r["lin_vel_x"]),
        np.clip(cmd[1], *r["lin_vel_y"]),
        np.clip(cmd[2], *r["ang_vel_z"]),
    ], dtype=np.float32)


class GaitPhase:
    """นาฬิกาจังหวะก้าว (gait_phase_from_command): เดินทุก policy step แม้ obs จะเป็น 0"""

    def __init__(self, cfg: PolicyConfig):
        self.dt = cfg.step_dt
        self.period = cfg.gait_period
        self.phase = 0.0

    def reset(self):
        self.phase = 0.0

    def step(self, cmd) -> np.ndarray:
        # เหมือน C++: เดิน phase ก่อน แล้วค่อยเช็ค cmd (ถ้าสลับลำดับ phase จะหยุดตอนยืน และไม่ตรงกับ g1_ctrl ตอนเริ่มเดิน)
        self.phase = math.fmod(self.phase + self.dt / self.period, 1.0)
        if math.sqrt(sum(float(c) ** 2 for c in cmd)) < 0.1:
            return np.zeros(2, dtype=np.float32)
        a = 2.0 * math.pi * self.phase
        return np.array([math.sin(a), math.cos(a)], dtype=np.float32)


# ---------------------------------------------------------------------------
# รวม
# ---------------------------------------------------------------------------
def build_obs(msg, cmd, last_action, phase_obs, cfg: PolicyConfig, joint_ids=None, default=None) -> np.ndarray:
    """(80,) float32 เรียงตาม deploy.yaml · last_action = action ดิบของ step ก่อน (ไม่ใช่ q_des)"""
    imu = msg.imu_state
    return np.concatenate([
        np.asarray(imu.gyroscope, dtype=np.float32),          # base_ang_vel (gyro ตรงๆ)
        projected_gravity(imu.quaternion),                     # projected_gravity
        clamp_command(cmd, cfg),                               # velocity_commands
        np.asarray(phase_obs, dtype=np.float32),               # gait_phase
        joint_pos_rel(msg, cfg, joint_ids, default),           # joint_pos_rel
        joint_vel_rel(msg, cfg, joint_ids),                    # joint_vel_rel
        np.asarray(last_action, dtype=np.float32),             # last_action
    ]).astype(np.float32)


def action_to_q_des(action, cfg: PolicyConfig) -> np.ndarray:
    """q_des = offset + scale × action  (clip = null, ไม่มี arm EMA ใน v0)"""
    return cfg.action_offset + cfg.action_scale * np.asarray(action, dtype=np.float32)


class Policy:
    """เปิด ONNX ครั้งเดียว แล้วเรียก act(obs) ได้เรื่อยๆ"""

    def __init__(self, onnx_path: Path):
        import onnxruntime as ort
        self.session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name           # "obs"

    def act(self, obs: np.ndarray) -> np.ndarray:
        x = np.asarray(obs, dtype=np.float32)[None, :]                 # (1, 80) float32
        return self.session.run(None, {self.input_name: x})[0][0]     # (23,)


# ---------------------------------------------------------------------------
# เทสต์
# ---------------------------------------------------------------------------
def fake_lowstate(cfg: PolicyConfig, quat=(1.0, 0.0, 0.0, 0.0)):
    """LowState ปลอม: ยืนท่า default นิ่งสนิท (field ชื่อเดียวกับ message จริง)"""
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
    msg.motor_state[18].q += 0.1
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
    print("ผ่านทั้งหมด ✅" if ok else "ยังมี FAIL")


if __name__ == "__main__":
    run_tests()
