"""explore.py: สำรวจและตรวจข้อมูลก่อนวิเคราะห์ (งาน 6.1) ฉบับสมบูรณ์

รัน:  conda activate unitree_rl_mjlab && python week6/scripts/complete/explore.py kneeL    (→ explore_kneeL.png)
"""

import sys

import numpy as np

from pdlib import JOINTS, load_joint, window


def sanity(name, state, cmd, segs) -> None:
    info = JOINTS[name]
    slot = info["slot"]
    seg = segs[0]
    t0, t1 = float(seg["t0"]), float(seg["t1"])
    ts, tc = state["t"], cmd["t"]
    print(f"== {name} (slot {slot})")
    print(f"  state: {len(ts)} แถว  {ts[0]:.2f} → {ts[-1]:.2f} s  ({len(ts) / (ts[-1] - ts[0]):.0f} Hz)")
    print(f"  cmd  : {len(tc)} แถว  {tc[0]:.2f} → {tc[-1]:.2f} s  ({len(tc) / (tc[-1] - tc[0]):.0f} Hz)")
    for label, t in (("state", ts), ("cmd", tc)):
        d = np.diff(t)
        # t ใน CSV มีทศนิยม 4 ตำแหน่ง (0.1 ms): 2 ข้อความที่มาห่างกัน < 0.1 ms จะได้ t ซ้ำกัน (ไม่ใช่ข้อมูลเสีย)
        back, dup = int((d < 0).sum()), int((d == 0).sum())
        print(f"  {label:<5}: ไม่ถอยหลัง {'✓' if back == 0 else f'✗ ({back} จุด)'}  t ซ้ำ {dup} จุด (ปัดเศษ 0.1 ms)"
              f"  gap สูงสุด {d.max() * 1e3:.1f} ms")
    m = window(tc, t0, t1)
    kp, kd, mode = np.unique(cmd["kp"][m, slot]), np.unique(cmd["kd"][m, slot]), np.unique(cmd["mode"][m, slot])
    print(f"  ช่วง step {t0:.2f} → {t1:.2f} ({t1 - t0:.1f} s, test '{seg['test']}', amp {seg['amp']} rad, completed {seg['completed']})")
    print(f"    kp {np.round(kp, 3)} (คาด {info['kp']})  kd {np.round(kd, 3)}  mode {mode.astype(int)}")
    print(f"    อยู่ในช่วงของ cmd: {'✓' if tc[0] <= t0 and t1 <= tc[-1] else '✗'}")
    qd = cmd["q"][m, slot]
    print(f"    q_des: {qd.min():+.3f} → {qd.max():+.3f} rad (ช่วง {qd.max() - qd.min():.3f} = 2 × amp?)")


def plot(name, state, cmd, segs) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("(ไม่มี matplotlib: ใช้ env unitree_rl_mjlab)")
        return
    slot = JOINTS[name]["slot"]
    t0, t1 = float(segs[0]["t0"]), float(segs[0]["t1"])
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    a1.plot(state["t"] - t0, state["q"][:, slot], label="q (lowstate)")
    a1.step(cmd["t"] - t0, cmd["q"][:, slot], where="post", label="q_des (lowcmd)", lw=1)
    a1.set_ylabel("rad")
    a1.legend()
    a2.plot(state["t"] - t0, state["tau"][:, slot], label="tau_est", color="C2")
    a2.set_ylabel("Nm")
    a2.set_xlabel("t − step start [s]")
    for a in (a1, a2):
        a.axvspan(0, t1 - t0, color="0.9", zorder=0)
        a.grid(alpha=0.3)
    fig.suptitle(f"{name} slot {slot} (shaded = step test)")   # matplotlib ไม่มีฟอนต์ไทย ใช้อังกฤษในกราฟ
    fig.tight_layout()
    fig.savefig(f"explore_{name}.png", dpi=110)
    print(f"  กราฟ → explore_{name}.png")


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "kneeL"
    if name not in JOINTS:
        raise SystemExit(f"เลือก: {', '.join(JOINTS)}")
    state, cmd, segs = load_joint(name)
    sanity(name, state, cmd, segs)
    plot(name, state, cmd, segs)


if __name__ == "__main__":
    main()
