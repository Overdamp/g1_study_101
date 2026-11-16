# Reward ของ G1-23DoF velocity

อ้างอิง: `src/tasks/velocity/velocity_env_cfg.py` (ค่าพื้นฐาน), `src/tasks/velocity/config/g1_23dof/env_cfgs.py` (ค่าเฉพาะหุ่นเรา), `src/tasks/velocity/mdp/rewards.py` (สูตร), repo `doc/g1_23dof_reward_manager.md` (อธิบายละเอียด)
ค่าในตารางตรงกับ task `Unitree-G1-23Dof-Flat` บน branch `phase3-delay-dr` (ตัวที่ใช้เทรน P3b)

## กลไก (สรุปจาก `doc/g1_23dof_reward_manager.md`)
```
reward ต่อ step = Σ  term.func(env) × weight × dt          (dt = 0.02 s)
```
- **weight > 0** = รางวัล: ฟังก์ชันคืนค่า 0..1 เช่น `exp(−error²/std²)`
- **weight < 0** = บทลงโทษ: ฟังก์ชันคืนค่า ≥ 0 เช่น `error²` แล้วคูณ weight ติดลบ
- คูณ `dt` ทำให้มอง weight เป็น "อัตราต่อวินาที" (เปลี่ยนความถี่ของ policy แล้วผลรวมไม่เพี้ยน)
- weight = 0 ปิด term ได้ (ยังเห็นใน log)
- **deploy ไม่มี reward** reward มีผลแค่ตอนเทรน เปลี่ยน reward จึงไม่ต้องแก้ `deploy.yaml` (ตราบใดที่ obs/action/gain เหมือนเดิม)

## ทุก term
| term | weight | ชนิด | สูตร/เจตนา (ย่อ) | CLI override |
|---|---|---|---|---|
| `track_linear_velocity` | +1.0 | รางวัล | `exp(−(‖v_xy,cmd − v_xy‖² + 2·v_z²)/0.25)` วิ่งตามคำสั่ง vx, vy | `--env.rewards.track-linear-velocity.weight` |
| `track_angular_velocity` | +1.0 | รางวัล | `exp(−err_wz²/0.5)` หมุนตามคำสั่ง | `...track-angular-velocity.weight` |
| `pose` (`variable_posture`) | +1.0 | รางวัล | ท่าใกล้ default โดย std ขึ้นกับสถานะ: ยืน 0.05 ทุกข้อต่อ / เดิน / วิ่ง (เข่า, hip pitch หลวม 0.5 ส่วน ankle roll, แขนแน่น 0.1) | `...pose.weight` |
| `foot_gait` | +0.5 | รางวัล | เท้าแตะพื้นตามจังหวะ period 0.6 s, offset [0, 0.5] (สลับซ้ายขวา) เฉพาะ cmd > 0.1 | `...foot-gait.weight` |
| `body_orientation_l2` | −1.0 | โทษ | ลำตัว (`torso_link`) เอียงจากแนวตั้ง | `...body-orientation-l2.weight` |
| `body_ang_vel` | −0.05 | โทษ | ลำตัวหมุนเร็ว (ส่าย) | `...body-ang-vel.weight` |
| `angular_momentum` | −0.025 | โทษ | โมเมนตัมเชิงมุมของทั้งตัว (แกว่งแขนขาเกิน) | `...angular-momentum.weight` |
| `is_terminated` | −200 | โทษ | จบ episode เพราะล้ม (ไม่ใช่หมดเวลา) | `...is-terminated.weight` |
| `joint_acc_l2` | −2.5e-7 | โทษ | ความเร่งข้อต่อ² (ค่าดิบใหญ่มาก weight จึงเล็ก) | `...joint-acc-l2.weight` |
| `joint_pos_limits` | −10 | โทษ | เข้าใกล้ลิมิตข้อต่อ | `...joint-pos-limits.weight` |
| `action_rate_l2` | −0.05 | โทษ | `‖action_t − action_{t−1}‖²` action กระตุก | `...action-rate-l2.weight` |
| `foot_clearance` | −1.0 | โทษ | ยกเท้าไม่ถึง 10 cm ตอนก้าว (cmd > 0.1) | `...foot-clearance.weight` |
| `foot_slip` | −0.25 | โทษ | เท้าเลื่อนขณะแตะพื้น (cmd > 0.1) | `...foot-slip.weight` |
| `soft_landing` | −1e-3 | โทษ | แรงกระแทกตอนเท้าลง | `...soft-landing.weight` |
| `stand_still` | −1.0 | โทษ | `Σ(q − q_default)²` **เฉพาะตอน cmd ≤ 0.1** ยืนแล้วต้องอยู่ท่า default | `...stand-still.weight` |
| `self_collisions` | −1.0 | โทษ | ชิ้นส่วนตัวเองชนกัน (แรง > 10 N) | `...self-collisions.weight` |

ตรวจชื่อ CLI ด้วย: `python scripts/train.py Unitree-G1-23Dof-Flat --help | grep rewards` (ต้องใช้ env `unitree_rl_mjlab`)

**termination** (ไม่ใช่ reward แต่เกี่ยวกัน): `time_out` (20 s) และ `fell_over` (เอียง > 70°) ตัวหลังทำให้ได้ `is_terminated` −200

## term ที่ดึงกัน (ตัวอย่าง)
| คู่ | ดึงกันยังไง |
|---|---|
| `track_linear_velocity` ↔ `action_rate_l2` | เดินเร็วต้องเปลี่ยน action เร็ว แต่โดนลงโทษเรื่องกระตุก |
| `track_linear_velocity` ↔ `pose` | ก้าวยาวต้องงอเข่า/hip มาก ซึ่งห่างจาก default |
| `foot_clearance` ↔ `soft_landing` | ยกเท้าสูง = ตกลงมาแรงกว่า |
| `stand_still` ↔ `track_*` ตอนคำสั่งเปลี่ยนจาก 0 | ถ้ายืนแข็งเกินไป จะออกตัวช้า |
| `is_terminated` −200 ↔ ทุกอย่าง | ล้มครั้งเดียวเสียเท่ากับรางวัล tracking เต็มๆ ~200 วินาที → policy "เล่นปลอดภัย" ก่อน |

## ตัวเลขช่วยคิด
- รางวัล tracking ได้มากสุด 1.0/s ต่อ term ตลอด 20 s
- ล้ม 1 ครั้ง = −200 (คูณ dt แล้วเป็น −4 ใน step นั้น แต่ได้ในครั้งเดียว และ episode จบ เสียรางวัลที่เหลือทั้งหมดด้วย)
- ดังนั้นถ้าเพิ่ม `track_linear_velocity` เป็น 2.0 ก็เท่ากับลดความกลัวล้มลงครึ่งหนึ่ง เมื่อเทียบกัน

## เติมเอง (งาน 5.1)
| term | ทำให้หุ่น ... | ถ้า weight = 0 คิดว่าจะเกิด ... |
|---|---|---|
| `track_linear_velocity` | | |
| `pose` | | |
| `foot_gait` | | |
| `action_rate_l2` | | |
| `stand_still` | | |
| `foot_slip` | | |
| `is_terminated` | | |

คำถามเพิ่ม:
1. `stand_still` กับ `pose` (ตอนยืน std 0.05) ทำงานคล้ายกัน ต่างกันยังไง
2. ทำไม `joint_acc_l2` weight เล็กถึง 2.5e-7
3. ถ้าจะลดการเตะขาตอนแขวนของ Hist5 คุณจะลองแก้ reward ตัวไหน (หรือแก้ด้วย reward ไม่ได้ เพราะอะไร)
