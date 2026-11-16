"""pdlib_skeleton.py: ไลบรารี pd_check แบบง่าย (งาน 6.2–6.4, 6.6) + เทสต์ด้วยข้อมูลปลอม

ไฟล์อื่น (explore / torque_compare / fit / break) import จากไฟล์นี้ **เติมให้เทสต์ผ่านก่อน**
รันตรงๆ = รันเทสต์ (ไม่ต้องมีข้อมูลจริง):  python week6/scripts/skelatons/pdlib_skeleton.py

อ้างอิง: week6/docs/alignment_and_delay.md, least_squares.md
เฉลยระดับโปร: ~/nvidia/unitree/unitree_rl_mjlab/deploy/robots/g1_23dof/scripts/pd_check.py (เขียนเองก่อนค่อยเปิด)
"""

import csv
from pathlib import Path

import numpy as np

DATA = Path.home() / "g1_study/week6/data"
NUM_SLOTS = 29

# ข้อมูลของแต่ละข้อต่อ (หลังรัน ../cut_logs.sh) + ค่าอ้างอิงจาก pd_check --segments
JOINTS = {
    "kneeL":  dict(slot=3,  kp=99.1, ref_kp_x=0.93, ref_kd_x=0.86, ref_off=-0.28),
    "elbowL": dict(slot=18, kp=14.3, ref_kp_x=0.97, ref_kd_x=0.88, ref_off=-0.13),
    "elbowR": dict(slot=25, kp=14.3, ref_kp_x=0.96, ref_kd_x=0.84, ref_off=+0.15),
}


# ---------------------------------------------------------------------------
# อ่านไฟล์ (ให้ไว้แล้ว)
# ---------------------------------------------------------------------------
def read_csv(path: Path, keys: list) -> dict:
    """คอลัมน์ตาม keys: 't' → (N,), 'q' → (N, 29) จาก q0..q28  (แบบเดียวกับ read_csv ใน pd_check.py)"""
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
    """คืน (state, cmd, segments) ของข้อต่อนั้นจาก week6/data/"""
    state = read_csv(DATA / f"{name}_state.csv", ["t", "q", "dq", "tau"])          # tau = tau_est
    cmd = read_csv(DATA / f"{name}_cmd.csv", ["t", "q", "dq", "kp", "kd", "tau", "mode"])   # q = q_des, tau = tau_ff
    with open(DATA / f"{name}_seg.csv", newline="") as f:
        segs = [r for r in csv.DictReader(f) if int(r["slot"]) >= 0]
    return state, cmd, segs


# ---------------------------------------------------------------------------
# งานของสัปดาห์
# ---------------------------------------------------------------------------
def align(state_t: np.ndarray, cmd_t: np.ndarray, delay: float) -> np.ndarray:
    """index ของคำสั่งที่มีผล ณ เวลา state_t − delay (zero-order hold)  คืน −1 ถ้ามาก่อนคำสั่งแรก"""
    # TODO [6.2] np.searchsorted(cmd_t, state_t − delay, side="right") − 1
    return np.full(len(state_t), -1)


def pd_terms(state: dict, cmd: dict, slot: int, delay: float):
    """คืน (mask, P, D, y) ของ slot เดียว

    mask : แถวของ state ที่จับคู่คำสั่งได้ (j ≥ 0)
    P    = kp·(q_des − q)        D = kd·(dq_des − dq)        y = tau_est − tau_ff
    """
    # TODO [6.3] j = align(...);  mask = j >= 0;  jj = j[mask]
    # TODO [6.3] คำนวณ P, D, y จาก state[...][mask, slot] และ cmd[...][jj, slot]
    n = 0
    return np.zeros(len(state["t"]), bool), np.zeros(n), np.zeros(n), np.zeros(n)


def fit(P: np.ndarray, D: np.ndarray, y: np.ndarray, offset: bool = True, use_d: bool = True):
    """least squares  y ≈ a·P (+ b·D) (+ c)   คืน (a, b, c, y_fit)   b = nan ถ้า use_d=False, c = 0 ถ้า offset=False"""
    # TODO [6.4] คอลัมน์ X: [P] + [D ถ้า use_d] + [ones ถ้า offset]  → np.column_stack
    # TODO [6.4] theta = np.linalg.lstsq(X, y, rcond=None)[0];  y_fit = X @ theta
    # TODO [6.4] แกะ a, b, c จาก theta ตามคอลัมน์ที่ใส่
    return float("nan"), float("nan"), 0.0, np.zeros_like(y)


def rms(x: np.ndarray) -> float:
    # TODO [6.4]
    return 0.0


def corr(a: np.ndarray, b: np.ndarray) -> float:
    # TODO [6.4] np.corrcoef(a, b)[0, 1]  (คืน nan ถ้าตัวใดตัวหนึ่งคงที่)
    return float("nan")


def window(t: np.ndarray, t0: float, t1: float) -> np.ndarray:
    """mask ของช่วงเวลา [t0, t1]"""
    # TODO [6.5]
    return np.zeros(len(t), bool)


def best_delay(state: dict, cmd: dict, slot: int, t0: float, t1: float, delays_ms=range(0, 31)):
    """กวาด delay หาค่าที่ residual RMS ต่ำสุด (fit มี offset ในช่วง [t0, t1])  คืน (delay_s, ตาราง [(ms, resid, a, b)])"""
    # TODO [6.6] วน delays_ms: pd_terms → ตัดช่วง → fit(offset=True) → residual = rms(y − y_fit)
    return 0.0, []


# ---------------------------------------------------------------------------
# เทสต์ (ให้ไว้แล้ว): ข้อมูลปลอมที่รู้คำตอบ
# ---------------------------------------------------------------------------
def run_tests():
    ok = True

    def check(name, cond_fn):
        """cond_fn = lambda ที่คืน True/False · ถ้า error (เช่นยังไม่ได้เติม) นับเป็น FAIL"""
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
    j = align(np.array([12.0]), np.array([0.0, 10.0, 20.0]), 3.0)
    check("delay 3: state 12 → ใช้คำสั่งที่ 9 → index 0", lambda: list(j) == [0])

    print("pd_terms")
    st = {"t": np.array([0.5, 1.5]), "q": np.zeros((2, 29)), "dq": np.zeros((2, 29)), "tau": np.zeros((2, 29))}
    st["q"][:, 3] = [0.1, 0.2]
    st["dq"][:, 3] = [1.0, 0.0]
    st["tau"][:, 3] = [5.0, 6.0]
    cm = {"t": np.array([0.0, 1.0]), "q": np.zeros((2, 29)), "dq": np.zeros((2, 29)),
          "kp": np.full((2, 29), 100.0), "kd": np.full((2, 29), 2.0), "tau": np.zeros((2, 29))}
    cm["q"][:, 3] = [0.15, 0.3]
    cm["tau"][:, 3] = [1.0, 0.0]
    m, P, D, y = pd_terms(st, cm, 3, 0.0)
    check("P = kp(q_des − q) = [5, 10]", lambda: np.allclose(P, [5.0, 10.0]))
    check("D = kd(dq_des − dq) = [−2, 0]", lambda: np.allclose(D, [-2.0, 0.0]))
    check("y = tau_est − tau_ff = [4, 6]", lambda: np.allclose(y, [4.0, 6.0]))

    print("fit (ข้อมูลปลอม: y = 0.93 P + 0.86 D − 0.28 + noise)")
    rng = np.random.default_rng(0)
    P = rng.normal(0, 2.5, 5000)
    D = rng.normal(0, 1.8, 5000)
    y = 0.93 * P + 0.86 * D - 0.28 + rng.normal(0, 0.05, 5000)
    a, b, c, yf = fit(P, D, y, offset=True)
    check("มี offset → a ≈ 0.93, b ≈ 0.86, c ≈ −0.28 (±1%)", lambda: 
          abs(a - 0.93) < 0.0093 and abs(b - 0.86) < 0.0086 and abs(c + 0.28) < 0.01)
    check("corr(y_fit, y) > 0.99", lambda: corr(yf, y) > 0.99)
    check("rms(y − y_fit) ≈ noise 0.05", lambda: abs(rms(y - yf) - 0.05) < 0.005)

    print("offset สำคัญเมื่อแรงบิดเล็ก (แบบศอก)")
    Ps = 0.5 + rng.normal(0, 0.1, 5000)                 # ค้างท่า: P เล็ก เกือบคงที่ (≈ แรงโน้มถ่วง)
    ys = 0.96 * Ps + 0.15 + rng.normal(0, 0.02, 5000)
    a_no, _, _, _ = fit(Ps, np.zeros_like(Ps), ys, offset=False, use_d=False)
    a_off, _, c_off, _ = fit(Ps, np.zeros_like(Ps), ys, offset=True, use_d=False)
    check("ไม่มี offset → a เพี้ยนเกิน 0.1", lambda: abs(a_no - 0.96) > 0.1)
    check("มี offset → a ≈ 0.96, c ≈ +0.15", lambda: abs(a_off - 0.96) < 0.03 and abs(c_off - 0.15) < 0.02)

    print("omitted variable bias")
    Pc = rng.normal(0, 2.0, 5000)
    Dc = -0.6 * Pc + rng.normal(0, 0.5, 5000)           # step: P ใหญ่ ↔ D ใหญ่ทิศตรงข้าม (สัมพันธ์กัน)
    yc = 1.0 * Pc + 1.0 * Dc
    a_drop, _, _, _ = fit(Pc, Dc, yc, offset=False, use_d=False)
    check("ตัด D ทิ้ง → a ไม่ใช่ 1 (ต่างเกิน 0.2)", lambda: abs(a_drop - 1.0) > 0.2)

    print("window")
    check("[1, 2] ของ t=[0,1,1.5,2,3] → [F,T,T,T,F]", lambda: 
          list(window(np.array([0, 1, 1.5, 2, 3]), 1.0, 2.0)) == [False, True, True, True, False])

    print("ผ่านทั้งหมด ✅" if ok else "ยังมี FAIL: เติม TODO แล้วรันใหม่")


if __name__ == "__main__":
    run_tests()
