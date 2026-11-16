# โมดูล I: ฉบับสมบูรณ์ (เฉลย)

> โครงให้ฝึกเขียนเองอยู่ใน `../skelatons/` (สร้างจากไฟล์นี้ด้วย `../make_skeletons.py`) · docs อยู่ที่ `../../docs/`
> `source ~/g1_study/weekI_isaaclab/env.sh` ก่อนทุกครั้ง · GPU ว่าง ~1 GB (i4 ใช้มากกว่า) · ไม่แก้ repo หลัก · ไม่ใช้ DDS

| ไฟล์ | งาน | อะไร | Kit? |
|---|---|---|---|
| `ilib.py` | ทั้งหมด | ค่าหุ่น (ลำดับ policy) · build_g1 / joint_table / make_model · G1Sim (CUDA graph) · quat/tilt · เทสต์ 16 ข้อ | ไม่ |
| `n1_model.py` | N1 | MJCF ดิบ vs หลังใส่ค่า · ตาราง joint · Model หลาย world · `--mjcf` MJCF ที่ Newton สร้าง | ไม่ |
| `n2_pd_drop.py` | N2 | gain ต่อ world · ยืน PD ล้วน · sag ตาม gain | ไม่ |
| `n3_vs_mujoco.py` | N3 | Newton vs MuJoCo C · implicit vs explicit PD · frictionloss · `--dt` | ไม่ |
| `n4_speed_solver.py` | N4 | step/s ตาม world, graph vs eager · พารามิเตอร์ solver | ไม่ |
| `n5_viewer.py` | N5 | viewer OpenGL ของ Newton + ลากหุ่น · `--null` ไม่เปิดหน้าต่าง | ไม่ |
| `i1_presets.py` | I1 | PresetCfg · diff physx→newton · ค่า solver · task vs deploy.yaml | ไม่ (import อย่างเดียว) |
| `i2_env_newton.py` | I2 | env จริงบน Newton: manager, Model, ลำดับ joint, gain, sim.step ต่อ env.step, เวลา · `--physx` `--fast-path` `--save-mjcf` | headless |
| `i3_cross_sim.py` | I3 | เรียก `play_deploy_onnx.py` ทั้ง PhysX และ Newton แล้วทำตาราง | headless |
| `i4_train_newton.sh` | I4 | `train.py ... presets=newton` สั้นๆ log ลง `weekI_isaaclab/logs/rsl_rl/` | headless |
| `contract_common.py` | I5/I6 | ค่าร่วม: ลำดับ obs, reward weight, termination, คำสั่ง, scale | - |
| `my_terms_isaac.py` | I5 | gait_phase · base_height · feet_too_close · vx_ema_error (ManagerTermBase) · pelvis_too_low | - |
| `contract_manager.py` | I5 | ObsGroup/Rew/Done/Event cfg + `make_cfg()` แทน MDP ของ task Unitree · register `WeekI-G1-Contract-Manager` | - |
| `i5_manager_terms.py` | I5 | layout obs · term ของเรา · friction DR ใน Newton · ศูนย์ vs P3b ทีละ term · `--dump` `--physx` | headless |
| `contract_direct.py` | I6 | `G1ContractDirectEnv(DirectRLEnv)` + cfg · register `WeekI-G1-Contract-Direct` | - |
| `i6_direct_env.py` | I6 | spaces · index จากชื่อ · ศูนย์ vs P3b (ตารางเดียวกับ I5) · `--dump` | headless |
| `i6_compare.py` | I6 | รัน i5/i6 `--dump` แล้วเทียบ obs/reward/done ทีละ step + จับเวลา (P3b vs ศูนย์) | headless (subprocess) |
| `i6_train.py` | I6 | rsl_rl PPO ประกอบเอง · `--mode manager/direct` · `--init-p3b` | headless |

## รัน
```bash
source ~/g1_study/weekI_isaaclab/env.sh && cd complete
python ilib.py                         # 16/16
python n1_model.py --mjcf
python n2_pd_drop.py
python n3_vs_mujoco.py && python n3_vs_mujoco.py --dt 0.02
python n4_speed_solver.py
python n5_viewer.py                    # เปิดหน้าต่าง
python i1_presets.py
python i2_env_newton.py && python i2_env_newton.py --physx && python i2_env_newton.py --fast-path --num-envs 512 --steps 100
python i3_cross_sim.py                 # ~75 s
bash i4_train_newton.sh newton 256 10
python i5_manager_terms.py --friction-dr 0 0.3
python i6_direct_env.py
python i6_compare.py                   # ~70 s
python i6_train.py --mode direct --num-envs 512 --iters 10
python i6_train.py --mode direct --init-p3b --iters 10
tensorboard --logdir ~/g1_study/weekI_isaaclab/logs/rsl_rl
```

## ผลทดสอบ (13/11/2026, RTX 3060 Laptop 6 GB)
| สคริปต์ | ผล |
|---|---|
| `ilib.py` | 16/16 PASS · skeleton เริ่ม 6/16 |
| `n1` | 24 body / 29 dof / 30 coord · ชน capsule 29 + sphere 2 · MJCF ที่สร้าง: nu 23, ngeom 32, actuator position, actfrcrange ±139 (เข่า) |
| `n2` | ล้ม (s): ×0.25 0.5 · ×0.5 1.2 · ×1 1.2 · ×2 1.4 · ×4 1.8 · ×8 ไม่ล้ม · sag ศอก +0.107/+0.056/+0.028/+0.013/+0.006/+0.003 |
| `n3` dt 0.005 | rise90: A 135 / B 135 / C 140 / D 165 ms · max\|A−B\| 1.8e-3 rad · final err D −0.0077 |
| `n3` dt 0.02 | A, B overshoot 2.1% นิ่ง · C overshoot 45% → unstable (MuJoCo warning NaN) |
| `n4` A | 1 / 16 / 256 / 1024 world: 1.0k / 15.5k / 116k / 178k step/s · graph/eager ×3.1 (16 world) |
| `n4` B | default iters 1.9 ยืน · euler / ls_iterations 2 / dt 0.01 → ล้ม · cg ช้า 4× |
| `n5` | `--null` 100 เฟรม: ×8 ยืน ตัวอื่นล้มที่ ~1.5 s · ViewerGL headless ได้ภาพ |
| `i1` | 3 PresetCfg · 59 field · task vs class default ต่าง 5 ค่า (njmax, nconmax, ls_iterations, integrator, ls_parallel) |
| `i2` | ดูตารางใน docs/README · Newton 4 env 9 ms/step |
| `i3` | PhysX 102/79/72 · Newton 99/73/79 (%) · 42 s + 31 s |
| `i4` | Newton 0.53 s/it · PhysX 0.89 s/it (256 env, หลัง iteration 2) |
| `i5` | ศูนย์: ล้ม 80, รวม +0.48/s · P3b: ล้ม 0, vx 0.448, รวม +1.40/s · `--friction-dr 0 0.3` → Model.joint_friction 0.001–0.300 |
| `i6_direct_env` | ตารางตรงกับ i5 ถึงหลักที่ 3 · find_joints = identity, feet body [6, 12] |
| `i6_compare` | obs step0 7e-7 → step299 2e-4 · reward ≤ 8.4e-5 · done ตรง · 512 env: manager 9.66/16.35 ms, direct 8.73/9.14 ms (P3b/ศูนย์) |
| `i6_train` | 512 env 10 it: direct 0.41 s/it (collection 0.34) · manager 0.45 s/it (0.39) · `--init-p3b` missing/unexpected = 0, Mean reward −0.07 → +1.43, died 0 |
