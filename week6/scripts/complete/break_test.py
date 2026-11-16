"""break_test.py: ความไวของวิธีวัด (งาน 6.8) ฉบับสมบูรณ์

  (ก) ตัด D ออกจาก fit       (ข) delay 0 / 15 ms       (ค) ทั้งไฟล์ + offset       (ง) kd × 2 ในสูตร
รัน:  conda activate unitree_rl_mjlab && python week6/scripts/complete/break_test.py kneeL
"""

import sys

from pdlib import JOINTS, best_delay, fit, load_joint, pd_terms, window


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "kneeL"
    slot = JOINTS[name]["slot"]
    state, cmd, segs = load_joint(name)
    t0, t1 = float(segs[0]["t0"]), float(segs[0]["t1"])
    delay, _ = best_delay(state, cmd, slot, t0, t1)

    def step_fit(d, **kw):
        mask, P, D, y = pd_terms(state, cmd, slot, d)
        m = window(state["t"][mask], t0, t1)
        return fit(P[m], kw.pop("dscale", 1.0) * D[m], y[m], **kw)

    base = step_fit(delay, offset=True)
    rows = [(f"ตั้งต้น (step + offset, {delay * 1e3:.0f} ms)", base)]
    rows.append(("(ก) ตัด D", step_fit(delay, offset=True, use_d=False)))
    rows.append(("(ข) delay 0 ms", step_fit(0.0, offset=True)))
    rows.append(("(ข) delay 15 ms", step_fit(0.015, offset=True)))
    mask, P, D, y = pd_terms(state, cmd, slot, delay)
    rows.append(("(ค) ทั้งไฟล์ + offset", fit(P, D, y, offset=True)))
    rows.append(("(ง) kd × 2 ในสูตร", step_fit(delay, offset=True, dscale=2.0)))

    print(f"== {name}")
    print(f"  {'การทดลอง':<30} {'kp x':>7} {'kd x':>7} {'Δkp':>7} {'Δkd':>7}")
    for label, (a, b, c, _) in rows:
        bs = f"{b:7.3f}" if b == b else f"{'—':>7}"
        db = f"{b - base[1]:+7.3f}" if b == b else f"{'—':>7}"
        print(f"  {label:<30} {a:7.3f} {bs} {a - base[0]:+7.3f} {db}")
    print("\n(ง) คาดได้ด้วยพีชคณิต: y = b·D = (b/2)·(2D) → kd x ที่ได้ = ครึ่งหนึ่งพอดี (kp x ไม่เปลี่ยน)")
    print("    ถ้า kd ใน log ผิด (เช่น slot เลื่อน) pd_check จะรายงาน kd x เพี้ยนเป็นสัดส่วนตรงกัน")


if __name__ == "__main__":
    main()
