"""eval_policy_skeleton.py: ประเมิน policy ด้วย gain_check + vel_eval แล้วเทียบหลายตัว (งาน 5.3, 5.6)  ❌ ไม่ต่อ DDS

สองคำสั่งย่อย:
  eval    <ชื่อ> <policy.onnx>   → จัดโฟลเดอร์ week5/policies/<ชื่อ>/ (onnx + deploy.yaml ของ v0)
                                    → gain_check → vel_eval (8 case) + vel_eval --hang → เซฟ results.json
  compare <ชื่อ> <ชื่อ> ...       → ตาราง % ของคำสั่ง (baseline / control / ทดลอง) + ผลต่าง ทดลอง − control

รัน (env g1_sdk: มี mujoco + onnxruntime ที่ vel_eval ใช้):
  python eval_policy_skeleton.py eval baseline ~/nvidia/unitree/unitree_rl_mjlab/deploy/robots/g1_23dof/config/policy/velocity/v0/exported/policy.onnx
  python eval_policy_skeleton.py eval control  ~/g1_study/week5/logs/rsl_rl/g1_23dof_velocity/<run>/policy.onnx
  python eval_policy_skeleton.py compare baseline control exp_a
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
POLICIES = Path.home() / "g1_study/week5/policies"


def make_policy_dir(name: str, onnx: Path) -> Path:
    """ให้ไว้แล้ว: week5/policies/<name>/exported/policy.onnx + params/deploy.yaml (ของ v0)  โครงที่ gain_check ต้องการ"""
    d = POLICIES / name
    (d / "exported").mkdir(parents=True, exist_ok=True)
    (d / "params").mkdir(parents=True, exist_ok=True)
    shutil.copy2(onnx, d / "exported" / "policy.onnx")
    shutil.copy2(V0_DEPLOY, d / "params" / "deploy.yaml")
    return d


def run_gain_check(policy_dir: Path) -> bool:
    """คืน True ถ้า PASS"""
    # TODO [5.3] subprocess.run([sys.executable, SCRIPTS / "gain_check.py", policy_dir], capture_output=True, text=True)
    # TODO [5.3] พิมพ์ output · PASS = return code 0 และไม่มีคำว่า FAIL / MISMATCH (เปิด gain_check.py ดูว่ามันจบยังไง)
    return False


def run_vel_eval(policy_dir: Path, extra: list) -> list:
    """คืน list ของ dict (1 ต่อ case) จาก JSON ที่ vel_eval พิมพ์บรรทัดละ case"""
    # TODO [5.3] คำสั่ง: python vel_eval.py --policy <dir>/exported/policy.onnx --deploy <dir>/params/deploy.yaml  + extra
    # TODO [5.3] แต่ละบรรทัดของ stdout ที่ขึ้นต้นด้วย "{" → json.loads
    # key ที่ได้: cmd [vx,vy,wz], fell, tilt_max_deg, vx, vy, wz, vx_std, joint_vel_std, yaw_rate_std, safety{...}
    return []


def tracking_pct(r: dict):
    """% ของคำสั่งที่ทำได้ ใช้แกนหลักของ case นั้น (vx ถ้า cmd vx ≠ 0, ไม่งั้น wz, ไม่งั้น vy)  None ถ้ายืนนิ่ง"""
    # TODO [5.3] เช่น cmd (0.8, 0, 0), vx จริง 0.59 → 74%
    # คำถาม: case (0.4, 0, 0.5) มีสองแกน จะรายงานแกนไหน หรือรายงานทั้งคู่
    return None


def cmd_eval(name: str, onnx: Path) -> None:
    d = make_policy_dir(name, onnx)
    print(f"policy dir: {d}")
    ok = run_gain_check(d)
    cases = run_vel_eval(d, [])
    hang = run_vel_eval(d, ["--cases", "0,0,0", "--hang"])
    stand = run_vel_eval(d, ["--cases", "0,0,0"])
    if not cases:
        print("eval_policy: ยังไม่ได้เติม [5.3]")
        return
    result = {"name": name, "onnx": str(onnx), "gain_check": ok, "cases": cases, "hang": hang, "stand": stand}
    (d / "results.json").write_text(json.dumps(result, indent=1))
    # TODO [5.3] พิมพ์สรุป: ทุก case → cmd | % | fell · ยืน: joint_vel_std, yaw_rate_std · แขวน: max_speed_ratio (safety)
    # เทียบ baseline กับตารางใน week5/docs/evaluation.md (vault: vx 0.4 97%, vx 0.8 74%, vx 1.0 41% ...)


def cmd_compare(names: list) -> None:
    results = []
    for n in names:
        f = POLICIES / n / "results.json"
        if not f.exists():
            raise SystemExit(f"ไม่มี {f}: รัน eval {n} ก่อน")
        results.append(json.loads(f.read_text()))
    # TODO [5.6] ตาราง: แถว = case (จับคู่ด้วย cmd), คอลัมน์ = ชื่อ policy, ค่า = tracking_pct
    # TODO [5.6] ถ้ามีชื่อ "control" และ policy อื่น: เพิ่มคอลัมน์ "ทดลอง − control" (นี่คือผลของการเปลี่ยน reward)
    # TODO [5.6] แถวท้าย: gain_check, ยืน (joint_vel_std), แขวน (max_speed_ratio)
    # คำถาม: ต่างกันกี่ % ถึงจะเชื่อว่าไม่ใช่ noise (evaluation.md ข้อ 5)
    print("compare: ยังไม่ได้เติม [5.6]")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("eval")
    e.add_argument("name")
    e.add_argument("onnx", type=Path)
    c = sub.add_parser("compare")
    c.add_argument("names", nargs="+")
    args = p.parse_args()
    if args.cmd == "eval":
        cmd_eval(args.name, args.onnx)
    else:
        cmd_compare(args.names)


if __name__ == "__main__":
    main()
