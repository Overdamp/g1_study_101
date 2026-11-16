# Action → q_des

อ้างอิง: `deploy/include/isaaclab/envs/mdp/actions/joint_actions.h` (`process_actions`), vault `Action Scale.md`

## สูตร
```
q_des[i] = offset[i] + scale[i] × action[i]
```
| ส่วน | มาจาก (`deploy.yaml` → `actions.JointPositionAction`) |
|---|---|
| `action[i]` | output ของ ONNX (ค่าดิบ ปกติอยู่ราว −2..+2) |
| `scale[i]` | `scale` (0.55 / 0.35 / 0.44) |
| `offset[i]` | `offset` = `default_joint_pos` |
| clip | `clip: null` = ไม่ clip |

ลำดับใน `process_actions()`: คูณ scale → บวก offset → clip (ถ้ามี) → EMA สำหรับแขน (ถ้ามี `arm_ema_alpha` ค่าเริ่มต้นคือ 1.0 = ไม่กรอง และ v0 ไม่ได้ตั้งไว้)

## ทำไม action = 0 แปลว่า "ยืนท่า default"
`q_des = offset + scale × 0 = default_joint_pos` policy จึงเรียนรู้เป็น "การเบี่ยงจากท่ายืน" ไม่ใช่มุมสัมบูรณ์ ตัวเลขจึงอยู่ในช่วงเล็กๆ ซึ่งเทรนได้ง่ายกว่า

## ทำไม scale ผูกกับ kp
vault `Action Scale.md`: `scale = 0.25 × effort_limit / kp`
ตอนข้อต่อนิ่ง แรงบิดที่ได้จาก action = 1 คือ:
```
tau = kp × (q_des − default) = kp × scale × 1 = 0.25 × effort_limit
```
แปลว่า action = 1 สร้างแรงบิด 25% ของลิมิต ทุกข้อต่อเหมือนกันหมด ถ้าเปลี่ยน kp แต่ไม่เปลี่ยน scale ความหมายของ action ก็จะเปลี่ยนไปด้วย → ต้องเทรนใหม่

ตัวอย่างข้อต่อแขน (kp 14.3, scale 0.44): action = 1 → q_des ห่าง default 0.44 rad (25°) → tau ≈ 14.3 × 0.44 ≈ 6.3 Nm

## raw กับ processed
| ชื่อ | คือ | ใช้ที่ไหน |
|---|---|---|
| `raw_actions()` / `action()` | output ของ ONNX ตรงๆ | `last_action` ใน obs step ถัดไป |
| `processed_actions()` | q_des หลังคูณ scale + offset | `State_RLBase::run()` → lowcmd |

หลัง `reset()`: raw = 0, processed = offset (ท่า default)

## จาก q_des ถึง lowcmd
`State_RLBase.cpp` `run()` ทุก 1 ms:
```cpp
lowcmd->msg_.motor_cmd()[ids[i]].q() = q_start[i] + alpha * (action[i] - q_start[i]);   // action = processed
```
ส่วน kp/kd ถูกตั้งครั้งเดียวใน `State_RLBase::enter()` จาก `stiffness`/`damping` ของ deploy.yaml และ slot ที่ไม่มีข้อต่อถูกตั้ง kp = kd = 0

## จุดที่ควรรู้
- **ไม่มี clip:** q_des อาจเกินลิมิตข้อต่อได้ (ใน sim ≤ 1% ของ step) vault มีข้อเสนอให้ใส่ clip = ลิมิตของ MJCF
- **ค่า scale ในสองที่:** deploy.yaml กับ metadata ของ ONNX ควรตรงกัน งาน 4.1 ให้เทียบเอง แล้วดูว่า g1_ctrl ใช้ตัวไหน
- งาน 4.3: obs ยืนนิ่งสมบูรณ์แบบ ถ้า policy ดี action ควรเล็ก (q_des ใกล้ default) ถ้าออกมาใหญ่ ให้สงสัยว่า obs ผิดก่อนจะสงสัย policy

## คำถามเช็ค
1. action ของเข่าซ้าย = 0.5 → q_des เท่าไหร่ (เข่า: offset 0.3, scale 0.35)
2. ทำไม `last_action` ใช้ raw ไม่ใช้ processed
3. ถ้าเปลี่ยน kp แขนจาก 14.3 เป็น 28.6 โดยไม่แตะ scale action = 1 จะได้แรงบิดเท่าไหร่ คิดเป็นกี่ % ของที่ policy "คาดหวัง"
