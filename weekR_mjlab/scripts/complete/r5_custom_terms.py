"""R5: เพิ่ม/ลบ/ปิด term เองโดยไม่แตะ repo หลัก ฉบับสมบูรณ์

  python r5_custom_terms.py                  # เพิ่ม term ของเรา (my_terms.py) แล้วรัน policy 3 s
  python r5_custom_terms.py --actor-obs      # ใส่ base_height ใน actor ด้วย → 81 → โหลด P3b ไม่ได้
  python r5_custom_terms.py --rough          # ดู actor ของ Rough (มี height_scan) ว่ากี่ตัว

สิ่งที่ควรเห็น
  1. แก้ config = แก้ dict ก่อนสร้าง env: เพิ่ม key / del / ตั้งเป็น None / weight = 0
  2. critic เปลี่ยนขนาดได้อิสระ (95 → 96) ไม่กระทบ deploy · actor เปลี่ยน → checkpoint/ONNX เดิมใช้ไม่ได้
  3. term ใหม่ขึ้นในตาราง reward พร้อมค่า · termination ใหม่นับใน Episode_Termination
  4. weight = 0: ยังอยู่ในรายการแต่ไม่คำนวณ (reward_manager.py: `if weight == 0: continue`)
     ตั้งเป็น None: manager ข้ามตอนสร้าง (`term_cfg is None → skipping`) · del: หายจาก dict
"""
import argparse
import contextlib
import io
import math

import torch

import rlib

rlib.setup_path()
from mjlab.managers.observation_manager import ObservationTermCfg  # noqa: E402
from mjlab.managers.reward_manager import RewardTermCfg  # noqa: E402
from mjlab.managers.scene_entity_config import SceneEntityCfg  # noqa: E402
from mjlab.managers.termination_manager import TerminationTermCfg  # noqa: E402

import my_terms  # noqa: E402


def add_my_terms(cfg, actor_obs: bool) -> None:
    """แก้ cfg ด้วยมือ = สิ่งที่ env_cfgs.py ของ repo ทำ (แต่ทำในไฟล์ของเรา)"""
    # obs: critic ได้ความสูง pelvis (privileged) · actor ได้ด้วยถ้าสั่ง
    cfg.observations["critic"].terms["base_height"] = ObservationTermCfg(func=my_terms.base_height)
    if actor_obs:
        cfg.observations["actor"].terms["base_height"] = ObservationTermCfg(func=my_terms.base_height)

    feet = SceneEntityCfg("robot", site_names=("left_foot", "right_foot"))
    cfg.rewards["feet_too_close"] = RewardTermCfg(
        func=my_terms.feet_too_close, weight=-5.0, params={"min_dist": 0.15, "asset_cfg": feet})
    cfg.rewards["vx_ema_error"] = RewardTermCfg(
        func=my_terms.vx_ema_error, weight=-0.5, params={"command_name": "twist", "alpha": 0.05})

    cfg.terminations["pelvis_too_low"] = TerminationTermCfg(
        func=my_terms.pelvis_too_low, params={"min_height": 0.45})

    # ลบ / ปิด term เดิม 3 แบบ
    cfg.rewards["soft_landing"].weight = 0.0      # ยังอยู่ แต่ไม่คำนวณ
    cfg.rewards["joint_acc_l2"] = None            # manager ข้าม
    del cfg.rewards["stand_still"]                # หายจาก dict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--actor-obs", action="store_true")
    ap.add_argument("--rough", action="store_true")
    args = ap.parse_args()

    if args.rough:
        cfg = rlib.load_cfg(rlib.ROUGH, 2)
        with contextlib.redirect_stdout(io.StringIO()):
            env = rlib.make_env(cfg)
        sl = rlib.term_slices(env, "actor")
        print("Rough actor:", {k: e - s for k, (s, e) in sl.items()}, "รวม", max(e for _, e in sl.values()))
        print("height_scan =", sl["height_scan"][1] - sl["height_scan"][0],
              "จุด (grid 1.6×1.0 m ละเอียด 0.1 m = 17 × 11)")
        print("P3b actor รับ 80 → resume บน Rough ตรงๆ ไม่ได้ (mlp.0.weight ขนาด 512×80 ไม่ตรง)"
              " → Rough-Blind จึง del height_scan (env_cfgs.py:314)")
        env.close()
        return

    cfg = rlib.load_cfg(rlib.FLAT, 8)
    rlib.fix_command(cfg, 0.5)
    cfg.observations["actor"].enable_corruption = False
    add_my_terms(cfg, args.actor_obs)
    with contextlib.redirect_stdout(io.StringIO()):
        env = rlib.make_env(cfg)

    a_dim = max(e for _, e in rlib.term_slices(env, "actor").values())
    c_dim = max(e for _, e in rlib.term_slices(env, "critic").values())
    print(f"actor {a_dim} · critic {c_dim}")
    rm = env.reward_manager
    print(f"reward terms ({len(rm.active_terms)}): joint_acc_l2 {'อยู่' if 'joint_acc_l2' in rm.active_terms else 'หาย'} · "
          f"stand_still {'อยู่' if 'stand_still' in rm.active_terms else 'หาย'} · "
          f"soft_landing {'อยู่ (w=0)' if 'soft_landing' in rm.active_terms else 'หาย'}")
    print("terminations:", env.termination_manager.active_terms)

    actor = rlib.ActorMLP(device=env.device)
    obs, _ = env.reset()
    try:
        actor(obs["actor"])
    except RuntimeError as e:
        print(f"\n❌ P3b ใช้กับ actor {a_dim} ไม่ได้: {str(e).splitlines()[0]}")
        print("   ตอน resume ด้วย train.py สาเหตุเดียวกันจะขึ้นเป็น: size mismatch for actor mlp.0.weight [512, 80] vs [512, 81]")
        env.close()
        return

    steps = int(3.0 / env.step_dt)
    sums = torch.zeros(len(rm.active_terms), device=env.device)
    h = []
    for _ in range(steps):
        with torch.no_grad():
            obs, _, _, _, _ = env.step(actor(obs["actor"]))
        sums += rm._step_reward.mean(0)
        h.append(obs["critic"][:, -1].mean().item())       # base_height = term สุดท้ายของ critic
    print(f"\nรัน P3b {steps} step (vx 0.5) · base_height ใน critic เฉลี่ย {sum(h) / len(h):.3f} m")
    rows = [(n, f"{rm.get_term_cfg(n).weight:g}", f"{sums[i] / steps:+.4f}")
            for i, n in enumerate(rm.active_terms) if n in ("feet_too_close", "vx_ema_error", "soft_landing", "track_linear_velocity")]
    rlib.print_table(rows, ["term", "weight", "เฉลี่ย (ต่อวินาที)"])
    print(f"pelvis_too_low จบ episode ไปกี่ env: {int(env.termination_manager.get_term('pelvis_too_low').sum())} (step สุดท้าย)")
    print(f"(min_height 0.45 m vs pelvis เดินจริง ~0.75 m · limit_angle ของ fell_over = {math.degrees(cfg.terminations['fell_over'].params['limit_angle']):.0f}°)")
    env.close()


if __name__ == "__main__":
    main()
