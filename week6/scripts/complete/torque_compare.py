"""torque_compare.py: แรงบิดที่ "ควรเป็น" vs tau_est (งาน 6.3) ฉบับสมบูรณ์

รัน:  conda activate unitree_rl_mjlab && python week6/scripts/complete/torque_compare.py kneeL   (→ torque_kneeL.png)
"""

import sys

import numpy as np

from pdlib import JOINTS, corr, load_joint, pd_terms, rms, window


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "kneeL"
    slot = JOINTS[name]["slot"]
    state, cmd, segs = load_joint(name)
    t0, t1 = float(segs[0]["t0"]), float(segs[0]["t1"])
    mask, P, D, y = pd_terms(state, cmd, slot, delay=0.0)
    t = state["t"][mask]
    tau_exp = P + D                                   # tau_ff ตัดออกไปแล้วทั้งสองฝั่ง (y = tau_est − tau_ff)

    print(f"== {name} (delay 0)")
    for label, m in (("ทั้งไฟล์", np.ones_like(t, bool)), ("ช่วง step", window(t, t0, t1))):
        print(f"  {label:<9} corr {corr(tau_exp[m], y[m]):.3f}   rms(tau_exp − tau_est) {rms(tau_exp[m] - y[m]):.3f} Nm"
              f"   rms(tau_est) {rms(y[m]):.3f}   rms(tau_exp) {rms(tau_exp[m]):.3f}   อัตราส่วน {rms(y[m]) / rms(tau_exp[m]):.3f}")
    hold = window(t, t0 - 2.0, t0 - 0.2)              # ช่วงค้างก่อน step
    if hold.any():
        print(f"  ช่วงค้างก่อน step: tau_est − tau_exp เฉลี่ย {np.mean(y[hold] - tau_exp[hold]):+.3f} Nm  (≈ offset คงที่)")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("(ไม่มี matplotlib)")
        return
    m = window(t, t0 - 0.5, t1 + 0.5)
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(t[m] - t0, tau_exp[m], label="kp(q_des − q) + kd(dq_des − dq)")
    ax.plot(t[m] - t0, y[m], label="tau_est − tau_ff", alpha=0.8)
    ax.set_xlabel("t − step start [s]")
    ax.set_ylabel("Nm")
    ax.legend()
    ax.grid(alpha=0.3)
    ax.set_title(f"{name}: expected PD torque vs tau_est")   # ไม่มีฟอนต์ไทยใน matplotlib
    fig.tight_layout()
    fig.savefig(f"torque_{name}.png", dpi=110)
    print(f"  กราฟ → torque_{name}.png")


if __name__ == "__main__":
    main()
