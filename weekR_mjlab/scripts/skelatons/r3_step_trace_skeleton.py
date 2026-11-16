"""R3: ตามรอยว่า env.step() เรียกอะไร ตามลำดับไหน โครงให้เติม (TODO) · เฉลย ../complete/r3_step_trace.py

ทายก่อนรัน
  1. ใน 1 env.step() action.apply_action ถูกเรียกกี่ครั้ง? process_action กี่ครั้ง?
  2. reward คำนวณ "ก่อน" หรือ "หลัง" observation? ทำไมต้องเป็นลำดับนั้น
  3. ถ้ามี env หมดเวลาใน step นี้ จะมีอะไรถูกเรียกเพิ่ม? obs ที่คืนมาเป็นของ episode เก่าหรือใหม่?
TODO ในไฟล์นี้: บังคับให้ env 0 หมดเวลา (--reset) · และ StepTracer._wrap/__exit__ ใน rlib_skeleton.py

  python r3_step_trace.py                # step ปกติ 1 ครั้ง
  python r3_step_trace.py --reset        # step ที่มี env ล้ม/หมดเวลา → เห็น _reset_idx (curriculum, event reset)
  python r3_step_trace.py --raw          # ไม่ย่อรายการซ้ำ

สิ่งที่ควรเห็น (ตรงกับ manager_based_rl_env.py:368–419)
  action.process_action ×1                         ← policy ส่ง action มา 1 ครั้ง (50 Hz)
  (action.apply_action → sim.step) ×4              ← decimation 4: q_des เดิม, ฟิสิกส์ 4 step (200 Hz)
  termination.compute → reward.compute             ← ตัดสินจากสถานะหลัง 4 step
  [ถ้ามี env ต้อง reset: curriculum.compute → event.apply(reset)]
  sim.forward → command.compute → event.apply(interval) → sim.sense → observation.compute
"""
import argparse

import torch

import rlib_skeleton as rlib


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="บังคับให้ env 0 หมดเวลาใน step ที่ trace")
    ap.add_argument("--raw", action="store_true")
    args = ap.parse_args()

    cfg = rlib.load_cfg(rlib.FLAT, num_envs=2)
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()):
        env = rlib.make_env(cfg)
    env.reset()
    a = torch.zeros(env.num_envs, env.action_manager.total_action_dim, device=env.device)
    env.step(a)                                 # อุ่นเครื่อง 1 step (step แรกมี kernel compile)

    if args.reset:
        # time_out = episode_length_buf >= max_episode_length → ตั้งให้ env 0 ครบเวลาใน step ถัดไป
        # TODO: time_out = episode_length_buf >= max_episode_length และ step จะ +1 ก่อนเช็ค
        #       → ตั้ง env.episode_length_buf[0] ให้ step ถัดไปครบเวลาพอดี
        pass

    with rlib.StepTracer(env) as tr:
        obs, rew, terminated, time_outs, extras = env.step(a)

    calls = tr.calls if args.raw else rlib.compress(tr.calls)
    print(f"env.step() เรียก {len(tr.calls)} ครั้ง:\n")
    for i, c in enumerate(calls, 1):
        print(f"  {i:2d}. {c}")

    print(f"\nผลที่คืน: obs {{{', '.join(f'{k}: {tuple(v.shape)}' for k, v in obs.items())}}} · "
          f"reward {tuple(rew.shape)} · terminated {terminated.tolist()} · time_outs {time_outs.tolist()}")
    if args.reset:
        log = extras.get("log", {})
        keys = [k for k in log if k.startswith(("Episode_Reward/", "Episode_Termination/"))]
        print(f"\nextras['log'] มี {len(log)} key หลัง reset เช่น:")
        for k in keys[:4] + [k for k in keys if "Termination" in k]:
            v = log[k]
            print(f"  {k:45s} {float(v):.4f}")
        print("  → runner เอาค่าเหล่านี้ไปเฉลี่ยแล้วลง TensorBoard (Episode_Reward/... ที่เห็นในกราฟ)")
    env.close()


if __name__ == "__main__":
    main()
