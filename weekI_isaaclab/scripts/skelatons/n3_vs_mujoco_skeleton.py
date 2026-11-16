"""N3: Newton (MuJoCo Warp บน GPU) vs MuJoCo C ปกติ: โมเดลเดียวกัน ผลเหมือนกันแค่ไหน · PD แบบ implicit vs explicit

    python n3_vs_mujoco.py                 # dt 0.005 (ค่าที่ใช้เทรน)
    python n3_vs_mujoco.py --dt 0.02       # dt ใหญ่: explicit PD เริ่มสั่น/ระเบิด, implicit ยังนิ่ง

การทดลอง: pelvis ตรึง (fixed base) ทุกข้อต่อค้างท่า default แล้วสั่งศอกซ้าย +0.3 rad แบบขั้นบันไดที่ t = 0.2 s
  A  Newton SolverMuJoCo (GPU, float32) · PD = actuator ของ MuJoCo (implicit ใน implicitfast)
  B  MuJoCo C (CPU, float64) อ่าน MJCF ที่ Newton สร้าง (save_to_mjcf) · ctrl = เป้า → ควรเกือบเท่า A
  C  MuJoCo C โมเดลเดียวกันแต่ปิด actuator แล้วคิดแรง PD เองทุก step (explicit) แบบ unitree_mujoco bridge
  D  C + frictionloss 0.2 / damping 0.05 ต่อข้อ (ค่า default ใน scene ของ unitree_mujoco)

[skeleton] ทายก่อนรัน
  1. A (Newton GPU) กับ B (MuJoCo C) ต่างกันประมาณเท่าไร: 0 / 1e-6 / 1e-3 / 1e-1 rad
  2. dt 0.02: implicit กับ explicit PD ตัวไหนพัง และพังเพราะอะไร
  3. frictionloss 0.2 ทำให้ final error ใหญ่ขึ้นหรือเล็กลง (เทียบ weekM ศอก +69°)
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import ilib_skeleton as ilib  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--dt", type=float, default=0.005)
ap.add_argument("--secs", type=float, default=1.2)
args = ap.parse_args()

ilib.quiet()
import mujoco  # noqa: E402
import newton  # noqa: E402
import numpy as np  # noqa: E402

DT, T_STEP = args.dt, 0.2
N = int(round(args.secs / DT))
N += N % 2
I_E = ilib.POLICY_JOINTS.index("left_elbow_joint")
STEP = 0.3


def target_at(k):
    t = ilib.HOME.copy()
    if k * DT >= T_STEP:
        t[I_E] += STEP
    return t


# ---------------------------------------------------------------- A. Newton
proto = ilib.build_g1(floating=False)
xml_path = ilib.LOGS / "newton_fixed_generated.xml"
xml_path.parent.mkdir(exist_ok=True)
simA = ilib.G1Sim(worlds=1, floating=False, dt=DT, use_graph=False, proto=proto, save_to_mjcf=str(xml_path))
qA = np.zeros((N, 23))
# TODO(N3) วน N step: set_target(target_at(k)) → step(1) → เก็บ simA.q()[0] ลง qA[k]
raise NotImplementedError('TODO(N3) วน N step: set_target(target_at(k)) → step(1) → เก็บ simA.q()[0] ลง qA[k]')

# ---------------------------------------------------------------- B/C/D. MuJoCo C
def mj_load(frictionloss=0.0, damping=0.0):
    m = mujoco.MjModel.from_xml_path(str(xml_path))
    m.opt.timestep = DT                    # XML ที่ Newton เขียนมี timestep 0.002 (ค่าเริ่มของ MuJoCo) → ต้องตั้งเอง
    jnames = [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_JOINT, j) for j in range(m.njnt)]
    # ชื่อใน XML ที่ Newton สร้างเป็น path ยาว '..._left_elbow_joint' → จับคู่ด้วยท้ายชื่อ
    jid = [next(j for j, n in enumerate(jnames) if n.endswith(p)) for p in ilib.POLICY_JOINTS]
    qadr = np.array([m.jnt_qposadr[j] for j in jid])
    dadr = np.array([m.jnt_dofadr[j] for j in jid])
    aid = [next(a for a in range(m.nu) if m.actuator_trnid[a, 0] == j) for j in jid]
    m.dof_frictionloss[dadr] = frictionloss
    m.dof_damping[dadr] = damping
    d = mujoco.MjData(m)
    d.qpos[qadr] = ilib.HOME
    mujoco.mj_forward(m, d)
    return m, d, qadr, dadr, np.array(aid)


def run_mj(explicit=False, frictionloss=0.0, damping=0.0):
    m, d, qadr, dadr, aid = mj_load(frictionloss, damping)
    if explicit:
        m.actuator_gainprm[:, 0] = 0.0     # ปิด actuator: แรง = 0·ctrl + 0
        m.actuator_biasprm[:, :3] = 0.0
    q = np.zeros((N, 23))
    for k in range(N):
        tgt = target_at(k)
        if explicit:
            # TODO(N3) แรง PD คิดเอง ณ ต้น step (explicit): τ = kp(q* − q) − kd·qd → d.qfrc_applied[dadr]
            raise NotImplementedError('TODO(N3) แรง PD คิดเอง ณ ต้น step (explicit): τ = kp(q* − q) − kd·qd → d.qfrc_applied[dadr]')
        else:
            d.ctrl[aid] = tgt
        mujoco.mj_step(m, d)
        q[k] = d.qpos[qadr]
    return q


qB = run_mj()
qC = run_mj(explicit=True)
qD = run_mj(explicit=True, frictionloss=0.2, damping=0.05)


# ---------------------------------------------------------------- สรุป
def metrics(q):
    e = q[:, I_E]
    k0 = int(round(T_STEP / DT))
    tgt = ilib.HOME[I_E] + STEP
    resp = e[k0:] - ilib.HOME[I_E]
    if not np.all(np.isfinite(resp)):
        return dict(rise90_ms=None, overshoot_pct=None, final_err=None, peak_to_peak_last=None)
    i90 = np.argmax(resp >= 0.9 * STEP) if np.any(resp >= 0.9 * STEP) else None
    last = e[-int(0.2 / DT):]
    return dict(rise90_ms=None if i90 is None else (i90 + 1) * DT * 1e3,
                overshoot_pct=max(0.0, (resp.max() - STEP) / STEP * 100),
                final_err=float(e[-1] - tgt), peak_to_peak_last=float(np.ptp(last)))


print(f"ศอกซ้าย step +{STEP} rad ที่ t={T_STEP}s · dt {DT} · {N} step · MJCF จาก Newton: {xml_path.name}")
rows = []
for name, q in [("A Newton GPU (implicit)", qA), ("B MuJoCo C (implicit)", qB), ("C MuJoCo C explicit PD", qC),
                ("D C + frictionloss/damping", qD)]:
    rows.append(dict(case=name, **metrics(q)))
ilib.print_table(rows, fmt={"rise90_ms": "{:.0f}", "overshoot_pct": "{:.1f}", "final_err": "{:+.4f}",
                            "peak_to_peak_last": "{:.1e}"})
print(f"\nmax |A − B| ทุกข้อ ทุก step = {np.nanmax(np.abs(qA - qB)):.2e} rad   ← float32 GPU vs float64 CPU (คณิตเดียวกัน)")
print(f"max |B − C| ศอก            = {np.nanmax(np.abs(qB[:, I_E] - qC[:, I_E])):.2e} rad   ← implicit vs explicit PD")
print(f"max |C − D| ศอก            = {np.nanmax(np.abs(qC[:, I_E] - qD[:, I_E])):.2e} rad   ← frictionloss 0.2 + damping 0.05")
