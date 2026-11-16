"""N1: Newton ล้วน: MJCF → ModelBuilder → Model แล้วดูว่าข้างในเก็บอะไรไว้ที่ไหน

    python n1_model.py               # สรุป + ตาราง joint
    python n1_model.py --mjcf        # + เขียน MJCF ที่ Newton แปลงให้ MuJoCo Warp แล้วอ่านกลับด้วย mujoco

คำถามที่ไฟล์นี้ตอบ
  - free joint ของ pelvis กิน coordinate กี่ช่อง dof กี่ช่อง · quaternion เรียงแบบไหน
  - joint_q_start / joint_qd_start คืออะไร · มุมเข่าซ้ายอยู่ช่องไหนของ joint_q
  - ค่าที่ mjlab ตั้งด้วย Python (armature, kp, kd) ไปอยู่ตรงไหนใน Newton
  - Newton ส่งอะไรให้ MuJoCo Warp จริงๆ (actuator ชนิดไหน, ค่า limit ใดถูกเติมให้)

[skeleton] ทายก่อนรัน
  1. MJCF ของ mjlab มี armature / kp ของเข่าอยู่ในไฟล์ไหม (ค่าในไฟล์ดิบ = ?)
  2. shape 64 ชิ้น: ชิ้นไหนใช้ชน ชิ้นไหนใช้ดูอย่างเดียว · MuJoCo Warp จะได้ geom กี่ชิ้น
  3. actuator ที่ Newton สร้างให้ MuJoCo เป็นชนิดไหน (motor / position / general) และ biasprm = ?
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import ilib_skeleton as ilib  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--mjcf", action="store_true")
args = ap.parse_args()

ilib.quiet()
import newton  # noqa: E402
import numpy as np  # noqa: E402

# ---------------------------------------------------------------- 1. builder ดิบจาก MJCF (ยังไม่ใส่ค่าของ mjlab)
raw = newton.ModelBuilder()
newton.solvers.SolverMuJoCo.register_custom_attributes(raw)
raw.add_mjcf(str(ilib.XML), floating=True)
print("[1] MJCF ดิบ:", ilib.XML.name)
print(f"    body {raw.body_count} · joint {raw.joint_count} · dof {raw.joint_dof_count} · "
      f"coord {raw.joint_coord_count} · shape {raw.shape_count}")
print(f"    joint_label[0] = {raw.joint_label[0]!r}   ← ชื่อเป็น path ยาว ใช้ ilib.short_name()")
print(f"    joint_q[0:7] (free joint) = {np.round(raw.joint_q[0:7], 3)}  ← (x, y, z, qx, qy, qz, qw)")
i_knee = [ilib.short_name(x) for x in raw.joint_label].index("left_knee_joint")
print(f"    left_knee ในไฟล์ดิบ: armature {raw.joint_armature[raw.joint_qd_start[i_knee]]} · "
      f"kp {raw.joint_target_ke[raw.joint_qd_start[i_knee]]}  ← mjlab ไม่ได้เขียนใน XML แต่ตั้งด้วย Python")

for label, want in (("ชนได้", True), ("ภาพอย่างเดียว", False)):
    kinds = {}
    for t, f in zip(raw.shape_type, raw.shape_flags):
        if bool(int(f) & int(newton.ShapeFlags.COLLIDE_SHAPES)) == want:
            k = newton.GeoType(int(t)).name
            kinds[k] = kinds.get(k, 0) + 1
    print(f"    shape {label}: {kinds}")

# ---------------------------------------------------------------- 2. builder หลังใส่ค่า mjlab
b = ilib.build_g1()
print("\n[2] หลัง ilib.build_g1() (ใส่ armature, kp, kd, ท่า default แบบ mjlab)")
rows = ilib.joint_table(b)
ilib.print_table(rows, cols=["name", "type", "q_start", "qd_start", "ndof", "lower", "upper", "armature", "kp", "kd"],
                 fmt={"lower": "{:+.3f}", "upper": "{:+.3f}", "armature": "{:.4f}", "kp": "{:.2f}", "kd": "{:.3f}"})
print("    type: ", {int(v): v.name for v in newton.JointType})

# ---------------------------------------------------------------- 3. Model (finalize → GPU)
try:
    m = ilib.make_model(b, worlds=2)
except NotImplementedError as e:
    print(f"\n[3] ข้าม: {e} (ทำใน N2)")
    sys.exit()
print(f"\n[3] Model 2 world: joint_q.shape {m.joint_q.shape} (= 2 × {b.joint_coord_count}) · "
      f"joint_qd.shape {m.joint_qd.shape} (= 2 × {b.joint_dof_count}) · device {m.device}")
jq = m.joint_q.numpy()
k = b.joint_q_start[i_knee]
print(f"    มุมเข่าซ้าย world 0 = joint_q[{k}] = {jq[k]:.3f} · world 1 = joint_q[{b.joint_coord_count + k}] = "
      f"{jq[b.joint_coord_count + k]:.3f}")
print(f"    shape_world: {np.unique(m.shape_world.numpy(), return_counts=True)}  (−1 = พื้น ใช้ร่วมทุก world)")
print(f"    gravity {m.gravity.numpy()[0]} · up_axis {m.up_axis}")

# ---------------------------------------------------------------- 4. MJCF ที่ Newton ส่งให้ MuJoCo Warp
if args.mjcf:
    import mujoco

    out = ilib.LOGS / "newton_generated.xml"
    out.parent.mkdir(exist_ok=True)
    solver = newton.solvers.SolverMuJoCo(ilib.make_model(b, 1), save_to_mjcf=str(out), **ilib.G1Sim.SOLVER_DEFAULT)
    mm = mujoco.MjModel.from_xml_path(str(out))
    print(f"\n[4] {out}")
    print(f"    nq {mm.nq} · nv {mm.nv} · nu (actuator) {mm.nu} · ngeom {mm.ngeom}")
    print(f"    option: integrator {mm.opt.integrator} (3 implicitfast) · cone {mm.opt.cone} · "
          f"iterations {mm.opt.iterations} · ls_iterations {mm.opt.ls_iterations} · "
          f"timestep {mm.opt.timestep}  ← ยังไม่ใช่ dt จริง (Newton เขียนทับทุก step)")
    a = [mujoco.mj_id2name(mm, mujoco.mjtObj.mjOBJ_ACTUATOR, i) for i in range(mm.nu)]
    i = next(j for j, n in enumerate(a) if n and n.endswith("left_knee_joint")) if any(a) else 3
    print(f"    actuator ของเข่าซ้าย (index {i}): gainprm[0] {mm.actuator_gainprm[i, 0]:.3f} · "
          f"biasprm[:3] {np.round(mm.actuator_biasprm[i, :3], 3)}")
    print("      → แรง = gain·ctrl + b0 + b1·q + b2·qd = kp·(q* − q) − kd·qd  = actuator ชนิด position ของ MuJoCo")
    jn = mm.actuator_trnid[i, 0]
    print(f"    joint เข่า: armature {mm.dof_armature[mm.jnt_dofadr[jn]]:.4f} · frictionloss "
          f"{mm.dof_frictionloss[mm.jnt_dofadr[jn]]} · damping {mm.dof_damping[mm.jnt_dofadr[jn]]} · "
          f"actfrcrange {mm.jnt_actfrcrange[jn]}  ← effort limit")
    print(f"    solreflimit {mm.jnt_solref[jn]}  ← ค่าลบ = (−stiffness, −damping) ตรงๆ จาก limit_ke/limit_kd ของ Newton")
    del solver
