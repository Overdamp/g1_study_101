"""R4: แกะ reward ทีละ term: action ศูนย์ vs policy P3b โครงให้เติม (TODO) · เฉลย ../complete/r4_reward_probe.py

ทายก่อนรัน
  1. action ศูนย์ (ยืนท่า default ด้วย PD) จะล้มไหม? ถ้าล้ม term ไหนติดลบมากสุด
  2. policy P3b สั่ง 0.5 m/s จะเดินได้จริงกี่ m/s? (vault บอก P3b ติดตาม ~0.4)
  3. reward รวมต่อวินาทีของ policy ≈ ? (บวกหรือลบ)
TODO ในไฟล์นี้: run() · และ fix_command / manual_reward / ActorMLP.__call__ ใน rlib_skeleton.py

  python r4_reward_probe.py                    # vx 0.5 m/s, 16 env, 5 s
  python r4_reward_probe.py --vx 1.0 --seconds 10
  python r4_reward_probe.py --vx 0.0           # สั่งยืน → term ไหนเปลี่ยน

สิ่งที่ควรเห็น
  1. reward ต่อ step = Σ func × weight × dt  (ตรวจกับ env.reward_buf ทุก step → max error ~1e-7)
  2. action ศูนย์ (= ยืนท่า default ด้วย PD) ล้มใน ~1–2 s → is_terminated −200 กินคะแนนเกือบหมด
  3. policy: track_linear_velocity สูง, ไม่ล้ม · penalty term ไหนใหญ่สุด
  4. Episode_Reward/<term> ใน TensorBoard = ผลรวมทั้ง episode ÷ episode_length_s (20 s เสมอ แม้ล้มเร็ว)
"""
import argparse
import contextlib
import io

import torch

import rlib_skeleton as rlib


def run(env, policy, steps):
    """รัน steps ครั้ง → (rate เฉลี่ยต่อ term, จำนวนล้ม, vx เฉลี่ย, error สูงสุดของ manual_reward)"""
    obs, _ = env.reset()
    rm = env.reward_manager
    rate_sum = torch.zeros(len(rm.active_terms), device=env.device)
    falls, vx_sum, max_err = 0, 0.0, 0.0
    robot = env.scene["robot"]
    for _ in range(steps):
        # TODO:
        #   1. a = policy(obs["actor"]) ใน torch.no_grad()
        #   2. obs, rew, term, _to, _ = env.step(a)
        #   3. max_err = ค่ามากสุดของ |manual_reward(env) − rew|
        #   4. rate_sum += rm._step_reward เฉลี่ยข้าม env (dim=0)
        #   5. falls += จำนวน env ที่ term เป็น True · vx_sum += vx กรอบหุ่น (root_link_lin_vel_b[:, 0]) เฉลี่ย
        break
    return rate_sum / steps, falls, vx_sum / steps, max_err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vx", type=float, default=0.5)
    ap.add_argument("--seconds", type=float, default=5.0)
    ap.add_argument("--num-envs", type=int, default=16)
    args = ap.parse_args()

    cfg = rlib.load_cfg(rlib.FLAT, args.num_envs)
    rlib.fix_command(cfg, args.vx)
    cfg.observations["actor"].enable_corruption = False   # วัดผล: ไม่ใส่ noise
    cfg.events.pop("push_robot", None)                    # วัดผล: ไม่ผลัก
    with contextlib.redirect_stdout(io.StringIO()):
        env = rlib.make_env(cfg)
    actor = rlib.ActorMLP(device=env.device)
    steps = int(args.seconds / env.step_dt)

    zero = lambda o: torch.zeros(o.shape[0], 23, device=o.device)  # noqa: E731
    r0, f0, v0, e0 = run(env, zero, steps)
    r1, f1, v1, e1 = run(env, actor, steps)

    rm = env.reward_manager
    rows = []
    for i, name in enumerate(rm.active_terms):
        w = rm.get_term_cfg(name).weight
        rows.append((name, f"{w:g}", f"{r0[i]:+.3f}", f"{r1[i]:+.3f}"))
    rows.append(("รวม (ต่อวินาที)", "", f"{r0.sum():+.3f}", f"{r1.sum():+.3f}"))
    print(f"\nคำสั่ง vx = {args.vx} m/s · {args.num_envs} env · {steps} step ({args.seconds:g} s)\n"
          f"ค่าในตาราง = func × weight เฉลี่ย (หน่วย 'ต่อวินาที' · คูณ dt {env.step_dt} = ต่อ step)\n")
    rlib.print_table(rows, ["term", "weight", "action ศูนย์", "policy P3b"])
    print(f"\nล้ม (terminated):  ศูนย์ {f0} ครั้ง · policy {f1} ครั้ง")
    print(f"vx จริงเฉลี่ย:      ศูนย์ {v0:+.2f} · policy {v1:+.2f} m/s (สั่ง {args.vx})")
    print(f"manual_reward vs reward_buf: error สูงสุด {max(e0, e1):.1e}")
    env.close()


if __name__ == "__main__":
    main()
