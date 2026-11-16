# สัปดาห์ 3: FSM: controller จริงจัดลำดับการสั่งอย่างไร

> สถานะ: **ร่าง** (เขียน 10/11/2026) ปรับได้เมื่อเริ่มจริง
> แผนตัวจริง: vault `05 Study/Study Plan.md` · ภาพรวม: `~/g1_study/STUDY_PLAN.md`

## เป้าหมาย
1. อธิบายได้ว่า `g1_ctrl` ทำงานยังไงตั้งแต่ `main()` ถึง loop 1 kHz และเปลี่ยน state เมื่อไหร่
2. เขียน **FSM เล็กๆ ใน Python เอง** (Passive → Hold → Wave) ต่อยอดจาก publisher สัปดาห์ 2
3. เพิ่ม **`State_HoldPose`** ใน g1_ctrl ภาษา C++ (ใช้สำเนาใน `~/g1_study/week3/`) build แล้วทดสอบใน sim

## ทำไมต้องมี FSM (เชื่อมกับสัปดาห์ 2)
สัปดาห์ 2 โปรแกรมทำอย่างเดียว เช่น "ค้างศอก" แต่หุ่นจริงต้องการหลายโหมด และต้องเปลี่ยนโหมดอย่าง**ปลอดภัย**:
```
เปิดโปรแกรม → หนืด (ปลอดภัย) → ค่อยๆ ยืน → ให้ policy คุม → มีปัญหา → กลับไปหนืด
```
FSM คือโครงที่บังคับว่า "ตอนนี้อยู่โหมดไหน, เข้าโหมดทำอะไร, ออกได้เมื่อไหร่" แทนการเขียน `if` ซ้อนกันเต็มไฟล์

## ต่อยอดจากสัปดาห์ก่อน
| เคยทำ | สัปดาห์นี้เจอใน g1_ctrl |
|---|---|
| callback + `Lock` (1.3) | `lowstate->update()` ใน `pre_run()` |
| `None` = ยังไม่มีข้อมูล (1.4) | `wait_for_connection()` + `isTimeout()` 100 ms → Passive |
| `--network` / `--domain` (1.7) | `main.cpp`: `take_domain_arg()`, ค่าเริ่มต้น = sim |
| damping kp=0 (2.3) | `State_Passive` |
| ค้างศอก q_des = มุมปัจจุบัน (2.4) | Passive คัดลอก q จริงเป็นคำสั่งทุกรอบ → FixStand เริ่มจากท่าจริง |
| step แล้วกระตุก (2.5, 2.8) | FixStand ไล่ท่าใน 3 s · Velocity มี Soft Start 0.5 s |
| 2 โปรแกรมส่ง lowcmd พร้อมกัน (2.8) | `init_fsm_state()` เช็คว่ามีคนส่ง lowcmd อยู่ไหม |
| CRC, `mode_machine` (2.1) | `unlockAndPublish()`, `check_mode_machine()` |

## ⚠️ กฎของสัปดาห์นี้
- **ไม่แก้ repo หลัก** (`~/nvidia/unitree/unitree_rl_mjlab`) ให้ทำในสำเนา `~/g1_study/week3/deploy/` (วิธีอยู่ใน `build_and_run.md`)
- **sim เท่านั้น**: รัน g1_ctrl สำเนาด้วยค่าเริ่มต้น (`lo`, domain 1) **ห้ามใส่ `--network enp43s0`** กับ binary ที่แก้เอง
- ห้ามรัน g1_ctrl ของจริงกับสำเนาพร้อมกัน (2 โปรแกรมส่ง lowcmd)
- อย่ารัน sim สองตัว: ใช้ `~/g1_study/start_sim.sh` ตัวเดียว (ไม่ใช้ `sim2sim_policy.sh` ซึ่งเปิด sim ของมันเอง)

## โน้ตในโฟลเดอร์นี้
| ไฟล์ | อ่านเมื่อ |
|---|---|
| `fsm_concepts.md` | ก่อน 3.1: FSM คืออะไร, enter/run/exit, transition, ทำไม Passive ต้องเป็นที่พัก |
| `g1_ctrl_architecture.md` | ก่อน 3.5: แผนที่ไฟล์, ลำดับการทำงาน, กลไกลงทะเบียน state, gotchas |
| `cpp_for_python.md` | ก่อน 3.5: C++ เท่าที่ต้องใช้อ่านไฟล์ FSM (เทียบกับ Python) |
| `build_and_run.md` | ก่อน 3.5: ทำสำเนา, build, รันกับ sim, แก้ปัญหา |
| `holdpose_spec.md` | ก่อน 3.7: สเปคของ `State_HoldPose`, ไฟล์ที่ต้องแตะ, แผนทดสอบ |
| vault `04 Code Map/FSM Code Walkthrough.md` | ไล่โค้ดทีละบรรทัด (อ้างอิงหลัก ละเอียดที่สุด) |

## งาน (โฟลเดอร์ `~/g1_study/week3/`)

### ส่วน A: FSM ใน Python (ภาษาที่ถนัด ได้แนวคิดก่อน)
| งาน | ทำอะไร | แนวคิด |
|---|---|---|
| **3.1** วาดก่อนเขียน | อ่าน `fsm_concepts.md` + vault `g1_ctrl FSM.md` แล้ววาดแผนภาพ state ของ g1_ctrl เองบนกระดาษ: state, ปุ่ม, timeout | state, transition, guard |
| **3.2** mini FSM | `mini_fsm.py`: class `State` มี `enter/run/exit` + `Passive`, `Hold` สลับด้วยคีย์บอร์ด (thread อ่าน `input()`) loop ส่ง lowcmd 500 Hz | โครงเดียวกับ `CtrlFSM::run_()` |
| **3.3** safety timeout | ถ้า LowState ไม่มาเกิน 100 ms ให้กลับ Passive ทุก state ทดสอบโดยปิด sim ระหว่างอยู่ใน Hold | `isTimeout()` |
| **3.4** Wave + เข้าแบบนุ่ม | state `Wave`: ศอกแกว่ง sine ±20° รอบมุมปัจจุบัน เริ่มจาก amplitude 0 แล้วค่อยๆ เพิ่มใน 1 s | FixStand interpolate, Soft Start |

### ส่วน B: g1_ctrl จริง (C++)
| งาน | ทำอะไร | แนวคิด |
|---|---|---|
| **3.5** build สำเนา | ทำตาม `build_and_run.md` รันกับ sim แล้วกด `u` → `v` → `p` ดู log การเปลี่ยน state | build C++, config ข้าง binary |
| **3.6** อ่านโค้ด | ตอบแบบฝึกหัด 1–4 ท้าย vault `FSM Code Walkthrough.md` จากการอ่านโค้ด แล้วทดสอบใน sim | อ่านโค้ด C++ เป็น |
| **3.7** `State_HoldPose` | เพิ่ม state ตาม `holdpose_spec.md` เข้าจาก Passive (คีย์ `o`) ออกด้วย `p` / LT + B | REGISTER_FSM, config, main.cpp |
| **3.8** ทำให้พัง | (ก) ลืม `#include` (ข) ย้าย HoldPose ขึ้นบรรทัดแรกใน `_:` (ค) แก้ `config.yaml` ระหว่างรัน (ง) กด 2 transition พร้อมกัน | gotchas ของ g1_ctrl |

### เกณฑ์ผ่าน
- 3.2: กดคีย์สลับ Passive ↔ Hold ได้ ศอกไม่กระตุกตอนเข้า Hold (ต่างจากมุมเดิม < 1°)
- 3.3: ปิด sim แล้วโปรแกรมพิมพ์ว่ากลับ Passive ภายใน ~0.1 s
- 3.4: กราฟ q ของศอกตอนเข้า Wave ไม่มีการกระโดด
- 3.5: เห็น log `FSM: Change state from Passive to FixStand` ใน terminal
- 3.7: log แสดง `Passive → HoldPose → Passive` ลากแขนใน MuJoCo ระหว่าง HoldPose แล้วแขนกลับที่เดิม

## บันทึกการทาย (เขียนก่อนรัน)
| งาน | ทายว่า | ผลจริง | ถ้าต่าง ทำไม |
|---|---|---|---|
| 3.3 ปิด sim ระหว่าง Hold โปรแกรมจะ... แขนใน sim จะ... | | | |
| 3.5 กด `v` (Velocity) ตอนหุ่นห้อย เกิดอะไร | | | |
| 3.6 ข้อ 3: LowState ขาด 150 ms ใน FixStand แล้วกลับมา อยู่ state ไหน | | | |
| 3.8 (ก) ลืม include: error ตอน compile หรือตอนรัน | | | |
| 3.8 (ข) HoldPose บรรทัดแรก: เริ่มโปรแกรมแล้วเกิดอะไร | | | |
| 3.8 (ค) แก้ kd ของ Passive ระหว่างรัน แล้วกด p มีผลไหม | | | |

## คำถามทวน (ตอบโดยไม่เปิดโน้ต)
1. `enter()`, `run()`, `exit()` ต่างกันยังไง อะไรควรอยู่ใน `enter` อะไรควรอยู่ใน `run`
2. ทำไม Passive ต้องคัดลอก q จริงเป็น q คำสั่งทุกรอบ ทั้งที่ kp = 0
3. ถ้าสองเงื่อนไข transition เป็นจริงในรอบเดียวกัน g1_ctrl เลือกอันไหน
4. เพิ่ม state ใหม่ใน g1_ctrl ต้องแตะกี่ที่ อะไรบ้าง
5. ทำไม timeout ของ LowState ป้องกันได้แค่ "ขาเข้า" แต่ป้องกัน "ขาออก" ไม่ได้
6. ทำไมคีย์บอร์ดใช้ได้เฉพาะ `--network lo`

## สรุปของฉัน (เขียนเอง)
- วันที่ 1:
- วันที่ 2:
- วันที่ 3:
