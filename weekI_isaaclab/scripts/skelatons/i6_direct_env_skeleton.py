"""I6: contract task แบบ Direct (contract_direct.py) บน Newton: สร้าง, ดูข้างใน, ให้ P3b เดิน

    python i6_direct_env.py                       # 16 env, vx 0.5, 6 s: action ศูนย์ vs P3b (ตารางเดียวกับ I5)
    python i6_direct_env.py --physx
    python i6_direct_env.py --dump ../../logs/i6.npz   # ให้ i6_compare

พิมพ์
  [1] gym spaces ที่ DirectRLEnv สร้างจาก cfg (observation_space / state_space / action_space)
  [2] index ของ joint/feet ที่ find_joints / find_bodies หาให้ (เทียบ SceneEntityCfg ของ manager)
  [3] ตาราง reward ทีละ term: action ศูนย์ vs P3b (ควรใกล้ I5 มาก เพราะคือ MDP เดียวกัน)
"""
import argparse
import sys
from pathlib import Path

from isaaclab.app import AppLauncher

ap = argparse.ArgumentParser()
ap.add_argument("--num-envs", type=int, default=16)
ap.add_argument("--vx", type=float, default=0.5)
ap.add_argument("--secs", type=float, default=6.0)
ap.add_argument("--physx", action="store_true")
ap.add_argument("--dump", default=None)
AppLauncher.add_app_launcher_args(ap)
ap.set_defaults(headless=True, visualizer="none")
args = ap.parse_args()
app = AppLauncher(args).app

import gymnasium as gym  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
import contract_common_skeleton as C  # noqa: E402
import contract_direct_skeleton as D  # noqa: E402
import ilib_skeleton as ilib  # noqa: E402


def run(env, policy, steps: int, record: bool = False):
    u = env.unwrapped
    with torch.inference_mode():
        obs, _ = env.reset()
        sums = torch.zeros(len(u.term_names), device=u.device)
        falls, vx, total = 0, [], 0.0
        rec = {"policy": [], "critic": [], "step_reward": [], "reward": [], "done": []}
        if record:                                   # แถวแรก = obs หลัง reset (ก่อน step แรก)
            rec["reset_policy"] = [obs["policy"].cpu().numpy()]
            rec["reset_critic"] = [obs["critic"].cpu().numpy()]
        for _ in range(steps):
            # TODO(I6) เหมือน I5 แต่ค่า func×weight อยู่ที่ u.step_reward (เราเก็บเองใน _get_rewards)
            raise NotImplementedError('TODO(I6) เหมือน I5 แต่ค่า func×weight อยู่ที่ u.step_reward (เราเก็บเองใน _get_rewards)')
            total += float(rew.mean())
            falls += int(term.sum())
            d = u._robot.data
            up = torch.acos(-d.projected_gravity_b.torch[:, 2]) < 0.35
            if up.any():
                vx.append(float(d.root_lin_vel_b.torch[up, 0].mean()))
            if record:
                rec["policy"].append(obs["policy"].cpu().numpy())
                rec["critic"].append(obs["critic"].cpu().numpy())
                rec["step_reward"].append(u.step_reward.cpu().numpy().copy())
                rec["reward"].append(rew.cpu().numpy())
                rec["done"].append((term | trunc).cpu().numpy())
    return dict(names=u.term_names, rate=(sums / steps).cpu().numpy(), falls=falls,
                vx=float(np.mean(vx[len(vx) // 2:])) if len(vx) > 1 else float("nan"),
                total_per_s=total / steps / u.step_dt, rec=rec)


def main():
    cfg = D.make_cfg(num_envs=args.num_envs, preset="physx" if args.physx else "newton",
                     fixed_cmd=(args.vx, 0.0, 0.0), corruption=False)
    env = gym.make(D.TASK_ID, cfg=cfg)
    u = env.unwrapped

    print(f"\n[1] DirectRLEnv ({type(u.cfg.sim.physics).__name__}) · class {type(u).__name__}")
    print(f"    single_observation_space: { {k: v.shape for k, v in u.single_observation_space.items()} }")
    print(f"    single_action_space: {u.single_action_space.shape} · step_dt {u.step_dt} · "
          f"max_episode_length {u.max_episode_length}")
    print(f"    manager ที่ DirectRLEnv ยังสร้างให้: event_manager = {getattr(u, 'event_manager', None) is not None} "
          f"(cfg.events = {u.cfg.events}) · ไม่มี reward/obs/action/termination/command manager")

    print("\n[2] index จากชื่อ")
    print(f"    find_joints(POLICY_JOINTS) → {u._jids.tolist()}")
    print(f"    find_bodies({C.FEET}) → {u._feet}")
    print(f"    scale (6 ตัวแรก) {u._scale[:6].cpu().numpy().round(4)} · default (6 ตัวแรก) "
          f"{u._default[0, :6].cpu().numpy().round(3)}")

    steps = int(args.secs / u.step_dt)
    policy = ilib.ActorMLP(device=u.device)
    print(f"\n[3] {args.num_envs} env · คำสั่ง vx {args.vx} · {args.secs} s ({steps} step) · noise ปิด")
    # P3b ก่อน: env ยังสด ทุก env เริ่มจากสถานะเดียวกันจริง (ดูหมายเหตุ "ค่าแคชหลัง reset" ใน docs/05)
    r1 = run(env, policy, steps, record=args.dump is not None)
    r0 = run(env, None, steps)
    rows = [dict(term=n, weight=C.REWARD_W[n], zero=float(a), p3b=float(b))
            for n, a, b in zip(r0["names"], r0["rate"], r1["rate"])]
    ilib.print_table(rows, fmt={"zero": "{:+.3f}", "p3b": "{:+.3f}"})
    print(f"    รวม (reward/s):   ศูนย์ {r0['total_per_s']:+.2f} · P3b {r1['total_per_s']:+.2f}")
    print(f"    ล้ม:              ศูนย์ {r0['falls']} ครั้ง · P3b {r1['falls']} ครั้ง")
    print(f"    vx ครึ่งหลัง (env ที่ตั้งตรง): ศูนย์ {r0['vx']:+.3f} · P3b {r1['vx']:+.3f} m/s (สั่ง {args.vx})")
    if args.dump:
        out = Path(args.dump).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        np.savez(out, names=np.array(r1["names"]), **{k: np.array(v) for k, v in r1["rec"].items()})
        print(f"    บันทึก {out}")
    env.close()


if __name__ == "__main__":
    main()
    app.close()
