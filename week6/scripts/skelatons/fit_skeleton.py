"""fit_skeleton.py: pd_check แบบง่ายของเรา (งาน 6.5–6.7)

ต่อข้อต่อ:
  1. หา delay (6.6) จากช่วง step
  2. fit 3 แบบ (6.5):  ทั้งไฟล์ ไม่มี offset · ช่วง step ไม่มี offset · ช่วง step + offset
  3. ตารางเทียบกับค่าอ้างอิงของ pd_check --segments (JOINTS ใน pdlib)
ทำครบ 3 ข้อต่อ (6.7):  python fit_skeleton.py kneeL elbowR elbowL

รัน:  conda activate unitree_rl_mjlab && python week6/scripts/skelatons/fit_skeleton.py kneeL
"""

import sys

from pdlib_skeleton import JOINTS, best_delay, corr, fit, load_joint, pd_terms, rms, window

MIN_TAU_RMS = 0.3        # Nm: term ที่ rms เล็กกว่านี้ "อยู่ในสมการ" แต่ไม่รายงาน gain (pd_check ทำแบบนี้)


def analyze(name: str) -> dict:
    info = JOINTS[name]
    state, cmd, segs = load_joint(name)
    seg = segs[0]
    t0, t1 = float(seg["t0"]), float(seg["t1"])

    # TODO [6.6] delay, table = best_delay(state, cmd, info["slot"], t0, t1)  · พิมพ์ 5 ค่าแรกของตาราง (ms, resid)
    delay = 0.0
    mask, P, D, y = pd_terms(state, cmd, info["slot"], delay)
    if len(P) == 0:
        print("fit: เติม pdlib_skeleton.py ก่อน [6.5]")
        return {}
    t = state["t"][mask]
    m = window(t, t0, t1)

    results = {}
    # TODO [6.5] "ทั้งไฟล์ ไม่มี offset":   fit(P, D, y, offset=False)
    # TODO [6.5] "step ไม่มี offset":       fit(P[m], D[m], y[m], offset=False)
    # TODO [6.5] "step + offset":           fit(P[m], D[m], y[m], offset=True)
    # TODO [6.5] เก็บ a, b, c, corr(y_fit, y), rms(P), rms(D) ของแต่ละแบบลง results
    # TODO [6.5] ถ้า rms(D) < MIN_TAU_RMS ให้แสดง kd x เป็น "—" (ยังอยู่ในสมการ ไม่ตัดทิ้ง: omitted variable bias)
    return {"name": name, "delay_ms": delay * 1e3, "fits": results}


def print_report(r: dict) -> None:
    info = JOINTS[r["name"]]
    # TODO [6.5] ตาราง: แบบ | kp x | kd x | offset Nm | corr | rms P | rms D
    # TODO [6.7] แถวท้าย: "pd_check" | ref_kp_x | ref_kd_x | ref_off  และผลต่างจากแบบ "step + offset"
    # คำถาม 6.5: ทำไมแบบ "ทั้งไฟล์" ต่ำกว่ามาก (vault: ศอกขวา 0.61, เข่า 0.77)
    pass


def main():
    names = sys.argv[1:] or ["kneeL"]
    for n in names:
        if n not in JOINTS:
            raise SystemExit(f"เลือก: {', '.join(JOINTS)}")
        r = analyze(n)
        if r:
            print_report(r)
    # TODO [6.7] ถ้าหลายข้อต่อ: ตารางสรุปท้าย ชื่อ | kp x | kd x | offset | delay | pd_check kp x  (ใช้ใน report.md)


if __name__ == "__main__":
    main()
