# RL และ PPO เท่าที่ต้องใช้

## คำศัพท์ (เทียบกับของที่เรารู้แล้ว)
| คำ | ความหมาย | ในงานเรา |
|---|---|---|
| env | โลกจำลองที่หุ่นอยู่ | MuJoCo (mjlab) พื้นเรียบ (`Unitree-G1-23Dof-Flat`) |
| observation | สิ่งที่ policy เห็น | obs 80 ตัว (สัปดาห์ 4) |
| action | สิ่งที่ policy สั่ง | 23 ตัว → `q_des` |
| reward | คะแนนที่ได้ต่อ step | ผลรวมของหลาย term (`rewards.md`) |
| episode | 1 รอบ ตั้งแต่ reset จนล้มหรือหมดเวลา | สูงสุด 20 s = 1000 step (50 Hz) |
| return | ผลรวม reward ทั้งอนาคต ลดค่าด้วย γ | γ = 0.99 → "มองไกล" ประมาณ 100 step = 2 s |
| policy (actor) | network ที่เลือก action | MLP 512-256-128, ELU = `policy.onnx` |
| critic | network ที่ประเมินว่า "สถานการณ์นี้ดีแค่ไหน" | MLP 512-256-128 (ใช้ตอนเทรนเท่านั้น ไม่ได้ export) |

## PPO ทำงานยังไง (1 iteration)
```
1. เก็บข้อมูล:  1024 env × 24 step = 24,576 ตัวอย่าง  (ทุก env ใช้ policy ปัจจุบัน + สุ่ม action รอบๆ ค่าเฉลี่ย)
2. คำนวณ advantage: action นี้ "ดีกว่าที่ critic คาด" แค่ไหน  (GAE, λ = 0.95)
3. อัพเดท:  5 epoch × 4 mini-batch  ปรับ actor ให้ทำ action ที่ advantage บวกบ่อยขึ้น
            แต่จำกัดไม่ให้เปลี่ยนเกิน (clip 0.2, desired_kl 0.01)  ← "Proximal" = เปลี่ยนทีละนิด
4. ทุก 100 iteration: save model_XXXX.pt + export policy.onnx
```
ค่าทั้งหมดอยู่ใน `src/tasks/velocity/config/g1_23dof/rl_cfg.py`

**ตัวเลขของ run เรา**
- 1 iteration ≈ 24,576 step ของหุ่น ≈ 8 นาทีของเวลาหุ่น (รวมทุก env)
- บนเครื่องนี้ (RTX 3060 Laptop) P3b ใช้ประมาณ **1.2 s/iteration** (ดูจากเวลาของไฟล์ checkpoint: 1000 iteration ≈ 20 นาที)
- P3b เทรนรวม ~16,000 iteration (P1 → P2 → P3b)
- fine-tune 300 iteration ≈ 6 นาที ≈ 2% ของการเทรนทั้งหมด → **คาดว่าเปลี่ยนได้ไม่มาก** (นี่คือเหตุผลที่ต้องมี control)

## ทำไม actor สุ่ม action ตอนเทรน
actor ส่งค่าเฉลี่ย + ส่วนเบี่ยงเบน (`std`, เริ่มที่ 1.0) แล้วสุ่ม action ตามนั้นเพื่อ "สำรวจ" ส่วน `entropy_coef = 0.01` ให้รางวัลเล็กน้อยกับการยังสุ่มอยู่ ตอน export เป็น ONNX ใช้แค่**ค่าเฉลี่ย** policy ที่ deploy จึงเป็น deterministic (ตรงกับที่ทดลองไว้ใน `week4/docs/onnx_basics.md`)

## obs normalization
`obs_normalization=True`: network เก็บค่าเฉลี่ย/ส่วนเบี่ยงเบนของ obs แต่ละตัวไว้แล้ว normalize ก่อนเข้า MLP ค่านี้ถูก export อยู่ใน `policy.onnx` ด้วย (สัปดาห์ 4: ป้อน obs ดิบได้เลย) ⚠️ ตอน fine-tune ค่าพวกนี้ยังอัพเดทต่อ

## กราฟใน TensorBoard ที่ต้องดู
```bash
conda activate unitree_rl_mjlab
tensorboard --logdir ~/g1_study/week5/logs/rsl_rl          # run ของเรา
tensorboard --logdir ~/nvidia/unitree/unitree_rl_mjlab/logs/rsl_rl/g1_23dof_velocity   # P3b (อ่านอย่างเดียว)
```
| กราฟ | ความหมาย | ดีคือ |
|---|---|---|
| `Train/mean_reward` | reward รวมเฉลี่ยต่อ episode | ขึ้น แล้วนิ่ง |
| `Train/mean_episode_length` | อยู่รอดกี่ step (สูงสุด 1000) | ใกล้ 1000 |
| `Episode_Reward/<term>` | แต่ละ term มีส่วนเท่าไหร่ (หน่วย reward/วินาที เฉลี่ย) | ดูว่า term ไหนครอบงำ |
| `Episode_Termination/fell_over` | สัดส่วนที่จบเพราะล้ม | ใกล้ 0 |
| `Metrics/twist/error_vel_xy`, `error_vel_yaw` | ติดตามความเร็วผิดเท่าไหร่ | ลง |
| `Loss/value_function`, `Loss/surrogate` | loss ของ critic / actor | ไม่ระเบิด |
| `Policy/mean_noise_std` | std ของการสุ่ม | ค่อยๆ ลง |

**ระวัง:** `mean_reward` ขึ้น ≠ เดินดีขึ้นเสมอ ถ้าแก้ weight ทำให้ "ระดับคะแนน" เปลี่ยน จะเทียบ mean_reward ข้าม run ที่ reward ต่างกันไม่ได้ ให้ใช้ `vel_eval` และ `Metrics/*` แทน

## คำถามเช็ค
1. γ = 0.99 ที่ 50 Hz หมายถึง policy "สนใจอนาคต" ประมาณกี่วินาที ถ้าเปลี่ยนเป็น 0.9 จะเป็นยังไง
2. ทำไม critic ไม่ต้อง export ไปใช้บนหุ่น
3. ถ้า `Train/mean_reward` ของ run ทดลองสูงกว่า control แปลว่า policy ดีกว่าไหม
