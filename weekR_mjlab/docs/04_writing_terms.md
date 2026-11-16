# 04: เขียน term เอง

## 1. รูปแบบฟังก์ชัน
```python
def ชื่อ(env, <params ตาม cfg>, asset_cfg: SceneEntityCfg = SceneEntityCfg("robot")) -> torch.Tensor:
    robot = env.scene[asset_cfg.name]           # Entity
    ...                                          # คำนวณเป็น tensor ทุก env พร้อมกัน
    return x                                     # obs (N, k) · reward (N,) · termination (N,) bool
```
- `env` ตัวแรกเสมอ · ที่เหลือมาจาก `params={...}` ใน cfg (ชื่อต้องตรงกัน)
- ห้าม `for i in range(num_envs)` (ช้ามากบน GPU 4096 env) ใช้ indexing / broadcasting
- obs ต้องมี 2 มิติ: `x[:, 2:3]` ได้ (N, 1) แต่ `x[:, 2]` ได้ (N,) → ต่อกับ term อื่นไม่ได้
- manager เรียก func 1 ครั้งตอนสร้างเพื่อวัดขนาด obs (`observation_manager.py:440`) → ฟังก์ชันต้องเรียกได้ตั้งแต่ก่อน reset

## 2. SceneEntityCfg: ชื่อ → index ให้อัตโนมัติ
```python
SceneEntityCfg("robot", site_names=("left_foot", "right_foot"))
SceneEntityCfg("robot", body_names=("torso_link",))
SceneEntityCfg("robot", joint_names=(".*_knee_joint",))      # regex ได้
```
ตอนสร้าง manager: `_resolve_common_term_cfg` เรียก `value.resolve(env.scene)` กับทุก params ที่เป็น SceneEntityCfg (`manager_base.py:133–139`) → ใน func ใช้ `asset_cfg.site_ids`, `body_ids`, `joint_ids` ได้เลย

ใน config พื้นฐานจึงเห็น `site_names=()  # Set per-robot.` แล้ว `env_cfgs.py` มาเติมชื่อทีหลัง (`env_cfgs.py:107–112, 234–237`)

## 3. ข้อมูลของหุ่น: `robot.data.<ชื่อ>` (`mjlab/entity/data.py`)
| อยากได้ | ชื่อ | shape | หมายเหตุ |
|---|---|---|---|
| ตำแหน่ง/ท่าของ pelvis | `root_link_pos_w`, `root_link_quat_w` | (N,3), (N,4) | quat = (w, x, y, z) · `_w` = กรอบโลก |
| ความเร็ว pelvis กรอบหุ่น | `root_link_lin_vel_b`, `root_link_ang_vel_b` | (N,3) | `_b` = กรอบลำตัว · ang_vel_b = gyro |
| gravity กรอบหุ่น | `projected_gravity_b` | (N,3) | ยืนตรง = (0, 0, −1) |
| ทิศหัว | `heading_w` | (N,) | yaw |
| ข้อต่อ | `joint_pos`, `joint_vel`, `joint_acc`, `default_joint_pos` | (N,23) | เรียงตาม policy index (= `robot.joint_names`) |
| แรงบิด | `actuator_force`, `joint_torques` | (N,23) | |
| body / site / geom | `body_link_pos_w[:, ids]`, `site_pos_w[:, ids]`, `site_lin_vel_w` | (N,k,3) | ids จาก SceneEntityCfg |

sensor: `env.scene["feet_ground_contact"].data` (`found`, `force`, `current_air_time`, `current_contact_time`) · `env.scene["robot/imu_ang_vel"].data`
คำสั่ง: `env.command_manager.get_command("twist")` (N,3) · action: `env.action_manager.action / prev_action`
เวลา: `env.episode_length_buf` (N,) · `env.step_dt` · `env.common_step_counter`

## 4. term แบบ class (มี state)
```python
class vx_ema_error:                                  # weekR my_terms.py
    def __init__(self, cfg, env):                    # ครั้งเดียวตอนสร้าง manager
        self.alpha = cfg.params.get("alpha", 0.05)
        self.ema = torch.zeros(env.num_envs, device=env.device)
    def __call__(self, env, command_name, alpha=0.05):   # ทุก step · params ยังถูกส่งเข้ามาด้วย
        ...
    def reset(self, env_ids=None):                   # ตอน env ใดๆ reset (ล้าง state ของ env นั้น)
        self.ema[env_ids] = 0.0
```
manager เห็นว่า `func` เป็น class → `func(cfg=term_cfg, env=env)` (`manager_base.py:138`) แล้วใช้ instance แทน · ถ้ามี `reset` จะถูกเรียกใน `RewardManager.reset` (`reward_manager.py:250`)
ใช้เมื่อ: ต้องจำค่าข้าม step (EMA, เวลาตั้งแต่ก้าวล่าสุด), หรือคำนวณของแพงครั้งเดียว (`variable_posture` แปลง regex → tensor ตอน `__init__`)

## 5. ลงทะเบียนใน config (ไม่ต้องแก้ repo)
```python
cfg = rlib.load_cfg(rlib.FLAT)                       # deepcopy จาก registry
cfg.rewards["feet_too_close"] = RewardTermCfg(func=my_terms.feet_too_close, weight=-5.0,
    params={"min_dist": 0.15, "asset_cfg": SceneEntityCfg("robot", site_names=("left_foot", "right_foot"))})
cfg.observations["critic"].terms["base_height"] = ObservationTermCfg(func=my_terms.base_height)
cfg.terminations["pelvis_too_low"] = TerminationTermCfg(func=my_terms.pelvis_too_low, params={"min_height": 0.45})
env = rlib.make_env(cfg)
```
ถ้าจะเทรนจริงด้วย term ของเรา: ทำแบบ R8 (ประกอบ runner เอง) หรือ register task ใหม่ในไฟล์ของเรา (`register_mjlab_task("My-G1-...", env_cfg=cfg, ...)`) แล้วเรียก `launch_training("My-G1-...")` · `train.py` ใช้ CLI เพิ่ม term ใหม่ไม่ได้ (CLI แก้ได้แค่ค่าของ field ที่มีอยู่แล้ว)

## 6. ปิด / ลบ term 3 แบบ (R5)
| วิธี | ผล | resume checkpoint |
|---|---|---|
| `cfg.rewards["x"].weight = 0` | ยังอยู่ในตาราง แต่ข้ามตอนคำนวณ | ได้ (reward ไม่กระทบขนาด network) |
| `cfg.rewards["x"] = None` | manager พิมพ์ `skipping` แล้วข้ามตอนสร้าง | ได้ |
| `del cfg.rewards["x"]` | หายจาก dict | ได้ |
| ลบ/เพิ่ม **obs ของ actor** | ขนาด actor เปลี่ยน | **ไม่ได้** (`mlp.0.weight` ไม่ตรง) + ONNX / deploy.yaml เดิมใช้ไม่ได้ |
| ลบ/เพิ่ม obs ของ critic | ขนาด critic เปลี่ยน | ไม่ได้ (critic ไม่ตรง) แต่ deploy ไม่กระทบ |

## 7. ตรวจ term ใหม่ก่อนเทรนจริง
1. shape ถูก: `func(env, **params).shape` ใน REPL
2. ค่าสมเหตุผล: รัน P3b ใน R5 แล้วดูค่าเฉลี่ยต่อวินาที เทียบกับ term อื่น (คูณ weight แล้วไม่ควรใหญ่กว่า `track_linear_velocity` หลายเท่า)
3. ไม่มี NaN: reward manager จะแปลง NaN เป็น 0 เงียบๆ (`nan_to_num`) → bug ซ่อนได้
4. เทรนสั้น (R8 / week5 smoke) เทียบกับ run ควบคุม seed เดียวกัน

## แบบฝึก (ต่อจาก R5)
1. เขียน `arm_swing_reward`: ให้รางวัลเมื่อไหล่ซ้าย/ขวาแกว่งสวนกับขาข้างเดียวกัน (ใช้ `joint_pos` ของ `left_shoulder_pitch_joint` กับ `left_hip_pitch_joint`)
2. เขียน obs `foot_height` ของ actor แล้วดูว่า P3b พังด้วย error อะไร
3. เขียน termination `torso_contact` ด้วย sensor `self_collision` (ดู `illegal_contact` ใน `repo/src/tasks/velocity/mdp/terminations.py`)
