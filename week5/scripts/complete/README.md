# สัปดาห์ 5: ฉบับสมบูรณ์ (เฉลย)

> โครงให้ฝึกเขียนเองอยู่ใน `../skelatons/` · โฟลเดอร์นี้คือเฉลย
> ⚠️ ไม่แก้ repo หลัก (เปลี่ยน reward ผ่าน CLI) · log ลง `~/g1_study/week5/logs/` · policy ที่เทรนที่นี่ห้ามขึ้นหุ่นจริง

| ไฟล์ | งาน | env | อะไร |
|---|---|---|---|
| `runlog.py` | – | – | อ่าน `env.yaml` / `agent.yaml` (มี tag ของ Python) + หา run |
| `reward_table.py` | 5.1 | `unitree_rl_mjlab` | ตาราง reward + termination จาก config ของ run จริง (`--sort` เรียงตาม \|weight\|) |
| `read_tb.py` | 5.2, 5.6 | `unitree_rl_mjlab` | TensorBoard → ตาราง: หลัก + `Episode_Reward/*` เทียบหลาย run |
| `diff_configs.py` | 5.4 | `unitree_rl_mjlab` | เทียบ config 2 run (รวม term ที่มีฝั่งเดียวเป็นบรรทัดเดียว) |
| `run_experiment.sh` | 5.4, 5.5, 5.8 | `unitree_rl_mjlab` | smoke / control / exp / break · override ผ่านตัวแปร `EXP_OVERRIDE`, `BREAK_OVERRIDE` |
| `eval_policy.py` | 5.3, 5.6 | `g1_sdk` | `eval`: gain_check + vel_eval (8 case + ยืน + แขวน) · `compare`: ตาราง + คอลัมน์ ทดลอง − control |

## ลำดับการใช้
```bash
cd ~/g1_study/week5/scripts/complete
conda activate unitree_rl_mjlab
python reward_table.py --sort                     # 5.1
python read_tb.py                                 # 5.2 (P3b + run ของเรา)
../prepare_seed.sh
./run_experiment.sh smoke                         # ~20 s
./run_experiment.sh control                       # 300 iter ≈ 5–6 นาที
EXP_OVERRIDE="--env.rewards.track-linear-velocity.weight=2.0" ./run_experiment.sh exp
python diff_configs.py <control_run> <exp_run>    # ต้องต่างกันแค่ weight ที่ตั้งใจ
conda activate g1_sdk
python eval_policy.py eval baseline ~/nvidia/unitree/unitree_rl_mjlab/deploy/robots/g1_23dof/config/policy/velocity/v0/exported/policy.onnx
python eval_policy.py eval control <control_run>/policy.onnx
python eval_policy.py eval exp_b   <exp_run>/policy.onnx
python eval_policy.py compare baseline control exp_b
```

## ผลทดสอบ (10/11/2026)
**reward_table** (run P3b): 16 term = รางวัล 4 · โทษ 12 · fell_over limit 1.22 rad (70°) · episode 20 s · 1024 env ✅

**read_tb** (P3b vs run ข้างกัน): ช่วง 12999 → 15998 · mean_reward 30.4 · episode length 998/1000 · fell_over 1%
รางวัลมากสุด `pose` (0.76) · โทษมากสุด `action_rate_l2` (−0.27) ตามด้วย `joint_acc_l2` (−0.19) ✅

**eval_policy baseline (v0)** ทำซ้ำตัวเลขใน vault ได้ตรงทุกตัว ใช้เวลา ~6 s:
vx 0.4 / 0.8 / 1.0 = **97 / 74 / 41 %** · wz ±0.5 = 69 % · vy 0.3 = 59 % · ยืน joint_vel_std 0 · แขวน speed ratio 0.08 · gain_check PASS ✅

**run_experiment.sh smoke** (เทรนจริงบน RTX 3060, log ลง scratchpad): resume ที่ 15998 → 16002, **~1.05 s/iteration**, ได้ `policy.onnx`, run ชื่อ `<เวลา>_smoke` ✅
`diff_configs` smoke vs run P3b: **env.yaml ต่างกัน 0 จุด** (config ปัจจุบันของ branch = config ตอนเทรน P3b) · agent.yaml ต่างแค่ max_iterations ✅

## ⚠️ ข้อค้นพบสำคัญ: fine-tune แค่ 5 iteration ก็เปลี่ยนผลได้
| cmd | baseline (v0) | smoke (+5 iter, ไม่เปลี่ยน reward) |
|---|---|---|
| vx 0.4 | 97 | **84** |
| vx 0.8 | 74 | 70 |
| wz +0.5 | 69 | 76 |
| vy 0.3 | 59 | **47** |

แม้ไม่ได้เปลี่ยน reward เลย ผลก็เปลี่ยนได้ถึง ±13 จุด เหตุผลที่เป็นไปได้: PPO อัพเดททันทีด้วย lr 1e-3, normalizer ของ obs อัพเดทต่อ และ checkpoint ที่ใช้เริ่ม (`model_15998.pt`) ไม่ใช่ไฟล์เดียวกับ `policy.onnx` ของ v0 (`policy_phase3b_16000.onnx`)
→ **นี่คือเหตุผลที่ต้องมี run ควบคุม** ผลของ reward = ทดลอง − control เสมอ ห้ามเทียบกับ baseline ตรงๆ
→ ช่วงแรกของ run ใหม่ `mean_episode_length` ต่ำ (39) เพราะ episode เพิ่ง reset ตัวเลขจาก run สั้นๆ ใน TensorBoard จึงยังเชื่อไม่ได้
