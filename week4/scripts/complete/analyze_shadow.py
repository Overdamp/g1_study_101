"""analyze_shadow.py: วิเคราะห์ CSV จาก shadow_mode (งาน 4.4–4.5) ฉบับสมบูรณ์  ❌ ไม่ต่อ DDS

รัน:  python week4/scripts/complete/analyze_shadow.py shadow.csv [--skip 2.0]
      กราฟ: conda activate unitree_rl_mjlab (g1_sdk ไม่มี matplotlib จะข้ามการพล็อต)
"""

import argparse

import numpy as np

NAMES = ["L_hip_p", "L_hip_r", "L_hip_y", "L_knee", "L_ank_p", "L_ank_r",
         "R_hip_p", "R_hip_r", "R_hip_y", "R_knee", "R_ank_p", "R_ank_r", "waist_y",
         "L_sh_p", "L_sh_r", "L_sh_y", "L_elbow", "L_wrist",
         "R_sh_p", "R_sh_r", "R_sh_y", "R_elbow", "R_wrist"]
PASS_MEAN = 0.01         # rad


def load(path):
    d = np.loadtxt(path, delimiter=",", skiprows=1, ndmin=2)
    return d[:, 0], d[:, 1:24], d[:, 24:47], d[:, 47:127]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("csv")
    p.add_argument("--skip", type=float, default=2.0, help="ตัดกี่วินาทีแรก (last_action ยังไม่ลู่เข้า)")
    args = p.parse_args()
    t, ours, g1, obs = load(args.csv)
    keep = (t - t[0]) >= args.skip
    t, ours, g1, obs = t[keep], ours[keep], g1[keep], obs[keep]
    if len(t) == 0:
        raise SystemExit("ไม่มีข้อมูลหลังตัดช่วงแรก (ลด --skip)")

    err = np.abs(ours - g1)
    print(f"{len(t)} แถว ({t[-1] - t[0]:.1f} s หลังตัด {args.skip} s แรก)")
    print(f"{'joint':<8} {'mean':>8} {'max':>8}  ผล")
    worst = None
    for i, n in enumerate(NAMES):
        m, mx = err[:, i].mean(), err[:, i].max()
        ok = m < PASS_MEAN
        print(f"{n:<8} {m:8.4f} {mx:8.4f}  {'PASS' if ok else 'FAIL'}")
        if worst is None or m > worst[1]:
            worst = (n, m)
    n_fail = int((err.mean(axis=0) >= PASS_MEAN).sum())
    print(f"\nสรุป: {'ผ่านทุกข้อต่อ ✅' if n_fail == 0 else f'FAIL {n_fail} ข้อต่อ'}  · แย่สุด {worst[0]} ({worst[1]:.4f} rad)")
    if np.all(err == 0):
        print("!! error เป็น 0 พอดีทุกแถว: น่าสงสัย (อ่าน lowcmd ของตัวเอง? หรือ g1_ctrl ไม่ได้อยู่ใน Velocity?)")
    if n_fail:
        print("ไล่ตามลำดับ (shadow_mode.md): ลำดับข้อต่อ → ลบ default → gravity → last_action raw/processed → ลำดับ term")

    g = obs[:, 3:6]
    print(f"\nprojected_gravity: x [{g[:, 0].min():+.3f}, {g[:, 0].max():+.3f}]  y [{g[:, 1].min():+.3f}, {g[:, 1].max():+.3f}]"
          f"  z [{g[:, 2].min():+.3f}, {g[:, 2].max():+.3f}]")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("(ไม่มี matplotlib: ข้ามการพล็อต)")
        return
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 6), sharex=True)
    for i, lab in enumerate("xyz"):
        a1.plot(t - t[0], g[:, i], label=f"gravity {lab}")
    a1.set_ylabel("projected gravity")
    a1.legend()
    a1.grid(alpha=0.3)
    a2.plot(t - t[0], err.mean(axis=1), label="mean |q_ours − q_g1|")
    a2.axhline(PASS_MEAN, color="r", ls="--", lw=1, label="เกณฑ์ 0.01 rad")
    a2.set_ylabel("rad")
    a2.set_xlabel("t [s]")
    a2.legend()
    a2.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig("shadow.png", dpi=120)
    print("กราฟ → shadow.png")


if __name__ == "__main__":
    main()
