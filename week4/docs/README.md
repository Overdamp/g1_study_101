# สัปดาห์ 4: Policy: จาก LowState ถึง action ด้วยมือตัวเอง

> สถานะ: **ร่าง** (เขียน 10/11/2026) ปรับได้เมื่อเริ่มจริง
> แผนตัวจริง: vault `05 Study/Study Plan.md` · ภาพรวม: `~/g1_study/STUDY_PLAN.md`

## เป้าหมาย
1. อธิบาย pipeline ได้ครบ: `rt/lowstate` → observation 80 ตัว → `policy.onnx` → action 23 ตัว → `q_des` → PD → แรงบิด
2. เขียน **policy runner ใน Python เอง** ที่สร้าง observation จาก LowState ได้ตรงกับ g1_ctrl
3. พิสูจน์ว่าตรงจริงด้วย **shadow mode**: รันคู่กับ g1_ctrl ใน sim แล้วเทียบ `q_des` (**อ่านอย่างเดียว ไม่ส่งคำสั่ง**)

## ต่อยอดจากสัปดาห์ก่อน
| เคยทำ | สัปดาห์นี้ |
|---|---|
| `motor_state[slot].q`, dict slot → ชื่อ (1.5) | `joint_ids_map`: ลำดับข้อต่อของ policy → slot |
| IMU roll/pitch/yaw (1.6) | `projected_gravity` จาก quaternion, `base_ang_vel` จาก gyro |
| monitor `rt/lowcmd` (2.2) | อ่าน `q_des` ที่ g1_ctrl ส่ง เพื่อเทียบกับของเรา |
| PD, kp/kd ตอนเทรน (2.4–2.6) | `stiffness` / `damping` ใน `deploy.yaml` = gain ชุดเดียวกัน |
| step แล้วกระตุก (2.8) | Soft Start 0.5 s ใน `State_RLBase.cpp` |
| FSM Passive → FixStand → … (3.x) | state Velocity = `State_RLBase` (thread policy 50 Hz + FSM 1 kHz) |

## ⚠️ กฎของสัปดาห์นี้
- งาน 4.1–4.6 **ไม่ publish อะไรเลย** อ่านอย่างเดียว ปลอดภัยแม้รันคู่กับ g1_ctrl
- งาน 4.7 (ท้าทาย) ส่ง lowcmd จาก Python **ใน sim เท่านั้น** ห้ามรันพร้อม g1_ctrl (2 โปรแกรมส่ง lowcmd)
- ห้ามใช้ runner ของตัวเองกับหุ่นจริงจาก session นี้
- ทุกไฟล์ policy อ่านจาก repo หลักได้ แต่**ห้ามแก้** (ถ้าจะทดลองแก้ `deploy.yaml` ให้ก็อปมาไว้ใน `week4/`)

## โน้ตในโฟลเดอร์นี้
| ไฟล์ | อ่านเมื่อ |
|---|---|
| `policy_pipeline.md` | ก่อน 4.1: ภาพรวม, ความถี่, thread ใน g1_ctrl |
| `onnx_basics.md` | ก่อน 4.1: เปิด ONNX ใน Python, input/output, metadata |
| `observations.md` | ก่อน 4.2: obs 80 ตัวทีละ term พร้อมสูตรและโค้ด C++ ที่อ้างอิง |
| `actions.md` | ก่อน 4.3: action → q_des, `last_action`, scale ผูกกับ kp |
| `shadow_mode.md` | ก่อน 4.4: วิธีเทียบกับ g1_ctrl อย่างปลอดภัย + สาเหตุที่ค่าอาจไม่ตรง |
| vault `01 Concepts/` | `Deploy Contract`, `Observations`, `Action Scale`, `Observation History`, `Timing and Rates`, `Soft Start` |

## งาน (โฟลเดอร์ `~/g1_study/week4/`)

| งาน | ทำอะไร | แนวคิด |
|---|---|---|
| **4.1** อ่านสัญญา | `inspect_policy.py`: เปิด `v0/exported/policy.onnx` พิมพ์ input/output/metadata แล้วเทียบทีละ field กับ `v0/params/deploy.yaml` จดทุกจุดที่ต่างกัน | deploy contract |
| **4.2** obs builder | `obs.py`: ฟังก์ชัน `build_obs(msg, cmd, last_action, phase) -> np.ndarray (80,)` + เทสต์: ท่ายืนนิ่งต้องได้ `joint_pos_rel ≈ 0`, `gravity ≈ (0,0,−1)` | observation |
| **4.3** policy 1 ครั้ง | ป้อน obs "ยืนนิ่งสมบูรณ์แบบ" (สร้างเอง ไม่ใช้ sim) → action → `q_des` ทายก่อนว่า action จะใหญ่แค่ไหน | inference, action scale |
| **4.4** shadow mode | รัน g1_ctrl (sim, FixStand → Velocity, cmd = 0) + runner ของเราที่ฟัง lowstate และ lowcmd เทียบ `q_des` ทุก 20 ms บันทึก CSV | ตรวจว่าเข้าใจถูกด้วยตัวเลข |
| **4.5** IMU ทิศทาง | ใน shadow mode ลากหุ่นให้ก้ม/เอียง ดูว่า `projected_gravity` เปลี่ยนทางไหน เทียบกับ vault `Observations.md` | กรอบอ้างอิง |
| **4.6** gait phase | ในเทสต์ offline: cmd = 0 กับ cmd = (0.5, 0, 0) phase ต่างกันยังไง ทำไมตอน cmd เล็กต้องเป็น 0 | clock input |
| **4.7** (ท้าทาย) ให้ Python คุม | ต่อ mini FSM สัปดาห์ 3: Passive → Stand (interpolate 3 s) → Policy (soft start 0.5 s) เท้าแตะพื้น (ไม่แขวน) sim เท่านั้น | deploy เต็มวงจร |
| **4.8** ทำให้พัง (offline/shadow) | (ก) ลำดับข้อต่อผิด (ใช้ slot 0–22) (ข) ลืมลบ default (ค) gravity ผิดเครื่องหมาย (ง) `last_action` ใส่ q_des แทน raw action (จ) เรียก policy 1 kHz | policy ไวต่ออะไร |

### เกณฑ์ผ่าน
- 4.1: ตารางเทียบ deploy.yaml ↔ metadata ครบทุก field พร้อมระบุจุดที่ต่าง (มีอย่างน้อย 1 จุด)
- 4.2: เทสต์ผ่าน และขนาด obs = 80 ตรงกับ input ของ ONNX
- 4.4: ตอน cmd = 0 และหลัง soft start ผ่านไปแล้ว |q_des ของเรา − q_des ของ g1_ctrl| เฉลี่ย < 0.01 rad ทุกข้อต่อ (ถ้าไม่ผ่าน อธิบายได้ว่าเพราะอะไร)
- 4.8: แต่ละข้อมีตัวเลขว่า q_des ต่างจากค่าที่ถูกเท่าไหร่

## บันทึกการทาย (เขียนก่อนรัน)
| งาน | ทายว่า | ผลจริง | ถ้าต่าง ทำไม |
|---|---|---|---|
| 4.3 ยืนนิ่งสมบูรณ์แบบ |action| สูงสุดประมาณ | | | |
| 4.4 q_des ต่างจาก g1_ctrl ประมาณ (rad) | | | |
| 4.5 หุ่นก้มไปข้างหน้า gravity_x เป็น + หรือ − | | | |
| 4.8 (ก) ลำดับข้อต่อผิด: q_des เพี้ยนแค่ไหน | | | |
| 4.8 (จ) policy 1 kHz แทน 50 Hz: เกิดอะไร | | | |

## คำถามทวน (ตอบโดยไม่เปิดโน้ต)
1. observation 80 ตัวประกอบด้วยอะไรบ้าง เรียงยังไง แต่ละตัวมาจาก field ไหนของ LowState
2. `projected_gravity` คืออะไร ทำไมยืนตรงแล้วได้ (0, 0, −1) และทำไม policy ใช้มันแทน roll/pitch
3. action ของ policy ไม่ใช่มุม แปลงเป็น `q_des` ยังไง ทำไม scale ต้องผูกกับ kp
4. `last_action` เก็บค่าก่อนหรือหลังคูณ scale ถ้าเก็บผิดจะเกิดอะไร
5. policy 50 Hz แต่ส่ง lowcmd ~1 kHz ระหว่าง step ของ policy ส่งอะไรไป
6. ทำไมห้ามเอา policy สาย Hist5 เข้า Velocity ตอนแขวน

## สรุปของฉัน (เขียนเอง)
- วันที่ 1:
- วันที่ 2:
- วันที่ 3:
