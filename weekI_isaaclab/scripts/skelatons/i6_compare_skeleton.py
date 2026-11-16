"""I6: เทียบ manager-based (I5) กับ Direct (I6) ทีละ step ทีละ term: MDP เดียวกันจริงไหม และเร็วต่างกันเท่าไร

    python i6_compare.py                     # รัน i5/i6 --dump (P3b, 16 env, 6 s) แล้วเทียบ + จับเวลา
    python i6_compare.py --no-run            # เทียบไฟล์ dump เดิมใน logs/
    python i6_compare.py --time-envs 1024    # จับเวลา env.step ที่ 1024 env (ทั้งสองแบบ)

Isaac Lab สร้าง sim ได้ครั้งละ 1 ตัวต่อ process → รันแต่ละแบบเป็น subprocess แล้วเทียบไฟล์ .npz

อ่านผล
  - step แรกที่ obs ต่างเกิน 1e-4 และ term ไหนต่างก่อน → บอกว่านิยามตรงไหนไม่ตรง
  - ถ้าต่างกันระดับ 1e-6 แล้วค่อยๆ โต = ลำดับการบวกเลขบน GPU (float32) ต่างกัน แล้วหุ่นที่ "ไม่เสถียร" ขยายความต่าง (chaos)

[skeleton] ทายก่อนรัน
  1. obs ของ manager กับ Direct ที่ step 0 ต่างกันเท่าไร · step 299 ล่ะ
  2. Direct เร็วกว่า manager กี่ % ตอนไม่มี reset · ตอน reset เยอะ
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import contract_common_skeleton as C  # noqa: E402
import ilib_skeleton as ilib  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--no-run", action="store_true")
ap.add_argument("--secs", type=float, default=6.0)
ap.add_argument("--num-envs", type=int, default=16)
ap.add_argument("--time-envs", type=int, default=512)
ap.add_argument("--time-steps", type=int, default=100)
args = ap.parse_args()

HERE = Path(__file__).parent
PY = sys.executable
ENV = dict(os.environ, OMNI_KIT_ACCEPT_EULA="YES")
DUMP = {"manager": ilib.LOGS / "i5.npz", "direct": ilib.LOGS / "i6.npz"}
SCRIPT = {"manager": "i5_manager_terms_skeleton.py", "direct": "i6_direct_env_skeleton.py"}

TIMER = r'''
import sys, time
sys.path.insert(0, "{here}")
from isaaclab.app import AppLauncher
app = AppLauncher(headless=True, visualizer="none").app
import gymnasium as gym, torch
import contract_manager_skeleton as M, contract_direct as D, ilib
mod = M if "{mode}" == "manager" else D
cfg = mod.make_cfg(num_envs={n}, preset="newton", fixed_cmd=(0.5, 0.0, 0.0), corruption=True)
env = gym.make(mod.TASK_ID, cfg=cfg)
u = env.unwrapped
pol = ilib.ActorMLP(device=u.device)
out = []
with torch.inference_mode():
    for name in ("p3b", "zero"):              # p3b = เดินไม่ล้ม (ไม่มี reset) · zero = ล้มบ่อย (reset เยอะ)
        obs, _ = env.reset()
        for _ in range(5): obs, *_ = env.step(pol(obs["policy"]))
        n_reset = 0
        torch.cuda.synchronize(); t = time.perf_counter()
        for _ in range({steps}):
            a = pol(obs["policy"]) if name == "p3b" else torch.zeros(u.num_envs, 23, device=u.device)
            obs, r, te, tr, _ = env.step(a)
            n_reset += int((te | tr).sum())
        torch.cuda.synchronize(); out.append((name, (time.perf_counter() - t) / {steps}, n_reset))
    # ฟิสิกส์ล้วน (sim.step × decimation) → ส่วนที่เหลือของ env.step = Python ของ MDP
    t = time.perf_counter()
    for _ in range({steps}):
        for _ in range(u.cfg.decimation):
            u.scene.write_data_to_sim(); u.sim.step(render=False); u.scene.update(dt=u.physics_dt)
    torch.cuda.synchronize(); ph = (time.perf_counter() - t) / {steps}
for name, el, nr in out:
    print(f"TIMING {{name}} {{el*1e3:.3f}} {{ph*1e3:.3f}} {{nr}}")
env.close(); app.close()
'''


def sh(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, env=ENV, cwd=HERE)
    if p.returncode != 0:
        print("\n".join((p.stderr or p.stdout).splitlines()[-15:]))
    return p.stdout


# ---------------------------------------------------------------- 1. รัน + dump
if not args.no_run:
    for mode in ("manager", "direct"):
        print(f"[run] {SCRIPT[mode]} --dump ...", flush=True)
        out = sh([PY, SCRIPT[mode], "--num-envs", str(args.num_envs), "--secs", str(args.secs),
                  "--dump", str(DUMP[mode])])
        for line in out.splitlines():
            if line.strip().startswith(("ล้ม", "vx")):
                print(f"      {line.strip()}")

# ---------------------------------------------------------------- 2. เทียบ
A, B = (np.load(DUMP[m]) for m in ("manager", "direct"))
assert list(A["names"]) == list(B["names"]), "ชื่อ/ลำดับ reward term ไม่ตรงกัน"
T = min(len(A["policy"]), len(B["policy"]))
print(f"\n[เทียบ] {T} step × {A['policy'].shape[1]} env")

# ช่วง index ของแต่ละ obs term (policy) + critic extra
edges = np.cumsum([0] + C.POLICY_DIMS + C.CRITIC_EXTRA_DIMS)
names = C.POLICY_TERMS + C.CRITIC_EXTRA

# TODO(I6) diff[t, k] = max |manager − direct| ของ term k ที่ step t (ใช้ critic เพราะมีครบทุก term)
raise NotImplementedError('TODO(I6) diff[t, k] = max |manager − direct| ของ term k ที่ step t (ใช้ critic เพราะมีครบทุก term)')

rows = []
for k, n in enumerate(names):
    first = np.argmax(diff[:, k] > 1e-4) if (diff[:, k] > 1e-4).any() else None
    rows.append(dict(obs_term=n, step0=float(diff[0, k]), step1=float(diff[1, k]), step10=float(diff[10, k]),
                     max_all=float(diff[:, k].max()), first_gt_1e4=first))
ilib.print_table(rows, fmt={c: "{:.1e}" for c in ("step0", "step1", "step10", "max_all")})
rows = []
for k, n in enumerate(A["names"]):
    first = np.argmax(rdiff[:, k] > 1e-4) if (rdiff[:, k] > 1e-4).any() else None
    rows.append(dict(reward_term=str(n), step0=float(rdiff[0, k]), step10=float(rdiff[10, k]),
                     max_all=float(rdiff[:, k].max()), first_gt_1e4=first))
print()
ilib.print_table(rows, fmt={c: "{:.1e}" for c in ("step0", "step10", "max_all")})
same_done = (A["done"][:T] == B["done"][:T]).all()
print(f"\ndone ตรงกันทุก step/env: {same_done} · ผลรวม done: manager {int(A['done'][:T].sum())} · "
      f"direct {int(B['done'][:T].sum())}")
grow = diff.max(axis=1)
for t in (0, 1, 5, 10, 25, 50, 100, 200, T - 1):
    if t < T:
        print(f"    step {t:3d}: max |obs diff| = {grow[t]:.2e}")

# ---------------------------------------------------------------- 3. เวลา
print(f"\n[เวลา] env.step() · {args.time_envs} env · {args.time_steps} step · Newton · noise เปิด · (รวมเวลา actor P3b ~0.1 ms)")
for mode in ("manager", "direct"):
    out = sh([PY, "-c", TIMER.format(here=HERE, mode=mode, n=args.time_envs, steps=args.time_steps)])
    for m in re.finditer(r"TIMING (\w+) ([\d.]+) ([\d.]+) (\d+)", out):
        name, el, ph, nr = m.group(1), float(m.group(2)), float(m.group(3)), int(m.group(4))
        print(f"    {mode:8s} {name:4s} {el:7.2f} ms/step · ฟิสิกส์ล้วน {ph:6.2f} ms · ส่วน MDP {el - ph:6.2f} ms · "
              f"reset {nr:5d} ครั้ง → {args.time_envs / el * 1e3:,.0f} env-step/s")
