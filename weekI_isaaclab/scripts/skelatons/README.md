# โมดูล I: โครงให้เติม (skeleton)

> เฉลยอยู่ที่ `../complete/` · docs อยู่ที่ `../../docs/` · ไฟล์ในนี้สร้างด้วย `python ../make_skeletons.py` (รันซ้ำ = ทับงานที่เติมไว้! ก็อปเก็บก่อน)

## ลำดับ
1. อ่าน `docs/README.md` → `01_big_picture.md` → `02_newton_core.md` §1–2
2. ```bash
   source ~/g1_study/weekI_isaaclab/env.sh && cd skelatons
   python ilib_skeleton.py          # ตอนเริ่ม PASS 6/16 → ครบ 16/16
   ```
   | TODO ใน `ilib_skeleton.py` | งาน | เทสต์ที่จะผ่าน |
   |---|---|---|
   | `build_g1`, `joint_table`, `quat_xyzw_to_wxyz` | N1 | 3 ข้อ (knee index, kp/armature, quat) |
   | `tilt_from_quat_xyzw`, `make_model`, `_simulate`, `capture`, `set_target` | N2 | 7 ข้อ (tilt + GPU ทั้งหมด) |
3. ทำสคริปต์ตามลำดับ n1 → n5 → i1 → i4 · แต่ละไฟล์มี **"ทายก่อนรัน"** ในหัวไฟล์ และ TODO ของไฟล์นั้นเอง
   | ไฟล์ | TODO ของตัวเอง |
   |---|---|
   | `n1_model_skeleton.py` | ไม่มี (ใช้ TODO(n1) ใน ilib) |
   | `n2_pd_drop_skeleton.py` | `set_gain_scale` (แก้ Model ต่อ world + notify), จับเวลาล้ม |
   | `n3_vs_mujoco_skeleton.py` | loop ของ Newton, แรง PD แบบ explicit |
   | `n4_speed_solver_skeleton.py` | `throughput`, loop เทียบพารามิเตอร์ |
   | `n5_viewer_skeleton.py` | ไม่มี (อ่าน loop ของ viewer ให้เข้าใจ) |
   | `i1_presets_skeleton.py` | `diff_cfg`, action scale จาก regex |
   | `i2_env_newton_skeleton.py` | เลือก preset, นับชนิด geom, perm, นับ sim.step |
   | `i3_cross_sim_skeleton.py` | เรียก subprocess แล้วอ่าน JSON |
   | `my_terms_isaac_skeleton.py` (I5) | 5 term: gait_phase, base_height, feet_too_close, vx_ema_error, pelvis_too_low |
   | `contract_manager_skeleton.py` (I5) | ObsGroup 7 term, ลงทะเบียน reward ของเรา, DR friction, แทน MDP ใน make_cfg |
   | `i5_manager_terms_skeleton.py` | loop step + สะสม _step_reward, ช่วง index ของ obs |
   | `contract_direct_skeleton.py` (I6) | _setup_scene, _pre_physics_step, obs dict, reward 10 term, dones, reset state |
   | `i6_direct_env_skeleton.py` | loop step (อ่าน u.step_reward) |
   | `i6_compare_skeleton.py` | diff ทีละ term |
   | `i6_train_skeleton.py` | agent cfg, โหลด actor P3b, ประกอบ env + wrapper |
   ลำดับ I5: `my_terms_isaac` → `contract_manager` → `i5_manager_terms` · I6: `contract_direct` → `i6_direct_env` → `i6_compare` → `i6_train`
   (`contract_common_skeleton.py` = ค่าคงที่ ไม่มี TODO · `contract_manager_skeleton` มี TODO ใน class body → import ไม่ผ่านจนกว่าจะเติม)

ไฟล์ที่ยังไม่เติมจะรันไปจนเจอ TODO แรกแล้วหยุดด้วย `NotImplementedError: TODO(...) <คำใบ้>`
ยกเว้น 3 จุดใน ilib ที่มีโค้ดสำรอง (`build_g1` ไม่ตั้ง gain, `joint_table` มีแค่ชื่อ, `capture` ไม่ใช้ graph) ซึ่งรันได้แต่ผลผิด/ช้า

## ส่วนที่ให้ไว้แล้ว (อ่านให้เข้าใจ ไม่ต้องเขียน)
ค่าคงที่ของหุ่น, `joint_params`, `G1Sim.__init__` / `step` / `q` / `base_pos`, `print_table`, เทสต์, ส่วน AppLauncher ของ i2

## ถ้าติด
| อาการ | ดูที่ |
|---|---|
| `ModuleNotFoundError: newton` / `isaaclab` | ยังไม่ได้ `source env.sh` หรือ conda ยังเปิดซ้อน (`which python` ต้องอยู่ใน env_isaaclab) |
| Isaac ค้างตอนเริ่ม ไม่มี output | ไม่ได้ตั้ง `OMNI_KIT_ACCEPT_EULA=YES` (env.sh ตั้งให้) |
| หุ่นทรุดลงทันทีแม้ fixed base | `build_g1` ยังไม่ตั้ง kp/kd หรือ `joint_target_mode` ไม่ใช่ POSITION |
| หุ่นสะบัดตอนเริ่ม | ตั้ง `joint_q` แล้วแต่ไม่ได้ตั้ง `joint_target_pos` (เป้า = 0) |
| `set_target` แล้วไม่มีผล | สร้าง array ใหม่แทนการ `.assign()` ลง array เดิม (graph จำที่อยู่เดิม) |
| แก้ `model.joint_target_ke` แล้วไม่มีผล | ลืม `solver.notify_model_changed(JOINT_DOF_PROPERTIES)` |
| tilt ผิดเพี้ยน (หุ่นตั้งตรงแต่ได้ 180°) | ใช้ quat ลำดับ (w,x,y,z) กับข้อมูล Newton ที่เป็น (x,y,z,w) |
| `assert n % 2 == 0` | ใช้ graph แล้ว step จำนวนคี่ |
| `ResetNeeded` ใน i2 | gym บังคับ `env.reset()` ก่อน `env.step()` |
| `CUDA out of memory` | ลด world / num_envs · ปิด sim ตัวอื่น · session หลักเทรนอยู่ |
| Newton + task Rough → ValueError | Newton ยังไม่รองรับ terrain generator ใช้ `-Flat` |
| `'ProxyArray' ... has no attribute` / คูณกับ tensor ไม่ได้ | ลืม `.torch` หลัง `robot.data.xxx` (Isaac Lab 3) |
| class term: `TypeError ... ManagerTermBase` / ไม่ถูก reset | ต้องสืบทอด `ManagerTermBase` และเรียก `super().__init__(cfg, env)` |
| obs ต่อกันไม่ได้ (shape) | term คืน (N,) แทน (N, 1) → `[:, 2:3]` |
| Direct: `observation_space` ไม่ตรง | ประกาศใน cfg เอง (80 / 84 / 23) ให้ตรงขนาดที่ `_get_observations` คืน |
| Direct: หุ่นไม่ reset / ลอยค้าง | ลืมบวก `env_origins` หรือลืม `write_root_velocity_to_sim_index` |
| เทียบ manager/Direct แล้ว obs ต่างตั้งแต่ reset | ค่าแคชหลัง reset (docs/05 §5) → เริ่มจาก env สด |
| `KeyError: 'class_name'` ใน rsl_rl | ลืม `handle_deprecated_rsl_rl_cfg(cfg, version("rsl-rl-lib"))` (rsl_rl 5) |
