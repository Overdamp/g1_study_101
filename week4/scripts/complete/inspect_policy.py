"""inspect_policy.py: เปิด policy.onnx แล้วเทียบกับ deploy.yaml (งาน 4.1) ฉบับสมบูรณ์  ❌ ไม่ต่อ DDS

รัน:  conda activate g1_sdk && python week4/scripts/complete/inspect_policy.py [--policy-dir <โฟลเดอร์ policy>]
"""

import argparse
from pathlib import Path

import numpy as np
import onnxruntime as ort
import yaml

V0 = Path.home() / "nvidia/unitree/unitree_rl_mjlab/deploy/robots/g1_23dof/config/policy/velocity/v0"

# (metadata, ชื่อใน deploy.yaml, วิธีดึง, tolerance สัมพัทธ์)  tolerance เท่ากับ CHECKS ใน gain_check.py:
# deploy.yaml ปัดเศษ gain เป็น 1–2 ตำแหน่ง (kd 0.9 แทน 0.907, 2.6 แทน 2.558 = 1.6%) จึงยอมให้ gain ต่างได้ 6%
PAIRS = [
    ("joint_stiffness", "stiffness", lambda d: d["stiffness"], 0.06),
    ("joint_damping", "damping", lambda d: d["damping"], 0.06),
    ("default_joint_pos", "default_joint_pos", lambda d: d["default_joint_pos"], 1e-3),
    ("default_joint_pos", "actions.offset", lambda d: d["actions"]["JointPositionAction"]["offset"], 1e-3),
    ("action_scale", "actions.scale", lambda d: d["actions"]["JointPositionAction"]["scale"], 0.01),
]


def to_floats(s: str) -> np.ndarray:
    return np.array([float(x) for x in s.split(",")], dtype=np.float64)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--policy-dir", type=Path, default=V0)
    args = p.parse_args()
    deploy = yaml.safe_load(open(args.policy_dir / "params" / "deploy.yaml"))
    sess = ort.InferenceSession(str(args.policy_dir / "exported" / "policy.onnx"), providers=["CPUExecutionProvider"])

    print("== ONNX input / output")
    for i in sess.get_inputs():
        print(f"  in   {i.name:<8} {i.shape} {i.type}")
    for o in sess.get_outputs():
        print(f"  out  {o.name:<8} {o.shape} {o.type}")

    meta = sess.get_modelmeta().custom_metadata_map
    print("\n== metadata")
    for k, v in meta.items():
        print(f"  {k:<18} {v[:80]}{'…' if len(v) > 80 else ''}")

    print("\n== เทียบกับ deploy.yaml (tolerance ต่อ field เท่า gain_check.py)")
    print(f"  {'metadata':<18} {'deploy.yaml':<20} {'max |diff|':>10} {'max %':>7} {'tol':>5}  ผล")
    for mkey, dname, get, tol in PAIRS:
        a, b = to_floats(meta[mkey]), np.array(get(deploy), dtype=np.float64)
        if a.shape != b.shape:
            print(f"  {mkey:<18} {dname:<20} ความยาวไม่เท่ากัน {a.shape} vs {b.shape}  ❌")
            continue
        diff = np.abs(a - b)
        rel = np.divide(diff, np.abs(a), out=np.zeros_like(diff), where=np.abs(a) > 1e-9)   # ค่า 0 ไม่หาร
        # เหมือน gain_check: นับว่าผิดเมื่อ |diff| > 1e-3 และ % เกิน tol
        bad = (diff > 1e-3) & (rel > tol)
        verdict = "ตรง" if diff.max() < 1e-6 else ("❌ ต่างเกิน tolerance" if bad.any() else "ปัดเศษ (ใน tolerance)")
        print(f"  {mkey:<18} {dname:<20} {diff.max():10.4f} {rel.max() * 100:6.2f}% {tol * 100:4.1f}%  {verdict}")

    # ชื่อข้อต่อ: metadata มีชื่อตามลำดับ policy ส่วน deploy.yaml มีเลข slot → เทียบกับ slot map
    names = meta["joint_names"].split(",")
    print(f"\n== ข้อต่อ: metadata {len(names)} ชื่อ · joint_ids_map {len(deploy['joint_ids_map'])} slot")
    print("  " + ", ".join(f"{n.removesuffix('_joint')}→{s}" for n, s in zip(names, deploy["joint_ids_map"])))

    # ลำดับ obs: ชื่อฝั่งเทรน vs ชื่อฝั่ง deploy (ต่างชื่อ แต่ลำดับต้องตรง)
    terms = deploy["observations"]
    print("\n== ลำดับ obs (เทรน ↔ deploy)  มิติ")
    total = 0
    for train_name, (dep_name, t) in zip(meta["observation_names"].split(","), terms.items()):
        dim = len(t["scale"]) * t.get("history_length", 1)
        total += dim
        print(f"  {train_name:<18} ↔ {dep_name:<20} {dim}")
    n_in = sess.get_inputs()[0].shape[-1]
    print(f"  รวม {total} · ONNX input {n_in}  {'ตรง' if total == n_in else '❌ ไม่ตรง'}")
    print("\nหมายเหตุ: g1_ctrl ใช้ค่าจาก deploy.yaml เท่านั้น (ไม่อ่าน metadata)")


if __name__ == "__main__":
    main()
