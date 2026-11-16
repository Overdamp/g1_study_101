# 03: manager ทีละตัว (ของจริงใน env ของเรา)

> path ย่อ: `mjlab/` = `~/miniconda3/envs/unitree_rl_mjlab/lib/python3.11/site-packages/mjlab/` · `repo/` = `~/nvidia/unitree/unitree_rl_mjlab/`

## 1. ObservationManager (`mjlab/managers/observation_manager.py`)
แต่ละ term ผ่านท่อเดียวกัน (บรรทัด 328–361):
```
func(env, **params) → noise → clip → scale → delay → history → ต่อกันเป็นเวกเตอร์ของ group
```
| ขั้น | ของเรา |
|---|---|
| noise | actor: gyro ±0.2, gravity ±0.05, q ±0.01, dq ±1.5 (uniform) · **เปิดเฉพาะ group ที่ `enable_corruption=True`** (actor ตอนเทรน) · critic ไม่มี noise · play ปิดหมด |
| clip / scale | ไม่ใช้ (ยกเว้น height_scan scale 1/5 ใน Rough) → deploy.yaml จึงมี scale 1 ทุกตัว |
| delay | ไม่ใช้ใน obs (delay ไปอยู่ที่ actuator แทน ดูข้อ 2) |
| history | `history_length=1` = ไม่มีประวัติ (repo มี task `hist5` แยก) |

**actor ≠ critic (asymmetric actor-critic):**
| group | ขนาด | ใช้ทำอะไร | มีอะไรเพิ่ม |
|---|---|---|---|
| actor | 80 | policy ที่ deploy ขึ้นหุ่น | เฉพาะที่หุ่นจริงวัดได้: gyro, gravity (จาก IMU), คำสั่ง, phase, q, dq, action ก่อนหน้า |
| critic | 95 | value function ใช้แค่ตอนเทรน | + base_lin_vel 3 · foot_height 2 · foot_air_time 2 · foot_contact 2 · foot_contact_forces 6 (= **privileged**: หุ่นจริงวัดตรงๆ ไม่ได้) |

critic เปลี่ยนขนาดได้โดยไม่กระทบ deploy (ทิ้งตอน export) แต่ resume checkpoint เดิมจะพังที่ `critic mlp.0.weight` (R5)

**phase** (`repo/src/tasks/velocity/mdp/observations.py:47`):
```python
global_phase = (episode_length_buf * step_dt) % period / period      # period 0.6 s
phase = [sin(2π·global_phase), cos(2π·global_phase)]
phase = 0 ถ้า |คำสั่ง| < 0.1                                           # ยืน → ไม่มีจังหวะก้าว
```
นาฬิกานี้ไม่มี state: คำนวณจากเวลาใน episode ตรงๆ ส่วน deploy ใช้ตัวนับที่ `+= dt` ก่อนคำนวณ → step แรกต่างกัน 1 step (R7 วัดได้ 0.209)

## 2. ActionManager + JointPositionAction (`mjlab/managers/action_manager.py`, `mjlab/envs/mdp/actions/actions.py`)
```
process_action(a)   ← ครั้งเดียว/step:  history: prev_prev ← prev ← action ← a (ดิบ)
                                           processed = a × scale + offset          (offset = default_joint_pos)
apply_action()      ← ทุก substep (×4):  target = processed − encoder_bias → set_joint_position_target
                                           → actuator (BuiltinPosition = PD ใน MuJoCo) + DelayedActuator
```
| เรื่อง | ค่า | ที่มา |
|---|---|---|
| scale | `0.25 × effort_limit / kp` ต่อข้อต่อ (hip pitch 0.25 × 88 / 40.2 = 0.547) | `g1_23dof_constants.py:279` |
| offset | ท่า default (เข่า 0.3, ศอก 0.87 ...) | `use_default_offset=True` |
| obs `actions` | action **ดิบ** (ก่อน scale) ของ step ก่อน | `last_action` → `env.action_manager.action` |
| `action_rate_l2` | ‖a − a_prev‖² ใช้ history ที่เก็บไว้ | reward |
| delay | ทุก actuator ห่อด้วย `DelayedActuatorCfg` lag 0–4 physics step (0–20 ms) สุ่มใหม่ทุก episode (event `action_delay` mode reset) | `env_cfgs.py:41–53, 181–188` |
| encoder_bias | สุ่ม ±0.015 rad ตอน startup · **ลบออกจากเป้า PD เท่านั้น obs ไม่เห็น** (`joint_pos_rel` ใช้ `biased=False`) | `actions.py: apply_actions` |

ตรงกับ deploy: `q_des = offset + scale × action` (week4 `action_to_q_des`) · R2 เทียบแล้วตรงทั้ง 23 ตัว

## 3. CommandManager + UniformVelocityCommand (`mjlab/tasks/velocity/mdp/velocity_command.py` ← ตัวที่ใช้จริง)
```
reset(env_ids)   → _resample: สุ่ม vx, vy, wz จาก ranges · ตั้งเวลา time_left ~ U(3, 8) s
                   สุ่มว่า env นี้เป็น "standing" (5%) และ "heading" (100%)
compute(dt)      → time_left −= dt · หมดเวลา → สุ่มใหม่ · แล้ว _update_command:
                   heading env: wz = clip(0.5 × wrap(heading_target − heading), ranges.ang_vel_z)
                   standing env: คำสั่ง = 0
```
- `rel_heading_envs = 1.0` → **wz ของทุก env มาจากตัวคุม heading** ranges ของ `ang_vel_z` ใช้แค่ clip
- `get_command("twist")` = `vel_command_b` (N, 3) = obs `command` ที่ policy เห็น
- metrics `error_vel_xy`, `error_vel_yaw` → TensorBoard `Metrics/twist/...`
- R4 / R7 ใช้ `fix_command()` ปิด heading, standing, curriculum เพื่อให้คำสั่งคงที่

## 4. RewardManager (`mjlab/managers/reward_manager.py`)
```python
for term:                                  # บรรทัด 257–268
    if weight == 0: continue               # weight 0 = ข้าม (ไม่คำนวณ)
    value = func(env, **params) * weight * dt        # dt = step_dt = 0.02
    value = nan_to_num(value)
    reward_buf += value
    episode_sums[name] += value
    _step_reward[:, i] = value / dt         # ค่า "ต่อวินาที" ไว้แสดงผล
```
แปลง 3 หน่วยให้คล่อง (R4):
| ชื่อ | สูตร | ใช้ที่ |
|---|---|---|
| ต่อ step | func × w × 0.02 | `reward_buf` → PPO |
| ต่อวินาที | func × w | `_step_reward`, ตาราง R4 |
| Episode_Reward/x | Σ(ต่อ step ทั้ง episode) ÷ **20 s** | TensorBoard (บรรทัด 246) |

ถ้าเดินครบ 20 s ด้วย func เฉลี่ย 0.85 → Episode_Reward ≈ 0.85 · ถ้าล้มที่ 2 s → ≈ 0.085 (ไม่ใช่ว่าเดินแย่ลง 10 เท่า แค่ episode สั้น)

term ที่ต้องรู้จัก (week5 `rewards.md` มีครบ 16 ตัว):
- `track_linear_velocity` = `exp(−(‖v_cmd,xy − v_xy‖² + 2·v_z²) / std²)` std² = 0.25 → อยู่ในช่วง (0, 1]
- `is_terminated` w −200 = `termination_manager.terminated` (**ล้มเท่านั้น** หมดเวลาไม่โดน) → ล้ม 1 ครั้ง = −200 × 0.02 = −4 ต่อ step นั้น
- `pose` (class `variable_posture`) std ต่างกันตอนยืน/เดิน/วิ่ง ตามขนาดคำสั่ง

## 5. TerminationManager (`mjlab/managers/termination_manager.py`)
| term | func | time_out | ความหมายกับ PPO |
|---|---|---|---|
| `time_out` | `episode_length_buf >= 1000` | **True** → `truncated` | ไม่ได้ "แพ้" แค่ตัดเวลา → PPO bootstrap ค่า V(s') ต่อ (ถือว่าอนาคตยังมี) |
| `fell_over` | `acos(−g_z) > 70°` | False → `terminated` | จบจริง อนาคต = 0 + โดน `is_terminated` |

`env.step()` คืนทั้งสองแยกกัน → `RslRlVecEnvWrapper` รวมเป็น `dones` และใส่ `extras["time_outs"]` ให้ PPO แยก bootstrap
log: `Episode_Termination/fell_over` = จำนวน env ที่จบเพราะล้มในรอบ reset นั้น

## 6. EventManager (`mjlab/managers/event_manager.py`)
| mode | เมื่อไร | ของเรา |
|---|---|---|
| `startup` | ครั้งเดียวหลังสร้าง manager | DR 9 ตัว: foot_friction 0.3–1.6 · encoder_bias ±0.015 · base_com ±5 cm · torso_mass +(−1..3.5) kg · limb_mass ×0.9–1.1 · joint_friction 0–0.3 · joint_damping 0–0.1 · pd_gains ×0.85–1.15 · effort_limits ×0.85–1.05 |
| `reset` | ทุกครั้งที่ env นั้น reset | reset_base (x, y ±0.5 m, yaw ±π) · reset_robot_joints (offset 0 = ท่า default) · action_delay (lag 0–4) |
| `interval` | นับถอยหลังต่อ env, สุ่มช่วง 5–6 s | push_robot (เปลี่ยนความเร็ว ±0.5 m/s, ±0.52 rad/s) |
| `step` | ทุก step | (ไม่ใช้) |

- startup สุ่ม **ต่อ env** (ต่อ "world" ของ mujoco_warp) ค่าเก็บใน `env.sim.model.<field>` ที่มีมิติแรก = num_envs หลัง `expand_model_fields` (R6 พิมพ์ให้ดู) → env 4096 ตัว = หุ่น 4096 แบบ ไปพร้อมกัน
- startup ไม่สุ่มใหม่ตลอดการเทรน (ต่อให้ reset) · reset events สุ่มทุก episode
- interval: event เขียนความเร็วลง sim **หลัง** step นั้นคำนวณ obs/reward แล้ว → เห็นผลใน step ถัดไป (R6)
- ค่าใน XML ของ mjlab: frictionloss = 0, damping = 0 (unitree_mujoco = 0.2, 0.05) → DR ครอบค่า sim2sim แต่ไม่ได้อยู่ตรงกลาง

## 7. CurriculumManager (`mjlab/managers/curriculum_manager.py`, `repo/src/tasks/velocity/mdp/curriculums.py`)
เรียก**ตอน reset** (บรรทัดแรกของ `_reset_idx`) ไม่ใช่ทุก step
| term | ทำอะไร | ดูอะไร |
|---|---|---|
| `command_vel` | เปลี่ยน `ranges` ของคำสั่งตาม stage | `env.common_step_counter > stage["step"]` |
| `terrain_levels` (Rough/Blind) | เดินได้ > ครึ่งความยาวแปลง → ขึ้นแปลงยาก · ได้ < ครึ่งของระยะที่คำสั่งต้องการ → ลง | ระยะที่เดินได้ใน episode นั้น |

`common_step_counter` นับ **env step** (ไม่คูณ num_envs) และ runner เก็บ 24 step/iteration → `"step": 5000 * 24` = iteration 5000 · checkpoint P3b เก็บ counter 384024 = 16001 × 24 (ดู `infos.env_state`) → resume แล้ว curriculum ไม่เริ่มใหม่

stage แรก `"step": 0` ใช้ `>` → ที่ counter 0 ยังไม่เข้า stage แรก คำสั่งชุดแรกจึงมาจาก ranges ตั้งต้น (−1..2) (R6)

## 8. MetricsManager
log อย่างเดียว ไม่กระทบการเรียนรู้: `mean_action_acc` → `Metrics/...` · term บางตัวก็เขียน `env.extras["log"]` เอง (เช่น `angular_momentum_penalty`)

## คำถามเช็ค
1. noise ของ joint_vel ±1.5 rad/s ใส่ใน critic ด้วยไหม ทำไมออกแบบแบบนั้น
2. `time_out` กับ `fell_over` ทำให้ PPO คำนวณ target ของ value ต่างกันยังไง
3. curriculum `command_vel` จะทำงานกี่ครั้งต่อ iteration
4. Episode_Reward/track_linear_velocity = 0.45 · ถ้า episode เฉลี่ยยาว 10 s แปลว่า func เฉลี่ยประมาณเท่าไร
