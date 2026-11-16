"""R8: ประกอบ train.py เองทีละชิ้น แล้วเทรนจิ๋ว ฉบับสมบูรณ์

  python r8_mini_train.py                      # เริ่มจากศูนย์ 10 iteration, 256 env (~1 นาที)
  python r8_mini_train.py --resume             # เริ่มจาก P3b → reward สูงตั้งแต่ iteration แรก
  python r8_mini_train.py --iters 30 --num-envs 512 --weight foot_clearance=-2

log อยู่ที่ weekR_mjlab/logs/r8_<เวลา>/ (model_*.pt, policy.onnx, params/env.yaml, TensorBoard)

train.py จริง (scripts/train.py) ทำแค่นี้:
  1. cfg = load_env_cfg(task) + load_rl_cfg(task)       ← registry (R1)
  2. tyro แปลง --env.x.y=... / --agent.x=... มาเขียนทับ cfg  ← เราเขียนทับด้วยมือแทน (--weight)
  3. env = ManagerBasedRlEnv(cfg.env)                    ← R2
  4. env = RslRlVecEnvWrapper(env)                       ← แปลงให้ rsl_rl ใช้ได้ (obs dict → TensorDict)
  5. runner = VelocityOnPolicyRunner(env, asdict(agent_cfg), log_dir)
  6. (resume) runner.load(ckpt)                          ← โหลด actor + critic + optimizer + common_step_counter
  7. dump params/env.yaml, agent.yaml
  8. runner.learn(max_iterations, init_at_random_ep_len=True)
     ทุก iteration: rollout num_steps_per_env (24) step × num_envs → PPO update 5 epoch × 4 mini-batch
"""
import argparse
import contextlib
import io
import time
from dataclasses import asdict
from datetime import datetime

import rlib


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iters", type=int, default=10)
    ap.add_argument("--num-envs", type=int, default=256)
    ap.add_argument("--resume", action="store_true", help="เริ่มจาก checkpoint P3b")
    ap.add_argument("--weight", action="append", default=[], metavar="TERM=W",
                    help="เปลี่ยน weight ของ reward (เหมือน --env.rewards.TERM.weight W ของ train.py)")
    args = ap.parse_args()

    rlib.setup_path()
    from mjlab.rl import RslRlVecEnvWrapper
    from mjlab.tasks.registry import load_rl_cfg
    from mjlab.utils.os import dump_yaml
    from src.tasks.velocity.rl import VelocityOnPolicyRunner

    # 1–2. config + override
    env_cfg = rlib.load_cfg(rlib.FLAT, args.num_envs)
    agent_cfg = load_rl_cfg(rlib.FLAT)
    for kv in args.weight:
        term, w = kv.split("=")
        old = env_cfg.rewards[term].weight
        env_cfg.rewards[term].weight = float(w)
        print(f"override: rewards.{term}.weight {old} → {w}")
    agent_cfg.max_iterations = args.iters
    agent_cfg.save_interval = args.iters            # save ตอนจบครั้งเดียว
    agent_cfg.logger = "tensorboard"
    env_cfg.seed = agent_cfg.seed

    log_dir = rlib.LOGS / f"r8_{datetime.now():%Y-%m-%d_%H-%M-%S}{'_resume' if args.resume else ''}"
    print(f"log_dir: {log_dir}")
    print(f"rollout ต่อ iteration = {agent_cfg.num_steps_per_env} step × {args.num_envs} env "
          f"= {agent_cfg.num_steps_per_env * args.num_envs} transition")

    # 3–5. env → wrapper → runner
    with contextlib.redirect_stdout(io.StringIO()):
        env = rlib.make_env(env_cfg)
    venv = RslRlVecEnvWrapper(env, clip_actions=agent_cfg.clip_actions)
    runner = VelocityOnPolicyRunner(venv, asdict(agent_cfg), str(log_dir), env.device)

    # 6. resume
    if args.resume:
        runner.load(str(rlib.CKPT_P3B))
        print(f"resume จาก {rlib.CKPT_P3B.name} · iteration {runner.current_learning_iteration} · "
              f"common_step_counter {env.common_step_counter}")

    # 7. เก็บ config ที่ใช้จริง
    dump_yaml(log_dir / "params" / "env.yaml", asdict(env_cfg))
    dump_yaml(log_dir / "params" / "agent.yaml", asdict(agent_cfg))

    # 8. เทรน (rsl_rl พิมพ์ตารางทุก iteration)
    t0 = time.time()
    runner.learn(num_learning_iterations=args.iters, init_at_random_ep_len=True)
    dt = time.time() - t0
    print(f"\n{args.iters} iteration ใน {dt:.0f} s ({dt / args.iters:.2f} s/iteration)")
    print("ไฟล์ที่ได้:", sorted(p.name for p in log_dir.iterdir()))
    print(f"ดูกราฟ: tensorboard --logdir {rlib.LOGS}")
    env.close()


if __name__ == "__main__":
    main()
