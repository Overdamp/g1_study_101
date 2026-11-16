# โมดูล I: Isaac Lab 3.0 + Newton (ส่วนเสริม)

> เป้าหมาย: เข้าใจว่า Newton คืออะไร ใช้เองได้แบบไม่ผ่าน Isaac Lab, รู้ว่า Isaac Lab ต่อกับ Newton ยังไง,
> ตรวจได้เองว่า policy จาก mjlab เดินใน engine อื่นได้เท่ากันไหม (cross-sim) · และเขียน task ของ Isaac Lab เองได้ทั้งแบบ manager-based และ Direct (I5–I6)
> ต่อจากโมดูล R (mjlab) และ M (MuJoCo)

## เตรียม
```bash
source ~/g1_study/weekI_isaaclab/env.sh      # conda deactivate + source env_isaaclab + OMNI_KIT_ACCEPT_EULA=YES
cd skelatons                                  # (หรือ complete/ ถ้าจะดูเฉลย)
python ilib_skeleton.py                       # ตอนเริ่ม PASS 6/16
nvidia-smi                                    # GPU ว่างไหม (session งานหลักเทรนอยู่ = รอ)
```
- env: `~/nvidia/IsaacLab-unitree/env_isaaclab` (Isaac Lab 3.0, Isaac Sim 6.0, newton 1.2.0, mujoco 3.8.1) ← env เดียวกับที่ session งานหลักใช้ทำ cross-sim
- ไม่แก้ repo หลัก: import `unitree_rl_lab` / เรียก `play_deploy_onnx.py`, `train.py` แบบอ่านอย่างเดียว · log ลง `weekI_isaaclab/logs/`
- ไม่ใช้ DDS ไม่แตะหุ่นจริง · **ห้าม `uv sync` ใน env_isaaclab** (isaacsim หาย)
- n1–n5 = Newton ล้วน (เปิดเร็ว ~3 s) · i1 ไม่เปิด Kit (~5 s) · i2–i4 เปิด Isaac Sim แบบ headless (~25 s ต่อครั้ง)

## ลำดับอ่าน/ทำ
| # | อ่าน | ทำ | ได้อะไร |
|---|---|---|---|
| I0 | `01_big_picture.md` | - | Newton / MuJoCo Warp / PhysX / Isaac Lab อยู่ชั้นไหน |
| N1 | `02_newton_core.md` §1–2, §4 | ilib TODO(n1) → `n1_model` | MJCF → Model · joint_q layout · quat xyzw · Newton สร้าง MuJoCo actuator แบบไหน |
| N2 | `02` §1, §3, §6 | ilib TODO(n2) → `n2_pd_drop` | world · แก้ gain ต่อ world · CUDA graph · PD ล้วนยืนได้ไหม |
| N3 | `02` §4 | `n3_vs_mujoco` | Newton GPU vs MuJoCo C · implicit vs explicit PD · frictionloss |
| N4 | `02` §5–6 | `n4_speed_solver` | throughput vs world · พารามิเตอร์ solver ตัวไหนสำคัญ |
| N5 | - | `n5_viewer` | ดูด้วยตา ลากหุ่นด้วยเมาส์ |
| I1 | `03_isaaclab_newton.md` §1–2 | `i1_presets` | preset PhysX↔Newton · ค่า solver ของ task · task Isaac vs deploy.yaml |
| I2 | `03` §3–7 | `i2_env_newton` (+ `--physx`, `--fast-path`) | NewtonManager · ลำดับ joint · gain ใน sim · decimation ใน graph |
| I3 | `04_cross_sim_training.md` §1–3 | `i3_cross_sim` | v0 เดินใน PhysX/Newton กี่ % เทียบ MuJoCo |
| I4 | `04` §4 | `i4_train_newton.sh` | เทรนบน Newton จริง (สั้นๆ) · อ่าน log |
| I5 | `05_manager_vs_direct.md` §1–2 | `my_terms_isaac` + `contract_manager` → `i5_manager_terms` | task manager ของเราเอง: obs ตรง deploy (gait_phase เขียนเอง), reward/termination/class term, DR frictionloss → P3b เดินจาก obs ของ env |
| I6 | `05` §3–6 | `contract_direct` → `i6_direct_env` → `i6_compare` → `i6_train` | task เดียวกันแบบ Direct · เทียบทีละ term ว่าเท่ากัน · เวลา · เทรน/fine-tune P3b ด้วย rsl_rl |

## ผลที่ควรได้ (complete/, RTX 3060 Laptop, 13/11/2026)
| งาน | ผล |
|---|---|
| ilib | 16/16 PASS (~40 s ครั้งแรก) |
| N1 | body 24 · joint 24 · dof 29 · coord 30 · เข่าซ้าย q_start 10 / qd_start 9 · ชน: capsule 29 + sphere 2 · actuator position gain 99.098 bias [0, −99.098, −6.309] · actfrcrange ±139 |
| N2 | gain ×0.25–×4 ล้มใน 0.5–1.8 s · **×8 ยืนครบ 3 s** (z 0.782) · sag ศอก ×1 = +0.028 rad, ∝ 1/gain (แรงบิดน้ำหนัก ~0.36 N·m) |
| N3 | dt 0.005: A กับ B เท่ากัน (rise 135 ms), explicit 140 ms, + frictionloss 165 ms final err −0.008 · **dt 0.02: implicit นิ่ง, explicit overshoot 45% แล้ว NaN** |
| N4 | 1 world 1.0k step/s → 1024 world 178k (×890 เวลาจริง) · graph เร็วกว่า eager ×2.5–3.6 · ล้มเมื่อ: euler, ls_iterations 2, dt 0.01 |
| I1 | PresetCfg 3 จุด · physx→newton ต่าง 59 field · task ตั้ง implicitfast (คลาส default = euler) · obs Isaac 6 term × history 5 ≠ deploy 7 term · scale ต่าง 0.0025 (ปัดเศษ) |
| I2 | Newton: ลำดับ joint = policy (PhysX = BFS) · kp ต่าง < 2e-6 · sim.step ×4/env.step (fast-path ×1) · 512 env: Newton 24k, fast-path 26k, PhysX 16.7k env-step/s · USD ชน: convex mesh 20 + cylinder 4 + sphere 8 |
| I3 | v0 vx 0.4 / 0.8 / wz 0.5: PhysX 102 / 79 / 72 % · Newton 99 / 73 / 79 % · MuJoCo (vault) 97 / 74 / 69–73 % · ไม่ล้ม |
| I4 | 256 env: Newton 0.53 s/iteration · PhysX 0.89 s |
| I5 | obs policy 80 ลำดับ = deploy.yaml · critic 84 · P3b ไม่ล้ม vx 0.448 (PhysX 0.486) ที่คำสั่ง 0.5 · action ศูนย์ล้ม 80 ครั้ง · friction DR ใน Newton Model 0.001–0.300 N·m |
| I6 | Direct = manager: obs ต่าง ≤ 7e-7 ที่ step 0, reward ทุก term ≤ 8e-5, done ตรงทุก step · 512 env: ไม่มี reset 8.7 vs 9.7 ms, reset เยอะ 9.1 vs 16.4 ms · เทรน 512 env: 0.39–0.47 s/it · `--init-p3b` ไม่ล้มเลย Mean reward −0.07 → +1.43 ใน 10 it |

## สิ่งที่เจอระหว่างเขียน (findings)
1. **Isaac Lab + Newton ใช้ MuJoCo Warp ตัวเดียวกับ mjlab** · ที่ต่างคือโมเดล: USD (convex mesh) vs MJCF (capsule), ค่า solver
2. **ลำดับ joint ของ Newton = DFS = ลำดับ policy** แต่ PhysX = BFS → โค้ด deploy/cross-sim ต้อง map ด้วยชื่อเสมอ
3. **`MJWarpSolverCfg()` ค่าเริ่ม integrator = euler** · task ของ Unitree ตั้ง implicitfast ไว้ · task ใหม่ลืมตั้ง = PD gain สูงไม่เสถียร
4. Newton เก็บ quaternion เป็น **(x, y, z, w)** · Isaac Lab API แปลงให้แล้ว แต่ใช้ Newton ตรงต้องระวัง
5. PD ของ Newton = actuator `position` ของ MuJoCo (implicit ใน implicitfast) · ไม่ตั้ง effort limit = ±1e6
6. `opt.timestep` ใน MJCF ที่ save ไว้เป็น 0.002 แต่ Newton เขียน dt จริงทับทุก step → เอา XML ไปรันเองต้องตั้ง timestep เอง
7. fast path (`sim.use_newton_actuators=True`) ย้าย decimation เข้า CUDA graph: sim.step 4 → 1 ครั้ง, เร็วขึ้น ~10%
8. deploy.yaml เก็บ action scale ปัด 2 ตำแหน่ง (0.55 vs 0.5475) · ต่าง 0.0025 = ~0.5% ไม่มีผลจริง แต่ควรรู้ว่ามาจากไหน
9. **manager vs Direct ให้ MDP เดียวกันได้ถึง float32** · Direct เร็วกว่า ~10% ตอน step ปกติ แต่ ~1.8× ตอน reset เยอะ (ต้นทุนของ manager อยู่ที่ reset)
10. ⚠ **ค่าแคชหลัง reset**: `projected_gravity_b`, `root_*_vel_b` ยังเป็นค่าก่อน reset จนกว่าจะ step ถัดไป (joint/root_pos สดแล้ว) → obs เฟรมแรกหลัง reset ปนค่าเก่า ทั้ง manager และ Direct
11. Isaac Lab 3: ข้อมูลหุ่นเป็น warp array ต้อง `.torch` · class term ต้องสืบทอด `ManagerTermBase` · G1 USD ไม่มี site เท้า ใช้ body `*_ankle_roll_link`
12. obs ตรงสัญญา deploy = เอา P3b ไป fine-tune ใน Isaac/Newton ได้ (actor โหลดตรง, critic ใหม่)

## เช็คลิสต์จบโมดูล
- [ ] อธิบาย Model / State / Control / Solver ด้วยคำตัวเอง และบอกว่าค่า kp อยู่ object ไหน
- [ ] หาช่องของมุมเข่าขวา world 5 ใน `joint_q` ได้โดยไม่รันโค้ด
- [ ] อธิบายว่าทำไม explicit PD ที่ dt 0.02 พัง แต่ implicit ไม่พัง
- [ ] สลับ PhysX ↔ Newton ได้ทั้งจาก CLI และจากโค้ด
- [ ] บอกได้ว่า 1 env.step ของ Isaac Lab บน Newton เรียกฟิสิกส์กี่ครั้ง และเมื่อไรเหลือ 1
- [ ] รัน cross-sim แล้วอ่านผลเทียบเกณฑ์ ±8 pp ได้
- [ ] บอกได้ 3 อย่างที่ต้องแก้ ถ้าจะเทรนใน Isaac แล้ว deploy ด้วย g1_ctrl เดิม
- [ ] เขียน obs/reward/termination/class term ของ Isaac Lab เองได้ และแทน MDP ของ task ที่มีอยู่ด้วย config
- [ ] เขียน DirectRLEnv ครบ 6 method และบอกลำดับที่ DirectRLEnv.step เรียก
- [ ] อธิบายได้ว่าเมื่อไรเลือก manager เมื่อไรเลือก Direct โดยอ้างตัวเลขจาก I6

## คำถามทวน
1. SolverMuJoCo กับ mjlab ต่างกันตรงไหน ถ้าคณิตเหมือนกัน
2. ทำไม `capture()` ต้องบันทึก 2 step
3. ลืม `notify_model_changed` หลังแก้ `model.joint_target_ke` จะเกิดอะไร
4. Newton ไม่รองรับ terrain generator: ถ้าอยากเทรน stairs ใน Isaac ใช้ทางไหน
5. ผล cross-sim Newton 79% แต่ MuJoCo 69–73% ในการหมุน: อะไรต่างกันได้บ้าง (ไล่จาก checklist ใน 04)
6. ทำไม P3b เดินใน contract task ได้ แต่เดินใน task Isaac ของ Unitree ไม่ได้
7. obs เฟรมแรกหลัง reset ของ Isaac Lab มีค่าอะไรที่ยังเก่า และทำไม

## ดูเพิ่ม
- vault: `03 Training and Sim/Cross-Sim Isaac Lab.md`, `06 my_note/g1_23_dof isaaclab_sim cmd.md`, `Environments Map.md`
- โค้ด: `~/nvidia/IsaacLab-unitree/source/isaaclab_newton/isaaclab_newton/physics/newton_manager.py` · Newton: `env_isaaclab/lib/python3.12/site-packages/newton/examples/robot/example_robot_g1.py`
- ดู policy ใน viewer ของ Newton: `python ~/nvidia/unitree/unitree_rl_lab/scripts/play_deploy_onnx.py --visualizer newton --policy-dir <v0> --cases "0.4,0,0" --walk 30 presets=newton`
