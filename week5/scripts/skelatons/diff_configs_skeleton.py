"""diff_configs_skeleton.py: เทียบ config (env.yaml + agent.yaml) ของ 2 run (งาน 5.4 ขั้นที่ 5)  ❌ อ่านไฟล์อย่างเดียว

ใช้ตรวจว่า:
  - control กับ ทดลอง ต่างกัน "แค่" weight ที่ตั้งใจเปลี่ยน
  - config ปัจจุบันของ branch ยังเหมือนตอนเทรน P3b ไหม (เทียบ control กับ run P3b)

รัน:  conda activate unitree_rl_mjlab && python week5/scripts/skelatons/diff_configs_skeleton.py <run_a> <run_b>
"""

import sys
from pathlib import Path

from runlog import load_agent_yaml, load_env_yaml

# key ที่ต่างกันแน่ๆ ระหว่าง run และไม่มีความหมาย (ชื่อ run, path, resume ...)  เติมเพิ่มได้
IGNORE_SUBSTR = ("run_name", "load_run", "load_checkpoint", "resume", "log_dir")


def flatten(d, prefix="") -> dict:
    """dict ซ้อนกัน → dict แบน key เป็น path เช่น 'rewards.action_rate_l2.weight'"""
    # TODO [5.4] ถ้า d เป็น dict: วน key → flatten(ค่า, prefix + key + ".")
    # TODO [5.4] ถ้าเป็น list: วน index → flatten(ค่า, prefix + f"[{i}].")  หรือเก็บทั้ง list เป็นค่าเดียว (เลือกเอง)
    # TODO [5.4] ไม่งั้น: {prefix[:-1]: d}
    return {}


def diff(a: dict, b: dict) -> list:
    """คืน list ของ (key, ค่าใน a, ค่าใน b) ที่ต่างกัน (รวม key ที่มีแค่ฝั่งเดียว)"""
    # TODO [5.4] รวม key ทั้งสองฝั่ง เทียบค่า ข้าม key ที่มีคำใน IGNORE_SUBSTR
    # TODO [5.4] ระวัง float: 0.1 กับ 0.10000000001 ถือว่าเท่ากันไหม
    return []


def main():
    if len(sys.argv) != 3:
        raise SystemExit("ใช้: python diff_configs_skeleton.py <run_a> <run_b>")
    a, b = Path(sys.argv[1]), Path(sys.argv[2])
    for label, loader in (("env.yaml", load_env_yaml), ("agent.yaml", load_agent_yaml)):
        rows = diff(flatten(loader(a)), flatten(loader(b)))
        # TODO [5.4] พิมพ์หัวข้อ label + จำนวนจุดที่ต่าง แล้วพิมพ์ทีละแถว: key | a | b  (ตัดค่ายาวเกิน 60 ตัวอักษร)
        if not rows:
            print(f"{label}: ไม่มีจุดต่าง (หรือยังไม่ได้เติม [5.4])")
    # ทายก่อนรัน control vs ทดลอง: ควรต่างกันกี่จุด  แล้ว control vs P3b ล่ะ


if __name__ == "__main__":
    main()
