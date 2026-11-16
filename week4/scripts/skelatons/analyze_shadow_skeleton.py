"""analyze_shadow_skeleton.py: วิเคราะห์ CSV จาก shadow_mode (งาน 4.4–4.5)  ❌ ไม่ต่อ DDS

1. |q_des(เรา) − q_des(g1_ctrl)| ต่อข้อต่อ: mean / max  (เกณฑ์ผ่าน: mean < 0.01 rad ทุกข้อต่อ)
2. ตัดช่วงแรกทิ้ง (last_action ยังไม่ลู่เข้า)
3. (4.5) พล็อต projected_gravity (obs 3–5) ตามเวลา ดูทิศเมื่อก้ม/เอียง
4. ถ้าไม่ผ่าน: ข้อต่อไหนแย่สุด → ไล่ตามลำดับใน shadow_mode.md

รัน:  python week4/scripts/skelatons/analyze_shadow_skeleton.py shadow.csv [--skip 2.0]
      พล็อต: conda activate unitree_rl_mjlab (g1_sdk ไม่มี matplotlib)
"""

import argparse

import numpy as np

NAMES = ["L_hip_p", "L_hip_r", "L_hip_y", "L_knee", "L_ank_p", "L_ank_r",
         "R_hip_p", "R_hip_r", "R_hip_y", "R_knee", "R_ank_p", "R_ank_r", "waist_y",
         "L_sh_p", "L_sh_r", "L_sh_y", "L_elbow", "L_wrist",
         "R_sh_p", "R_sh_r", "R_sh_y", "R_elbow", "R_wrist"]
PASS_MEAN = 0.01         # rad


def load(path):
    """คืน t (N,), ours (N,23), g1 (N,23), obs (N,80)"""
    # TODO [4.4] np.loadtxt(path, delimiter=",", skiprows=1) แล้วแบ่งคอลัมน์ 1 + 23 + 23 + 80
    return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("csv")
    p.add_argument("--skip", type=float, default=2.0, help="ตัดกี่วินาทีแรก")
    args = p.parse_args()
    data = load(args.csv)
    if data is None:
        print("analyze_shadow: ยังไม่ได้เติม [4.4]")
        return
    # TODO [4.4] ตัดแถวที่ t − t[0] < args.skip
    # TODO [4.4] err = |ours − g1| → ตาราง: ชื่อ | mean | max | PASS/FAIL
    # TODO [4.4] สรุป: ผ่านทุกข้อต่อไหม · ข้อต่อที่แย่สุด
    # TODO [4.5] (ถ้ามี matplotlib) พล็อต obs[:, 3:6] เทียบเวลา บันทึก gravity.png
    # คำถาม: error ทุกข้อต่อเป็น 0 พอดีทุกแถว แปลว่าอะไร น่าสงสัยไหม (shadow_mode.md)


if __name__ == "__main__":
    main()
