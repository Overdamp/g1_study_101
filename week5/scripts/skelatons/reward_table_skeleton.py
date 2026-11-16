"""reward_table_skeleton.py: พิมพ์ตาราง reward ทุก term จาก config ของ run จริง (งาน 5.1)  ❌ อ่านไฟล์อย่างเดียว

อ่าน <run>/params/env.yaml (config ที่ใช้เทรนจริง ไม่ใช่โค้ดปัจจุบัน) แล้วพิมพ์:
    term | weight | รางวัล/โทษ | params สำคัญ
ใช้เติมตาราง "เติมเอง" ใน week5/docs/rewards.md และเทียบกับตารางใน docs ว่าตรงกันไหม

รัน:  conda activate unitree_rl_mjlab && python week5/scripts/skelatons/reward_table_skeleton.py [<run_dir> ...]
      ไม่ใส่ run_dir = run ของ P3b
"""

import sys
from pathlib import Path

from runlog import P3B_RUN, load_env_yaml

# params ที่น่าสนใจ (ตัวอื่นเช่น asset_cfg ยาวและไม่ค่อยช่วยให้เข้าใจ)
INTERESTING = ("std", "command_threshold", "target_height", "period", "threshold", "force_threshold")


def reward_rows(env: dict) -> list:
    """คืน list ของ (ชื่อ term, weight, dict params ที่น่าสนใจ)"""
    # TODO [5.1] env["rewards"] เป็น dict: ชื่อ term → {"func": ..., "weight": ..., "params": {...}}
    # TODO [5.1] ดึง weight และ params เฉพาะ key ใน INTERESTING
    return []


def print_table(name: str, rows: list) -> None:
    # TODO [5.1] หัวตาราง: term | weight | ชนิด (รางวัล ถ้า weight > 0, โทษ ถ้า < 0, ปิด ถ้า = 0) | params
    # TODO [5.1] เรียงตาม |weight| จากมากไปน้อย ไหม? หรือตามลำดับใน config? (ลองทั้งสองแบบ แบบไหนอ่านง่ายกว่า)
    # TODO [5.1] บรรทัดสรุป: กี่ term เป็นรางวัล กี่ term เป็นโทษ
    pass


def main():
    runs = [Path(p) for p in sys.argv[1:]] or [P3B_RUN]
    for run in runs:
        env = load_env_yaml(run)
        rows = reward_rows(env)
        if not rows:
            print("reward_table: ยังไม่ได้เติม [5.1]")
            return
        print_table(run.name, rows)
        # TODO [5.1] พิมพ์ termination ด้วย: env["terminations"] (ชื่อ + params เช่น limit_angle)
        # คำถาม: is_terminated −200 กับ track_linear_velocity +1.0 ต่างกัน 200 เท่า หมายความว่ายังไงต่อพฤติกรรมของ policy


if __name__ == "__main__":
    main()
