"""ilib.py: ไลบรารีกลางของโมดูล I (Isaac Lab + Newton) ฉบับสมบูรณ์

ส่วนนี้เป็น **Newton ล้วน** ไม่ต้องเปิด Isaac Sim/Kit จึงเร็ว (import ~3 s) ใช้ใน n1–n4
ส่วนที่ใช้ Isaac Lab (i1–i4) import ของตัวเองแยกต่างหาก

env:  source ~/g1_study/weekI_isaaclab/env.sh      (= conda deactivate + source env_isaaclab + EULA)
รันเทสต์:  python ilib.py        (GPU ว่าง ~0.5 GB · ~30 s ครั้งแรกเพราะ compile kernel, ครั้งต่อไป ~10 s)

สิ่งที่มีในไฟล์นี้
  POLICY_JOINTS / HOME / KP / KD / ARMATURE   ค่าของหุ่นเรียงตาม "ลำดับ policy" (= deploy.yaml)
  build_g1()          อ่าน MJCF ของ mjlab → ModelBuilder ของหุ่น 1 ตัว + ใส่ armature, PD gain, ท่าเริ่ม
  joint_table()       ตาราง joint: ชื่อ, q_start, qd_start, limit, armature, kp, kd
  make_model()        คัดลอกหุ่นเป็น W world (replicate) + พื้น → finalize เป็น Model บน GPU
  G1Sim               ห่อ Model/State/Control/Solver: set_target(), step(), q(), base_pos(), tilt()
                      step ผ่าน CUDA graph (บันทึก kernel ทั้งชุดครั้งเดียว แล้วเล่นซ้ำ)
  quat_xyzw_to_wxyz() Newton เก็บ quaternion เป็น (x, y, z, w) แต่ MuJoCo/mjlab/Isaac Lab ใช้ (w, x, y, z)

[skeleton] ทายก่อนรัน (เขียนคำตอบลงกระดาษก่อน แล้วค่อยรันเทสต์เทียบ)
  1. free joint ของ pelvis กิน coordinate (joint_q) กี่ช่อง และ dof (joint_qd) กี่ช่อง ทำไมไม่เท่ากัน
  2. joint_q_start ของเข่าซ้ายคือเท่าไร (เข่าเป็น joint ตัวที่ 4 ของขาซ้าย)
  3. ทำไม capture() ต้องบันทึก 2 step ไม่ใช่ 1
"""
from __future__ import annotations

import math
import os
import re
import time
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------- ที่อยู่ไฟล์
HOME_DIR = Path.home()
MJLAB = HOME_DIR / "nvidia/unitree/unitree_rl_mjlab"
XML = MJLAB / "src/assets/robots/unitree_g1/xmls/g1_23dof.xml"     # MJCF ที่ mjlab ใช้เทรน (collision เป็น capsule)
V0 = MJLAB / "deploy/robots/g1_23dof/config/policy/velocity/v0"    # policy P3b ที่ export แล้ว
DEPLOY_YAML = V0 / "params/deploy.yaml"
CKPT_P3B = V0 / "checkpoints/model_phase3b_15998.pt"               # checkpoint (rsl_rl) ที่ export เป็น v0
RL_LAB = HOME_DIR / "nvidia/unitree/unitree_rl_lab"                # repo Isaac Lab ของ Unitree (task G1 23-DoF)
ISAACLAB = HOME_DIR / "nvidia/IsaacLab-unitree"                    # Isaac Lab 3.0 worktree ที่ env_isaaclab ใช้
WEEKI = Path(__file__).resolve().parents[2]                        # ~/g1_study/weekI_isaaclab
LOGS = WEEKI / "logs"

TASK_FLAT = "Unitree-G1-23dof-Velocity-Flat"

# ---------------------------------------------------------------- ค่าของหุ่น (ลำดับ policy)
# ลำดับนี้ = DFS ของ MJCF = ลำดับใน deploy.yaml / ONNX metadata "joint_names"
POLICY_JOINTS = [
    "left_hip_pitch_joint", "left_hip_roll_joint", "left_hip_yaw_joint",
    "left_knee_joint", "left_ankle_pitch_joint", "left_ankle_roll_joint",
    "right_hip_pitch_joint", "right_hip_roll_joint", "right_hip_yaw_joint",
    "right_knee_joint", "right_ankle_pitch_joint", "right_ankle_roll_joint",
    "waist_yaw_joint",
    "left_shoulder_pitch_joint", "left_shoulder_roll_joint", "left_shoulder_yaw_joint",
    "left_elbow_joint", "left_wrist_roll_joint",
    "right_shoulder_pitch_joint", "right_shoulder_roll_joint", "right_shoulder_yaw_joint",
    "right_elbow_joint", "right_wrist_roll_joint",
]


def _reflected_inertia(rotor, gear):
    """armature ของเกียร์ planetary 2 ชั้น (สูตรเดียวกับ g1_23dof_constants.py ของ mjlab)"""
    return rotor[0] * (gear[1] * gear[2]) ** 2 + rotor[1] * gear[2] ** 2 + rotor[2]


ARM_5020 = _reflected_inertia((0.139e-4, 0.017e-4, 0.169e-4), (1, 1 + 46 / 18, 1 + 56 / 16))
ARM_7520_14 = _reflected_inertia((0.489e-4, 0.098e-4, 0.533e-4), (1, 4.5, 1 + 48 / 22))
ARM_7520_22 = _reflected_inertia((0.489e-4, 0.109e-4, 0.738e-4), (1, 4.5, 5))
W_N = 10 * 2 * math.pi      # ความถี่ธรรมชาติ 10 Hz
ZETA = 2.0                  # damping ratio 2 (overdamped)

# (regex, armature, effort limit)  ← ลำดับสำคัญ: ตัวแรกที่ match ชนะ
_GROUPS = [
    (r"ankle", 2 * ARM_5020, 50.0),                                  # ข้อเท้า = มอเตอร์ 5020 สองตัวผ่าน linkage
    (r"elbow|shoulder|wrist", ARM_5020, 25.0),
    (r"hip_pitch|hip_yaw|waist", ARM_7520_14, 88.0),
    (r"hip_roll|knee", ARM_7520_22, 139.0),
]
_HOME_RULES = {r"hip_pitch": -0.1, r"knee": 0.3, r"ankle_pitch": -0.2, r"shoulder_pitch": 0.35,
               r"elbow": 0.87, r"left_shoulder_roll": 0.18, r"right_shoulder_roll": -0.18}


def joint_params(name: str) -> dict:
    """armature / kp / kd / effort / ท่าเริ่ม ของ joint ชื่อนี้ (kp = J·ω², kd = 2ζ·J·ω)"""
    arm, eff = next((a, e) for p, a, e in _GROUPS if re.search(p, name))
    home = next((v for p, v in _HOME_RULES.items() if re.search(p, name)), 0.0)
    return dict(armature=arm, kp=arm * W_N**2, kd=2 * ZETA * arm * W_N, effort=eff, home=home)


ARMATURE = np.array([joint_params(n)["armature"] for n in POLICY_JOINTS])
KP = np.array([joint_params(n)["kp"] for n in POLICY_JOINTS])
KD = np.array([joint_params(n)["kd"] for n in POLICY_JOINTS])
EFFORT = np.array([joint_params(n)["effort"] for n in POLICY_JOINTS])
HOME = np.array([joint_params(n)["home"] for n in POLICY_JOINTS])
SCALE = 0.25 * EFFORT / KP       # action scale แบบ mjlab


# ---------------------------------------------------------------- import ช้า (warp/newton)
def quiet() -> None:
    """ปิดข้อความ "Module ... load on device" ของ warp ที่พิมพ์ทุก kernel"""
    import warp as wp
    wp.config.quiet = True
    os.environ.setdefault("PYTHONWARNINGS", "ignore")


def short_name(label: str) -> str:
    """Newton ตั้งชื่อ joint เป็น path ยาว 'g1_23dof_rev_1_0/worldbody/pelvis/.../left_knee_joint' → เอาท่อนท้าย"""
    return label.split("/")[-1]


def build_g1(floating: bool = True, armature: bool = True, gains: bool = True, home: bool = True,
             base_z: float = 0.8, gain_scale: float = 1.0):
    """อ่าน MJCF ของ mjlab เป็น ModelBuilder ของหุ่น 1 ตัว แล้วตั้งค่าที่ mjlab ตั้งด้วย Python (ไม่ได้อยู่ใน XML)

    floating=False → ตรึง pelvis ไว้กับโลก (เหมือนแขวนแน่นๆ) เหลือ 23 dof
    ค่าใน builder เป็น list ธรรมดา เรียงตาม dof ของหุ่นตัวนี้ → index ด้วย joint_qd_start / joint_q_start
    """
    import newton

    b = newton.ModelBuilder()
    newton.solvers.SolverMuJoCo.register_custom_attributes(b)   # ให้ builder มีช่องเก็บค่าเฉพาะของ MuJoCo
    b.add_mjcf(str(XML), floating=floating)
    for j, label in enumerate(b.joint_label):
        name = short_name(label)
        if name not in POLICY_JOINTS:          # floating_base (free joint) หรือ fixed
            continue
        p = joint_params(name)
        # TODO(n1) ตั้งค่า dof ของ joint นี้: d = index ใน joint_qd_start, q = index ใน joint_q_start
        pass  # ยังไม่ตั้ง → armature/kp/kd = 0, ท่าเริ่ม = 0
    if floating:
        b.joint_q[2] = base_z                  # free joint: q[0:3] = ตำแหน่ง, q[3:7] = quaternion (x,y,z,w)
    return b


def joint_table(b) -> list[dict]:
    """ตาราง joint จาก builder (หุ่น 1 ตัว)"""
    rows = []
    for j, label in enumerate(b.joint_label):
        # TODO(n1) เก็บ name, type, q_start, qd_start, ndof, lower, upper, armature, kp, kd ของแต่ละ joint
        rows.append(dict(name=short_name(label)))
    return rows


def make_model(proto, worlds: int = 1, spacing=(2.0, 2.0, 0.0), ground: bool = True):
    """คัดลอกหุ่น `worlds` ตัว (แต่ละตัวอยู่คนละ world ชนกันไม่ได้) + พื้น → Model บน GPU"""
    import newton

    # TODO(n2) builder ใหม่ → replicate(proto, worlds, spacing) → add_ground_plane() → finalize()
    raise NotImplementedError('TODO(n2) builder ใหม่ → replicate(proto, worlds, spacing) → add_ground_plane() → finalize()')


def quat_xyzw_to_wxyz(q: np.ndarray) -> np.ndarray:
    """(…, 4) xyzw → wxyz"""
    # TODO(n1) ย้ายช่องสุดท้าย (w) มาไว้หน้า
    raise NotImplementedError('TODO(n1) ย้ายช่องสุดท้าย (w) มาไว้หน้า')


def tilt_from_quat_xyzw(q: np.ndarray) -> np.ndarray:
    """มุมเอียงของลำตัว [rad] = มุมระหว่างแกน z ของ pelvis กับแกน z โลก (0 = ตั้งตรง)"""
    x, y = q[..., 0], q[..., 1]
    # แถว z ขององค์ประกอบ R[2,2] = 1 − 2(x² + y²)  → cos(tilt)
    # TODO(n2) คืน arccos(clip(1 - 2(x²+y²), -1, 1))
    raise NotImplementedError('TODO(n2) คืน arccos(clip(1 - 2(x²+y²), -1, 1))')


class G1Sim:
    """หุ่น G1 W ตัวใน Newton + SolverMuJoCo (MJWarp)

    ค่าเริ่มของ solver = ค่าที่ task Isaac Lab ของ Unitree ใช้ (unitree_rl_lab PhysicsCfg.newton)
    """

    SOLVER_DEFAULT = dict(njmax=300, nconmax=150, cone="pyramidal", impratio=1.0,
                          integrator="implicitfast", ls_parallel=True, ls_iterations=15)

    def __init__(self, worlds: int = 1, dt: float = 0.005, floating: bool = True, use_graph: bool = True,
                 proto=None, **solver_kwargs):
        import newton
        import warp as wp

        self.wp, self.newton = wp, newton
        self.proto = proto if proto is not None else build_g1(floating=floating)
        self.model = make_model(self.proto, worlds)
        self.W = worlds
        self.dt = dt
        self.floating = floating
        kw = dict(self.SOLVER_DEFAULT, **solver_kwargs)
        self.solver = newton.solvers.SolverMuJoCo(self.model, **kw)
        self.state_0, self.state_1 = self.model.state(), self.model.state()
        self.control = self.model.control()
        # body_q (ท่าของ body) คำนวณจาก joint_q ด้วย forward kinematics ก่อนเริ่ม
        newton.eval_fk(self.model, self.model.joint_q, self.model.joint_qd, self.state_0)

        # index ของ joint ตามลำดับ policy (ภายในหุ่น 1 ตัว)
        names = [short_name(lbl) for lbl in self.proto.joint_label]
        self.nq = self.proto.joint_coord_count       # coordinate ต่อ world (30 ถ้า floating)
        self.nd = self.proto.joint_dof_count         # dof ต่อ world (29 ถ้า floating)
        self.q_idx = np.array([self.proto.joint_q_start[names.index(n)] for n in POLICY_JOINTS])
        self.d_idx = np.array([self.proto.joint_qd_start[names.index(n)] for n in POLICY_JOINTS])
        self._target = np.array(self.control.joint_target_pos.numpy(), copy=True)
        self.graph = None
        self.steps = 0
        self.use_graph = use_graph and wp.get_device().is_cuda
        self._simulate()                              # รอบแรก = compile kernel (ช้า) + ห้าม capture ตอน compile
        if self.use_graph:
            self.capture()

    # ---------------- ฟิสิกส์
    def _simulate(self) -> None:
        """1 physics step"""
        # TODO(n2) clear_forces → solver.step(state_0, state_1, control, None, dt) → สลับ state_0/state_1
        raise NotImplementedError('TODO(n2) clear_forces → solver.step(state_0, state_1, control, None, dt) → สลับ state_0/state_1')

    def capture(self) -> None:
        """บันทึก 2 physics step เป็น CUDA graph (2 เพื่อให้ state_0/state_1 สลับกลับที่เดิมพอดี)

        graph จำ "ที่อยู่หน่วยความจำ" ไม่ได้จำ object python → ถ้าสลับจำนวนคี่ครั้ง state_0 ใน python
        จะชี้ไปอีกก้อน แต่ graph ยังเขียนก้อนเดิม
        """
        wp = self.wp
        # TODO(n2) with wp.ScopedCapture() as cap: เรียก _simulate() 2 ครั้ง → self.graph = cap.graph
        self.graph = None  # ยังไม่มี graph → step() จะเรียก _simulate() ทีละครั้ง (ช้ากว่าแต่ถูก)

    def step(self, n: int = 1) -> None:
        """เดินฟิสิกส์ n step (n คู่ถ้าใช้ graph)"""
        if self.graph is not None:
            assert n % 2 == 0, "graph บันทึกไว้ 2 step → n ต้องเป็นเลขคู่"
            for _ in range(n // 2):
                self.wp.capture_launch(self.graph)
        else:
            for _ in range(n):
                self._simulate()
        self.steps += n

    # ---------------- คำสั่ง / อ่านค่า
    def set_target(self, q_des) -> None:
        """q_des: (23,) หรือ (W, 23) ลำดับ policy → control.joint_target_pos"""
        q_des = np.broadcast_to(np.asarray(q_des, dtype=np.float32), (self.W, 23))
        t = self._target.reshape(self.W, self.nd)
        # TODO(n2) ใส่ q_des ลงช่อง d_idx ของทุก world แล้ว .assign() กลับเข้า control.joint_target_pos
        raise NotImplementedError('TODO(n2) ใส่ q_des ลงช่อง d_idx ของทุก world แล้ว .assign() กลับเข้า control.joint_target_pos')

    def q(self) -> np.ndarray:
        """มุม joint (W, 23) ลำดับ policy"""
        return self.state_0.joint_q.numpy().reshape(self.W, self.nq)[:, self.q_idx]

    def qd(self) -> np.ndarray:
        return self.state_0.joint_qd.numpy().reshape(self.W, self.nd)[:, self.d_idx]

    def base_pos(self) -> np.ndarray:
        assert self.floating
        return self.state_0.joint_q.numpy().reshape(self.W, self.nq)[:, 0:3]

    def base_quat_xyzw(self) -> np.ndarray:
        assert self.floating
        return self.state_0.joint_q.numpy().reshape(self.W, self.nq)[:, 3:7]

    def tilt(self) -> np.ndarray:
        return tilt_from_quat_xyzw(self.base_quat_xyzw())

    def solver_iters(self) -> np.ndarray:
        """จำนวน iteration ที่ solver ใช้จริงใน step ล่าสุด ต่อ world"""
        return self.solver.mjw_data.solver_niter.numpy()


# ---------------------------------------------------------------- policy P3b (ใช้ใน I5/I6)
class ActorMLP:
    """actor ของ P3b จาก checkpoint rsl_rl (.pt) แบบเขียนเอง (เหมือน weekR rlib.ActorMLP)

    obs 80 ลำดับ deploy.yaml → normalizer (x − mean)/(std + 0.01) → Linear/ELU ×3 → Linear → action 23 (ลำดับ policy)
    ไม่ต้องใช้ rsl_rl/onnx · ใช้ "mean" ของ action (ไม่สุ่ม) เหมือน deploy
    """

    EPS = 1e-2

    def __init__(self, ckpt_path: Path = CKPT_P3B, device: str = "cuda:0"):
        import torch

        sd = torch.load(ckpt_path, map_location=device, weights_only=False)["actor_state_dict"]
        self.mean, self.std = sd["obs_normalizer._mean"], sd["obs_normalizer._std"]
        self.layers = [(sd[f"mlp.{i}.weight"], sd[f"mlp.{i}.bias"]) for i in (0, 2, 4, 6)]
        self.obs_dim = self.mean.shape[-1]

    def __call__(self, obs):
        import torch

        x = (obs - self.mean) / (self.std + self.EPS)
        for k, (w, b) in enumerate(self.layers):
            x = x @ w.T + b
            if k < len(self.layers) - 1:
                x = torch.nn.functional.elu(x)
        return x


# ---------------------------------------------------------------- พิมพ์ตาราง
def print_table(rows: list[dict], cols: list[str] | None = None, fmt: dict | None = None) -> None:
    if not rows:
        print("(ว่าง)")
        return
    cols = cols or list(rows[0])
    fmt = fmt or {}

    def cell(r, c):
        v = r.get(c)
        if v is None:
            return "-"
        if c in fmt:
            return fmt[c].format(v)
        if isinstance(v, float):
            return f"{v:.4g}"
        return str(v)

    w = {c: max(len(c), *(len(cell(r, c)) for r in rows)) for c in cols}
    print("  ".join(c.ljust(w[c]) for c in cols))
    print("  ".join("-" * w[c] for c in cols))
    for r in rows:
        print("  ".join(cell(r, c).ljust(w[c]) for c in cols))


# ---------------------------------------------------------------- เทสต์
N_GPU_TESTS = 6


def run_tests() -> int:
    quiet()
    import yaml

    results = []

    def check(name, fn):
        try:
            ok, info = fn()
        except NotImplementedError:
            ok, info = False, "TODO"
        except Exception as e:  # noqa: BLE001
            ok, info = False, f"{type(e).__name__}: {e}"
        results.append(ok)
        print(f"  {'PASS' if ok else 'FAIL'}  {name}  {info}")

    dep = yaml.safe_load(open(DEPLOY_YAML))
    print("== ค่าคงที่ (ไม่ใช้ GPU)")
    check("KP ตรง deploy.yaml (±0.05)", lambda: (np.abs(KP - dep["stiffness"]).max() < 0.05,
                                                f"max diff {np.abs(KP - dep['stiffness']).max():.3f}"))
    check("HOME ตรง deploy.yaml", lambda: (np.allclose(HOME, dep["default_joint_pos"]), ""))
    check("quat xyzw→wxyz", lambda: (np.allclose(quat_xyzw_to_wxyz(np.array([0.1, 0.2, 0.3, 0.9])),
                                                 [0.9, 0.1, 0.2, 0.3]), ""))
    check("tilt ของ quat ตั้งตรง = 0, หมุนรอบ x 90° = π/2",
          lambda: (abs(tilt_from_quat_xyzw(np.array([0, 0, 0, 1.0]))) < 1e-9 and
                   abs(tilt_from_quat_xyzw(np.array([math.sin(math.pi / 4), 0, 0, math.cos(math.pi / 4)]))
                       - math.pi / 2) < 1e-6, ""))

    print("== builder (CPU)")
    b = build_g1()
    rows = joint_table(b)
    by = {r["name"]: r for r in rows}
    check("floating: joint 24, dof 29, coord 30",
          lambda: ((b.joint_count, b.joint_dof_count, b.joint_coord_count) == (24, 29, 30),
                   f"{b.joint_count}/{b.joint_dof_count}/{b.joint_coord_count}"))
    check("ลำดับ joint ใน MJCF = ลำดับ policy",
          lambda: ([r["name"] for r in rows if r["name"] in POLICY_JOINTS] == POLICY_JOINTS, ""))
    check("left_knee: qd_start 9, q_start 10 (free joint กิน dof 6 / coord 7)",
          lambda: ((by["left_knee_joint"]["qd_start"], by["left_knee_joint"]["q_start"]) == (9, 10),
                   f"{by['left_knee_joint']['qd_start']}/{by['left_knee_joint']['q_start']}"))
    check("left_knee kp ≈ 99.1, armature ≈ 0.0251",
          lambda: (abs(by["left_knee_joint"]["kp"] - 99.098) < 0.01 and
                   abs(by["left_knee_joint"]["armature"] - 0.02510) < 1e-4,
                   f"kp {by['left_knee_joint']['kp']:.3f}"))
    check("base เริ่มที่ z 0.8, quat (0,0,0,1)", lambda: (np.allclose(b.joint_q[2:7], [0.8, 0, 0, 0, 1]),
                                                     str(np.round(b.joint_q[2:7], 3))))
    bf = build_g1(floating=False)
    check("fixed base: dof 23", lambda: (bf.joint_dof_count == 23, str(bf.joint_dof_count)))

    print("== Model + solver (GPU)")
    t0 = time.time()
    n_before = len(results)
    try:
        sim = G1Sim(worlds=4)
        check("4 world: model dof = 4×29", lambda: (sim.model.joint_dof_count == 116, str(sim.model.joint_dof_count)))
        check("q() เริ่ม = HOME", lambda: (np.allclose(sim.q(), HOME, atol=1e-6), ""))
        sim.step(100)  # 0.5 s
        z = sim.base_pos()[:, 2]
        check("ทุก world ได้ผลเท่ากัน (deterministic)", lambda: (np.ptp(z) < 1e-5, f"z {z.round(4)}"))
        sim.step(300)  # รวม 2 s
        check("ยืนด้วย PD อย่างเดียว 2 s → ล้ม (pelvis z < 0.4)", lambda: (sim.base_pos()[:, 2].max() < 0.4,
                                                                       f"z {sim.base_pos()[0, 2]:.3f}"))

        sim2 = G1Sim(worlds=1, floating=False)
        tgt = HOME.copy()
        i = POLICY_JOINTS.index("left_elbow_joint")
        tgt[i] = HOME[i] + 0.3
        sim2.set_target(tgt)
        sim2.step(200)  # 1 s
        err = sim2.q()[0, i] - tgt[i]
        check("fixed base: ศอกซ้ายไปถึงเป้า +0.3 rad ใน 1 s (|err| < 0.02)", lambda: (abs(err) < 0.02, f"err {err:+.4f}"))

        simE = G1Sim(worlds=1, floating=False, use_graph=False)
        simE.set_target(tgt)
        simE.step(200)
        check("graph กับ eager ได้ผลเท่ากัน", lambda: (np.abs(simE.q() - sim2.q()).max() < 1e-5,
                                                   f"max diff {np.abs(simE.q() - sim2.q()).max():.2e}"))
    except NotImplementedError as e:
        print(f"  FAIL  ส่วน GPU หยุดที่ {e}")
        results.extend([False] * (N_GPU_TESTS - (len(results) - n_before)))
    print(f"  (ส่วน GPU ใช้ {time.time() - t0:.1f} s)")
    n = sum(results)
    print(f"\nผล {n}/{len(results)} PASS")
    return n


if __name__ == "__main__":
    run_tests()
