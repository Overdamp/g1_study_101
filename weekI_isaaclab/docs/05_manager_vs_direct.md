# 05: manager-based vs Direct: task เดียวกันเขียน 2 แบบ (I5, I6)

## 1. "contract task" คืออะไร ทำไมต้องมี
task Isaac ของ Unitree มี obs คนละชุดกับ deploy.yaml ของ mjlab (04 §2) → P3b ใช้ในนั้นไม่ได้ ต้องสร้าง obs เองข้างนอก (`play_deploy_onnx.py`)
contract task = task ใหม่ที่เรากำหนด MDP เอง โดย **obs ของ actor = deploy.yaml ทุกตัว** (7 term, 80 ช่อง, ลำดับเดียวกัน)
- P3b เดินได้ทันทีจาก `obs["policy"]` ของ env (I5: 0.448 m/s ที่คำสั่ง 0.5, ไม่ล้ม)
- ใช้ fine-tune P3b ต่อใน Isaac/Newton ได้ (I6 `--init-p3b`)
- เป็นโจทย์ที่ดีสำหรับเทียบ 2 วิธีเขียน เพราะต้องได้ตัวเลขเท่ากันทุก term
ค่าที่ใช้ร่วมกันอยู่ใน `contract_common.py` (reward weight, ช่วงคำสั่ง, ขอบเขต termination)

| ส่วน | กำหนด |
|---|---|
| obs actor (80) | base_ang_vel · projected_gravity · velocity_commands · **gait_phase (เขียนเอง)** · joint_pos_rel · joint_vel_rel · last_action |
| obs critic (84) | actor + base_lin_vel + **base_height (เขียนเอง)** |
| action | q_des = default + scale·a · scale = 0.25·effort/kp (สูตร mjlab) |
| reward (10) | track_lin/ang (exp, std 0.5) · lin_vel_z · ang_vel_xy · flat_orientation · action_rate · joint_pos_limits · is_alive · **feet_too_close** · **vx_ema_error (class)** |
| termination | time_out · bad_orientation (0.8 rad) · **pelvis_too_low (0.45 m)** |
| คำสั่ง | uniform ใน ranges ของ deploy.yaml ทุก 10 s · `fixed_cmd` ล็อกได้ |

## 2. I5: เขียน term เองใน Isaac Lab 3 (`my_terms_isaac.py`)
เหมือน weekR `my_terms.py` แทบทุกบรรทัด ต่างกัน 3 จุด:
| | mjlab | Isaac Lab 3 |
|---|---|---|
| ข้อมูลหุ่น | `robot.data.root_link_pos_w` = torch | `robot.data.root_pos_w.torch` (warp array → ต้อง `.torch`) |
| term แบบ class | class ธรรมดา `__init__(cfg, env)` | ต้องสืบทอด `ManagerTermBase` |
| ตำแหน่งเท้า | site `left_foot` ใน MJCF | USD ไม่มี site นั้น → body `left_ankle_roll_link` (`body_ids` = [6, 12]) |

ลงทะเบียนโดย "แทน MDP ทั้งชุด" ใน config ของ task Unitree (`contract_manager.make_cfg`):
```python
cfg = load_cfg_from_registry("Unitree-G1-23dof-Velocity-Flat", "env_cfg_entry_point")   # หุ่น + ฉาก + sim
cfg = resolve_presets(cfg, {"newton"})
cfg.observations = ObservationsCfg(); cfg.actions = ActionsCfg(); cfg.commands = CommandsCfg()
cfg.rewards = RewardsCfg(); cfg.terminations = TerminationsCfg(); cfg.events = EventsCfg(); cfg.curriculum = EmptyCfg()
env = gym.make("WeekI-G1-Contract-Manager", cfg=cfg)      # register ไว้ใน contract_manager.py
```
- **ลำดับใน vector = ลำดับที่ประกาศ field** ใน ObsGroup · critic สืบทอด PolicyCfg → term ของ actor อยู่ [0, 80) แล้วต่อด้วย [80, 84)
- `SceneEntityCfg(joint_names=POLICY_JOINTS, preserve_order=True)` ทุกที่ที่แตะ joint → ถูกทั้ง PhysX (BFS) และ Newton
- DR ของ frictionloss: `mdp.randomize_joint_parameters(friction_distribution_params=(0, 0.3), operation="abs")`
  → I5 อ่านกลับจาก `NewtonManager.get_model().joint_friction` ได้ช่วง 0.001–0.300 N·m ต่อ world ต่อ joint จริง (ครอบ 0.2 ของ unitree_mujoco)

## 3. I6: Direct (`contract_direct.py`)
Direct = สืบทอด `DirectRLEnv` แล้วเขียน method เอง ไม่มี manager ให้ (ยกเว้น EventManager ถ้าใส่ `cfg.events`)
```
DirectRLEnv.step(a):
  _pre_physics_step(a)                         ← ×1: เก็บ action, q_des = default + scale·a
  for decimation: _apply_action()              ← ×4: set_joint_position_target_index
                  write_data_to_sim → sim.step → scene.update
  episode_length_buf += 1
  _get_dones()   → (died, time_out)            ← ก่อน reward (is_alive ใช้ reset_terminated ได้)
  _get_rewards() → (N,)                        ← คิด 10 term เอง × weight × step_dt
  _reset_idx(env ที่จบ)                         ← เขียน root/joint state ลง sim เอง + ล้าง buffer ของเรา
  [EventManager interval]
  _get_observations() → {"policy", "critic"}   ← อัปเดตคำสั่งเองก่อน แล้ว torch.cat
```
| manager-based (I5) | Direct (I6) |
|---|---|
| `ObsTerm` ×9 + ObservationManager (noise, clip, scale, history ให้) | `torch.cat` เอง + noise เอง |
| `JointPositionActionCfg` | 3 บรรทัดใน `_pre_physics_step` / `_apply_action` |
| `UniformVelocityCommandCfg` | `_resample_commands` + ตัวจับเวลาเอง |
| `RewTerm` ×10 · log `Episode_Reward/*` ให้ | dict 10 term inline + `_episode_sums` + `extras["log"]` เอง |
| `DoneTerm` ×3 (time_out=True → truncated) | คืน `(died, time_out)` |
| `EventTerm` reset | `write_root_pose/velocity/joint_*_to_sim_index` เอง |
| class term + `reset()` | ตัวแปร `self._ema` + ล้างใน `_reset_idx` |
| เพิ่ม term = เพิ่ม 1 field ใน cfg (หรือ CLI แก้ weight) | แก้โค้ด env |
| gym spaces คำนวณจาก term ให้ | ต้องประกาศ `observation_space=80, state_space=84, action_space=23` ใน cfg เอง |

## 4. ผลเทียบ (`i6_compare.py`, 16 env, P3b, vx 0.5, 300 step)
| | ผล |
|---|---|
| obs หลัง reset | เท่ากันทุก term (0.0) |
| obs step 0 / 10 / 299 | ต่างสูงสุด 7e-7 / 6e-5 / 2e-4 |
| reward ทุก term ตลอด 300 step | ต่างไม่เกิน 8.4e-5 |
| done | ตรงกันทุก step ทุก env |
| ตารางใน I5 vs I6 | เหมือนกันถึงหลักที่ 3 · P3b 1.40 reward/s, vx 0.448, ล้ม 0 ทั้งคู่ |
→ **MDP เดียวกัน** ต่างกันแค่ลำดับการคำนวณ float32 บน GPU แล้วหุ่นขยายความต่างช้าๆ (chaos)

เวลา `env.step()` (512 env, Newton, noise เปิด):
| | ไม่มี reset (P3b เดิน) | reset เยอะ (action ศูนย์ ล้มหมด) |
|---|---|---|
| manager | 9.66 ms (MDP 2.1 ms) | 16.35 ms (MDP 8.8 ms) |
| Direct | 8.73 ms (MDP 1.35 ms) | 9.14 ms (MDP 1.8 ms) |
| ฟิสิกส์ล้วน (sim.step ×4) | ~7.4 ms | |
ตอนเทรนจริง 512 env 10 iteration: collection Direct 0.34 s vs manager 0.39 s ต่อ iteration (~13%)
→ ต้นทุนของ manager ส่วนใหญ่อยู่ที่ **ตอน reset** ส่วน step ปกติต่างแค่ ~10%
repo Unitree ทำไปอีกขั้น: `velocity_warp_g1_env.py` รวม reward/obs เป็น Warp kernel เดียว (Direct-Warp) ใช้อ่านต่อได้

## 5. ⚠ ค่าแคชหลัง reset (เจอระหว่างเทียบ)
ข้อมูลใน `robot.data` แบ่งเป็น 2 แบบ:
- อ่านตรงจาก state ของ sim: `joint_pos`, `joint_vel`, `root_pos_w` → หลัง `write_*_to_sim` ได้ค่าใหม่ทันที
- **คำนวณต่อแล้วแคชตาม timestamp**: `projected_gravity_b`, `root_lin_vel_b`, `root_ang_vel_b` … (`articulation_data.py:1003`)
  timestamp ขยับเฉพาะตอน `scene.update` หลัง physics step → **หลัง reset ก่อน step ถัดไป ยังเป็นค่าของหุ่นตัวที่เพิ่งล้ม**
หลักฐาน (I5/I6 ตอน reset หลังรอบ action ศูนย์): joint = default, base_height = 0.8 แต่ gravity = (0.40, 0, −0.92) (เอียง ~24°) และ ang_vel_y = 1.67
- เกิดทั้ง manager และ Direct → obs เฟรมแรกของ env ที่เพิ่ง reset มีค่าเก่าปน 1 step (ระหว่างเทรนก็เป็น)
- policy ต้องทนได้ (เหมือน noise 1 เฟรม) · ถ้าจะเทียบแบบ bit-exact ให้เริ่มจาก env สด (I5/I6 จึงรัน P3b ก่อน)
- mjlab: `sim.forward()` หลัง reset ทำให้ค่าพวกนี้สดเสมอ (weekR R3 เห็น `forward` ในลำดับ step)

## 6. ควรเลือกแบบไหน
| ใช้ manager เมื่อ | ใช้ Direct เมื่อ |
|---|---|
| ทดลอง reward/obs บ่อย แก้จาก config/CLI | MDP นิ่งแล้ว อยากได้ความเร็ว |
| อยากได้ log, noise, history, curriculum สำเร็จรูป | logic ที่ manager ทำยาก (state ข้าม term เยอะ, คิด reward ร่วมกันครั้งเดียว) |
| แชร์ term กับ task อื่น | อยากอ่าน step ทั้งหมดในไฟล์เดียว |
| export deploy.yaml อัตโนมัติจาก cfg (`export_deploy_cfg`) | ยอมเขียน deploy.yaml เอง |
งานเราตอนนี้ (ปรับ reward บ่อย) → manager · ถ้า MDP นิ่งแล้วจะเทรนนาน → พิจารณา Direct

## คำถามเช็ค
1. เพิ่ม obs `foot_height` ให้ actor ต้องแก้กี่ที่ในแต่ละแบบ (manager / Direct) และ P3b จะพังที่ไหน
2. ทำไมใน Direct ต้องประกาศ `observation_space` เอง แต่ manager ไม่ต้อง
3. `--init-p3b` ช่วงแรก Mean reward บวกเลย แต่ policy อาจแย่ลงก่อนดีขึ้น เพราะอะไร (คิดถึง critic ใหม่)
4. ค่าแคชหลัง reset มีผลกับ reward ของ step นั้นไหม (reward คิดก่อนหรือหลัง reset)
