"""damping_skeleton.py: ทุกข้อต่อ kp = 0, kd > 0 (งาน 2.3)  ✅ ส่ง lowcmd (sim เท่านั้น)

ก็อปโครงทั้งหมดจาก send_zero (StateReader, main loop, CRC) มาใส่ เปลี่ยนแค่ build_cmd()
นี่คือสิ่งเดียวกับ State_Passive ของ g1_ctrl (สัปดาห์ 3)

ทดลอง: ลากแขนใน MuJoCo (ดับเบิลคลิก + Ctrl + คลิกขวาลาก) ช้าๆ กับเร็วๆ เทียบกับตอนรัน send_zero
ทายก่อน: รู้สึกต่างกันไหม ลากเร็วกับลากช้าต่างกันยังไง  (pd_control.md: kd = โช้ค)
รัน:  conda activate g1_sdk && python week2/scripts/skelatons/damping_skeleton.py
"""

# TODO [2.3] imports เหมือน send_zero

DOMAIN = 1
IFACE = "lo"
CONTROL_DT = 0.002
NUM_MOTORS = 29
MODE_PR = 0

# kd ของ Passive ใน g1_ctrl  (deploy/robots/g1_23dof/config/config.yaml → FSM: Passive: kd)  เรียงตาม slot 0..28
PASSIVE_KD = [
    4.0, 4.0, 4.0, 6.0, 2.5, 2.5,          # ขาซ้าย   0-5
    4.0, 4.0, 4.0, 6.0, 2.5, 2.5,          # ขาขวา    6-11
    4.5, 4.5, 4.5,                         # เอว      12-14  (13, 14 ไม่มีข้อต่อบน 23-DoF)
    2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5,     # แขนซ้าย  15-21  (20, 21 ไม่มี)
    2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5,     # แขนขวา   22-28  (27, 28 ไม่มี)
]
KD_SCALE = None          # TODO [2.3] เริ่มที่ 1.0  แล้วลอง 0.2 และ 3.0 เทียบความรู้สึกตอนลาก


def safety_guard(iface: str, domain: int) -> None:
    """เขียนไว้ให้แล้ว ห้ามลบ ห้ามแก้"""
    if iface != "lo" or domain != 1:
        raise SystemExit(f"[safety] iface={iface!r} domain={domain}: แบบฝึกหัดนี้ใช้ได้กับ sim (lo, domain 1) เท่านั้น")


# TODO [2.3] class StateReader  (ก็อปจาก send_zero)


def build_cmd(cmd, state, t):
    # TODO [2.3] mode_pr, mode_machine เหมือน send_zero
    # TODO [2.3] วน slot: mode = 1, kp = 0, kd = PASSIVE_KD[i] * KD_SCALE, dq = 0, tau = 0
    # TODO [2.3] q = ?   ← g1_ctrl ตั้ง q = มุมปัจจุบันของ state ทุกรอบ ทั้งที่ kp = 0  ทำไม? (fsm_concepts.md สัปดาห์ 3)
    pass


def main():
    safety_guard(IFACE, DOMAIN)
    # TODO [2.3] เหมือน main ของ send_zero
    print("damping: ยังไม่ได้เติม [2.3]")


if __name__ == "__main__":
    main()
