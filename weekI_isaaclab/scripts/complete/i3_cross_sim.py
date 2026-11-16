"""I3: cross-sim: policy ที่เทรนใน mjlab (MuJoCo) เดินใน Isaac Lab PhysX vs Newton ได้เท่ากันไหม

    python i3_cross_sim.py                                  # v0 (P3b) 3 กรณี ทั้ง PhysX และ Newton (~2 นาที)
    python i3_cross_sim.py --cases "0.4,0,0;0,0.3,0" --backends newton
    python i3_cross_sim.py --policy hist5_yawstand          # policy อื่นใน deploy/.../velocity/

ไม่ได้เขียน loop เอง แต่เรียก `unitree_rl_lab/scripts/play_deploy_onnx.py` (ของ session งานหลัก, อ่านอย่างเดียว)
เป็น subprocess แล้วอ่าน JSON ที่มันพิมพ์ ทีละ backend · ก่อนรันให้อ่านสคริปต์นั้นก่อน: มันสร้าง obs จาก deploy.yaml
เอง (ไม่ใช้ observation manager ของ task) แล้วป้อน ONNX ที่ประเมินด้วย torch

เกณฑ์ (vault "Cross-Sim Isaac Lab"): ทุก engine ต่างกันไม่เกิน ~±8 pp และไม่ล้ม
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import ilib  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--policy", default="v0")
ap.add_argument("--cases", default="0.4,0,0;0.8,0,0;0,0,0.5")
ap.add_argument("--backends", default="physx,newton")
ap.add_argument("--walk", type=float, default=12.0)
ap.add_argument("--measure", type=float, default=8.0)
args = ap.parse_args()

PLAY = ilib.RL_LAB / "scripts/play_deploy_onnx.py"
POLICY_DIR = ilib.MJLAB / "deploy/robots/g1_23dof/config/policy/velocity" / args.policy
# ผล MuJoCo (vel_eval.py ของ mjlab) จาก vault: % ของคำสั่ง · ใช้เทียบเฉพาะ v0 = P3b
MUJOCO_P3B = {(0.4, 0, 0): "97", (0.8, 0, 0): "74", (1.0, 0, 0): "41", (0, 0, 0.5): "69–73", (0, 0, -0.5): "69–73",
              (0, 0.3, 0): "59"}


def run_backend(backend: str) -> tuple[list[dict], float]:
    """รัน play_deploy_onnx.py 1 ครั้ง (ทุกกรณีใน process เดียว) → list ของผลต่อกรณี"""
    cmd = [sys.executable, str(PLAY), "--headless", "--policy-dir", str(POLICY_DIR), "--cases", args.cases,
           "--walk", str(args.walk), "--measure", str(args.measure)]
    if backend == "newton":
        cmd.append("presets=newton")          # Hydra override: เลือก preset newton ทุกจุด
    env = dict(os.environ, OMNI_KIT_ACCEPT_EULA="YES")
    t = time.time()
    # >>>TODO(I3) subprocess.run(cmd, capture_output=True, text=True, env=env) → เลือกบรรทัดที่ขึ้นต้นด้วย '{"cmd"'
    #             → json.loads ทีละบรรทัด · ถ้า returncode ≠ 0 ให้พิมพ์ stderr 20 บรรทัดท้าย
    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    res = [json.loads(line) for line in p.stdout.splitlines() if line.startswith('{"cmd"')]
    if p.returncode != 0 or not res:
        print(f"  ✗ {backend} exit {p.returncode}\n" + "\n".join((p.stderr or p.stdout).splitlines()[-20:]))
    # <<<TODO
    for line in p.stdout.splitlines():
        if line.startswith("[deploy]"):
            print(f"  {backend:7s}{line}")
    return res, time.time() - t


def pct(r: dict) -> str:
    """% ของคำสั่ง: แกนที่คำสั่งใหญ่สุด"""
    c = r["cmd"]
    ax = max(range(3), key=lambda i: abs(c[i]))
    v = [r["vx"], r["vy"], r["wz"]][ax]
    return "-" if v is None else f"{100 * v / c[ax]:.0f}"


print(f"policy {POLICY_DIR}\nกรณี {args.cases}\n")
results = {}
for be in args.backends.split(","):
    res, el = run_backend(be)
    results[be] = res
    print(f"  {be:7s} เสร็จใน {el:.0f} s ({len(res)} กรณี)\n")

rows = []
cases = [tuple(float(x) for x in c.split(",")) for c in args.cases.split(";")]
for i, c in enumerate(cases):
    r = dict(cmd=f"({c[0]:g},{c[1]:g},{c[2]:g})")
    for be, res in results.items():
        if i < len(res):
            r[f"{be}_%"] = pct(res[i])
            r[f"{be}_fell"] = "ล้ม" if res[i]["fell"] else ""
            r[f"{be}_tilt"] = res[i]["tilt_max_deg"]
    if args.policy == "v0":
        r["mujoco_%(vault)"] = MUJOCO_P3B.get(c, "?")
    rows.append(r)
ilib.print_table(rows)
print("\n% = ความเร็วที่วัดได้ / คำสั่ง (แกนหลัก) ในช่วง measure วินาทีท้าย · tilt = มุมเอียงสูงสุด [deg]")
