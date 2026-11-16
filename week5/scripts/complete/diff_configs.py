"""diff_configs.py: เทียบ config (env.yaml + agent.yaml) ของ 2 run (งาน 5.4) ฉบับสมบูรณ์  ❌ อ่านไฟล์อย่างเดียว

รัน:  conda activate unitree_rl_mjlab && python week5/scripts/complete/diff_configs.py <run_a> <run_b> [--all]
      --all = แสดง key ที่ปกติข้าม (ชื่อ run, resume ...) ด้วย
"""

import argparse
import math
from pathlib import Path

from runlog import load_agent_yaml, load_env_yaml

IGNORE_SUBSTR = ("run_name", "load_run", "load_checkpoint", "resume", "log_dir", "seed")


def flatten(d, prefix="") -> dict:
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            out.update(flatten(v, f"{prefix}{k}."))
    elif isinstance(d, list) and d and any(isinstance(x, (dict, list)) for x in d):
        for i, v in enumerate(d):
            out.update(flatten(v, f"{prefix}[{i}]."))
    else:
        out[prefix[:-1]] = d                     # list ของตัวเลขเก็บเป็นค่าเดียว (อ่านง่ายกว่า)
    return out


def same(a, b) -> bool:
    if isinstance(a, float) and isinstance(b, float):
        return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)
    return a == b


def diff(a: dict, b: dict, show_all: bool) -> list:
    rows = []
    for k in sorted(set(a) | set(b)):
        if not show_all and any(s in k for s in IGNORE_SUBSTR):
            continue
        va, vb = a.get(k, "<ไม่มี>"), b.get(k, "<ไม่มี>")
        if not same(va, vb):
            rows.append((k, va, vb))
    return rows


def short(v, n=40) -> str:
    s = str(v)
    return s if len(s) <= n else s[:n - 1] + "…"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("run_a", type=Path)
    p.add_argument("run_b", type=Path)
    p.add_argument("--all", action="store_true")
    args = p.parse_args()
    print(f"A = {args.run_a.name}\nB = {args.run_b.name}")
    for label, loader in (("env.yaml", load_env_yaml), ("agent.yaml", load_agent_yaml)):
        rows = diff(flatten(loader(args.run_a)), flatten(loader(args.run_b)), args.all)
        print(f"\n== {label}: ต่างกัน {len(rows)} จุด")
        # term ที่มีแค่ฝั่งเดียว (เช่นเพิ่ม event ทั้งก้อน) มีหลายสิบ key: รวมเป็นบรรทัดเดียวต่อ term
        only = {}
        for k, va, vb in rows:
            if va == "<ไม่มี>" or vb == "<ไม่มี>":
                group = ".".join(k.split(".")[:2])
                side = "B" if va == "<ไม่มี>" else "A"
                only.setdefault((group, side), 0)
                only[(group, side)] += 1
            else:
                print(f"  {short(k, 60):<60} A={short(va):<40} B={short(vb)}")
        for (group, side), n in only.items():
            print(f"  {group + '.*':<60} มีแค่ใน {side} ({n} key)")
    # control vs ทดลอง: ควรต่างกันแค่ rewards.<term>.weight จุดเดียว


if __name__ == "__main__":
    main()
