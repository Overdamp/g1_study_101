# สัปดาห์ 2: PD control: สั่งข้อต่อเดียวผ่าน `rt/lowcmd` (sim เท่านั้น)

> สถานะ: **ร่าง** (เขียน 10/11/2026 ก่อนจบสัปดาห์ 1) ปรับได้เมื่อเริ่มจริง
> แผนตัวจริง: vault `05 Study/Study Plan.md` · ภาพรวม: `~/g1_study/STUDY_PLAN.md`

## เป้าหมาย
1. ส่ง `rt/lowcmd` ให้**ศอกซ้าย (slot 18)** ขยับใน sim ได้เอง โดยข้อต่ออื่นไม่พัง
2. เข้าใจว่า `kp` / `kd` ทำอะไรทาง**ฟิสิกส์** และวัดผลเป็นตัวเลขได้ (rise time, overshoot)
3. รู้ว่าทำไมคำสั่งต้องมี `mode`, `mode_machine`, `crc` และอะไรต่างระหว่าง sim กับหุ่นจริง

## ต่อยอดจากสัปดาห์ 1
| สัปดาห์ 1 | สัปดาห์ 2 |
|---|---|
| `ChannelSubscriber` รับ `rt/lowstate` | เพิ่ม `ChannelPublisher` ส่ง `rt/lowcmd` |
| callback เก็บ state ล่าสุด + `Lock` | loop ส่งคำสั่งต้องอ่าน state ล่าสุดแบบปลอดภัย (lock เดิม) |
| `motor_state[18].q` | `motor_cmd[18].q / kp / kd` |
| main ตื่นทุก 0.5–1 s | loop ส่งคำสั่งทุก **2 ms** (500 Hz) |

## ⚠️ ความปลอดภัย (อ่านก่อนเริ่ม)
- **sim เท่านั้น** = `ChannelFactoryInitialize(1, "lo")`
- **ห้ามส่ง `rt/lowcmd` ไป `enp43s0` (หุ่นจริง) จากแบบฝึกหัด** ถ้าอยากลองกับหุ่นจริง ให้ไปทำใน session งานหลัก (หุ่นแขวน, `motion_mode.py release`, L2 + B)
- แนะนำให้ใส่ guard ไว้บนสุดของทุกไฟล์ใน `week2/` เช่น ถ้า interface ไม่ใช่ `"lo"` ให้หยุดโปรแกรมทันที
- อย่าเปิด sim สองตัว หรือส่ง lowcmd จากสองโปรแกรมพร้อมกัน (เหตุผลดูใน `sim_vs_real.md`)

## โน้ตในโฟลเดอร์นี้
| ไฟล์ | อ่านเมื่อ |
|---|---|
| `lowcmd_structure.md` | ก่อนงาน 2.1: LowCmd มี field อะไร แต่ละตัวทำอะไร |
| `pd_control.md` | ก่อนงาน 2.4: สูตร PD, kp/kd ทางฟิสิกส์, gain ของหุ่นเรา |
| `sim_vs_real.md` | ก่อนงาน 2.8: sim คำนวณคำสั่งยังไง ต่างจากหุ่นจริงตรงไหน |

## งาน (โฟลเดอร์ `~/g1_study/week2/`)

| งาน | ทำอะไร | แนวคิด |
|---|---|---|
| **2.1** อ่านก่อนเขียน | เปิด `_LowCmd_.py`, `_MotorCmd_.py` แล้วเติมตารางใน `lowcmd_structure.md` ด้วยคำของตัวเอง | โครง message |
| **2.2** ส่งคำสั่งว่าง | `send_zero.py`: ส่ง LowCmd ที่ทุกค่าเป็น 0 ทุก 2 ms (มี CRC) แล้วเปิด monitor ฟัง `rt/lowcmd` อีกตัว | `ChannelPublisher`, `RecurrentThread`, `CRC` |
| **2.3** damping ทั้งตัว | ทุกข้อต่อ `kp = 0`, `kd > 0` แล้วลากแขนใน MuJoCo เทียบกับตอนไม่ส่งอะไร | kd = โช้ค |
| **2.4** ค้างศอก | ศอกซ้าย `kp 14.3 / kd 0.9`, `q_des` = มุมปัจจุบัน (อ่านจาก lowstate ก่อน) ลากแขนแล้วปล่อย | kp = สปริง |
| **2.5** step | เปลี่ยน `q_des` ของศอกขึ้น +30° ทันที บันทึก `t, q, dq, tau_est` ลง CSV | step response |
| **2.6** เทียบ gain | kp 5 / 14.3 / 40 (kd ตามสัดส่วน) และ kd = 0 วัด rise time, overshoot | trade-off ของ kp/kd |
| **2.7** คำนวณ tau เอง | `tau = kp(q_des − q) + kd(0 − dq)` จาก state แล้วเทียบกับ `tau_est` ทุกแถวใน CSV | sim ใช้สูตรนี้จริงไหม |
| **2.8** ทำให้พัง | (ก) ไม่ใส่ CRC (ข) `mode = 0` (ค) หยุดโปรแกรมกลางทาง (ง) `q_des` กระโดด 90° ทันที | sim ≠ หุ่นจริง |

### เกณฑ์ผ่านแต่ละงาน
- 2.2: monitor เห็น `rt/lowcmd` ~500 Hz และหุ่นใน sim **ไม่เปลี่ยน**
- 2.4: ลากศอกแล้วปล่อย ศอกกลับมาที่เดิม (คลาดเคลื่อน < 2°)
- 2.5–2.6: มีกราฟ q(t) อย่างน้อย 3 เส้นบนรูปเดียว พร้อมตัวเลข rise time
- 2.7: tau ที่คำนวณเองกับ `tau_est` ต่างกันน้อย และอธิบายได้ว่าต่างเพราะอะไร

## บันทึกการทาย (เขียนก่อนรัน)
| งาน | ทายว่า | ผลจริง | ถ้าต่าง ทำไม |
|---|---|---|---|
| 2.2 ส่งคำสั่ง 0 ทั้งหมด หุ่นจะ... | | | |
| 2.3 ลากแขนตอน damping รู้สึกต่างไหม | | | |
| 2.4 ห้อยค้างแล้ว ศอกจะคลาดจากเป้ากี่องศา | | | |
| 2.6 kp 40 vs 5: rise time ต่างกันกี่เท่า | | | |
| 2.6 kd = 0 จะเกิดอะไร | | | |
| 2.8 (ก) ไม่ใส่ CRC ใน sim | | | |
| 2.8 (ค) หยุดโปรแกรมกลางทาง แขนจะ... | | | |

## คำถามทวน (ตอบโดยไม่เปิดโน้ต)
1. kp กับ kd ทำหน้าที่ต่างกันอย่างไรทางฟิสิกส์ หน่วยของแต่ละตัวคืออะไร
2. ทำไม kp สูงเกินไปแล้วสั่น และทำไม kd ช่วยได้
3. ตอนห้อยค้าง ทำไมข้อต่อไม่ถึงเป้าพอดี (ห่างเท่าไหร่ ขึ้นกับอะไร)
4. CRC มีไว้ทำอะไร ถ้าหุ่นจริงได้ CRC ผิดจะทำอะไร
5. ทำไมต้องส่งคำสั่งต่อเนื่องทุก 2 ms ไม่ส่งครั้งเดียวแล้วจบ
6. ทำไม policy ต้อง deploy ด้วย kp/kd ชุดเดียวกับตอนเทรน

## แหล่งอ้างอิง
- ตัวอย่าง: `~/nvidia/unitree/unitree_sdk2_python/example/g1/low_level/g1_low_level_example.py` (ดู `LowCmdWrite`, `crc`, `mode_machine`)
- message: `unitree_sdk2py/idl/unitree_hg/msg/dds_/_LowCmd_.py`, `_MotorCmd_.py` · ค่าเริ่มต้น: `unitree_sdk2py/idl/default.py`
- CRC: `unitree_sdk2py/utils/crc.py` · thread ตามคาบ: `unitree_sdk2py/utils/thread.py`
- sim: `~/nvidia/unitree/unitree_mujoco/simulate/src/unitree_sdk2_bridge.h` (`run()`)
- vault: `01 Concepts/PD Control.md`, `Armature and Gains.md`, `LowState and LowCmd.md`
- เฉลยระดับโปร: `~/nvidia/unitree/unitree_rl_mjlab/deploy/robots/g1_23dof/scripts/pd_check.py`

## สรุปของฉัน (เขียนเอง)
- วันที่ 1:
- วันที่ 2:
- วันที่ 3:
