"""R2: สร้าง env จริง แล้วดูว่า manager แต่ละตัวได้อะไรจาก config โครงให้เติม (TODO) · เฉลย ../complete/r2_build_env.py

ทายก่อนรัน
  1. actor 80 แบ่งเป็น term ละกี่ตัว? critic 95 มีอะไรเพิ่มจาก actor อีก 15 ตัว?
  2. max_episode_length = กี่ step?
  3. scale ของ hip_pitch ≈ ? (สูตรใน g1_23dof_constants.py:279 = 0.25 × effort_limit / stiffness, hip pitch 88 Nm, kp 40.2)
TODO ในไฟล์นี้: เทียบ scale/offset ของ env กับ deploy.yaml · และ term_slices ใน rlib_skeleton.py

  python r2_build_env.py                 # สรุป (ซ่อนตาราง [INFO] ของ mjlab)
  python r2_build_env.py --verbose       # ดูตาราง [INFO] ทั้งหมดที่ mjlab พิมพ์ตอนสร้าง env
  python r2_build_env.py --task Unitree-G1-23Dof-Rough

สิ่งที่ควรเห็น
  1. ลำดับการสร้าง manager (load_managers): event → command → action → observation → termination → reward → curriculum → metrics
  2. obs actor 80 = 3+3+3+2+23+23+23 · critic 95 = 80 + 3+2+2+2+6 (ตำแหน่งของแต่ละ term)
  3. action 23 ตัว: q_des = action × scale + offset (offset = ท่า default) → ตรงกับ deploy.yaml ไหม
  4. step_dt, max_episode_length, จำนวน env, device
"""
import argparse
import contextlib
import io
import re
from pathlib import Path

import rlib_skeleton as rlib


def load_deploy_yaml(path: Path):
    """อ่าน deploy.yaml แบบไม่พึ่ง pyyaml: เอาแค่ list ตัวเลขที่ต้องใช้"""
    text = path.read_text()

    def grab(key, start=0):
        m = re.search(rf"{key}:\s*\[([^\]]*)\]", text[start:], re.S)
        return [float(x) for x in m.group(1).replace("\n", " ").split(",")]

    act = text.index("actions:")
    return {
        "joint_ids_map": [int(x) for x in grab("joint_ids_map")],
        "stiffness": grab("stiffness"),
        "damping": grab("damping"),
        "scale": grab("scale", act),
        "offset": grab("offset", act),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default=rlib.FLAT)
    ap.add_argument("--num-envs", type=int, default=4)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    cfg = rlib.load_cfg(args.task, args.num_envs)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf) if not args.verbose else contextlib.nullcontext():
        env = rlib.make_env(cfg)
    if not args.verbose:
        order = [ln.split("<")[1].split(">")[0] for ln in buf.getvalue().splitlines() if "[INFO] <" in ln]
        print("ลำดับที่สร้าง manager:", " → ".join(order))

    print(f"\nnum_envs {env.num_envs} · device {env.device} · physics_dt {env.physics_dt} · "
          f"step_dt {env.step_dt} · max_episode_length {env.max_episode_length} step "
          f"(= ceil({env.max_episode_length_s} / {env.step_dt}))")

    # ---- 2. observation
    for group in env.observation_manager.active_terms:
        sl = rlib.term_slices(env, group)
        total = max((e for _, e in sl.values()), default=0)
        print(f"\n[obs.{group}] รวม {total}")
        rlib.print_table([(n, f"[{s}, {e})", e - s) for n, (s, e) in sl.items()], ["term", "ช่วง", "ขนาด"])

    obs, _ = env.reset()
    print("\nobs จริงหลัง reset:", {k: tuple(v.shape) for k, v in obs.items()}, "← (num_envs, dim)")

    # ---- 3. action
    term = env.action_manager.get_term("joint_pos")
    names = term.target_names
    scale = term.scale if isinstance(term.scale, float) else term.scale[0].tolist()
    offset = term.offset[0].tolist()
    dep = load_deploy_yaml(rlib.V0 / "params/deploy.yaml")
    rows, bad = [], 0
    for i, n in enumerate(names):
        # TODO: s = scale ของ joint i (scale อาจเป็น float ตัวเดียว หรือ list)
        #       ok = scale ต่างจาก dep["scale"][i] < 0.01 และ offset ต่างจาก dep["offset"][i] < 1e-3
        #       เพิ่มแถว (i, slot = dep["joint_ids_map"][i], ชื่อ, scale env, scale deploy, offset env, offset deploy, ✓/✗)
        pass
    print(f"\n[action] {env.action_manager.total_action_dim} ตัว · q_des = action × scale + offset")
    rlib.print_table(rows, ["i", "slot", "joint", "scale(env)", "scale(deploy)", "offset(env)", "offset(deploy)", ""])
    print(f"ไม่ตรง deploy.yaml: {bad} ตัว  (deploy.yaml ปัด scale เหลือ 2 ตำแหน่ง)")

    env.close()


if __name__ == "__main__":
    main()
