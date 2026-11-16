"""read_tb.py: อ่าน TensorBoard เป็นตัวเลข เทียบหลาย run ข้างกัน (งาน 5.2, 5.6) ฉบับสมบูรณ์  ❌ อ่านไฟล์อย่างเดียว

รัน:  conda activate unitree_rl_mjlab && python week5/scripts/complete/read_tb.py [<run_dir> ...] [--last 50]
      ไม่ใส่ run_dir = P3b + ทุก run ใน ~/g1_study/week5/logs
"""

import argparse
from pathlib import Path

from runlog import P3B_RUN, find_runs

MAIN_TAGS = [
    "Train/mean_reward",
    "Train/mean_episode_length",
    "Episode_Termination/fell_over",
    "Metrics/twist/error_vel_xy",
    "Metrics/twist/error_vel_yaw",
    "Policy/mean_std",
]


def load_scalars(run_dir: Path) -> dict:
    """tag → [(step, value)]  รวมทุกไฟล์ tfevents ใน run (resume อาจสร้างหลายไฟล์) เรียงตาม step"""
    from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
    out = {}
    for f in sorted(run_dir.glob("events.out.tfevents.*")):
        ea = EventAccumulator(str(f), size_guidance={"scalars": 0})   # 0 = เก็บทุกจุด
        ea.Reload()
        for tag in ea.Tags()["scalars"]:
            out.setdefault(tag, []).extend((e.step, e.value) for e in ea.Scalars(tag))
    for tag in out:
        out[tag].sort()
    return out


def tail_mean(points: list, last: int):
    if not points:
        return None
    vals = [v for _, v in points[-last:]]
    return sum(vals) / len(vals)


def fmt(v) -> str:
    if v is None:
        return "—"
    return f"{v:.4g}" if abs(v) < 1000 else f"{v:.0f}"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("runs", nargs="*", type=Path)
    p.add_argument("--last", type=int, default=50)
    args = p.parse_args()
    runs = args.runs or [P3B_RUN, *find_runs()]
    data = {r.name: load_scalars(r) for r in runs}
    names = list(data)
    w = max(12, *(len(n) for n in names))

    print("== ช่วง iteration")
    for n, d in data.items():
        pts = d.get("Train/mean_reward", [])
        print(f"  {n:<{w}} {pts[0][0] if pts else '—'} → {pts[-1][0] if pts else '—'}  ({len(pts)} จุด)")

    def table(title, tags):
        print(f"\n== {title} (เฉลี่ย {args.last} iteration สุดท้าย)")
        print(f"  {'tag':<44}" + "".join(f"{n:>{w + 2}}" for n in names))
        for tag in tags:
            print(f"  {tag:<44}" + "".join(f"{fmt(tail_mean(data[n].get(tag, []), args.last)):>{w + 2}}" for n in names))

    table("หลัก", MAIN_TAGS)
    first = data[names[0]]
    rew_tags = sorted((t for t in first if t.startswith("Episode_Reward/")),
                      key=lambda t: -(tail_mean(first[t], args.last) or 0))
    table("Episode_Reward (เรียงตาม run แรก: รางวัลมาก → โทษมาก)", rew_tags)

    if rew_tags:
        top, bottom = rew_tags[0], rew_tags[-1]
        print(f"\n{names[0]}: รางวัลมากที่สุด {top.split('/')[-1]} · ลงโทษมากที่สุด {bottom.split('/')[-1]}")
    # 5.6: Episode_Reward = raw × weight (× dt) ถ้า weight เพิ่ม k เท่า ให้หารด้วย k ก่อนเทียบ
    #      ถ้าหารแล้วค่าเล็กลง = พฤติกรรมเปลี่ยนจริง (policy ทำให้ term นั้นเกิดน้อยลง)


if __name__ == "__main__":
    main()
