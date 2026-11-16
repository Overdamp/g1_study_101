"""read_tb_skeleton.py: อ่านกราฟ TensorBoard เป็นตัวเลข เทียบหลาย run ข้างกัน (งาน 5.2, 5.6)  ❌ อ่านไฟล์อย่างเดียว

ทุก run: ค่าเฉลี่ยของ N iteration สุดท้ายของ tag ที่สนใจ
    Train/mean_reward, Train/mean_episode_length, Episode_Termination/fell_over,
    Metrics/twist/error_vel_xy, Metrics/twist/error_vel_yaw, Episode_Reward/*
พิมพ์เป็นตาราง: แถว = tag, คอลัมน์ = run

รัน:  conda activate unitree_rl_mjlab && python week5/scripts/skelatons/read_tb_skeleton.py <run_dir> [<run_dir> ...] [--last 50]
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
]


def load_scalars(run_dir: Path) -> dict:
    """คืน dict: tag → list ของ (step, value)"""
    # TODO [5.2] from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
    # TODO [5.2] ไฟล์ = run_dir.glob("events.out.tfevents.*") (อาจมีหลายไฟล์ ใช้ทุกไฟล์หรือไฟล์ล่าสุด?)
    # TODO [5.2] ea = EventAccumulator(str(ไฟล์), size_guidance={"scalars": 0});  ea.Reload()
    #            (size_guidance 0 = เก็บทุกจุด ไม่สุ่มตัด)
    # TODO [5.2] วน ea.Tags()["scalars"]: [(e.step, e.value) for e in ea.Scalars(tag)]
    return {}


def tail_mean(points: list, last: int):
    """ค่าเฉลี่ยของ last จุดสุดท้าย (None ถ้าไม่มีข้อมูล)"""
    # TODO [5.2]
    return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("runs", nargs="*", type=Path)
    p.add_argument("--last", type=int, default=50, help="เฉลี่ยกี่ iteration สุดท้าย")
    args = p.parse_args()
    runs = args.runs or [P3B_RUN, *find_runs()]

    data = {r.name: load_scalars(r) for r in runs}
    if not any(data.values()):
        print("read_tb: ยังไม่ได้เติม [5.2]")
        return

    # TODO [5.2] พิมพ์ช่วง iteration ของแต่ละ run (step แรก → สุดท้าย) เช็คว่า fine-tune ต่อจาก 15998 จริง
    # TODO [5.2] ตารางที่ 1: MAIN_TAGS × runs
    # TODO [5.2] ตารางที่ 2: ทุก tag ที่ขึ้นต้นด้วย "Episode_Reward/" × runs  เรียงตามค่าของ run แรก
    # คำถาม 5.2: term ไหนให้รางวัลมากที่สุด / ลงโทษมากที่สุด
    # คำถาม 5.6: term ที่เปลี่ยน weight ใน run ทดลอง ค่า Episode_Reward ของมันเปลี่ยนเพราะ weight หรือเพราะพฤติกรรม? แยกยังไง
    #            (ใบ้: Episode_Reward = raw × weight ถ้า weight เพิ่ม 4 เท่าแต่ค่าเพิ่มแค่ 2 เท่า แปลว่า raw ลดลงครึ่งหนึ่ง)


if __name__ == "__main__":
    main()
