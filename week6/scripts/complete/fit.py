"""fit.py: pd_check แบบง่าย: delay + fit 3 แบบ + เทียบ pd_check (งาน 6.5–6.7) ฉบับสมบูรณ์

รัน:  conda activate unitree_rl_mjlab && python week6/scripts/complete/fit.py kneeL elbowR elbowL
"""

import sys

from pdlib import JOINTS, best_delay, corr, fit, load_joint, pd_terms, rms, window

MIN_TAU_RMS = 0.3        # Nm: term เล็กกว่านี้ยังอยู่ในสมการ แต่ไม่รายงาน gain (เหมือน pd_check)


def analyze(name: str) -> dict:
    info = JOINTS[name]
    state, cmd, segs = load_joint(name)
    t0, t1 = float(segs[0]["t0"]), float(segs[0]["t1"])
    delay, table = best_delay(state, cmd, info["slot"], t0, t1)
    mask, P, D, y = pd_terms(state, cmd, info["slot"], delay)
    t = state["t"][mask]
    m = window(t, t0, t1)

    fits = {}
    for label, sel, offset in (("ทั้งไฟล์ ไม่มี offset", slice(None), False),
                               ("step ไม่มี offset", m, False),
                               ("step + offset", m, True)):
        a, b, c, yf = fit(P[sel], D[sel], y[sel], offset=offset)
        fits[label] = dict(a=a, b=b, c=c if offset else None, corr=corr(yf, y[sel]),
                           rmsP=rms(P[sel]), rmsD=rms(D[sel]))
    return dict(name=name, delay_ms=delay * 1e3, delay_table=table, fits=fits)


def print_report(r: dict) -> None:
    info = JOINTS[r["name"]]
    tab = sorted(r["delay_table"], key=lambda x: x[1])[:3]
    print(f"\n== {r['name']} (slot {info['slot']}, kp {info['kp']})  delay ดีที่สุด {r['delay_ms']:.0f} ms"
          f"   (3 อันดับ: " + ", ".join(f"{ms} ms → {res:.4f}" for ms, res, _, _ in tab) + ")")
    print(f"  {'แบบ':<22} {'kp x':>6} {'kd x':>6} {'offset':>8} {'corr':>6} {'rms P':>6} {'rms D':>6}")
    for label, f in r["fits"].items():
        kd = f"{f['b']:6.3f}" if f["rmsD"] >= MIN_TAU_RMS else f"{'—':>6}"
        off = f"{f['c']:+8.3f}" if f["c"] is not None else f"{'—':>8}"
        print(f"  {label:<22} {f['a']:6.3f} {kd} {off} {f['corr']:6.3f} {f['rmsP']:6.2f} {f['rmsD']:6.2f}")
    s = r["fits"]["step + offset"]
    print(f"  {'pd_check --segments':<22} {info['ref_kp_x']:6.2f} {info['ref_kd_x']:6.2f} {info['ref_off']:+8.2f}")
    print(f"  ต่างจาก pd_check: kp x {s['a'] - info['ref_kp_x']:+.3f}  kd x {s['b'] - info['ref_kd_x']:+.3f}"
          f"  offset {s['c'] - info['ref_off']:+.3f}")


def main():
    names = sys.argv[1:] or ["kneeL"]
    results = []
    for n in names:
        if n not in JOINTS:
            raise SystemExit(f"เลือก: {', '.join(JOINTS)}")
        r = analyze(n)
        print_report(r)
        results.append(r)
    if len(results) > 1:
        print("\n== สรุป (step + offset)  ← ใช้ใน report.md")
        print(f"  {'ข้อต่อ':<8} {'kp x':>6} {'kd x':>6} {'offset':>8} {'delay':>6} {'corr':>6} {'pd_check':>9}")
        for r in results:
            s, info = r["fits"]["step + offset"], JOINTS[r["name"]]
            print(f"  {r['name']:<8} {s['a']:6.3f} {s['b']:6.3f} {s['c']:+8.3f} {r['delay_ms']:4.0f}ms {s['corr']:6.3f}"
                  f" {info['ref_kp_x']:.2f}/{info['ref_kd_x']:.2f}")
    print("\nแบบไม่มี offset เพี้ยน (สูงหรือต่ำ ขึ้นกับเครื่องหมายของ offset): ช่วงค้างแรงบิดเล็กเกือบคงที่ "
          "a จึงต้องดูดซับ offset ของ tau_est ไว้แทน c (ศอกซ้าย offset −0.12 → 1.17, ศอกขวา +0.14 → 0.70)")


if __name__ == "__main__":
    main()
