# 01: manager-based คืออะไร (ภาพรวม)

## 1. ปัญหาที่มันแก้
env ของ RL แบบเขียนเองทั้งก้อนจะมีฟังก์ชัน `step()` ยาวๆ ที่คำนวณ obs, reward, done ปนกันหมด อยากเพิ่ม reward 1 ตัวก็ต้องเข้าไปแก้กลางฟังก์ชัน

manager-based (มาจาก Isaac Lab, mjlab ลอกโครงมา) แยกเป็น:
- **term** = ฟังก์ชันเล็กๆ 1 ตัวที่ทำงานเดียว เช่น "คำนวณ projected gravity", "ให้รางวัลถ้าเดินตามคำสั่ง"
- **config** = dict ที่บอกว่าใช้ term อะไร พร้อม params / weight
- **manager** = ตัววน dict แล้วเรียก term ทุกตัวตามจังหวะที่ถูก

```python
# config (velocity_env_cfg.py:262)                       manager (reward_manager.py:257–268)
rewards = {                                              for name, term_cfg in terms:
  "track_linear_velocity": RewardTermCfg(                   value = term_cfg.func(env, **term_cfg.params)
     func=mdp.track_linear_velocity,                                 * term_cfg.weight * dt
     weight=1.0,                                            reward_buf += value
     params={"command_name": "twist", "std": 0.5}),
  ...
}
```
**เพิ่ม reward = เพิ่ม key ใน dict** ไม่ต้องแตะ env หรือ manager เลย (R5 ทำแบบนี้)

## 2. term = func + params (+ ของเฉพาะ manager)
```python
@dataclass
class ManagerTermBaseCfg:          # mjlab/managers/manager_base.py:17
  func: Any                        # ฟังก์ชัน หรือ class
  params: dict = {}                # ส่งเป็น keyword เข้า func ทุกครั้ง
```
| manager | cfg ของ term | ฟิลด์เพิ่ม | func คืน |
|---|---|---|---|
| observation | `ObservationTermCfg` | noise, clip, scale, delay, history | (N, k) |
| reward | `RewardTermCfg` | **weight** | (N,) |
| termination | `TerminationTermCfg` | **time_out** (True = หมดเวลา, False = ล้ม) | (N,) bool |
| event | `EventTermCfg` | **mode** (startup / reset / interval / step), interval_range_s | (แก้ sim ตรงๆ) |
| curriculum | `CurriculumTermCfg` | — | ค่าไว้ log |
| command | `UniformVelocityCommandCfg` ฯลฯ | ranges, resampling_time_range | (เป็น class เต็ม) |
| action | `JointPositionActionCfg` | scale, offset, actuator_names | (เป็น class เต็ม) |

N = จำนวน env ที่รันพร้อมกัน (4096 ตอนเทรน) **ทุก term คำนวณทุก env พร้อมกันเป็น tensor** ไม่มี for วนทีละ env

## 3. 8 manager ใน env ของเรา
| manager | ทำอะไร | เรียกเมื่อไร | ตัวอย่างของเรา |
|---|---|---|---|
| **action** | action ดิบ (23) → q_des → เขียนลง actuator | process 1 ครั้ง/step, apply ทุก substep | `joint_pos`: q_des = a × scale + default |
| **observation** | รวม term → เวกเตอร์ต่อ group | ท้าย step | actor 80, critic 95 |
| **command** | สุ่ม/อัพเดทคำสั่ง (vx, vy, wz) | ท้าย step, ตอน reset | `twist` สุ่มใหม่ทุก 3–8 s |
| **reward** | Σ func × weight × dt | หลัง physics | 16 term |
| **termination** | ตัดสินว่า episode จบไหม | หลัง physics ก่อน reward | `time_out` 20 s, `fell_over` 70° |
| **event** | แก้ sim: สุ่มค่า (DR), ตั้งท่าเริ่ม, ผลัก | startup / reset / interval | 13 term |
| **curriculum** | ปรับความยาก | ตอน reset | `command_vel` (Flat), + `terrain_levels` (Rough) |
| **metrics** | ค่าไว้ log อย่างเดียว | ทุก step | `mean_action_acc` |

## 4. 1 step ของ env (manager_based_rl_env.py:368–419) ← R3 พิสูจน์
```
policy ──action (N,23)──▶ env.step(action)
  ┌ action.process_action(action)         a → q_des = a·scale + offset (ครั้งเดียว)
  │ for _ in range(decimation=4):         ── 4 × 0.005 s = 0.02 s (50 Hz) ──
  │     action.apply_action()             เขียน q_des เดิมลง actuator (PD ใน MuJoCo)
  │     sim.step()                        ฟิสิกส์ 1 step (mujoco_warp บน GPU)
  │ episode_length_buf += 1
  │ termination.compute()                 ล้ม? หมดเวลา?
  │ reward.compute(dt)                    ← ตัดสิน "ผลของ action นี้" ก่อน reset
  │ ถ้ามี env จบ → _reset_idx(ids)        curriculum → sim/scene reset → event(reset) → log Episode_*
  │ sim.forward()                         sync xpos/sensor กับ qpos (weekM: sensor ช้า 1 step)
  │ command.compute(dt)                   นับถอยหลัง/สุ่มคำสั่งใหม่
  │ event.apply("interval")               ผลัก
  │ sim.sense()
  └ observation.compute()                 ← obs ของ env ที่เพิ่ง reset = obs ของ episode ใหม่
◀── (obs, reward, terminated, time_outs, extras)
```
สิ่งที่ต้องจำ:
- **q_des คงที่ตลอด 4 substep** ตรงกับหุ่นจริงที่ policy ส่งคำสั่ง 50 Hz แต่ PD วิ่ง 1 kHz+
- **reward ก่อน reset, obs หลัง reset** → reward ของ step ที่ล้มยังนับ (รวม `is_terminated` −200) แต่ obs ที่คืนเป็นท่าเริ่มของ episode ใหม่
- env ที่จบ **reset เฉพาะตัวมัน** ตัวอื่นเดินต่อ (ไม่มีการรอกัน)

## 5. ใครสร้างใคร
```
train.py  ─▶  load_env_cfg("Unitree-G1-23Dof-Flat")      (registry, R1)
          ─▶  ManagerBasedRlEnv(cfg)                     (R2)
                 Scene(cfg.scene) → compile MJCF → Simulation (mujoco_warp, N world)
                 load_managers(): Event → Command → Action → Observation → Termination → Reward → Curriculum → Metrics
                                  (ลำดับสำคัญ: obs อ้างถึง command จึงต้องสร้าง command ก่อน)
                 event.apply("startup")                  ← DR แบบสุ่มครั้งเดียว
          ─▶  RslRlVecEnvWrapper(env) ─▶ OnPolicyRunner ─▶ learn()   (R8, 05)
```

## คำถามเช็ค
1. ถ้าเพิ่ม reward term ใหม่ใน dict ต้องแก้ `ManagerBasedRlEnv` ไหม เพราะอะไร
2. term `fell_over` คืนค่าแบบไหน ขนาดเท่าไรตอนเทรน 4096 env
3. ทำไมสร้าง ObservationManager ก่อน CommandManager ไม่ได้
