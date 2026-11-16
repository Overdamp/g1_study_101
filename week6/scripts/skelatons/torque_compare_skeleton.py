"""torque_compare_skeleton.py: แรงบิดที่ "ควรเป็น" เทียบกับ tau_est (งาน 6.3)

tau_exp = kp(q_des − q) + kd(dq_des − dq) + tau_ff     (ใช้ delay 0 ก่อน)
พิมพ์ corr และ rms ของผลต่าง ทั้งช่วง step และทั้งไฟล์ · พล็อตทับกัน → torque_<ชื่อ>.png
ทายก่อนรัน: corr ช่วง step ประมาณเท่าไหร่ · tau_est จะใหญ่หรือเล็กกว่า tau_exp

รัน:  conda activate unitree_rl_mjlab && python week6/scripts/skelatons/torque_compare_skeleton.py kneeL
"""

import sys

import numpy as np

from pdlib_skeleton import JOINTS, corr, load_joint, pd_terms, rms, window


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "kneeL"
    slot = JOINTS[name]["slot"]
    state, cmd, segs = load_joint(name)
    mask, P, D, y = pd_terms(state, cmd, slot, delay=0.0)
    if len(P) == 0:
        print("torque_compare: เติม pdlib_skeleton.py ก่อน (pd_terms) [6.3]")
        return
    t = state["t"][mask]
    seg = segs[0]                                       # ช่วง step ของข้อต่อนี้
    # TODO [6.3] tau_exp = P + D  (เทียบกับ y = tau_est − tau_ff  → ตัด tau_ff ออกทั้งสองฝั่งแล้ว)
    # TODO [6.3] ทั้งไฟล์: corr(tau_exp, y), rms(tau_exp − y), rms(y)
    # TODO [6.3] ช่วง step: m = window(t, float(seg["t0"]), float(seg["t1"])) แล้วคำนวณเหมือนกัน
    # TODO [6.3] อัตราส่วน rms(y) / rms(tau_exp) ในช่วง step (≈ kp x คร่าวๆ ถ้า P ครอบงำ)
    # TODO [6.3] (matplotlib) พล็อต tau_exp กับ y ในช่วง step ± 0.5 s บันทึก torque_<name>.png
    # คำถาม: ช่วง hold ทำไม tau_exp กับ tau_est ห่างกันเป็น "ค่าคงที่" (นึกถึง offset)


if __name__ == "__main__":
    main()
