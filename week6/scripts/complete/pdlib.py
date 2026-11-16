"""pdlib.py: ไลบรารี pd_check แบบง่าย (งาน 6.2–6.4, 6.6) ฉบับสมบูรณ์ + เทสต์ 12 ข้อ

รันตรงๆ = เทสต์ด้วยข้อมูลปลอม (ไม่ต้องมีข้อมูลจริง):  python week6/scripts/complete/pdlib.py
ข้อมูลจริงอ่านจาก ~/g1_study/week6/data/ (สร้างด้วย ../cut_logs.sh) หรือกำหนดเองด้วยตัวแปร W6_DATA
เทียบ: ~/nvidia/unitree/unitree_rl_mjlab/deploy/robots/g1_23dof/scripts/pd_check.py (expected_torque, fit_pd, segment_check)
"""

import csv
import os
from pathlib import Path

import numpy as np

DATA = Path(os.environ.get("W6_DATA", Path.home() / "g1_study/week6/data"))
NUM_SLOTS = 29

# ค่าอ้างอิง = pd_check.py --segments กับไฟล์ที่ตัดแล้ว (10/11/2026)
JOINTS = {
    "kneeL":  dict(slot=3,  kp=99.1, ref_kp_x=0.93, ref_kd_x=0.86, ref_off=-0.28),
    "elbowL": dict(slot=18, kp=14.3, ref_kp_x=0.97, ref_kd_x=0.88, ref_off=-0.13),
    "elbowR": dict(slot=25, kp=14.3, ref_kp_x=0.96, ref_kd_x=0.84, ref_off=+0.15),
}


# ---------------------------------------------------------------------------
# อ่านไฟล์
# ---------------------------------------------------------------------------
def read_csv(path: Path, keys: list) -> dict:
    """'t' → (N,), 'q' → (N, 29) จาก q0..q28 · อ่านเฉพาะคอลัมน์ที่ใช้ (usecols) กินแรมน้อย"""
    with open(path, newline="") as f:
        header = next(csv.reader(f))
    col = {n: i for i, n in enumerate(header)}
    idx = {}
    for k in keys:
        if k in col:
            idx[k] = [col[k]]
        elif f"{k}0" in col:
            idx[k] = [col[f"{k}{i}"] for i in range(NUM_SLOTS)]
        else:
            raise SystemExit(f"{path.name}: ไม่มีคอลัมน์ '{k}'")
    usecols = [c for cols in idx.values() for c in cols]
    data = np.loadtxt(path, delimiter=",", skiprows=1, usecols=usecols, ndmin=2)
    out, start = {}, 0
    for k, cols in idx.items():
        a = data[:, start:start + len(cols)]
        out[k] = a[:, 0].copy() if len(cols) == 1 else a
        start += len(cols)
    return out


def load_joint(name: str):
    """(state, cmd, segments)  state: t, q, dq, tau(=tau_est) · cmd: t, q(=q_des), dq, kp, kd, tau(=tau_ff), mode"""
    if not (DATA / f"{name}_state.csv").exists():
        raise SystemExit(f"ไม่พบ {DATA / (name + '_state.csv')}: รัน week6/scripts/cut_logs.sh {name} ก่อน")
    state = read_csv(DATA / f"{name}_state.csv", ["t", "q", "dq", "tau"])
    cmd = read_csv(DATA / f"{name}_cmd.csv", ["t", "q", "dq", "kp", "kd", "tau", "mode"])
    with open(DATA / f"{name}_seg.csv", newline="") as f:
        segs = [r for r in csv.DictReader(f) if int(r["slot"]) >= 0]
    return state, cmd, segs


# ---------------------------------------------------------------------------
# งานของสัปดาห์
# ---------------------------------------------------------------------------
def align(state_t: np.ndarray, cmd_t: np.ndarray, delay: float) -> np.ndarray:
    """zero-order hold: คำสั่งล่าสุดที่ส่งก่อน (state_t − delay)  · −1 = มาก่อนคำสั่งแรก"""
    return np.searchsorted(cmd_t, np.asarray(state_t) - delay, side="right") - 1


def pd_terms(state: dict, cmd: dict, slot: int, delay: float):
    """(mask, P, D, y) ของ slot เดียว: P = kp(q_des − q), D = kd(dq_des − dq), y = tau_est − tau_ff"""
    j = align(state["t"], cmd["t"], delay)
    mask = j >= 0
    jj = j[mask]
    P = cmd["kp"][jj, slot] * (cmd["q"][jj, slot] - state["q"][mask, slot])
    D = cmd["kd"][jj, slot] * (cmd["dq"][jj, slot] - state["dq"][mask, slot])
    y = state["tau"][mask, slot] - cmd["tau"][jj, slot]
    return mask, P, D, y


def fit(P: np.ndarray, D: np.ndarray, y: np.ndarray, offset: bool = True, use_d: bool = True):
    """least squares  y ≈ a·P (+ b·D) (+ c)  → (a, b, c, y_fit)"""
    cols = [P] + ([D] if use_d else []) + ([np.ones_like(y)] if offset else [])
    X = np.column_stack(cols)
    theta = np.linalg.lstsq(X, y, rcond=None)[0]
    a = float(theta[0])
    b = float(theta[1]) if use_d else float("nan")
    c = float(theta[-1]) if offset else 0.0
    return a, b, c, X @ theta


def rms(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    return float(np.sqrt(np.mean(x ** 2))) if x.size else 0.0


def corr(a: np.ndarray, b: np.ndarray) -> float:
    if np.std(a) < 1e-12 or np.std(b) < 1e-12:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def window(t: np.ndarray, t0: float, t1: float) -> np.ndarray:
    t = np.asarray(t)
    return (t >= t0) & (t <= t1)


def best_delay(state: dict, cmd: dict, slot: int, t0: float, t1: float, delays_ms=range(0, 31)):
    """กวาด delay → residual RMS ของ fit (มี offset) ในช่วง [t0, t1] · คืน (delay_s ที่ดีที่สุด, ตาราง)"""
    table = []
    for ms in delays_ms:
        mask, P, D, y = pd_terms(state, cmd, slot, ms / 1000.0)
        m = window(state["t"][mask], t0, t1)
        a, b, _, yf = fit(P[m], D[m], y[m], offset=True)
        table.append((ms, rms(y[m] - yf), a, b))
    best = min(table, key=lambda r: r[1])
    return best[0] / 1000.0, table


# ---------------------------------------------------------------------------
# เทสต์ (ชุดเดียวกับ skeleton)
# ---------------------------------------------------------------------------
def run_tests():
    ok = True

    def check(name, cond_fn):
        nonlocal ok
        try:
            cond = bool(cond_fn())
        except Exception as e:
            cond = False
            name += f"  ({type(e).__name__})"
        ok &= cond
        print(f"  {'PASS' if cond else 'FAIL'}  {name}")

    print("align (zero-order hold)")
    j = align(np.array([5.0, 10.0, 15.0, 25.0, -1.0]), np.array([0.0, 10.0, 20.0]), 0.0)
    check("cmd_t=[0,10,20], state_t=[5,10,15,25,−1] → [0,1,1,2,−1]", lambda: list(j) == [0, 1, 1, 2, -1])
    j2 = align(np.array([12.0]), np.array([0.0, 10.0, 20.0]), 3.0)
    check("delay 3: state 12 → ใช้คำสั่งที่ 9 → index 0", lambda: list(j2) == [0])

    print("pd_terms")
    st = {"t": np.array([0.5, 1.5]), "q": np.zeros((2, 29)), "dq": np.zeros((2, 29)), "tau": np.zeros((2, 29))}
    st["q"][:, 3] = [0.1, 0.2]
    st["dq"][:, 3] = [1.0, 0.0]
    st["tau"][:, 3] = [5.0, 6.0]
    cm = {"t": np.array([0.0, 1.0]), "q": np.zeros((2, 29)), "dq": np.zeros((2, 29)),
          "kp": np.full((2, 29), 100.0), "kd": np.full((2, 29), 2.0), "tau": np.zeros((2, 29))}
    cm["q"][:, 3] = [0.15, 0.3]
    cm["tau"][:, 3] = [1.0, 0.0]
    _, P, D, y = pd_terms(st, cm, 3, 0.0)
    check("P = kp(q_des − q) = [5, 10]", lambda: np.allclose(P, [5.0, 10.0]))
    check("D = kd(dq_des − dq) = [−2, 0]", lambda: np.allclose(D, [-2.0, 0.0]))
    check("y = tau_est − tau_ff = [4, 6]", lambda: np.allclose(y, [4.0, 6.0]))

    print("fit (ข้อมูลปลอม: y = 0.93 P + 0.86 D − 0.28 + noise)")
    rng = np.random.default_rng(0)
    P = rng.normal(0, 2.5, 5000)
    D = rng.normal(0, 1.8, 5000)
    y = 0.93 * P + 0.86 * D - 0.28 + rng.normal(0, 0.05, 5000)
    a, b, c, yf = fit(P, D, y, offset=True)
    check("มี offset → a ≈ 0.93, b ≈ 0.86, c ≈ −0.28 (±1%)",
          lambda: abs(a - 0.93) < 0.0093 and abs(b - 0.86) < 0.0086 and abs(c + 0.28) < 0.01)
    check("corr(y_fit, y) > 0.99", lambda: corr(yf, y) > 0.99)
    check("rms(y − y_fit) ≈ noise 0.05", lambda: abs(rms(y - yf) - 0.05) < 0.005)

    print("offset สำคัญเมื่อแรงบิดเล็ก (แบบศอก)")
    Ps = 0.5 + rng.normal(0, 0.1, 5000)
    ys = 0.96 * Ps + 0.15 + rng.normal(0, 0.02, 5000)
    a_no, _, _, _ = fit(Ps, np.zeros_like(Ps), ys, offset=False, use_d=False)
    a_off, _, c_off, _ = fit(Ps, np.zeros_like(Ps), ys, offset=True, use_d=False)
    check("ไม่มี offset → a เพี้ยนเกิน 0.1", lambda: abs(a_no - 0.96) > 0.1)
    check("มี offset → a ≈ 0.96, c ≈ +0.15", lambda: abs(a_off - 0.96) < 0.03 and abs(c_off - 0.15) < 0.02)

    print("omitted variable bias")
    Pc = rng.normal(0, 2.0, 5000)
    Dc = -0.6 * Pc + rng.normal(0, 0.5, 5000)
    yc = 1.0 * Pc + 1.0 * Dc
    a_drop, _, _, _ = fit(Pc, Dc, yc, offset=False, use_d=False)
    check("ตัด D ทิ้ง → a ไม่ใช่ 1 (ต่างเกิน 0.2)", lambda: abs(a_drop - 1.0) > 0.2)

    print("window")
    check("[1, 2] ของ t=[0,1,1.5,2,3] → [F,T,T,T,F]",
          lambda: list(window(np.array([0, 1, 1.5, 2, 3]), 1.0, 2.0)) == [False, True, True, True, False])

    print("ผ่านทั้งหมด ✅" if ok else "ยังมี FAIL")


if __name__ == "__main__":
    run_tests()
