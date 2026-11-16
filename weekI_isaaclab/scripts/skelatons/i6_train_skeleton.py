"""I6: เทรน contract task ด้วย rsl_rl (PPO) ได้ทั้งแบบ manager และ Direct · ประกอบ train.py เองแบบสั้น (เหมือน R8 ของ mjlab)

    python i6_train.py --mode direct  --num-envs 512 --iters 20
    python i6_train.py --mode manager --num-envs 512 --iters 20
    python i6_train.py --mode direct --init-p3b --iters 20      # actor เริ่มจาก P3b (critic ใหม่) → fine-tune ใน Isaac/Newton

log: ~/g1_study/weekI_isaaclab/logs/rsl_rl/contract_<mode>/<วันเวลา>/ (tensorboard)
⚠ ใช้ GPU เต็ม อย่ารันตอน session งานหลักเทรน

ทำไม --init-p3b ได้: obs ของ actor (80) และ action (23) ตรงกับ P3b ทุกตัว → โหลดน้ำหนัก actor ได้
critic ของเรา 84 ≠ 95 ของ mjlab → เริ่ม critic ใหม่ (ช่วงแรก value ยังผิด, advantage เพี้ยน → policy อาจแย่ลงก่อน)

[skeleton] ทายก่อนรัน
  1. เริ่มจากศูนย์ 10 iteration: Mean reward บวกหรือลบ · ถ้า --init-p3b ล่ะ
  2. ทำไมโหลด actor ของ P3b ได้แต่ critic ไม่ได้
"""
import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

from isaaclab.app import AppLauncher

ap = argparse.ArgumentParser()
ap.add_argument("--mode", choices=["manager", "direct"], default="direct")
ap.add_argument("--num-envs", type=int, default=512)
ap.add_argument("--iters", type=int, default=20)
ap.add_argument("--physx", action="store_true")
ap.add_argument("--init-p3b", action="store_true")
ap.add_argument("--seed", type=int, default=0)
AppLauncher.add_app_launcher_args(ap)
ap.set_defaults(headless=True, visualizer="none")
args = ap.parse_args()
app = AppLauncher(args).app

import gymnasium as gym  # noqa: E402
import torch  # noqa: E402
from isaaclab.utils.io import dump_yaml  # noqa: E402
from isaaclab_rl.rsl_rl import RslRlOnPolicyRunnerCfg, RslRlPpoActorCriticCfg, RslRlPpoAlgorithmCfg  # noqa: E402
from isaaclab_rl.rsl_rl import RslRlVecEnvWrapper, handle_deprecated_rsl_rl_cfg  # noqa: E402
from rsl_rl.runners import OnPolicyRunner  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
import ilib_skeleton as ilib  # noqa: E402


def agent_cfg() -> RslRlOnPolicyRunnerCfg:
    """PPO แบบเดียวกับ mjlab (rl_cfg.py): MLP 512-256-128 ELU · 24 step/env · 5 epoch × 4 minibatch"""
    # TODO(I6) RslRlOnPolicyRunnerCfg: obs_groups actor←"policy", critic←"critic" (asymmetric) · logger tensorboard
    raise NotImplementedError('TODO(I6) RslRlOnPolicyRunnerCfg: obs_groups actor←"policy", critic←"critic" (asymmetric) · logger tensorboard')


def load_p3b_actor(runner) -> None:
    """โหลด actor ของ P3b (normalizer + MLP + std) เข้า runner.alg.actor · critic ไม่แตะ (เริ่มใหม่)

    rsl_rl 5: PPO มี self.actor / self.critic แยกกันเป็น MLPModel · key ชุดเดียวกับ actor_state_dict ใน checkpoint ของ mjlab
    (obs_normalizer._mean/_var/_std/count, mlp.0/2/4/6, distribution.std_param) → load_state_dict ตรงๆ ได้
    """
    sd = torch.load(ilib.CKPT_P3B, map_location="cuda:0", weights_only=False)["actor_state_dict"]
    # TODO(I6) runner.alg.actor.load_state_dict(sd, strict=False) → พิมพ์ key ที่ขาด/เกิน
    raise NotImplementedError('TODO(I6) runner.alg.actor.load_state_dict(sd, strict=False) → พิมพ์ key ที่ขาด/เกิน')
    print(f"[init-p3b] โหลด {len(sd)} tensor · missing {res.missing_keys} · unexpected {res.unexpected_keys}")


def main():
    preset = "physx" if args.physx else "newton"
    # TODO(I6) import โมดูลตาม mode (skeleton: contract_manager_skeleton / contract_direct_skeleton) → mod.make_cfg → gym.make → RslRlVecEnvWrapper
    raise NotImplementedError('TODO(I6) import โมดูลตาม mode (skeleton: contract_manager_skeleton / contract_direct_skeleton) → mod.make_cfg → gym.make → RslRlVecEnvWrapper')
    acfg = agent_cfg()
    # rsl_rl 5 เปลี่ยนรูปแบบ config (policy → actor/critic แยก) · ฟังก์ชันของ Isaac Lab แปลงให้ (train.py ก็เรียก)
    from importlib.metadata import version
    acfg = handle_deprecated_rsl_rl_cfg(acfg, version("rsl-rl-lib"))
    log_dir = ilib.LOGS / "rsl_rl" / acfg.experiment_name / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    runner = OnPolicyRunner(env, acfg.to_dict(), log_dir=str(log_dir), device=acfg.device)
    if args.init_p3b:
        load_p3b_actor(runner)
    dump_yaml(str(log_dir / "params/env.yaml"), cfg)
    dump_yaml(str(log_dir / "params/agent.yaml"), acfg)
    print(f"[I6 train] {args.mode} · {preset} · {args.num_envs} env · {args.iters} iteration → {log_dir}")
    t = time.time()
    runner.learn(num_learning_iterations=args.iters, init_at_random_ep_len=True)
    el = time.time() - t
    print(f"[I6 train] เสร็จ {el:.1f} s → {el / args.iters:.2f} s/iteration (รวม iteration แรกที่ช้า)")
    env.close()


if __name__ == "__main__":
    main()
    app.close()
