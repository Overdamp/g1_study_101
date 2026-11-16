# 03: Isaac Lab บน Newton: preset, NewtonManager, ลำดับใน env.step (I1, I2)

## 1. preset: สลับ engine ด้วยคำเดียว (I1)
task ประกาศ "ทางเลือก" ไว้ใน config ด้วย `PresetCfg` (`isaaclab_tasks/utils/hydra.py:100`)
```python
@configclass
class PhysicsCfg(PresetCfg):                 # unitree_rl_lab .../29dof/velocity_env_cfg.py
    physx: PhysxCfg = PhysxCfg(gpu_max_rigid_patch_count=10 * 2**15)
    default = physx
    newton: NewtonCfg = NewtonCfg(solver_cfg=MJWarpSolverCfg(njmax=95, nconmax=20, cone="pyramidal",
                                  impratio=1, integrator="implicitfast", ls_parallel=True, ls_iterations=15),
                                  num_substeps=1)
sim: SimulationCfg = SimulationCfg(physics=PhysicsCfg())
```
task G1 23-DoF มี PresetCfg 3 จุด: `sim.physics`, `events`, `scene.contact_forces`
- CLI: `python train.py ... presets=newton` (Hydra override) → ทุก PresetCfg ที่มี field `newton` ถูกแทนด้วยค่านั้น ที่ไม่มี = `default`
- ในโค้ด (ไม่ต้องเปิด Kit):
  ```python
  cfg = load_cfg_from_registry(task, "env_cfg_entry_point")
  cfg = resolve_presets(cfg, {"newton"})
  ```
- physx → newton ต่างกัน 59 field (I1 [2]): ส่วนใหญ่คือ `sim.physics.*` ทั้งก้อน + event สุ่ม friction + คลาส contact sensor

## 2. `NewtonCfg` / `MJWarpSolverCfg` (`isaaclab_newton/physics/`)
| field | ความหมาย | task | ค่าเริ่มของคลาส |
|---|---|---|---|
| `solver_cfg` | เลือก solver (MJWarp / XPBD / Featherstone / Kamino) | MJWarp | MJWarp |
| `num_substeps` | แบ่ง 1 physics step เป็นกี่ step ย่อย | 1 | 1 |
| `use_cuda_graph` | ห่อ step ทั้งหมดเป็น CUDA graph | True | True |
| `integrator` | | **implicitfast** | **euler** ⚠ |
| `njmax` / `nconmax` | constraint / contact สูงสุดต่อ world | 95 / 20 | 300 / auto |
| `ls_iterations` / `ls_parallel` | line search | 15 / True | 50 / False |
| `use_mujoco_contacts` | ให้ MuJoCo หา contact เอง (False = ใช้ CollisionPipeline ของ Newton) | True | True |
| `save_to_mjcf` | เขียน MJCF ที่สร้างให้ MuJoCo Warp | - | None (I2 `--save-mjcf`) |
ถ้าเขียน task ใหม่แล้วลืมตั้ง integrator → euler → PD gain สูงไม่เสถียร (N4)

## 3. NewtonManager: ตัวกลางระหว่าง Isaac Lab กับ Newton (`newton_manager.py`)
เป็นคลาสที่มีแต่ `classmethod` (มีตัวเดียวทั้งโปรแกรม) · `NewtonMJWarpManager` สืบทอดแล้วสร้าง `SolverMuJoCo`
```
เริ่ม sim:
  instantiate_builder_from_stage()      USD stage → หา /World/envs/env_0, env_1, ...
      proto = ModelBuilder; proto.add_usd(stage, root_path=env_0)       ← อ่านหุ่นตัวแรกตัวเดียว
      for แต่ละ env: begin_world(); add_builder(proto, xform=ตำแหน่ง env); end_world()
  finalize → Model  ·  _build_solver → SolverMuJoCo(model, **solver_cfg)  ·  capture CUDA graph
ทุก sim.step():
  notify_model_changed (ถ้า event แก้ Model เช่นสุ่มมวล)
  → wp.capture_launch(graph)   [actuator?] + solver.step × num_substeps + update sensors
```
- USD อ่านด้วย schema resolver ทั้งของ Newton และ PhysX → USD ที่ทำไว้สำหรับ PhysX ใช้กับ Newton ได้เลย
- สถานะอ่านได้จากโค้ดเรา: `NewtonManager.get_model()`, `._solver`, `.get_state_0()`, `.get_control()` (I2)

## 4. articulation: gain ไปถึง solver ยังไง
`ImplicitActuatorCfg(stiffness, damping, armature, effort_limit_sim)` ของ task
→ `isaaclab_newton/assets/articulation/articulation.py:3895`
```
ImplicitActuator  → write_joint_stiffness_to_sim → Model.joint_target_ke   (solver ทำ PD เอง = position actuator)
explicit actuator → ke = kd = 0, Isaac Lab คิดแรงเองแล้วเขียน Control.joint_f
armature          → Model.joint_armature
friction          → Model.joint_friction  (= frictionloss N·m)
```
I2 [4]: kp ใน sim ต่างจากสูตร mjlab ไม่เกิน 1.3e-6 ทั้ง PhysX และ Newton

## 5. ลำดับ joint (I2 [3])
| backend | ลำดับ | perm policy → sim |
|---|---|---|
| PhysX | BFS: `left_hip_pitch, right_hip_pitch, waist_yaw, left_hip_roll, ...` | `[0, 3, 7, 11, 15, 19, 1, ...]` |
| Newton | DFS ตาม USD: `left_hip_pitch, left_hip_roll, left_hip_yaw, ...` | identity |
ลำดับ policy (mjlab / deploy.yaml / g1_ctrl) = DFS → บน Newton ตรงกันเองโดยบังเอิญ
**อย่าพึ่งความบังเอิญ:** สร้าง obs/action ด้วยชื่อ joint เสมอ (`SceneEntityCfg(joint_names=..., preserve_order=True)` แบบ `play_deploy_onnx.py`)

## 6. `ManagerBasedRLEnv.step` ของ Isaac Lab vs mjlab
```
process_action ×1
ถ้า _physics_handles_decimation:          (Newton + use_newton_actuators + actuator graph-safe ทั้งหมด)
    apply_action → write_data_to_sim → sim.step() ×1        ← ใน graph: (actuator → solver) × decimation
ไม่งั้น:                                    (PhysX, Newton ปกติ)
    (apply_action → write_data_to_sim → sim.step → scene.update) × decimation
episode_length_buf++ · common_step_counter++
termination → reward(dt=step_dt) → reset ที่จบ → observation
```
| | mjlab | Isaac Lab |
|---|---|---|
| ลำดับ manager ใน step | เหมือนกัน (process → physics×4 → termination → reward → reset → obs) | เหมือนกัน |
| decimation | วนใน Python เสมอ | วนใน Python หรือ **อยู่ใน CUDA graph** (fast path) |
| episode_length_buf | `+= 1` ก่อน termination (`manager_based_rl_env.py:378`) | เหมือนกัน |
I2: Newton ปกติ `sim.step` ×4 ต่อ env.step · `--fast-path` ×1 และเร็วขึ้น ~10% (512 env: 21.4 → 19.5 ms)

## 7. sensor และ event บน Newton
- `isaaclab_newton.sensors.ContactSensorCfg` ใช้แทน PhysX (task ใส่ไว้ใน `ContactSensorPresetCfg`) · อ่านแรงจาก `solver.update_contacts`
- สุ่ม friction: Newton มี `mu` ตัวเดียว → `newton_randomize_rigid_body_material(static_friction_range=...)`
- สุ่มมวล/ผลัก: ใช้ event เดิมได้ (`randomize_rigid_body_mass`, `push_by_setting_velocity`) · เวลา articulation เขียนค่าลง Model มันเรียก `SimulationManager.add_model_change(...)` ให้เอง (`articulation.py:1342` ฯลฯ) แล้ว `NewtonManager.step` ค่อย `notify_model_changed` ก่อน step ถัดไป

## คำถามเช็ค
1. ถ้าเพิ่ม `PresetCfg` ให้ `scene.robot` (USD กับ MJCF) แล้วรัน `presets=newton` จะได้ตัวไหน · ถ้า field ชื่อ `mjcf` ล่ะ
2. เขียน obs ด้วย `robot.data.joint_pos[:, 0:6]` ว่า "ขาซ้าย" ใช้ได้บน backend ไหน
3. fast path เร็วขึ้นเพราะลดอะไร · ทำไมใช้ไม่ได้ถ้ามี explicit actuator ที่เขียนด้วย torch
