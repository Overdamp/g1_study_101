"""N2: PD ล้วนกับหุ่นทั้งตัว + gain ต่างกันในแต่ละ world (domain randomization แบบทำมือ)

    python n2_pd_drop.py                    # ส่วน A + B
    python n2_pd_drop.py --scales 0.5,1,2,4,8,16 --secs 4

A. floating base: หุ่น W ตัว ตัวที่ w ใช้ kp, kd × scale[w] ยืนด้วย PD ท่า default (ไม่มี policy)
   → ล้มเมื่อไร? gain สูงช่วยให้ยืนได้ไหม? (เทียบ weekM: PD ค้างท่า ล้มใน ~1.5 s)
B. fixed base: แขนห้อยด้วย PD ท่า default → มุมค้างห่างจากเป้าเท่าไร (sag) เทียบกับ scale
   → steady-state error ≈ แรงบิดจากน้ำหนัก / kp

สิ่งที่ฝึก: แก้ค่าใน Model หลัง finalize (ต่อ world) + บอก solver ว่า model เปลี่ยน (notify_model_changed)
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import ilib  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--scales", default="0.25,0.5,1,2,4,8")
ap.add_argument("--secs", type=float, default=3.0)
args = ap.parse_args()
scales = [float(s) for s in args.scales.split(",")]
W = len(scales)

ilib.quiet()
import newton  # noqa: E402
import numpy as np  # noqa: E402


def set_gain_scale(sim: ilib.G1Sim, scales) -> None:
    """kp, kd ของทุก joint ใน world w × scales[w]  (เฉพาะ 23 joint ไม่แตะ free joint)"""
    # >>>TODO(N2) อ่าน model.joint_target_ke/kd (.numpy() → reshape(W, nd)) → คูณทีละแถว → assign กลับ
    #             แล้ว solver.notify_model_changed(SolverNotifyFlags.JOINT_DOF_PROPERTIES)
    ke = sim.model.joint_target_ke.numpy().reshape(sim.W, sim.nd)
    kd = sim.model.joint_target_kd.numpy().reshape(sim.W, sim.nd)
    s = np.asarray(scales, dtype=np.float32)[:, None]
    ke[:, sim.d_idx] = ilib.KP[None, :] * s
    kd[:, sim.d_idx] = ilib.KD[None, :] * s
    sim.model.joint_target_ke.assign(ke.ravel())
    sim.model.joint_target_kd.assign(kd.ravel())
    # MuJoCo Warp มีสำเนา gain ของตัวเอง (actuator_gainprm/biasprm) → ต้องบอกให้คัดลอกใหม่
    sim.solver.notify_model_changed(newton.solvers.SolverNotifyFlags.JOINT_DOF_PROPERTIES)
    # <<<TODO


# ================================================================ A. floating
print(f"[A] floating base · {W} world · gain scale {scales} · ยืน PD ท่า default {args.secs} s")
sim = ilib.G1Sim(worlds=W)
set_gain_scale(sim, scales)
ke_check = sim.model.joint_target_ke.numpy().reshape(W, sim.nd)[:, sim.d_idx[3]]
print(f"    kp เข่าซ้ายแต่ละ world: {np.round(ke_check, 1)}")

dt_log = 0.1
n_log = int(round(dt_log / sim.dt))
n_log += n_log % 2                       # graph เดินทีละ 2
T = int(args.secs / dt_log)
fall_t = np.full(W, np.nan)
z_hist, tilt_hist = [], []
for k in range(T):
    sim.step(n_log)
    z, tilt = sim.base_pos()[:, 2], sim.tilt()
    z_hist.append(z)
    tilt_hist.append(tilt)
    # >>>TODO(N2) world ไหนเอียงเกิน 0.85 rad (≈ 49°, เกณฑ์เดียวกับ vel_eval) ครั้งแรก → บันทึกเวลา
    newly = np.isnan(fall_t) & (tilt > 0.85)
    fall_t[newly] = (k + 1) * n_log * sim.dt
    # <<<TODO

z_hist, tilt_hist = np.array(z_hist), np.array(tilt_hist)
rows = []
for w, s in enumerate(scales):
    rows.append(dict(scale=s, kp_knee=float(ke_check[w]), z_min=float(z_hist[:, w].min()),
                     z_end=float(z_hist[-1, w]), tilt_max_deg=float(np.degrees(tilt_hist[:, w].max())),
                     fall_s=None if np.isnan(fall_t[w]) else float(fall_t[w])))
ilib.print_table(rows, fmt={"kp_knee": "{:.1f}", "z_min": "{:.3f}", "z_end": "{:.3f}", "tilt_max_deg": "{:.1f}",
                            "fall_s": "{:.1f}"})
print("    (fall_s ว่าง = ไม่ล้มใน", args.secs, "s)")

# ================================================================ B. fixed base
print(f"\n[B] fixed base (pelvis ตรึง) · ค้างท่า default 2 s · sag = q − q_default")
simB = ilib.G1Sim(worlds=W, floating=False)
set_gain_scale(simB, scales)
simB.step(400)
sag = simB.q() - ilib.HOME
joints = ["left_shoulder_pitch_joint", "left_elbow_joint", "left_hip_pitch_joint", "left_knee_joint"]
rows = []
for w, s in enumerate(scales):
    r = dict(scale=s)
    for n in joints:
        r[n.replace("left_", "").replace("_joint", "")] = float(sag[w, ilib.POLICY_JOINTS.index(n)])
    rows.append(r)
ilib.print_table(rows, fmt={k: "{:+.4f}" for k in rows[0] if k != "scale"})
# ถ้า sag ∝ 1/kp จริง → sag × scale ต้องเกือบคงที่
i_e = ilib.POLICY_JOINTS.index("left_elbow_joint")
prod = sag[:, i_e] * np.array(scales)
print(f"    ศอก: sag × scale = {np.round(prod, 4)}  ← เกือบคงที่ = แรงบิดจากน้ำหนัก / kp(scale=1)")
print(f"    → แรงบิดจากน้ำหนักที่ศอก ≈ {prod[len(prod) // 2] * ilib.KP[i_e]:+.3f} N·m")
