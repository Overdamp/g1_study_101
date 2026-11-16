"""eval_policy.py: ประเมิน policy ด้วย gain_check + vel_eval แล้วเทียบหลายตัว (งาน 5.3, 5.6) ฉบับสมบูรณ์  ❌ ไม่ต่อ DDS

  eval    <ชื่อ> <policy.onnx>   → week5/policies/<ชื่อ>/ (onnx + deploy.yaml ของ v0) → gain_check → vel_eval
                                    (8 case + ยืน + แขวน) → results.json
  compare <ชื่อ> <ชื่อ> ...       → ตาราง % ของคำสั่ง + คอลัมน์ "ทดลอง − control"

รัน (env g1_sdk: มี mujoco + onnxruntime):
  python eval_policy.py eval baseline ~/nvidia/unitree/unitree_rl_mjlab/deploy/robots/g1_23dof/config/policy/velocity/v0/exported/policy.onnx
  python eval_policy.py eval control  ~/g1_study/week5/logs/rsl_rl/g1_23dof_velocity/<run>/policy.onnx
  python eval_policy.py compare baseline control exp_a
  (--root <โฟลเดอร์> เปลี่ยนที่เก็บ policies ได้)
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path.home() / "nvidia/unitree/unitree_rl_mjlab"
SCRIPTS = REPO / "deploy/robots/g1_23dof/scripts"
V0_DEPLOY = REPO / "deploy/robots/g1_23dof/config/policy/velocity/v0/params/deploy.yaml"
DEFAULT_ROOT = Path.home() / "g1_study/week5/policies"


def make_policy_dir(root: Path, name: str, onnx: Path) -> Path:
    d = root / name
    (d / "exported").mkdir(parents=True, exist_ok=True)
    (d / "params").mkdir(parents=True, exist_ok=True)
    shutil.copy2(onnx, d / "exported" / "policy.onnx")
    shutil.copy2(V0_DEPLOY, d / "params" / "deploy.yaml")     # เปลี่ยนแค่ reward → obs/action/gain เท่าเดิม ใช้ของ v0 ได้
    return d


def run_gain_check(policy_dir: Path) -> bool:
    r = subprocess.run([sys.executable, str(SCRIPTS / "gain_check.py"), str(policy_dir)], capture_output=True, text=True)
    text = r.stdout + r.stderr
    print(text.rstrip())
    return r.returncode == 0 and "FAIL" not in text and "MISMATCH" not in text


def run_vel_eval(policy_dir: Path, extra: list) -> list:
    cmd = [sys.executable, str(SCRIPTS / "vel_eval.py"),
           "--policy", str(policy_dir / "exported" / "policy.onnx"),
           "--deploy", str(policy_dir / "params" / "deploy.yaml"), *extra]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"vel_eval ล้มเหลว:\n{r.stderr[-2000:]}")
    return [json.loads(line) for line in r.stdout.splitlines() if line.startswith("{")]


def tracking_pct(r: dict):
    """% ของคำสั่ง ใช้แกนหลัก: vx ถ้าสั่ง vx, ไม่งั้น wz, ไม่งั้น vy · None ถ้ายืนนิ่ง"""
    vx, vy, wz = r["cmd"]
    for c, actual in ((vx, r["vx"]), (wz, r["wz"]), (vy, r["vy"])):
        if abs(c) > 1e-6 and actual is not None:
            return 100.0 * actual / c
    return None


def case_label(r: dict) -> str:
    vx, vy, wz = r["cmd"]
    return f"({vx:g}, {vy:g}, {wz:g})"


def cmd_eval(root: Path, name: str, onnx: Path) -> None:
    d = make_policy_dir(root, name, onnx)
    print(f"policy dir: {d}\n== gain_check")
    ok = run_gain_check(d)
    print("== vel_eval (8 case)", flush=True)
    cases = run_vel_eval(d, [])
    stand = run_vel_eval(d, ["--cases", "0,0,0"])
    hang = run_vel_eval(d, ["--cases", "0,0,0", "--hang"])
    result = {"name": name, "onnx": str(onnx), "gain_check": ok, "cases": cases, "stand": stand, "hang": hang}
    (d / "results.json").write_text(json.dumps(result, indent=1))

    print(f"\n  {'cmd (vx,vy,wz)':<18} {'%':>6} {'fell':>5} {'tilt°':>6}")
    for r in cases:
        pct = tracking_pct(r)
        extra = ""
        if abs(r["cmd"][0]) > 0 and abs(r["cmd"][2]) > 0:      # (0.4, 0, 0.5): รายงานทั้งสองแกน
            extra = f"  (wz {100 * r['wz'] / r['cmd'][2]:.0f}%)"
        print(f"  {case_label(r):<18} {pct:6.0f} {str(r['fell']):>5} {r['tilt_max_deg']:6.1f}{extra}")
    s, h = stand[0], hang[0]
    print(f"  ยืน: joint_vel_std {s['joint_vel_std']}  yaw_rate_std {s['yaw_rate_std']}  fell {s['fell']}")
    print(f"  แขวน: max_speed_ratio {h['safety']['max_speed_ratio']}  (ratio > 0.8 ≈ เตะขา)")
    print(f"  gain_check: {'PASS' if ok else 'FAIL'}  → {d / 'results.json'}")


def cmd_compare(root: Path, names: list) -> None:
    results = []
    for n in names:
        f = root / n / "results.json"
        if not f.exists():
            raise SystemExit(f"ไม่มี {f}: รัน eval {n} ก่อน")
        results.append(json.loads(f.read_text()))
    has_ctrl = "control" in names
    others = [n for n in names if n not in ("control", "baseline")]

    head = f"  {'cmd (vx,vy,wz)':<18}" + "".join(f"{n:>11}" for n in names)
    if has_ctrl:
        head += "".join(f"{n + '−ctrl':>13}" for n in others)
    print(head)
    for i, r0 in enumerate(results[0]["cases"]):
        vals = [tracking_pct(res["cases"][i]) for res in results]
        line = f"  {case_label(r0):<18}" + "".join(f"{v:11.0f}" for v in vals)
        if has_ctrl:
            c = vals[names.index("control")]
            line += "".join(f"{vals[names.index(n)] - c:+13.0f}" for n in others)
        print(line)
    print(f"  {'ยืน joint_vel_std':<18}" + "".join(f"{res['stand'][0]['joint_vel_std']:11.3f}" for res in results))
    print(f"  {'แขวน speed ratio':<18}" + "".join(f"{res['hang'][0]['safety']['max_speed_ratio'][1]:11.2f}" for res in results))
    print(f"  {'gain_check':<18}" + "".join(f"{'PASS' if res['gain_check'] else 'FAIL':>11}" for res in results))
    print("\nผลของการเปลี่ยน reward = ทดลอง − control (ไม่ใช่ − baseline) · ต่าง 1–3% อาจเป็น noise ถ้าจะมั่นใจให้รันซ้ำด้วย seed อื่น")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="ที่เก็บโฟลเดอร์ policy (ค่าเริ่มต้น week5/policies)")
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("eval")
    e.add_argument("name")
    e.add_argument("onnx", type=Path)
    c = sub.add_parser("compare")
    c.add_argument("names", nargs="+")
    args = p.parse_args()
    if args.cmd == "eval":
        cmd_eval(args.root, args.name, args.onnx.expanduser())
    else:
        cmd_compare(args.root, args.names)


if __name__ == "__main__":
    main()
