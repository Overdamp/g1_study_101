# สเปค `State_HoldPose` (งาน 3.7)

> ไฟล์นี้เป็น**สเปค** ไม่ใช่เฉลย บอกว่าต้องทำอะไรและแตะไฟล์ไหน ส่วนโค้ดเขียนเอง (หรือพิมพ์ `เฉลย`)
> ทำใน `~/g1_study/week3/deploy/` เท่านั้น

## พฤติกรรมที่ต้องการ
**HoldPose** = ค้างทุกข้อต่อไว้ที่ท่าตอนกดเข้า ด้วย **kp ต่ำ** (นุ่ม ลากได้ ปล่อยแล้วกลับที่เดิม)

| ข้อ | รายละเอียด |
|---|---|
| H1 | เข้าได้จาก **Passive เท่านั้น** ด้วยคีย์ `o` (sim) และปุ่มรีโมทที่เลือกเอง (เช่น `LT + down.on_pressed`) |
| H2 | ออกไป Passive ได้ด้วย `LT + B.on_pressed` และคีย์ `p` |
| H3 | ตอนเข้า: q เป้าหมาย = **ท่าปัจจุบัน** ห้ามกระตุก |
| H4 | gain อ่านจาก `config.yaml` (`FSM: HoldPose: kp / kd`) ห้าม hard-code |
| H5 | ค่าเริ่มต้นที่แนะนำ: ใช้ gain ตอนเทรน (แขน 14.3/0.9, hip pitch/yaw+เอว 40.2/2.6, hip roll+เข่า 99.1/6.3, ข้อเท้า 28.5/1.8) หรือต่ำกว่านั้น |
| H6 | timeout ของ LowState → Passive ต้องยังทำงาน (ได้จาก FSMState อยู่แล้ว เช็คว่าไม่ได้ทำให้มันหาย) |
| H7 (ท้าทาย) | **ramp gain**: kp ไล่จาก 0 ขึ้นไปค่าเต็มใน 1 s (แนวคิดเดียวกับ Soft Start) |

## ไฟล์ที่ต้องแตะ (checklist)
ใช้ `State_Handover.h` เป็นตัวอย่างว่า "state ที่เพิ่มเอง" ต้องมีอะไรบ้าง

- [ ] **`robots/g1_23dof/include/State_HoldPose.h`** (ไฟล์ใหม่)
  - class สืบทอดจาก `FSMState`
  - constructor: อ่าน kp/kd จาก config (หรืออ่านใน `enter()` แต่ระวังเรื่อง `static`)
  - `enter()`: ตั้ง gain + ตั้ง q เป้าหมายตาม H3
  - `run()`: (ไม่มี H7) แทบไม่ต้องทำอะไร / (มี H7) คำนวณ kp ตามเวลา
  - ท้ายไฟล์: `REGISTER_FSM(State_HoldPose)`
- [ ] **`robots/g1_23dof/main.cpp`**
  - `#include "State_HoldPose.h"`
  - คีย์ `o` (Passive → HoldPose) และ `p` (HoldPose → Passive) ดูแบบจากบล็อกที่ทำให้ Handover (`key_is("h")`)
- [ ] **`robots/g1_23dof/config/config.yaml`**
  - ใน `_:` เพิ่ม `HoldPose: id: <ไม่ซ้ำ>` (**ไม่ใช่บรรทัดแรก**)
  - ใน `Passive: transitions:` เพิ่มทางไป HoldPose
  - บล็อกใหม่ `HoldPose:` มี `transitions` (กลับ Passive), `kp`, `kd` (29 ค่า เรียงตาม slot)

## คำถามออกแบบ (ตอบก่อนเขียน)
1. **H3:** q ปัจจุบันเอามาจาก `lowstate->msg_.motor_state()[i].q()` หรือ `lowcmd->msg_.motor_cmd()[i].q()` ดี ถ้าเข้าจาก Passive สองค่านี้ต่างกันไหม (ดู `State_Passive::run()` และ `State_FixStand::enter()`)
2. kp/kd ใน yaml ต้องมีกี่ค่า slot 13, 14, 20, 21, 27, 28 ใส่อะไร (ดู Passive/FixStand ใน `config.yaml`)
3. ถ้าใช้ `static auto kp = ...` ใน `enter()` เหมือน FixStand มีข้อดีข้อเสียอะไร
4. `run()` ว่างเปล่าได้ไหม แล้ว lowcmd ยังถูกส่งทุก ms ไหม (ดู `post_run()`)
5. **H7:** ต้องจำอะไรไว้ใน `enter()` เพื่อให้ `run()` รู้ว่าผ่านไปกี่วินาทีแล้ว (ดู FixStand ว่าใช้อะไร)
6. ถ้าอยู่ใน HoldPose แล้วกด `u` จะเกิดอะไร ควรเกิดอะไร

## แผนทดสอบ (ใน sim + elastic band)
| # | ทำ | คาดว่า |
|---|---|---|
| T1 | เปิด g1_ctrl | log มี `Initializing State_HoldPose ...` ไม่มี warning `not found` |
| T2 | (Passive) ลากแขนไปท่าแปลกๆ แล้วกด `o` | log `Passive to HoldPose` แขนค้างอยู่ที่เดิม ไม่กระตุก |
| T3 | ลากแขนใน HoldPose แล้วปล่อย | แขนกลับมาท่าที่จดไว้ตอนเข้า (ห้อยลงบ้างเพราะ kp ต่ำ ดู `week2/docs/pd_control.md`) |
| T4 | กด `p` | กลับ Passive แขนหนืดและห้อยลง |
| T5 | อยู่ HoldPose แล้วปิด sim | log เปลี่ยนเป็น Passive จาก timeout |
| T6 | อยู่ HoldPose แล้วกด `u` | ตรงกับคำตอบข้อ 6 ไหม |
| T7 | (ถ้ามี `read_lowstate.py` จากสัปดาห์ 1) รันคู่กันระหว่าง T2–T3 | เห็นค่า q ของศอกนิ่งตอนเข้า และกลับที่เดิมหลังลาก |
| T8 | (ถ้ามี monitor `rt/lowcmd` จากสัปดาห์ 2) | kp/kd ในคำสั่งตรงกับ yaml ทุก slot |

## หลังทำเสร็จ
- `git diff` ในสำเนา แล้วอธิบายทุกบรรทัดที่เปลี่ยนด้วยคำของตัวเอง
- ตอบคำถามทวนข้อ 4 ใน README ("เพิ่ม state ใหม่ต้องแตะกี่ที่")
- เปรียบเทียบกับ `mini_fsm.py` (3.2): ส่วนไหนของ Python ตรงกับส่วนไหนของ C++
