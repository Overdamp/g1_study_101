"""explore_skeleton.py: สำรวจข้อมูลก่อนวิเคราะห์ (งาน 6.1)

1. ตรวจความถูกต้อง (data_guide.md): kp/kd ที่สั่ง, mode, ลำดับเวลา, gap, อัตรา Hz
2. พล็อต q กับ q_des ของข้อต่อตลอดช่วง + แรเงาช่วง step จาก segments → explore_<ชื่อ>.png

รัน:  conda activate unitree_rl_mjlab && python week6/scripts/skelatons/explore_skeleton.py kneeL
      (ต้องรัน ../cut_logs.sh ก่อน)
"""

import sys

import numpy as np

from pdlib_skeleton import JOINTS, load_joint


def sanity(name, state, cmd, segs) -> None:
    slot = JOINTS[name]["slot"]
    # TODO [6.1] จำนวนแถว state / cmd, ช่วงเวลา (t แรก → t สุดท้าย)
    # TODO [6.1] อัตรา: state ~1 kHz? cmd ~550 Hz?  (len / ช่วงเวลา)
    # TODO [6.1] t เรียงเพิ่มขึ้นตลอดไหม (np.all(np.diff(t) > 0)) · gap สูงสุดของ state เป็น ms
    # TODO [6.1] kp, kd ของ slot ในช่วง step: ค่าเดียวตลอดไหม ตรงกับ JOINTS[name]["kp"] ไหม · mode = 1 ไหม
    # TODO [6.1] segments: ช่วง step t0 → t1 ยาวกี่วินาที อยู่ในช่วงที่ cmd มีข้อมูลไหม
    # ทายก่อน: ไฟล์ state ที่ตัดแล้วมีกี่แถว (data_guide.md)
    print("explore: ยังไม่ได้เติม sanity [6.1]")


def plot(name, state, cmd, segs) -> None:
    # TODO [6.1] try: import matplotlib (matplotlib.use("Agg"))  except ImportError: บอกให้ใช้ env unitree_rl_mjlab แล้ว return
    # TODO [6.1] subplot 1: q (state) และ q_des (cmd) ของ slot เทียบเวลา (ลบ t ของ step ออกให้เริ่มที่ 0)
    #            subplot 2: tau_est (state) ของ slot
    #            แรเงาช่วง step (ax.axvspan) · บันทึก explore_<name>.png
    # สังเกต: q ตาม q_des ทันไหม ห่างกันเท่าไหร่ตอนค้าง (นึกถึง error = tau_gravity / kp สัปดาห์ 2)
    pass


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "kneeL"
    if name not in JOINTS:
        raise SystemExit(f"เลือก: {', '.join(JOINTS)}")
    state, cmd, segs = load_joint(name)
    sanity(name, state, cmd, segs)
    plot(name, state, cmd, segs)


if __name__ == "__main__":
    main()
