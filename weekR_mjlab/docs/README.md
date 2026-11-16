# โมดูล R (เสริม): mjlab แบบ manager-based ตั้งแต่ config ถึงเทรน

> **เป้าหมาย:** เปิด `env_cfgs.py` แล้วอ่านออกว่าแต่ละบรรทัดไปเปลี่ยนอะไรตอนเทรน · เพิ่ม/ลบ term เองได้ · รู้ว่า `train.py` ประกอบอะไรบ้าง
> **ต่อยอดจาก:** week4 (obs 80 / action 23 / deploy.yaml) · week5 (reward, CLI override, resume P3b) · weekM (MuJoCo: qpos, sensor lag, timestep)
> **ห้ามแก้ repo หลัก** (`~/nvidia/unitree/unitree_rl_mjlab`) ทุกอย่างในโมดูลนี้ import มาใช้แล้วแก้ config ในไฟล์ของเราเอง

## เตรียมเครื่อง
```bash
conda activate unitree_rl_mjlab            # มี mjlab 1.x, torch, rsl_rl (env g1_sdk ไม่มี)
cd ~/g1_study/weekR_mjlab/scripts/skelatons
python rlib_skeleton.py                    # เทสต์ 18 ข้อ · ตอนเริ่ม PASS 2
```
- ต้องมี **GPU ว่าง ~1 GB** (env ใช้ mujoco_warp บน GPU) ถ้า session งานหลักกำลังเทรนอยู่ ให้รอก่อน (เช็ค `nvidia-smi`)
- สร้าง env ครั้งละ ~2–5 วินาที (ครั้งแรกนานกว่าเพราะ compile kernel)
- ไม่ใช้ DDS ไม่ชนกับ sim ที่เปิดอยู่

## โน้ตในโฟลเดอร์นี้ (อ่านตามลำดับ)
| ไฟล์ | อ่านก่อนงาน | เรื่อง |
|---|---|---|
| `01_big_picture.md` | R1 | manager-based คืออะไร · term = func + params · 8 manager · ภาพรวม 1 step |
| `02_config_layers.md` | R1, R5 | config 3 ชั้น (factory → G1 → Flat/Blind) · registry · CLI override · กับดัก import |
| `03_managers.md` | R2–R6 | manager ทีละตัว: obs pipeline, action, command, reward ×dt, termination, event/DR, curriculum |
| `04_writing_terms.md` | R5 | เขียน term เอง: signature, SceneEntityCfg, entity data API, term แบบ class |
| `05_training_loop.md` | R7, R8 | runner + PPO 1 iteration · checkpoint มีอะไร · export ONNX · ไปถึง deploy ยังไง |

## งาน
| งาน | ไฟล์ (skeleton) | ทำอะไร | ได้ความเข้าใจ |
|---|---|---|---|
| **R0** | (อ่าน) | อ่าน `01` + `02` แล้วเปิด `velocity_env_cfg.py` กับ `env_cfgs.py` ไล่ตามทีละ dict | แผนที่ของ config |
| **R1** | `r1_cfg_tree` | พิมพ์ต้นไม้ term ของ task · `--where` บอกไฟล์:บรรทัดของทุก func · `--diff` Flat vs Blind · `--base` | config = dict ของ term · 3 ชั้น |
| **R2** | `r2_build_env` | สร้าง env จริง: ลำดับสร้าง manager · ช่วง index ของ obs 80/95 · scale/offset เทียบ deploy.yaml | config → manager → ขนาดเวกเตอร์ |
| **R3** | `r3_step_trace` | ดักการเรียกใน `env.step()` · `--reset` ดูตอน env หมดเวลา | decimation, ลำดับ reward/obs, reset กลาง step |
| **R4** | `r4_reward_probe` | reward ทีละ term: action ศูนย์ vs P3b · ตรวจ Σ×dt = reward_buf | reward ×weight×dt · term ไหนชนะ |
| **R5** | `r5_custom_terms` + `my_terms` | เพิ่ม obs/reward/termination ของเราเอง · ลบ/ปิด 3 แบบ · `--actor-obs` · `--rough` | เขียน term เอง · ทำไม resume พังเมื่อ obs เปลี่ยน |
| **R6** | `r6_events_curriculum` | ดูค่าที่ DR สุ่มให้แต่ละ env · reset · push · curriculum ตาม counter | event 4 mode · curriculum ดู step ไม่ใช่ iteration |
| **R7** | `r7_policy_vs_deploy` | สร้าง obs แบบ deploy (week4 `obs.py`) จากสถานะ env → เทียบกับ obs ของ env ทีละ term | sim ↔ deploy ตรงกันไหม |
| **R8** | `r8_mini_train` | ประกอบ `train.py` เอง: env → wrapper → runner → learn · `--resume` · `--weight` | training loop ทั้งหมด |
| R9 (เลือก) | — | ใช้ R5 + R8: เพิ่ม reward ของเรา แล้วเทรนต่อจาก P3b 50 iteration เทียบกราฟกับ run ควบคุม (แบบ week5) | ออกแบบการทดลองเอง |

แต่ละไฟล์มี **"ทายก่อนรัน"** ที่หัวไฟล์ จดคำตอบไว้ก่อนรัน แล้วค่อยเทียบ

### TODO → เทสต์ใน `rlib_skeleton.py`
| TODO | งาน | เทสต์ที่จะผ่าน |
|---|---|---|
| `cfg_summary`, `diff_cfg` | R1 | 6 ข้อ |
| `term_slices` | R2 | 3 ข้อ |
| `StepTracer._wrap`, `__exit__` | R3 | 4 ข้อ |
| `fix_command`, `manual_reward` | R4 | 2 ข้อ |
| `ActorMLP.__call__` | R7 | 1 ข้อ |
| (ให้ไว้แล้ว) `compress`, `ActorMLP.__init__` | — | 2 ข้อ (PASS ตั้งแต่แรก) |

## ผลจริงที่ควรได้ (รันเฉลย 13/11/2026 · RTX 3060 Laptop · mujoco 3.5 / mujoco_warp)
| งาน | ผล |
|---|---|
| R1 | Flat: actor 7 term · critic 12 · reward 16 · event 13 (startup 9, reset 3, interval 1) · Flat vs Blind ต่างแค่ 2 แถว: `terrain_levels` + `track_linear_velocity` w 1 → 2 (obs เหมือนกันทุกตัว) |
| R2 | สร้าง manager ตามลำดับ event → command → action → observation → termination → reward → curriculum → metrics · actor [0,3) gyro … [57,80) actions · scale ตรง deploy.yaml ทั้ง 23 ตัว (0.25 × effort / kp) |
| R3 | process_action ×1 → (apply_action → sim.step) ×4 → termination → reward → [curriculum → event(reset)] → forward → command → event(interval) → sense → observation |
| R4 | vx 0.5: action ศูนย์ล้ม 46 ครั้งใน 5 s × 16 env, is_terminated −2.3/s · P3b ไม่ล้ม, vx จริง 0.39, reward +3.0/s · Σ×dt − reward_buf < 1e-6 |
| R5 | critic 95 → 96 (P3b ยังใช้ได้) · actor 81 → shape mismatch · Rough actor = 267 (height_scan 187 = 17 × 11) |
| R6 | torso 7.2–10.9 kg · foot friction 0.9–1.3 · knee frictionloss ใน XML ของ mjlab = **0** (unitree_mujoco = 0.2) · push ครั้งแรก ~5.2 s · counter 0 → ranges (−1, 2), 1 → (−0.5, 1.0) |
| R7 | obs ทุก term ตรงกัน < 2e-7 **ยกเว้น phase** ต่างสูงสุด 0.209 = deploy นำ 1 step |
| R8 | 256 env ~0.9 s/iteration · เริ่มจากศูนย์ Mean reward ติดลบ · resume P3b เริ่มที่ iteration 15998 reward บวก |

## สิ่งที่เจอระหว่างเขียนโมดูลนี้ (ใช้ตรวจตอนทาย)
1. **คลาสคำสั่งความเร็วที่ใช้ตอนเทรนมาจาก mjlab ไม่ใช่ repo:** `velocity_env_cfg.py:27` import `UniformVelocityCommandCfg` จาก `mjlab.tasks.velocity.mdp` บรรทัด `*= norm > 0.1` ที่ repo เพิ่มใน `src/tasks/velocity/mdp/velocity_command.py:77` จึง**ไม่ถูกใช้** (`self_collision_cost` ก็มาจาก mjlab เพราะ `env_cfgs.py:19` import `mdp` ของ mjlab) → R1 `--where` เห็นได้
2. **heading_command = True + rel_heading_envs = 1.0:** ทุก env ได้ `ang_vel_z` จาก `0.5 × heading error` ไม่ได้มาจาก ranges ของ `ang_vel_z` ตรงๆ (ranges ใช้แค่ clip)
3. **phase เหลื่อม 1 step ระหว่างเทรนกับ deploy:** env ใช้ `episode_length_buf × dt` (step แรก = 0) ส่วน deploy (ตาม week4 `obs.py` ที่เลียน C++) เดินนาฬิกาก่อนคำนวณ (step แรก = dt) → 3.3% ของคาบ ผลน่าจะน้อย แต่เป็น mismatch จริง
4. **encoder_bias ไม่เข้า obs:** `joint_pos_rel` ใช้ `biased=False` (ค่าจริง) bias ไปกระทบแค่เป้า PD (`target − bias` ใน `JointPositionAction.apply_actions`)
5. **Episode_Reward/… หารด้วย 20 s เสมอ** (`reward_manager.py:246`) แม้ episode จบที่ 1 s → ล้มเร็ว = ค่าเล็ก ไม่ได้แปลว่า reward ต่อวินาทีเล็ก
6. **frictionloss / damping ใน XML ของ mjlab = 0** ส่วน DR สุ่ม 0–0.3 / 0–0.1 · unitree_mujoco ใช้ 0.2 / 0.05 คงที่ (ดู weekM M5) → อยู่ในช่วง DR แต่ไม่ใช่ค่ากลาง
7. **curriculum ใช้ `counter > step`:** ที่ counter = 0 ยังไม่เข้า stage แรก → คำสั่งชุดแรกสุ่มจาก ranges ตั้งต้น (−1..2 m/s) จน env นั้น reset ครั้งแรก

## เช็คลิสต์จบโมดูล
- [ ] อธิบายได้ว่า "เพิ่ม term ใน dict" แล้วไปโผล่ใน obs/reward ได้ยังไง (manager วน dict ตอน `_prepare_terms`)
- [ ] วาดลำดับใน `env.step()` ได้โดยไม่ดูโน้ต และบอกได้ว่าทำไม obs คำนวณหลัง reset
- [ ] บอกได้ว่า term ไหนเปลี่ยนแล้ว resume P3b ได้ / ไม่ได้ / ได้แต่ deploy ไม่ได้
- [ ] อ่าน `Episode_Reward/track_linear_velocity = 0.8` ใน TensorBoard แล้วแปลงเป็นค่าต่อ step ได้
- [ ] เขียน reward term ใหม่ 1 ตัวเอง ทดสอบใน R5 แล้ว
- [ ] สรุปด้วยคำของตัวเอง 5 บรรทัด: "ตั้งแต่พิมพ์ `python scripts/train.py ...` จนได้ `policy.onnx` เกิดอะไรบ้าง"

## คำถามทวน (ตอบโดยไม่เปิดโน้ต)
1. `decimation = 4`, `timestep = 0.005`: policy กี่ Hz · ใน 1 env step `apply_action` ถูกเรียกกี่ครั้ง · q_des เปลี่ยนไหมระหว่างนั้น
2. reward term `foot_clearance` weight −1 ได้ค่า func = 0.07 ต่อ step: `reward_buf` ได้เท่าไรจาก term นี้
3. ทำไม critic ใส่ `base_lin_vel` ได้ แต่ actor ใส่ไม่ได้
4. event `startup` กับ `reset` ต่างกันยังไง · `motor_pd_gains` เป็นแบบไหน แปลว่าอะไรกับ policy
5. `--env.rewards.track_linear_velocity.weight 2.0` ใน CLI ไปแก้ค่าที่ไหนก่อนสร้าง env
