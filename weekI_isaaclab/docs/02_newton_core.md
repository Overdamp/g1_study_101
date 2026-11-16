# 02: Newton ล้วน: Model, State, Control, Solver (N1–N4)

## 1. วัตถุ 5 ตัว
```
ModelBuilder (CPU, list ธรรมดา แก้ง่าย)
   add_mjcf / add_usd / add_urdf / add_body / add_joint_* / add_shape_*
   replicate(proto, W) · add_ground_plane()
        │ finalize()
        ▼
Model  (GPU, warp array · "ของที่ไม่เปลี่ยนทุก step": มวล, รูปทรง, gain, limit)
   model.state()   → State   (joint_q, joint_qd, body_q, body_qd · เปลี่ยนทุก step)
   model.control() → Control (joint_target_pos / vel, joint_f · สิ่งที่เราสั่ง)
Solver(model, ...) .step(state_in, state_out, control, contacts, dt)
```
| อยากทำ | ทำที่ |
|---|---|
| เปลี่ยน gain / armature ตอนสร้าง | `builder.joint_target_ke[d] = ...` (N1, `ilib.build_g1`) |
| เปลี่ยน gain หลังสร้าง (ต่อ world) | `model.joint_target_ke.assign(...)` + `solver.notify_model_changed(JOINT_DOF_PROPERTIES)` (N2) |
| สั่งท่า | `control.joint_target_pos.assign(...)` (`G1Sim.set_target`) |
| อ่านมุม | `state.joint_q.numpy()` |
| ตั้งท่าแล้วให้ body ขยับตาม | `newton.eval_fk(model, joint_q, joint_qd, state)` |

ลืม `notify_model_changed` = ค่าใน Newton เปลี่ยน แต่ MuJoCo Warp ยังใช้สำเนาเก่า (มันเก็บ `actuator_gainprm` ของตัวเอง)

## 2. joint_q / joint_qd: เลย์เอาต์ของหุ่น 1 ตัว (N1)
```
joint_q  (30):  [x y z  qx qy qz qw | 23 มุม]      coord: free joint = 7 (ตำแหน่ง 3 + quaternion 4)
joint_qd (29):  [vx vy vz wx wy wz  | 23 ความเร็ว]  dof:   free joint = 6
                 ↑ free joint        ↑ joint_q_start[j] / joint_qd_start[j] บอกว่า joint j เริ่มช่องไหน
```
- เข่าซ้าย: `q_start 10`, `qd_start 9` · W world ต่อกันเป็นแถวยาว: world w ช่อง `w·30 + 10`
- ⚠ **quaternion ของ Newton = (x, y, z, w)** แต่ MuJoCo / mjlab / Isaac Lab API ใช้ (w, x, y, z)
  สับสนตรงนี้ = gravity/tilt ผิดทั้งหมดแบบไม่มี error → `ilib.quat_xyzw_to_wxyz`
- ชื่อ joint เป็น path: `g1_23dof_rev_1_0/worldbody/pelvis/.../left_knee_joint` → `ilib.short_name`

## 3. world: หลายหุ่นในโมเดลเดียว
`builder.replicate(proto, W)` = คัดลอกหุ่นเป็น W ชุด แต่ละชุดอยู่ "world" ของตัวเอง → **ชนกันข้าม world ไม่ได้** แม้จะวางทับกัน
shape ของพื้นอยู่ world −1 = ใช้ร่วมทุก world · RL 4096 env = 4096 world ใน Model เดียว
ทุก array ใน Model/State ยาว W เท่า → kernel 1 ครั้งคำนวณทุก world พร้อมกัน (N4: 1024 world เร็วกว่า 1 world ~170 เท่าต่อ step)

## 4. SolverMuJoCo: Newton → MuJoCo Warp (N1 `--mjcf`, N3)
ตอนสร้าง solver: Model → `MjSpec` → `mjw_model` (เขียนไฟล์ดูได้ด้วย `save_to_mjcf=`)
ทุก `step()`:
```
_apply_mjc_control   control.joint_target_pos → mjw_data.ctrl
_update_mjc_data     state_in (joint_q/qd) → mjw_data.qpos/qvel
opt.timestep = dt    ← dt มาจากอาร์กิวเมนต์ของ step (ใน XML ที่ save ไว้ยังเป็น 0.002)
mujoco_warp.step     (collision + constraint solver + integrate)
_update_newton_state mjw_data → state_out
```
**PD ของ Newton = actuator ชนิด position ของ MuJoCo**
```
gainprm[0] = kp            biasprm = [0, −kp, −kd]
แรง = kp·ctrl − kp·q − kd·qd = kp(q* − q) − kd·qd
```
- integrator `implicitfast` คิดเทอม `−kd·qd` แบบ implicit → นิ่งแม้ dt ใหญ่ (N3: dt 0.02 implicit overshoot 2%, explicit 45% แล้วระเบิด)
- effort limit → `actuatorfrcrange` (ถ้าไม่ตั้ง Newton ใส่ ±1e6 = ไม่จำกัด)
- joint limit → `solreflimit = (−2500, −100)` ค่าลบใน MuJoCo = stiffness/damping ตรงๆ (จาก `limit_ke`/`limit_kd` ของ Newton)
- `frictionloss` ของ MuJoCo = `Model.joint_friction` ใน Newton (หน่วย N·m ไม่ใช่สัมประสิทธิ์)

## 5. พารามิเตอร์ของ solver (N4 B: หุ่นรูปปั้น PD ×8 ยืน 2 s)
| พารามิเตอร์ | ความหมาย | ผลที่วัดได้ |
|---|---|---|
| `integrator` | euler / implicitfast / rk4 | **euler + gain สูง → ล้ม** (damping explicit ไม่เสถียร) · ค่าเริ่มของ `MJWarpSolverCfg` = euler! |
| `ls_iterations` | line search ต่อ iteration | 15 → 2: solver ไม่ลู่เข้า (ชน 100 iteration) → ล้ม |
| `iterations` | iteration สูงสุดของ constraint solver | 100 → 3: ไม่ต่าง (ปกติใช้จริงแค่ 1–3) |
| `cone` / `impratio` | กรวยแรงเสียดทาน pyramidal/elliptic · ความ "แข็ง" ของแรงเสียดทาน | เกือบไม่ต่างกรณียืนนิ่ง (ต่างตอนลื่น/เดิน) |
| `solver` | newton / cg | cg ใช้ iteration ~4× ช้ากว่า 4× |
| dt | 0.002 / 0.005 / 0.01 | 0.01 → ล้ม (contact แข็งเกินสำหรับ step ใหญ่) |
| `njmax`, `nconmax` | ขนาด buffer constraint / contact ต่อ world | เล็กไป = contact หาย (task ใช้ 95 / 20) |

## 6. CUDA graph (N4 A)
`wp.ScopedCapture()` บันทึก "ลำดับ kernel + ที่อยู่หน่วยความจำ" ครั้งเดียว แล้ว `wp.capture_launch(graph)` เล่นซ้ำโดยไม่ผ่าน Python
- เร็วกว่าเรียกทีละ kernel ~3× ที่ world น้อย (Python overhead คือคอขวด) ส่วนที่ world เยอะ GPU เป็นคอขวดแทน
- graph จำ **ที่อยู่** ไม่ได้จำ object: `state_0, state_1 = state_1, state_0` ใน Python ไม่มีผลกับ graph
  → `G1Sim.capture` บันทึก 2 step ให้สลับกลับที่เดิม · Isaac Lab ใช้ `_use_single_state` (in-place) แทน
- ห้าม capture ตอน kernel ยังไม่ compile → step ครั้งแรกนอก graph ก่อน
- เปลี่ยนค่าใน array เดิม (`.assign`) ได้ แต่สร้าง array ใหม่ = graph ไม่เห็น

## คำถามเช็ค
1. world 3 เข่าขวา อยู่ช่องไหนของ `joint_q` (หุ่น floating)
2. ถ้า `set_target` แล้วหุ่นไม่ขยับ ใน graph mode สงสัยอะไรก่อน
3. N2: gain ×8 ยืนได้ แต่ทำไมเทรนด้วย gain ต่ำ (ω = 10 Hz) · gain สูงเสียอะไรบนหุ่นจริง
4. ทำไม explicit PD ที่ dt 0.02 ระเบิดทั้งที่ dt 0.005 ไม่เป็นไร (คิดจาก kd กับ inertia ของศอก)
