# โมดูล R: ฉบับสมบูรณ์ (เฉลย)

> โครงให้ฝึกเขียนเองอยู่ใน `../skelatons/` · ใช้ `conda activate unitree_rl_mjlab` · GPU ว่าง ~1 GB · ไม่แก้ repo หลัก · ไม่ใช้ DDS

| ไฟล์ | งาน | อะไร |
|---|---|---|
| `rlib.py` | ทั้งหมด | load_cfg / cfg_summary / diff_cfg / fix_command / make_env / term_slices / ActorMLP / manual_reward / StepTracer + เทสต์ 18 ข้อ |
| `r1_cfg_tree.py` | R1 | ต้นไม้ term · `--where` ไฟล์:บรรทัด · `--diff A B` · `--base` (ชั้น 1 vs ชั้น 2) |
| `r2_build_env.py` | R2 | ลำดับสร้าง manager · ช่วง obs 80/95 · scale/offset vs deploy.yaml |
| `r3_step_trace.py` | R3 | ลำดับการเรียกใน `env.step()` · `--reset` |
| `r4_reward_probe.py` | R4 | reward ทีละ term: action ศูนย์ vs P3b · `--vx` |
| `my_terms.py` | R5 | obs `base_height` · reward `feet_too_close`, `vx_ema_error` (class) · termination `pelvis_too_low` |
| `r5_custom_terms.py` | R5 | เพิ่ม/ปิด/ลบ term · `--actor-obs` (81 → P3b พัง) · `--rough` (267) |
| `r6_events_curriculum.py` | R6 | DR ต่อ env · reset · push · curriculum ตาม counter |
| `r7_policy_vs_deploy.py` | R7 | obs ของ env vs week4 `obs.py` ทีละ term + P3b vx จริง |
| `r8_mini_train.py` | R8 | ประกอบ train.py เอง · `--resume` · `--weight term=w` · log ลง `weekR_mjlab/logs/` |

## รัน
```bash
conda activate unitree_rl_mjlab
cd ~/g1_study/weekR_mjlab/scripts/complete
python rlib.py                                   # 18/18 (~20 s)
python r1_cfg_tree.py --where
python r1_cfg_tree.py --diff Unitree-G1-23Dof-Flat Unitree-G1-23Dof-Rough-Blind
python r2_build_env.py
python r3_step_trace.py --reset
python r4_reward_probe.py --vx 0.5
python r5_custom_terms.py --actor-obs
python r6_events_curriculum.py
python r7_policy_vs_deploy.py
python r8_mini_train.py --iters 10 --resume
tensorboard --logdir ~/g1_study/weekR_mjlab/logs
```

## ผลทดสอบ (13/11/2026, RTX 3060 Laptop)
| สคริปต์ | ผล |
|---|---|
| `rlib.py` | 18/18 PASS |
| `r1` | Flat vs Blind ต่าง 2 แถว (terrain_levels, track_linear w 2) · ชั้น 2 เพิ่ม event 7 + self_collisions · `UniformVelocityCommandCfg` มาจาก **site-packages/mjlab** |
| `r2` | actor [0,3) gyro · [3,6) gravity · [6,9) cmd · [9,11) phase · [11,34) q · [34,57) dq · [57,80) action · critic +15 · scale/offset ตรง deploy.yaml 23/23 |
| `r3` | process ×1 → (apply → sim.step) ×4 → termination → reward → [curriculum → event(reset)] → forward → command → event(interval) → sense → observation |
| `r4` (vx 0.5, 16 env, 5 s) | ศูนย์: ล้ม 46 ครั้ง, รวม −0.68/s (is_terminated −2.3) · P3b: ล้ม 0, vx 0.39, รวม +3.0/s · error Σ×dt 9.5e-7 |
| `r5` | critic 96 → P3b รันได้, `vx_ema_error` −0.09/s · `--actor-obs` 81 → size mismatch · `--rough` actor 267 |
| `r6` | torso 7.2–10.9 kg · knee frictionloss XML 0 → 0.11–0.17 · kp 97.7–113.9 · push แรกที่ ~5.2 s · counter 0/1/120000/120001 → (−1,2)/(−0.5,1)/(−0.5,1)/(−1,2) |
| `r7` | ทุก term < 2e-7 ยกเว้น phase 0.209 (deploy นำ 1 step) · P3b vx 0.35 m/s (สั่ง 0.5) |
| `r8` | 256 env: 0.98 s/iteration (เริ่มใหม่), 0.87 (resume) · ศูนย์ Mean reward −1.6 → −11.8 · resume +0.3 → +2.2 ใน 5 iteration |

ตัวเลข vx ของ P3b ต่างกันระหว่าง r4 (0.39) กับ r7 (0.35) เพราะจำนวน env/ระยะเวลา/DR ที่สุ่มได้ต่างกัน ทั้งสองค่าสอดคล้องกับ vault ("P3b ติดตาม ~0.4 m/s")
