"""rlib.py: ไลบรารีกลางของโมดูล R (mjlab manager-based) ฉบับสมบูรณ์

ใช้ conda env `unitree_rl_mjlab` (มี mjlab, torch, rsl_rl) · ไม่แก้ repo หลัก (อ่าน/import อย่างเดียว)
รันเทสต์:  python rlib.py        (ต้องมี GPU ว่าง ~1 GB · ใช้เวลา ~20 วินาที)

สิ่งที่มีในไฟล์นี้
  setup_path()             ให้ import `src.tasks...` ของ repo ได้จากทุกโฟลเดอร์
  load_cfg()               โหลด config ของ task จาก registry (ยังไม่สร้าง env → เร็ว, ไม่ใช้ GPU)
  cfg_summary()            สรุปว่า config มี term อะไรใน manager ไหน
  diff_cfg()               เทียบ 2 config ว่า term ไหนเพิ่ม/หาย/ค่าต่าง
  fix_command()            ล็อกคำสั่งความเร็วให้คงที่ (ปิด heading, standing, curriculum ของคำสั่ง)
  make_env()               สร้าง ManagerBasedRlEnv จริง
  term_slices()            ตำแหน่ง [start, end) ของแต่ละ obs term ในเวกเตอร์ 80 / 95
  ActorMLP                 โหลด actor จาก checkpoint ของ rsl_rl (.pt) มาเป็น MLP ธรรมดา
  manual_reward()          คำนวณ reward รวมเองจาก term → เทียบกับ env.reward_buf
  StepTracer               ดักการเรียก method ของ manager ระหว่าง env.step() เพื่อดูลำดับ
"""
from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path

# ---------------------------------------------------------------- ค่าคงที่
REPO = Path.home() / "nvidia/unitree/unitree_rl_mjlab"
V0 = REPO / "deploy/robots/g1_23dof/config/policy/velocity/v0"
CKPT_P3B = V0 / "checkpoints/model_phase3b_15998.pt"   # checkpoint ที่ export เป็น v0
WEEKR = Path(__file__).resolve().parents[2]              # ~/g1_study/weekR_mjlab
LOGS = WEEKR / "logs"

FLAT = "Unitree-G1-23Dof-Flat"
ROUGH = "Unitree-G1-23Dof-Rough"
BLIND = "Unitree-G1-23Dof-Rough-Blind"

# manager ที่อยู่ใน ManagerBasedRlEnvCfg เป็น dict ของ term (actions/observations แยกจัดการ)
TERM_DICTS = ("rewards", "terminations", "events", "commands", "curriculum", "metrics")


def setup_path() -> None:
    """เพิ่ม REPO ใน sys.path + ปิด warning ที่ไม่เกี่ยว

    ทำไมต้องมี: config ของ repo import แบบ `import src.tasks.velocity.mdp` ซึ่งหาเจอเฉพาะเมื่อ
    โฟลเดอร์ REPO อยู่ใน sys.path (train.py รันจาก cwd = REPO เลยเจอเอง) เราเลยเพิ่มให้เอง
    """
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    warnings.filterwarnings("ignore")
    os.environ.setdefault("MUJOCO_GL", "egl")


def load_cfg(task: str = FLAT, num_envs: int = 4, play: bool = False):
    """โหลด ManagerBasedRlEnvCfg ของ task (deep copy จาก registry → แก้ได้ไม่กระทบตัวกลาง)"""
    setup_path()
    import mjlab.tasks  # noqa: F401  ← import แล้ว task ของ mjlab ลงทะเบียนตัวเอง
    import src.tasks  # noqa: F401    ← task ของ repo เรา (G1 23-DoF) ลงทะเบียนตัวเอง
    from mjlab.tasks.registry import load_env_cfg

    cfg = load_env_cfg(task, play=play)
    cfg.scene.num_envs = num_envs
    return cfg


def _func_name(func) -> str:
    """ชื่อฟังก์ชันของ term (term แบบ class ก็ได้ชื่อ class)"""
    return getattr(func, "__name__", type(func).__name__)


def cfg_summary(cfg) -> dict[str, dict[str, str]]:
    """{manager: {term: คำอธิบายสั้น}} สำหรับพิมพ์/เทียบ

    - observations แยกตาม group: key = "obs.actor", "obs.critic"
    - rewards แสดง weight, events แสดง mode, terminations แสดงว่าเป็น time_out ไหม
    """
    out: dict[str, dict[str, str]] = {}
    for group, gcfg in cfg.observations.items():
        out[f"obs.{group}"] = {
            name: f"{_func_name(t.func)}" + (" +noise" if t.noise is not None and gcfg.enable_corruption else "")
            for name, t in gcfg.terms.items() if t is not None
        }
    out["actions"] = {name: type(a).__name__ for name, a in cfg.actions.items()}
    for mgr in TERM_DICTS:
        terms = getattr(cfg, mgr)
        d = {}
        for name, t in terms.items():
            if t is None:
                continue
            if mgr == "rewards":
                d[name] = f"w={t.weight:g} {_func_name(t.func)}"
            elif mgr == "events":
                d[name] = f"{t.mode} {_func_name(t.func)}"
            elif mgr == "terminations":
                d[name] = f"{_func_name(t.func)}" + (" (time_out)" if t.time_out else "")
            elif mgr == "commands":
                d[name] = type(t).__name__
            else:
                d[name] = _func_name(t.func)
        out[mgr] = d
    return out


def diff_cfg(a, b) -> list[tuple[str, str, str, str]]:
    """เทียบ cfg_summary ของ a กับ b → [(manager, term, ค่าใน a, ค่าใน b)] เฉพาะที่ต่างกัน
    ไม่มีใน a/b แสดงเป็น "—"
    """
    sa, sb = cfg_summary(a), cfg_summary(b)
    rows = []
    for mgr in sorted(set(sa) | set(sb)):
        ta, tb = sa.get(mgr, {}), sb.get(mgr, {})
        for term in list(ta) + [t for t in tb if t not in ta]:
            va, vb = ta.get(term, "—"), tb.get(term, "—")
            if va != vb:
                rows.append((mgr, term, va, vb))
    return rows


def fix_command(cfg, vx: float = 0.5, vy: float = 0.0, wz: float = 0.0) -> None:
    """ล็อกคำสั่งความเร็วให้ทุก env ได้ (vx, vy, wz) ตลอด (ใช้วัดผล policy)

    ต้องปิด 3 อย่าง ไม่งั้นคำสั่งถูกเขียนทับ:
      1. heading_command: ถ้าเปิด wz จะถูกแทนด้วย 0.5 × heading error (rel_heading_envs = 1.0 = ทุก env)
      2. rel_standing_envs: 5% ของ env ถูกสั่งให้ยืน (คำสั่ง = 0)
      3. curriculum "command_vel": ตั้ง ranges ใหม่ทุกครั้งที่ reset
    ⚠️ คลาสคำสั่งที่ใช้จริงมาจาก mjlab (site-packages) ไม่ใช่ repo/src/.../velocity_command.py
       เพราะ velocity_env_cfg.py:27 import `UniformVelocityCommandCfg` จาก mjlab โดยตรง (ดู R1 --where)
    """
    tw = cfg.commands["twist"]
    tw.heading_command = False
    tw.ranges.heading = None
    tw.rel_standing_envs = 0.0
    tw.ranges.lin_vel_x = (vx, vx)
    tw.ranges.lin_vel_y = (vy, vy)
    tw.ranges.ang_vel_z = (wz, wz)
    cfg.curriculum.pop("command_vel", None)


def make_env(cfg, device: str | None = None):
    """สร้าง env จริง (คอมไพล์ MJCF + mujoco_warp บน GPU + สร้าง manager ทั้งหมด)"""
    setup_path()
    import torch
    from mjlab.envs import ManagerBasedRlEnv

    if device is None:
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
    return ManagerBasedRlEnv(cfg, device=device)


def term_slices(env, group: str = "actor") -> dict[str, tuple[int, int]]:
    """{term: (start, end)} ตำแหน่งของแต่ละ term ใน obs ที่ต่อกันแล้ว (concatenate_terms=True)

    อาศัยข้อเท็จจริง: ObservationManager ต่อ term ตามลำดับใน dict และเก็บขนาดไว้ใน
    `group_obs_term_dim[group]` เป็น list ของ tuple เช่น [(3,), (3,), (3,), (2,), (23,), ...]
    """
    om = env.observation_manager
    names = om.active_terms[group]
    dims = om.group_obs_term_dim[group]
    out, i = {}, 0
    for name, dim in zip(names, dims):
        n = 1
        for d in dim:          # dim ไม่รวม num_envs แล้ว เช่น (23,) หรือ (2, 3)
            n *= d
        out[name] = (i, i + n)
        i += n
    return out


class ActorMLP:
    """actor ของ rsl_rl แบบเขียนเอง: normalizer → Linear/ELU ×3 → Linear (mean ของ action)

    checkpoint (`torch.save` จาก runner.save) มี key:
      actor_state_dict: obs_normalizer._mean/_std (1, 80) · mlp.{0,2,4,6}.weight/bias · distribution.std_param (23,)
      critic_state_dict, optimizer_state_dict, iter, infos{env_state{common_step_counter}}
    ตอนใช้งานจริง (deploy / play) ใช้ "mean" ไม่สุ่ม → ไม่ต้องใช้ std_param
    """

    EPS = 1e-2  # rsl_rl EmpiricalNormalization: (x - mean) / (std + eps)

    def __init__(self, ckpt_path: Path = CKPT_P3B, device: str = "cpu"):
        import torch

        ck = torch.load(ckpt_path, map_location=device, weights_only=False)
        sd = ck["actor_state_dict"]
        self.mean = sd["obs_normalizer._mean"]
        self.std = sd["obs_normalizer._std"]
        # mlp.0, mlp.2, mlp.4, mlp.6 = Linear (เลขคี่ 1, 3, 5 คือ ELU ไม่มีน้ำหนัก)
        self.layers = [(sd[f"mlp.{i}.weight"], sd[f"mlp.{i}.bias"]) for i in (0, 2, 4, 6)]
        self.action_std = sd["distribution.std_param"]
        self.iter = ck.get("iter")
        self.env_state = ck.get("infos", {}).get("env_state", {})
        self.obs_dim = self.mean.shape[-1]
        self.act_dim = self.layers[-1][0].shape[0]

    def __call__(self, obs):
        import torch

        x = (obs - self.mean) / (self.std + self.EPS)
        for k, (w, b) in enumerate(self.layers):
            x = x @ w.T + b
            if k < len(self.layers) - 1:
                x = torch.nn.functional.elu(x)
        return x


def manual_reward(env):
    """reward รวมของ step ล่าสุด คำนวณเองจากค่าที่ RewardManager เก็บไว้

    RewardManager.compute(dt):  reward_buf = Σ func(env) × weight × dt
    และเก็บ `_step_reward[:, i]` = func × weight (ไม่คูณ dt) ไว้แสดงผล
    → Σ_i _step_reward[:, i] × dt ต้องเท่ากับ reward_buf
    """
    rm = env.reward_manager
    return rm._step_reward.sum(dim=1) * env.step_dt


class StepTracer:
    """ดักการเรียก method ของ manager/sim ระหว่าง env.step() แล้วจดลำดับ

    ใช้:  with StepTracer(env) as tr: env.step(a)   →   tr.calls = ["action.process_action", ...]
    วิธีทำ: แทน method บน "instance" ด้วยตัวห่อที่จดชื่อก่อนเรียกของจริง แล้วคืนของเดิมตอนออก
    """

    TARGETS = {
        "action": ("action_manager", ("process_action", "apply_action")),
        "sim": ("sim", ("step", "forward", "sense")),
        "termination": ("termination_manager", ("compute",)),
        "reward": ("reward_manager", ("compute",)),
        "command": ("command_manager", ("compute",)),
        "event": ("event_manager", ("apply",)),
        "curriculum": ("curriculum_manager", ("compute",)),
        "observation": ("observation_manager", ("compute",)),
    }

    def __init__(self, env):
        self.env = env
        self.calls: list[str] = []
        self._saved = []

    def _wrap(self, label, fn):
        def wrapper(*args, **kwargs):
            extra = f"({kwargs['mode']})" if "mode" in kwargs else ""
            self.calls.append(label + extra)
            return fn(*args, **kwargs)
        return wrapper

    def __enter__(self):
        for short, (attr, methods) in self.TARGETS.items():
            obj = getattr(self.env, attr)
            for m in methods:
                if hasattr(obj, m):
                    self._saved.append((obj, m))
                    setattr(obj, m, self._wrap(f"{short}.{m}", getattr(obj, m)))
        return self

    def __exit__(self, *exc):
        for obj, m in self._saved:
            delattr(obj, m)        # ลบตัวห่อบน instance → กลับไปใช้ method ของ class
        self._saved.clear()
        return False


def compress(calls: list[str]) -> list[str]:
    """ย่อรายการที่ซ้ำติดกัน: [a, b, a, b, a, b] → ["(a → b) ×3"] และ [x, x] → ["x ×2"]"""
    out: list[str] = []
    i = 0
    while i < len(calls):
        done = False
        for period in (2, 3, 4):                     # หา pattern ที่ซ้ำ สั้นสุดก่อน (decimation loop = 2 ตัว)
            pat = calls[i:i + period]
            if len(pat) < period:
                continue
            n = 1
            while calls[i + n * period:i + (n + 1) * period] == pat:
                n += 1
            if n > 1:
                out.append(f"({' → '.join(pat)}) ×{n}")
                i += n * period
                done = True
                break
        if done:
            continue
        n = 1
        while i + n < len(calls) and calls[i + n] == calls[i]:
            n += 1
        out.append(calls[i] + (f" ×{n}" if n > 1 else ""))
        i += n
    return out


def print_table(rows, headers) -> None:
    """พิมพ์ตารางง่ายๆ (ไม่ต้องพึ่ง library)"""
    rows = [[str(c) for c in r] for r in rows]
    w = [max(len(h), *(len(r[i]) for r in rows)) if rows else len(h) for i, h in enumerate(headers)]
    print("  ".join(h.ljust(w[i]) for i, h in enumerate(headers)))
    print("  ".join("-" * w[i] for i in range(len(headers))))
    for r in rows:
        print("  ".join(c.ljust(w[i]) for i, c in enumerate(r)))


# ---------------------------------------------------------------- เทสต์
def run_tests() -> bool:
    """เทสต์ 18 ข้อ · แต่ละข้อรับ lambda → ถ้า TODO ยังไม่เติมแล้ว error จะนับเป็น FAIL ไม่พังทั้งไฟล์"""
    import contextlib
    import io

    import torch

    results = []

    def check(name, fn):
        try:
            ok = bool(fn())
            why = ""
        except Exception as e:  # noqa: BLE001  (เทสต์: จับทุกอย่างแล้วรายงาน)
            ok, why = False, f"  ← {type(e).__name__}: {str(e).splitlines()[0][:70] if str(e) else ''}"
        results.append(ok)
        print(f"{'PASS' if ok else 'FAIL'}  {name}{why}")

    # --- ไม่ต้องสร้าง env (CPU, เร็ว)
    flat, blind = load_cfg(FLAT), load_cfg(BLIND)
    s = cfg_summary(flat) or {}
    check("cfg_summary: actor มี 7 term", lambda: len(s.get("obs.actor", {})) == 7)
    check("cfg_summary: reward pose w=1", lambda: s.get("rewards", {}).get("pose", "").startswith("w=1 "))
    check("cfg_summary: event push_robot = interval", lambda: s.get("events", {}).get("push_robot", "").startswith("interval"))
    d = diff_cfg(flat, blind) or []
    keys = {(m, t) for m, t, _, _ in d}
    check("diff_cfg: Blind มี curriculum terrain_levels เพิ่ม", lambda: ("curriculum", "terrain_levels") in keys)
    check("diff_cfg: track_linear_velocity w 1 → 2", lambda: any(t == "track_linear_velocity" and "w=2" in vb for _, t, _, vb in d))
    check("diff_cfg: obs actor เหมือนกัน (ไม่มีแถว obs.actor)", lambda: len(d) > 0 and not any(m == "obs.actor" for m, _, _, _ in d))
    c = load_cfg(FLAT)
    fix_command(c, 0.5)
    tw = c.commands["twist"]
    check("fix_command: ranges/heading/standing/curriculum",
          lambda: tw.ranges.lin_vel_x == (0.5, 0.5) and not tw.heading_command and tw.rel_standing_envs == 0.0
          and "command_vel" not in c.curriculum)
    check("compress: [a,b,a,b,a,b,c] → 2 รายการ", lambda: compress(["a", "b"] * 3 + ["c"]) == ["(a → b) ×3", "c"])

    # --- actor จาก checkpoint
    actor = ActorMLP()
    check("ActorMLP: obs 80 → action 23", lambda: actor.obs_dim == 80 and actor.act_dim == 23)
    check("ActorMLP: output shape (2, 23)", lambda: tuple(actor(torch.zeros(2, 80)).shape) == (2, 23))

    # --- env จริง (GPU) · ซ่อนตาราง [INFO] ของ mjlab
    c = load_cfg(FLAT, num_envs=2)
    with contextlib.redirect_stdout(io.StringIO()):
        env = make_env(c)
    env.reset()
    sl = term_slices(env, "actor") or {}
    check("term_slices: actor รวม 80", lambda: max(e for _, e in sl.values()) == 80)
    check("term_slices: joint_pos = [11, 34)", lambda: sl.get("joint_pos") == (11, 34))
    check("term_slices: critic รวม 95", lambda: max(e for _, e in term_slices(env, "critic").values()) == 95)
    a = torch.zeros(2, 23, device=env.device)
    env.step(a)
    check("manual_reward == reward_buf", lambda: torch.allclose(manual_reward(env), env.reward_buf, atol=1e-6))
    with StepTracer(env) as tr:
        env.step(a)
    check("StepTracer: apply_action ×4 (decimation)", lambda: tr.calls.count("action.apply_action") == 4)
    check("StepTracer: process_action ×1", lambda: tr.calls.count("action.process_action") == 1)
    check("StepTracer: ลำดับ termination → reward → observation",
          lambda: tr.calls.index("termination.compute") < tr.calls.index("reward.compute") < tr.calls.index("observation.compute"))
    check("StepTracer: ถอดตัวห่อแล้ว", lambda: "process_action" not in vars(env.action_manager))
    env.close()

    n = sum(results)
    print(f"\n{n}/{len(results)} PASS")
    return n == len(results)


if __name__ == "__main__":
    sys.exit(0 if run_tests() else 1)
