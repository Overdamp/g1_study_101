"""I5: task manager-based ของเราเองใน Isaac Lab (บน Newton): obs ตรง deploy + term ที่เขียนเอง → P3b เดินจาก obs ของ env

    python i5_manager_terms.py                         # 16 env, vx 0.5, 6 s: action ศูนย์ vs P3b
    python i5_manager_terms.py --vx 0.8 --secs 10
    python i5_manager_terms.py --friction-dr 0 0.3     # + DR frictionloss ต่อข้อ (ดูว่าค่าไปถึง Newton Model จริง)
    python i5_manager_terms.py --physx                 # task เดียวกันบน PhysX
    python i5_manager_terms.py --dump ../../logs/i5.npz   # เก็บ obs/reward ทุก step ให้ i6_compare

พิมพ์
  [1] โครง obs ที่ ObservationManager สร้าง (term, ขนาด, ช่วง index) เทียบ deploy.yaml
  [2] term ของเราใน manager (class term → instance) + ค่า friction ใน Newton Model (ถ้า --friction-dr)
  [3] รัน action ศูนย์ และ P3b (actor จาก checkpoint mjlab) → reward ทีละ term (ต่อวินาที), ล้ม, vx

[skeleton] ทายก่อนรัน
  1. P3b เดินใน task manager ของเราได้ไหม ทั้งที่ไม่เคยเห็น Isaac/Newton · vx ที่คำสั่ง 0.5 ≈ ?
  2. reward ตัวไหนต่างระหว่างศูนย์กับ P3b มากที่สุด
  3. friction DR 0–0.3 ค่าไปอยู่ใน Newton Model field ไหน
"""
import argparse
import sys
from pathlib import Path

from isaaclab.app import AppLauncher

ap = argparse.ArgumentParser()
ap.add_argument("--num-envs", type=int, default=16)
ap.add_argument("--vx", type=float, default=0.5)
ap.add_argument("--secs", type=float, default=6.0)
ap.add_argument("--friction-dr", type=float, nargs=2, default=None)
ap.add_argument("--physx", action="store_true")
ap.add_argument("--dump", default=None)
AppLauncher.add_app_launcher_args(ap)
ap.set_defaults(headless=True, visualizer="none")
args = ap.parse_args()
app = AppLauncher(args).app

import gymnasium as gym  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402
import yaml  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
import contract_common_skeleton as C  # noqa: E402
import contract_manager_skeleton as M  # noqa: E402
import ilib_skeleton as ilib  # noqa: E402


def run(env, policy, steps: int, record: bool = False):
    """วน env.step · policy=None → action ศูนย์ · คืนสรุป reward ต่อ term (ต่อวินาที), ล้ม, vx"""
    u = env.unwrapped
    rm = u.reward_manager
    names = rm.active_terms
    with torch.inference_mode():
        obs, _ = env.reset()
        sums = torch.zeros(len(names), device=u.device)
        falls, vx, total = 0, [], 0.0
        rec = {"policy": [], "critic": [], "step_reward": [], "reward": [], "done": []}
        if record:                                   # แถวแรก = obs หลัง reset (ก่อน step แรก)
            rec["reset_policy"] = [obs["policy"].cpu().numpy()]
            rec["reset_critic"] = [obs["critic"].cpu().numpy()]
        for _ in range(steps):
            # TODO(I5) action = policy(obs["policy"]) หรือศูนย์ → env.step → สะสม rm._step_reward (= func × weight)
            raise NotImplementedError('TODO(I5) action = policy(obs["policy"]) หรือศูนย์ → env.step → สะสม rm._step_reward (= func × weight)')
            total += float(rew.mean())
            falls += int(term.sum())
            # vx เฉพาะ env ที่ยังตั้งตรง (เอียง < 20°) · ตัวที่กำลังล้มไปข้างหน้าก็มี vx บวก → ไม่นับ
            d = u.scene["robot"].data
            up = torch.acos(-d.projected_gravity_b.torch[:, 2]) < 0.35
            if up.any():
                vx.append(float(d.root_lin_vel_b.torch[up, 0].mean()))
            if record:
                rec["policy"].append(obs["policy"].cpu().numpy())
                rec["critic"].append(obs["critic"].cpu().numpy())
                rec["step_reward"].append(rm._step_reward.cpu().numpy().copy())
                rec["reward"].append(rew.cpu().numpy())
                rec["done"].append((term | trunc).cpu().numpy())
    rate = (sums / steps).cpu().numpy()                 # = reward ต่อวินาทีของแต่ละ term
    return dict(names=names, rate=rate, falls=falls, vx=float(np.mean(vx[len(vx) // 2:])) if len(vx) > 1 else float("nan"),
                total_per_s=total / steps / u.step_dt, rec=rec)


def main():
    cfg = M.make_cfg(num_envs=args.num_envs, preset="physx" if args.physx else "newton",
                     fixed_cmd=(args.vx, 0.0, 0.0), corruption=False,
                     friction_dr=tuple(args.friction_dr) if args.friction_dr else None)
    env = gym.make(M.TASK_ID, cfg=cfg)
    u = env.unwrapped
    om = u.observation_manager

    # ------------------------------------------------ [1] obs layout
    print(f"\n[1] ObservationManager ({type(u.cfg.sim.physics).__name__})")
    dep = yaml.safe_load(open(ilib.DEPLOY_YAML))
    for group in ("policy", "critic"):
        names = om.active_terms[group]
        dims = [int(np.prod(d)) for d in om.group_obs_term_dim[group]]
        # TODO(I5) ช่วง [start, end) ของแต่ละ term = ผลรวมสะสมของ dims
        raise NotImplementedError('TODO(I5) ช่วง [start, end) ของแต่ละ term = ผลรวมสะสมของ dims')
        print(f"    {group:6s} {sum(dims):3d}: {layout}")
    pol_names = om.active_terms["policy"]
    print(f"    ลำดับ policy = deploy.yaml? {pol_names == list(dep['observations'])}  · "
          f"ขนาด = actor ของ P3b (80)? {sum(int(np.prod(d)) for d in om.group_obs_term_dim['policy']) == 80}")

    # ------------------------------------------------ [2] term ของเรา
    rm = u.reward_manager
    print("\n[2] term ของเราใน manager")
    for name in ("feet_too_close", "vx_ema_error"):
        tc = rm.get_term_cfg(name)
        print(f"    reward {name:15s} func = {tc.func if not isinstance(tc.func, type) else tc.func.__name__} "
              f"({type(tc.func).__name__})  weight {tc.weight}")
    print(f"    termination: {u.termination_manager.active_terms}")
    feet_cfg = rm.get_term_cfg("feet_too_close").params["asset_cfg"]
    print(f"    FEET body_names {feet_cfg.body_names} → body_ids {feet_cfg.body_ids} (resolve ตอนสร้าง manager)")
    if args.friction_dr and not args.physx:
        from isaaclab_newton.physics import NewtonManager
        m = NewtonManager.get_model()
        fr = m.joint_friction.numpy().reshape(m.world_count, -1)[:, 6:]     # ตัด free joint 6 dof
        print(f"    Newton Model.joint_friction (N·m) world 0–2, joint 0–5:\n{np.round(fr[:3, :6], 3)}")
        print(f"    ช่วงทุก world/joint: {fr.min():.3f} – {fr.max():.3f}  (ขอ {args.friction_dr})")

    # ------------------------------------------------ [3] รัน
    steps = int(args.secs / u.step_dt)
    policy = ilib.ActorMLP(device=u.device)
    print(f"\n[3] {args.num_envs} env · คำสั่ง vx {args.vx} · {args.secs} s ({steps} step) · noise ปิด")
    # P3b ก่อน: env ยังสด ทุก env เริ่มจากสถานะเดียวกันจริง (ดูหมายเหตุ "ค่าแคชหลัง reset" ใน docs/05)
    r1 = run(env, policy, steps, record=args.dump is not None)
    r0 = run(env, None, steps)
    rows = [dict(term=n, weight=C.REWARD_W.get(n), zero=float(a), p3b=float(b))
            for n, a, b in zip(r0["names"], r0["rate"], r1["rate"])]
    ilib.print_table(rows, fmt={"zero": "{:+.3f}", "p3b": "{:+.3f}"})
    print(f"    รวม (reward/s):   ศูนย์ {r0['total_per_s']:+.2f} · P3b {r1['total_per_s']:+.2f}")
    print(f"    ล้ม:              ศูนย์ {r0['falls']} ครั้ง · P3b {r1['falls']} ครั้ง")
    print(f"    vx ครึ่งหลัง (env ที่ตั้งตรง): ศูนย์ {r0['vx']:+.3f} · P3b {r1['vx']:+.3f} m/s (สั่ง {args.vx})")
    print("    (ค่าในตาราง = func × weight เฉลี่ย = reward ต่อวินาที · reward ต่อ step = ค่านี้ × step_dt 0.02)")
    if args.dump:
        out = Path(args.dump).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        np.savez(out, names=np.array(r1["names"]), **{k: np.array(v) for k, v in r1["rec"].items()})
        print(f"    บันทึก {out}")
    env.close()


if __name__ == "__main__":
    main()
    app.close()
