"""reward_table.py: ตาราง reward ทุก term จาก config ของ run จริง (งาน 5.1) ฉบับสมบูรณ์  ❌ อ่านไฟล์อย่างเดียว

รัน:  conda activate unitree_rl_mjlab && python week5/scripts/complete/reward_table.py [<run_dir> ...] [--sort]
      ไม่ใส่ run_dir = run ของ P3b
"""

import argparse
from pathlib import Path

from runlog import P3B_RUN, load_env_yaml

INTERESTING = ("std", "command_threshold", "target_height", "period", "threshold", "force_threshold", "limit_angle")


def short(v) -> str:
    """ย่อค่า params ให้อ่านง่าย (dict ยาวๆ เช่น std ต่อข้อต่อ → แสดงจำนวน key)"""
    if isinstance(v, dict):
        return f"{{{len(v)} keys}}" if len(v) > 2 else str(v)
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def reward_rows(env: dict) -> list:
    rows = []
    for name, term in env["rewards"].items():
        if term is None:                                  # term ที่ถูกปิดด้วย None
            continue
        params = term.get("params") or {}
        keep = {k: params[k] for k in INTERESTING if k in params}
        rows.append((name, float(term["weight"]), keep))
    return rows


def print_table(title: str, rows: list, sort: bool) -> None:
    if sort:
        rows = sorted(rows, key=lambda r: -abs(r[1]))
    print(f"\n== {title}")
    print(f"  {'term':<24} {'weight':>10}  {'ชนิด':<7} params")
    for name, w, params in rows:
        kind = "รางวัล" if w > 0 else ("โทษ" if w < 0 else "ปิด")
        ps = ", ".join(f"{k}={short(v)}" for k, v in params.items())
        print(f"  {name:<24} {w:>10g}  {kind:<7} {ps}")
    n_pos = sum(1 for r in rows if r[1] > 0)
    n_neg = sum(1 for r in rows if r[1] < 0)
    print(f"  รวม {len(rows)} term: รางวัล {n_pos} · โทษ {n_neg}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("runs", nargs="*", type=Path)
    p.add_argument("--sort", action="store_true", help="เรียงตาม |weight| มาก → น้อย")
    args = p.parse_args()
    for run in args.runs or [P3B_RUN]:
        env = load_env_yaml(run)
        print_table(run.name, reward_rows(env), args.sort)
        print("  termination:")
        for name, term in (env.get("terminations") or {}).items():
            params = (term or {}).get("params") or {}
            ps = ", ".join(f"{k}={short(v)}" for k, v in params.items() if k in INTERESTING)
            print(f"    {name:<22} time_out={term.get('time_out', False)}  {ps}")
        print(f"  episode_length_s = {env.get('episode_length_s')}  · num_envs = {env['scene']['num_envs']}")
    # is_terminated −200 กับ tracking +1 ต่อวินาที: ล้มครั้งเดียวเท่ากับเสียรางวัล tracking เต็มๆ 200 วินาที
    # (มากกว่าทั้ง episode 20 s) → policy เรียนรู้ "อย่าล้ม" ก่อนอย่างอื่น


if __name__ == "__main__":
    main()
