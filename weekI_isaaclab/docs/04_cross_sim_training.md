# 04: task G1 23-DoF ใน Isaac, cross-sim และการเทรนบน Newton (I3, I4)

## 1. task `Unitree-G1-23dof-Velocity[-Flat]` สร้างมายังไง
`unitree_rl_lab/source/.../robots/g1/23dof/velocity_env_cfg.py` (session งานหลักเขียน)
```python
_g1_29dof = importlib.import_module("...g1.29dof.velocity_env_cfg")     # ชื่อแพ็กเกจขึ้นต้นด้วยเลข import ตรงไม่ได้
class RobotFlatEnvCfg(_g1_29dof.RobotFlatEnvCfg):                     # สืบทอด reward/obs/terrain ของ 29dof
    def __post_init__(self):
        super().__post_init__()
        self.scene.robot = G1_23DOF_CFG.replace(prim_path="{ENV_REGEX_NS}/Robot")   # หุ่น + gain แบบ mjlab
        self.actions.JointPositionAction.scale = G1_23DOF_ACTION_SCALE             # 0.25·effort/kp
```
- ไม่แก้ไฟล์ 29dof เลย ใช้ `.replace()` (สร้างสำเนา config แล้วเปลี่ยนบาง field) เหมือน factory ชั้น 2 ของ mjlab (weekR 02)
- gain/armature/scale = สูตรเดียวกับ `g1_23dof_constants.py` ของ mjlab → I1 [4], I2 [4] ตรวจแล้ว

## 2. task Isaac ≠ สัญญา deploy ของ mjlab (I1 [4])
| | mjlab (P3b → v0) | task Isaac (unitree_rl_lab) |
|---|---|---|
| obs actor | 7 term รวม `gait_phase`, history 1 → 80 | 6 term ไม่มี phase, history 5 → 390 |
| critic | privileged 95 (asymmetric) | `obs_groups = {"critic": ["policy"]}` = symmetric |
| reward | ของ mjlab | ของ unitree 29dof (gait, feet_clearance, ...) |
| คำสั่ง | lin_vel_x (−1, 2) curriculum | `UniformLevelVelocityCommandCfg` เริ่ม ±0.1 แล้วขยาย |
→ policy ที่เทรนใน task นี้ **ใช้กับ g1_ctrl + deploy.yaml เดิมไม่ได้** ต้องมี deploy.yaml ใหม่ (และ g1_ctrl ต้องรองรับ history)

## 3. cross-sim (I3): ทดสอบแค่ "ฟิสิกส์" ไม่ใช่ task
`play_deploy_onnx.py` ของ unitree_rl_lab:
1. สร้าง env `-Flat` แล้ว **ปิด** events / terminations / curriculum / rewards / contact sensor · 1 env
2. ไม่ใช้ observation manager ของ task: สร้าง obs 80 เองจาก `deploy.yaml` (ลำดับ term, scale, phase แบบ g1_ctrl)
3. ประเมิน ONNX ด้วย torch (ไม่มี onnxruntime ใน env) → action → แปลงลำดับ policy → ลำดับ action term (`perm`)
4. ต่อกรณี: settle 2 s → เดิน 12 s → วัด 8 s ท้าย · ล้ม = เอียง > 0.85 rad
เท่ากับว่า Isaac ทำตัวเป็น "หุ่น" ที่ g1_ctrl คุย ด้วยฟิสิกส์ของอีก engine

ผล I3 (v0 = P3b, ของเรา 13/11) เทียบกับ vault:
| คำสั่ง | PhysX | Newton | MuJoCo (vel_eval, vault) |
|---|---|---|---|
| vx 0.4 | 102% | 99% | 97% |
| vx 0.8 | 79% | 73% | 74% |
| wz 0.5 | 72% | 79% | 69–73% |
ไม่ล้มทุกกรณี · ต่างกันไม่เกิน ~±8 pp → ผ่านเกณฑ์
Newton ใกล้ MuJoCo ที่ vx (solver เดียวกัน) แต่ไม่เท่า เพราะ geom ชน (mesh จาก USD vs capsule), friction และ USD vs MJCF

## 4. เทรนบน Newton (I4)
```bash
bash i4_train_newton.sh newton 256 10       # = train.py --task Unitree-G1-23dof-Velocity-Flat --headless presets=newton
```
| 256 env (ของเรา) | s/iteration หลังอุ่นเครื่อง |
|---|---|
| Newton | 0.53 |
| PhysX | 0.89 |
- log อยู่ที่ `<cwd>/logs/rsl_rl/unitree_g1_23dof_velocity_flat/<วันเวลา>/` → สคริปต์ `cd` ไป weekI_isaaclab ก่อน
- iteration แรกๆ episode length ~8 → 60 step แล้ว bad_orientation พุ่ง = ปกติ (เริ่มจาก policy สุ่ม, คำสั่ง ±0.1)
- vault: 1024 env ≈ 1.14 s/iteration ทั้งสอง backend (ตอนนั้น Newton 1.2 ใหม่ๆ)
- ⚠ ใช้ GPU เต็ม: อย่ารันพร้อมงานเทรนของ session หลัก

## 5. checklist: จะเอา policy ข้าม engine ต้องตรงอะไรบ้าง
| อย่าง | ตรวจด้วย |
|---|---|
| ลำดับ joint (ใช้ชื่อเสมอ) | I2 [3] |
| kp / kd / armature / effort | I2 [4], I1 [4] |
| action scale / offset | I1 [4] (deploy.yaml ปัด 2 ตำแหน่ง ต่าง 0.0025) |
| step_dt = sim.dt × decimation | I1 [4] |
| quaternion convention ตอนสร้าง gravity | ilib `quat_xyzw_to_wxyz` (Newton ภายใน) · `mdp.projected_gravity` ทำให้แล้ว |
| solver option (integrator!) | I1 [3] |
| geom ที่ใช้ชน / friction | I2 [2] (ต่างกันโดยตั้งใจไม่ได้ → หวังให้ DR ครอบ) |

## คำถามเช็ค
1. ทำไม cross-sim ต้องปิด events/terminations แต่ไม่ปิด actuator
2. ถ้า Newton ได้ 99% แต่ PhysX ได้ 60% ที่ vx 0.4 สงสัยอะไรก่อน (ไล่จาก checklist)
3. อยากเทรนใน Isaac แล้ว deploy ด้วย g1_ctrl เดิม ต้องแก้ task Isaac ตรงไหนบ้าง (ดูตารางข้อ 2)
