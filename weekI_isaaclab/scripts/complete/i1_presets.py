"""I1: config ของ task G1 23-DoF ใน Isaac Lab + ระบบ preset (PhysX ↔ Newton) โดยไม่ต้องเปิด Kit

    python i1_presets.py                 # ทุกส่วน (~5 s)
    python i1_presets.py --diff-only     # เฉพาะส่วนที่ต่างระหว่าง preset default กับ newton

ส่วนที่พิมพ์
  [1] PresetCfg อยู่ตรงไหนใน config tree บ้าง และแต่ละจุดมีตัวเลือกอะไร
  [2] resolve_presets(cfg, {"newton"}) เปลี่ยนอะไรไปบ้าง (diff ทุก field)
  [3] ค่าของ solver ที่ task ตั้ง vs ค่าเริ่มของ MJWarpSolverCfg (ถ้าไม่ตั้งจะได้อะไร)
  [4] task Isaac vs สัญญา deploy ของ mjlab (deploy.yaml): obs, action scale, gain, dt
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import ilib  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--diff-only", action="store_true")
args = ap.parse_args()

import numpy as np  # noqa: E402
import unitree_rl_lab.tasks  # noqa: E402,F401  ← import แล้ว gym.register task ของ Unitree
import yaml  # noqa: E402
from isaaclab_newton.physics import MJWarpSolverCfg  # noqa: E402
from isaaclab_tasks.utils.hydra import collect_presets, resolve_presets  # noqa: E402
from isaaclab_tasks.utils.parse_cfg import load_cfg_from_registry  # noqa: E402


def load(preset: str | None):
    cfg = load_cfg_from_registry(ilib.TASK_FLAT, "env_cfg_entry_point")   # ได้ object ใหม่ทุกครั้ง
    return cfg if preset is None else resolve_presets(cfg, {preset})


def flatten(d, prefix=""):
    """dict ซ้อน → {"a.b.c": value}"""
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    else:
        out[prefix] = d
    return out


def diff_cfg(a, b) -> list[tuple[str, object, object]]:
    """field ที่ต่างกันระหว่าง 2 config (เทียบผ่าน to_dict)"""
    # >>>TODO(I1) flatten(a.to_dict()) กับ flatten(b.to_dict()) → คืน [(path, ค่า a, ค่า b)] ที่ไม่เท่ากัน
    fa, fb = flatten(a.to_dict()), flatten(b.to_dict())
    rows = []
    for k in sorted(set(fa) | set(fb)):
        va, vb = fa.get(k, "<ไม่มี>"), fb.get(k, "<ไม่มี>")
        if repr(va) != repr(vb):
            rows.append((k, va, vb))
    return rows
    # <<<TODO


def short(v, n=60):
    s = repr(v)
    return s if len(s) <= n else s[: n - 3] + "..."


# ---------------------------------------------------------------- [1]
raw = load(None)
if not args.diff_only:
    print("[1] PresetCfg ใน config ของ", ilib.TASK_FLAT)
    for path, alts in collect_presets(raw).items():
        print(f"    {path:24s} " + " · ".join(f"{k}={type(v).__name__}" for k, v in alts.items()))
    print("    → CLI `presets=newton` = เลือก field ชื่อ newton ของทุก PresetCfg (ไม่มี field นั้น = ใช้ default)")

# ---------------------------------------------------------------- [2]
d = diff_cfg(load("physx"), load("newton"))
print(f"\n[2] physx → newton: ต่างกัน {len(d)} field")
groups = {}
for k, va, vb in d:
    top = ".".join(k.split(".")[:2])
    groups.setdefault(top, []).append((k, va, vb))
for top, items in groups.items():
    print(f"  {top}  ({len(items)} field)")
    for k, va, vb in items[:6]:
        print(f"      {k:55s} {short(va, 38):40s} → {short(vb, 38)}")
    if len(items) > 6:
        print(f"      ... อีก {len(items) - 6}")
if args.diff_only:
    sys.exit()

# ---------------------------------------------------------------- [3]
newton_cfg = load("newton").sim.physics
task = newton_cfg.solver_cfg
default = MJWarpSolverCfg()
print("\n[3] MJWarpSolverCfg: ค่าที่ task ตั้ง vs ค่าเริ่มของคลาส")
rows = []
for f in ("njmax", "nconmax", "iterations", "ls_iterations", "solver", "integrator", "cone", "impratio",
          "ls_parallel", "use_mujoco_contacts", "tolerance"):
    rows.append(dict(field=f, task=getattr(task, f), class_default=getattr(default, f),
                     same="" if getattr(task, f) == getattr(default, f) else "≠"))
ilib.print_table(rows)
print(f"    NewtonCfg: num_substeps {newton_cfg.num_substeps} · use_cuda_graph {newton_cfg.use_cuda_graph} · "
      f"collision_cfg {newton_cfg.collision_cfg}")
print("    ⚠ class default integrator = euler: damping ของ PD ถูกคิดแบบ explicit (N4: gain สูง + euler → ล้ม)")

# ---------------------------------------------------------------- [4]
cfg = load("newton")
dep = yaml.safe_load(open(ilib.DEPLOY_YAML))
print("\n[4] task Isaac (unitree_rl_lab) vs สัญญา deploy ของ policy mjlab (deploy.yaml)")
pol = cfg.observations.policy
terms = [k for k, v in pol.to_dict().items() if isinstance(v, dict) and "func" in v]
print(f"    obs ของ policy (Isaac):  {terms}")
print(f"                             history_length {pol.history_length} · corruption {pol.enable_corruption}")
print(f"    obs ของ deploy (mjlab):  {list(dep['observations'])}")
print(f"                             history_length "
      f"{[dep['observations'][k].get('history_length', 1) for k in dep['observations']]}")
print("    → policy ที่เทรนจาก task Isaac นี้ ใช้กับ g1_ctrl/deploy.yaml ของ mjlab ตรงๆ ไม่ได้ (obs คนละชุด)")
print("      cross-sim จึงสร้าง obs เองจาก deploy.yaml (play_deploy_onnx.py) ไม่ใช้ observation manager ของ task")

# >>>TODO(I1) เทียบ action scale ของ task (cfg.actions.JointPositionAction.scale: dict regex → ค่า) กับ deploy.yaml
import re  # noqa: E402

sc = cfg.actions.JointPositionAction.scale
scale_task = np.array([next(v for p, v in sc.items() if re.fullmatch(p, n)) for n in ilib.POLICY_JOINTS])
scale_dep = np.array(dep["actions"]["JointPositionAction"]["scale"])
# <<<TODO
i = int(np.abs(scale_task - scale_dep).argmax())
print(f"    action scale: max |task − deploy.yaml| = {np.abs(scale_task - scale_dep).max():.4f} "
      f"({ilib.POLICY_JOINTS[i]}: {scale_task[i]:.4f} vs {scale_dep[i]})  ← deploy.yaml ปัดเหลือ 2 ตำแหน่ง")
acts = cfg.scene.robot.actuators
print(f"    actuator ของ task: " + " · ".join(f"{k}: kp {v.stiffness:.2f} kd {v.damping:.3f} arm {v.armature:.4f}"
                                          for k, v in acts.items()))
print(f"    sim.dt {cfg.sim.dt} · decimation {cfg.decimation} → step_dt {cfg.sim.dt * cfg.decimation} "
      f"(deploy {dep['step_dt']}) · episode {cfg.episode_length_s} s")
print(f"    init_state.pos {cfg.scene.robot.init_state.pos} · terrain {cfg.scene.terrain.terrain_type}")
