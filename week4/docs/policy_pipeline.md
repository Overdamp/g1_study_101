# Policy pipeline: ภาพรวม

## วงจรเต็ม
```
                  ┌──────────────── ทุก 20 ms (50 Hz) : policy thread ────────────────┐
rt/lowstate ──▶  robot->update()  ──▶  obs (80)  ──▶  policy.onnx  ──▶  action (23)  ──▶  q_des = offset + scale × action
 (~1 kHz)        q, dq, gyro, quat     ต่อ 7 term      normalizer+MLP     ค่าดิบ            (processed_actions)
                                                                                                │
                  ┌──────────────── ทุก 1 ms (1 kHz) : FSM thread ──────────────────────┐        │
                  State_RLBase::run():  q คำสั่ง = q_start + α·(q_des − q_start)  ◀──────────────┘
                  (α: 0 → 1 ใน 0.5 s = Soft Start)
                  post_run(): ส่ง rt/lowcmd (q, kp, kd จาก deploy.yaml) + CRC
                                                                                        │
มอเตอร์ / sim:    tau = kp·(q − q_now) + kd·(0 − dq_now)   ◀────────────────────────────────┘
```

**จุดสำคัญ:** policy ไม่ได้คุมแรงบิดเอง มันแค่บอก "เป้าหมาย" ทุก 20 ms ส่วน PD ทำงานถี่กว่ามาก ระหว่าง step ของ policy, lowcmd จะส่ง `q_des` ค่าเดิมซ้ำประมาณ 20 ครั้ง

## ความถี่ (vault `Timing and Rates.md`)
| อะไร | ความถี่ |
|---|---|
| policy (`step_dt` ใน deploy.yaml) | 50 Hz |
| physics ตอนเทรน (mjlab) | 200 Hz (decimation 4) |
| FSM thread ของ g1_ctrl | 1 kHz |
| `unitree_mujoco` physics | 500 Hz |
| `rt/lowstate` | sim ~905 Hz (งาน 1.3) / หุ่นจริง ~1000 Hz |

policy เทรนมาที่ 50 Hz เวลา deploy จึงต้องเรียกที่ 50 Hz ด้วย (`gait_phase` และ `last_action` ผูกกับจังหวะนี้) → งาน 4.8 (จ)

## ใน g1_ctrl มี 2 thread ทำงานใน state Velocity
| thread | ไฟล์ | ทำอะไร |
|---|---|---|
| policy thread | `deploy/include/FSM/State_RLBase.h` `enter()` | `env->reset()` แล้ววน `env->step()` ทุก `step_dt` ด้วย `sleep_until` |
| FSM thread (1 kHz) | `deploy/robots/g1_23dof/src/State_RLBase.cpp` `run()` | อ่าน `processed_actions()` ล่าสุด → soft start → ใส่ลง lowcmd |

`env->step()` (`deploy/include/isaaclab/envs/manager_based_rl_env.h`):
```cpp
episode_length += 1;
robot->update();                              // อ่าน lowstate → joint_pos, joint_vel, gyro, gravity
auto obs = observation_manager->compute();    // ต่อ term ตาม deploy.yaml
auto action = alg->act(obs);                  // ONNX
action_manager->process_action(action);       // scale + offset (+ clip, EMA ถ้าตั้งไว้)
```

ใน Python (งาน 4.4/4.7) ทำโครงเดียวกันได้: thread หนึ่งเก็บ lowstate (สัปดาห์ 1) และ loop 50 Hz อีกตัวสร้าง obs → ONNX → q_des

## ไฟล์ของ policy หนึ่งตัว (vault `Deploy Contract.md`)
```
deploy/robots/g1_23dof/config/policy/velocity/v0/
├── exported/policy.onnx     ← เครือข่าย + metadata (ชื่อข้อต่อ, gain, scale, ลำดับ obs)
├── params/deploy.yaml       ← สิ่งที่ g1_ctrl ใช้จริง: joint_ids_map, gain, default pose, scale, obs terms
└── checkpoints/*.pt         ← (ไว้เทรนต่อ ไม่ได้ใช้ตอน deploy)
```
g1_ctrl ใช้ค่าจาก **`deploy.yaml`** เท่านั้น ไม่ได้อ่าน metadata ใน ONNX ถ้าสองที่นี้ไม่ตรงกัน ตัวที่ใช้จริงคือ deploy.yaml → งาน 4.1

## Soft Start (vault `Soft Start.md`)
step แรกของ policy อาจสั่งเป้าห่างจากท่า FixStand มาก (history ว่าง, `last_action` = 0) จึงผสมค่า:
```
q คำสั่ง = q_start + α·(q_des − q_start),   α = min(1, เวลาที่ผ่านไป / 0.5 s)
```
ตอนทำ shadow mode (4.4) ให้เทียบ**หลัง** 0.5 s แรกเท่านั้น เพราะช่วงนั้น lowcmd ≠ q_des

## เช็คเอียง
`State_RLBase.cpp`: `torso_tilt_exceeds(env, 0.85)` ใช้ `projected_gravity_b[2]` คำนวณมุมเอียง ถ้าเกิน 0.85 rad (~49°) จะกลับ Passive (ของ Unitree ที่ใช้ร่วมกันถูกปิดไว้ G1-23DoF จึงมีตัวนี้แยกเอง)

## คำถามเช็ค
1. ระหว่าง step ของ policy (20 ms) FSM thread ส่ง lowcmd ไปกี่ครั้ง ค่า q เหมือนกันไหม (ช่วงหลัง soft start)
2. ถ้าแก้ `stiffness` ใน deploy.yaml แต่ไม่ได้เทรนใหม่ policy จะเป็นยังไง (นึกถึงสัปดาห์ 2)
3. ทำไม policy thread ใช้ `sleep_until(sleepTill)` แล้ว `sleepTill += dt` แทน `sleep(dt)` (นึกถึงงาน 1.3 ที่ `sleep(1)` ไม่ได้ 1.000 s พอดี)
