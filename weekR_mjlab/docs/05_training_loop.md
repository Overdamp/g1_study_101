# 05: training loop: runner, PPO, checkpoint, ONNX

## 1. train.py ทั้งไฟล์ในภาพเดียว (`repo/scripts/train.py`)
```
main(): task = argv[1] → import mjlab.tasks, src.tasks (ลงทะเบียน task)
        tyro.cli(TrainConfig)  ← default จาก registry + override จาก CLI
launch_training(): log_dir = logs/rsl_rl/<experiment_name>/<เวลา>_<run_name>   (cwd!)
                   เลือก GPU · MUJOCO_GL=egl
run_train():
   env    = ManagerBasedRlEnv(cfg.env, device)
   resume_path = get_checkpoint_path(log_root, load_run, load_checkpoint)  (ถ้า --agent.resume)
   env    = RslRlVecEnvWrapper(env, clip_actions)
   runner = VelocityOnPolicyRunner(env, asdict(agent), log_dir, device)
   runner.load(resume_path)
   dump_yaml(params/env.yaml, params/agent.yaml)
   runner.learn(max_iterations, init_at_random_ep_len=True)
```
R8 เขียนลำดับนี้เองทีละบรรทัด

## 2. RslRlVecEnvWrapper (`mjlab/rl/vecenv_wrapper.py`)
แปลง env ของ mjlab ให้หน้าตาเป็น `VecEnv` ของ rsl_rl:
- obs dict `{"actor": (N,80), "critic": (N,95)}` → TensorDict · `obs_groups = {"actor": ("actor",), "critic": ("critic",)}` บอกว่า network ไหนกิน group ไหน
- `dones = terminated | truncated` + `extras["time_outs"] = truncated` (PPO ใช้ bootstrap)
- `clip_actions` (ของเรา None = ไม่ clip)

## 3. 1 iteration ของ PPO (rsl_rl `OnPolicyRunner.learn`)
```
rollout (torch.inference_mode):  ทำซ้ำ num_steps_per_env = 24 ครั้ง
    a = actor(obs) + noise (Gaussian, std เรียนได้ เริ่ม 1.0)     ← สุ่มเพื่อสำรวจ
    obs, r, done = env.step(a)                                    ← 4096 env พร้อมกัน
    เก็บ (obs, a, r, done, V(obs), log π) ลง storage
→ ข้อมูล 24 × 4096 = 98,304 transition
คำนวณ advantage ด้วย GAE (γ = 0.99, λ = 0.95)  ← ตรงนี้ time_outs ได้ bootstrap
update: 5 epoch × 4 mini-batch (mini-batch ละ ~24.5k)
    loss = surrogate (clip 0.2) + 1.0 × value loss (clipped) − 0.01 × entropy
    Adam lr 1e-3 แบบ adaptive: ปรับ lr ให้ KL ใกล้ 0.01
log: Mean reward, Mean episode length, Episode_Reward/*, Episode_Termination/*, Metrics/*, Loss/*, Policy/mean_std
save ทุก 100 iteration → model_<it>.pt (+ policy.onnx จาก VelocityOnPolicyRunner.save)
```
| ค่า | ที่ไหน | ของเรา |
|---|---|---|
| network | `rl_cfg.py` | actor/critic MLP 512-256-128 ELU · obs_normalization = True |
| γ, λ | `rl_cfg.py` | 0.99 (มองไกล ~100 step = 2 s), 0.95 |
| num_steps_per_env | `rl_cfg.py` | 24 (= 0.48 s ต่อ rollout ต่อ env) |
| logger | `rl_cfg.py` default `wandb` | week5 / R8 ใช้ `tensorboard` |

**init_at_random_ep_len=True:** ตอนเริ่ม `episode_length_buf` ของแต่ละ env ถูกสุ่ม 0–999 → env ไม่ timeout พร้อมกันทั้ง 4096 ตัว · ผลข้างเคียง: iteration แรกๆ "Mean episode length" สั้นผิดปกติ เพราะ episode ที่จบก่อนคือตัวที่ถูกสุ่มให้ใกล้ 1000 (R8 เห็น 11 → 65 ใน 5 iteration แม้ resume P3b)

## 4. obs normalization
`EmpiricalNormalization` (rsl_rl) เก็บ mean/var ของ obs แบบสะสมระหว่างเทรน แล้วป้อน network ด้วย `(x − mean) / (std + 0.01)`
- อยู่**ใน** actor (`actor_state_dict["obs_normalizer._mean"]`) → export ONNX ติดไปด้วย → deploy ป้อน obs ดิบได้เลย
- R7 `ActorMLP` เขียนส่วนนี้เอง

## 5. checkpoint `.pt` มีอะไร (R7 `ActorMLP` อ่าน)
```
actor_state_dict:   obs_normalizer._mean/_var/_std (1,80) · count
                    mlp.0 (512,80) → ELU → mlp.2 (256,512) → ELU → mlp.4 (128,256) → ELU → mlp.6 (23,128)
                    distribution.std_param (23,)        ← noise ตอนเทรน (deploy ไม่ใช้)
critic_state_dict:  obs_normalizer (1,95) · mlp ... → (1,128)   (ค่า V ตัวเดียว)
optimizer_state_dict: Adam (lr ล่าสุด เช่น 1.5e-5 ใน P3b)
iter: 15998
infos: {"env_state": {"common_step_counter": 384024}}   ← resume แล้ว curriculum ต่อจากเดิม
```
resume = โหลดทั้งหมดนี้ → ต้องการ **ขนาด actor และ critic เท่าเดิม** · reward/event/terrain เปลี่ยนได้

## 6. จาก checkpoint ถึงหุ่น
```
model_15998.pt ──export (runner.save / play.py)──▶ policy.onnx   input "obs" [1,80] → output "actions" [1,23]
                                                   (มี normalizer ในตัว, ใช้ mean ไม่สุ่ม)
env cfg ──────(ค่าต้องตรงกัน · repo นี้ไม่มีสคริปต์ export → R2 ตรวจ)──▶ deploy.yaml   joint_ids_map, kp/kd, default, scale, offset, obs terms
                                                   ↓
g1_ctrl (C++) / week4 policy_runner:  LowState → obs 80 (ตามลำดับใน deploy.yaml) → ONNX → q_des = offset + scale·a → LowCmd kp/kd
```
ทุกอย่างที่ deploy ต้องทำให้ตรงกับตอนเทรน = สิ่งที่ R7 ตรวจ (ลำดับ joint, กรอบของ gyro/gravity, phase, last_action ดิบ, scale/offset)
สิ่งที่ "ตั้งใจให้ไม่ตรง" แล้วหวังว่า DR ครอบ: kp/kd จริง, มวล, friction, delay, encoder bias

## 7. อ่านกราฟให้เป็น (เชื่อมกับ week5 `rl_basics.md`)
| กราฟ | ดูอะไร |
|---|---|
| Mean reward | ผลรวม reward ต่อ episode (หน่วย ต่อ step สะสม) เพิ่มขึ้น = ดี แต่เทียบข้าม config ที่ weight ต่างกันไม่ได้ |
| Mean episode length | 1000 = เดินครบ 20 s ไม่ล้ม |
| Episode_Reward/track_linear_velocity | ใกล้ weight (1.0 หรือ 2.0 ใน Blind) = ติดตามคำสั่งได้ดี (หาร 20 s แล้ว) |
| Episode_Termination/fell_over | จำนวนที่ล้มต่อรอบ reset |
| Policy/mean_std | noise ของ action ลดลง = policy มั่นใจขึ้น · ไม่ลดเลย = ยังไม่รู้จะทำอะไร |
| Curriculum/terrain_levels | Rough/Blind: ระดับเฉลี่ย (stairs_blind ติดที่ระดับต่ำ ↔ weekM: v0 สะดุดขั้น 3 cm) |

## คำถามเช็ค
1. 1 iteration ที่ 4096 env ได้ transition กี่ตัว · ถ้าลด num_envs เหลือ 1024 ต้องเปลี่ยนอะไรเพื่อให้ข้อมูลต่อ iteration เท่าเดิม
2. ทำไม deploy ป้อน obs ดิบเข้า ONNX ได้ ไม่ต้อง normalize เอง
3. resume P3b แล้วเปลี่ยน `track_linear_velocity` weight 1 → 2 ได้ไหม · เปลี่ยน `phase.period` 0.6 → 0.8 ได้ไหม (พังไหม / สมเหตุผลไหม)
