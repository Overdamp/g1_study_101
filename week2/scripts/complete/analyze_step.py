"""analyze_step.py: วิเคราะห์ CSV จาก step_elbow.py (งาน 2.6–2.7)  ❌ ไม่ต่อ DDS

1. rise time (10% → 90%), overshoot, steady-state error ของช่วง step ขึ้น
2. tau ที่คำนวณเอง = kp·(q_des − q) + kd·(0 − dq) เทียบกับ tau_est ที่ sim รายงาน
3. พล็อต q(t) ทุกไฟล์บนรูปเดียว → step_compare.png (ถ้ามี matplotlib)

รัน:  python week2/scripts/complete/analyze_step.py step_kp5.csv step_kp14.csv step_kp40.csv step_kd0.csv
      พล็อต: conda activate unitree_rl_mjlab  (g1_sdk ไม่มี matplotlib จะข้ามการพล็อต)
"""

import math
import sys
from pathlib import Path

import numpy as np

SETTLE_S = 2.0           # ต้องตรงกับ step_elbow.py
HOLD_S = 3.0
TAU_LIMIT = 25.0         # ctrlrange ของศอกใน g1_23dof.xml (sim ตัดแรงบิดที่ ±25 Nm)


def load(path: str) -> dict:
    data = np.loadtxt(path, delimiter=",", skiprows=1, ndmin=2)
    names = ["t", "q_des", "q", "dq", "tau_est", "kp", "kd"]
    return {n: data[:, i] for i, n in enumerate(names)}


def step_window(d: dict) -> dict:
    """ช่วงที่เป้า = q0 + amp"""
    m = (d["t"] >= SETTLE_S) & (d["t"] < SETTLE_S + HOLD_S)
    return {k: v[m] for k, v in d.items()}


def step_metrics(d: dict):
    """คืน (rise_s, overshoot_pct, ss_error_deg)"""
    pre = d["t"] < SETTLE_S
    q0 = float(np.mean(d["q"][pre][-50:]))           # มุมจริงก่อน step (เฉลี่ย 0.1 s สุดท้าย)
    w = step_window(d)
    q_final = float(w["q_des"][0])                    # เป้าหมายของ step
    span = q_final - q0
    if abs(span) < 1e-6:
        return float("nan"), float("nan"), float("nan")

    progress = (w["q"] - q0) / span                   # 0 = จุดเริ่ม, 1 = ถึงเป้า (ใช้ได้ทั้ง step บวกและลบ)
    t = w["t"] - SETTLE_S

    def first_cross(level):
        idx = np.nonzero(progress >= level)[0]
        return t[idx[0]] if len(idx) else float("nan")

    rise = first_cross(0.9) - first_cross(0.1)
    overshoot = max(0.0, float(progress.max()) - 1.0) * 100.0
    tail = w["t"] >= SETTLE_S + HOLD_S - 0.5          # 0.5 s สุดท้ายของช่วง
    ss_error = math.degrees(q_final - float(np.mean(w["q"][tail])))
    return rise, overshoot, ss_error


def torque_check(d: dict):
    """เทียบ tau ที่คำนวณเองกับ tau_est เฉพาะช่วงที่ศอกมี kp (ไม่รวมช่วง damping)"""
    m = d["kp"] > 0
    tau_calc = d["kp"][m] * (d["q_des"][m] - d["q"][m]) + d["kd"][m] * (0.0 - d["dq"][m])
    tau_calc = np.clip(tau_calc, -TAU_LIMIT, TAU_LIMIT)   # sim ตัดที่ ctrlrange เหมือนกัน
    tau_est = d["tau_est"][m]
    rms = float(np.sqrt(np.mean((tau_calc - tau_est) ** 2)))
    corr = float(np.corrcoef(tau_calc, tau_est)[0, 1]) if np.std(tau_est) > 1e-9 else float("nan")
    return rms, corr, float(np.max(np.abs(tau_est)))


def plot(datasets: list, out: str = "step_compare.png") -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")                         # เซฟเป็นไฟล์ ไม่ต้องมีหน้าจอ
        import matplotlib.pyplot as plt
    except ImportError:
        print("(ไม่มี matplotlib: ข้ามการพล็อต ใช้ env unitree_rl_mjlab ถ้าต้องการกราฟ)")
        return

    fig, (ax_q, ax_tau) = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
    for name, d in datasets:
        q0 = np.mean(d["q"][d["t"] < SETTLE_S][-50:])
        t = d["t"] - SETTLE_S
        ax_q.plot(t, np.degrees(d["q"] - q0), label=f"{name} (kp {d['kp'].max():g}, kd {d['kd'].max():g})")
        ax_tau.plot(t, d["tau_est"], label=name)
    first = datasets[0][1]
    q0 = np.mean(first["q"][first["t"] < SETTLE_S][-50:])
    ax_q.plot(first["t"] - SETTLE_S, np.degrees(first["q_des"] - q0), "k--", lw=1, label="q_des")
    ax_q.set_ylabel("q − q0 [deg]")
    ax_q.legend(fontsize=8)
    ax_q.grid(alpha=0.3)
    ax_tau.set_ylabel("tau_est [Nm]")
    ax_tau.set_xlabel("t − step [s]")
    ax_tau.grid(alpha=0.3)
    ax_q.set_xlim(-0.5, HOLD_S + 1.0)
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    print(f"กราฟ → {out}")


def main():
    paths = sys.argv[1:]
    if not paths:
        raise SystemExit("ใช้: python analyze_step.py step_a.csv [step_b.csv ...]")

    print(f"{'file':<18} {'kp':>5} {'kd':>4} {'rise ms':>8} {'over %':>7} {'ss err °':>9} {'tau rms':>8} {'corr':>5} {'|tau|max':>8}")
    datasets = []
    for p in paths:
        d = load(p)
        rise, over, sse = step_metrics(d)
        rms, corr, tmax = torque_check(d)
        name = Path(p).stem
        datasets.append((name, d))
        print(f"{name:<18} {d['kp'].max():5.1f} {d['kd'].max():4.1f} {rise * 1e3:8.0f} {over:7.1f} {sse:9.2f}"
              f" {rms:8.3f} {corr:5.2f} {tmax:8.2f}")
    plot(datasets)

    print("\nอ่านผล:")
    print("  rise: kp สูง → ขึ้นเร็ว · overshoot: kd ต่ำเทียบกับ kp → พุ่งเกิน/แกว่ง")
    print("  ss err: ≈ tau_gravity / kp  (kp สูง error เล็ก แต่ไม่เป็น 0 ถ้าไม่มี tau_ff)")
    print("  tau rms เล็ก + corr ≈ 1 → sim ใช้สูตร PD เดียวกับเรา (ต่างเพราะ q คนละจังหวะ ~1–2 ms)")


if __name__ == "__main__":
    main()
