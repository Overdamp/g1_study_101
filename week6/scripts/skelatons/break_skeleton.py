"""break_skeleton.py: ทำให้พัง: วิธีวัดของเราไวต่ออะไร (งาน 6.8)

ทุกข้อใช้ช่วง step + offset เป็นค่าตั้งต้น แล้วเปลี่ยนทีละอย่าง:
  (ก) ตัด D ออกจาก fit                  → kp x เปลี่ยนเท่าไหร่ (omitted variable bias)
  (ข) delay 0 ms และ 15 ms              → เทียบกับ delay ที่ดีที่สุด
  (ค) ไม่ตัดช่วง (ทั้งไฟล์) แต่มี offset  → เทียบกับช่วง step
  (ง) ใช้ kd × 2 ใน "สูตร" (D = 2·kd·...) → kd x ที่ fit ได้ควรเป็นเท่าไหร่ (ทายด้วยพีชคณิตก่อน)
ทายทุกข้อก่อน แล้วเติมตารางใน week6/docs/README.md

รัน:  conda activate unitree_rl_mjlab && python week6/scripts/skelatons/break_skeleton.py kneeL
"""

import sys

from pdlib_skeleton import JOINTS, best_delay, fit, load_joint, pd_terms, window


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "kneeL"
    info = JOINTS[name]
    state, cmd, segs = load_joint(name)
    t0, t1 = float(segs[0]["t0"]), float(segs[0]["t1"])
    delay, _ = best_delay(state, cmd, info["slot"], t0, t1)
    mask, P, D, y = pd_terms(state, cmd, info["slot"], delay)
    if len(P) == 0:
        print("break: เติม pdlib_skeleton.py ก่อน [6.8]")
        return
    m = window(state["t"][mask], t0, t1)
    base = fit(P[m], D[m], y[m], offset=True)
    print(f"ตั้งต้น (step + offset, delay {delay * 1e3:.0f} ms): kp x {base[0]:.3f}  kd x {base[1]:.3f}  off {base[2]:+.3f}")

    # TODO [6.8 ก] fit(P[m], D[m], y[m], offset=True, use_d=False) → kp x
    # TODO [6.8 ข] วน delay ใน (0.0, 0.015): pd_terms ใหม่ → ตัดช่วง → fit → kp x, kd x
    # TODO [6.8 ค] fit(P, D, y, offset=True)  (ทั้งไฟล์)
    # TODO [6.8 ง] fit(P[m], 2 * D[m], y[m], offset=True) → kd x  (เทียบกับที่ทาย)
    # TODO [6.8] ตาราง: การทดลอง | kp x | kd x | ต่างจากตั้งต้น
    # คำถาม: ข้อไหนทำให้ผลเพี้ยนมากที่สุด บอกอะไรเกี่ยวกับสิ่งที่ "ต้องทำให้ถูก" ใน pd_check


if __name__ == "__main__":
    main()
