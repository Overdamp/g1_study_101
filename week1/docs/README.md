# สัปดาห์ 1: DDS และข้อมูลหุ่น: อ่าน `rt/lowstate` ด้วยโค้ดของตัวเอง

> แผนตัวจริง (checkbox, บันทึกการทาย): vault `05 Study/Study Plan.md` · ภาพรวม: `~/g1_study/STUDY_PLAN.md`
> สถานะ (10/11/2026): 1.1–1.4 ✅ · 1.5–1.8 ยังไม่ได้ทำ

## เป้าหมาย
1. เขียนโปรแกรมอ่าน `rt/lowstate` จาก sim ได้เอง โดยไม่ต้องก็อปจาก repo
2. อธิบายได้ว่าข้อมูลเดินทางจาก sim มาถึง `print` ของเราได้ยังไง (DDS, domain, multicast, topic, type, callback, thread)
3. รู้ว่าข้อมูลแต่ละ field ใน LowState คืออะไร หน่วยอะไร อยู่ slot ไหน
4. วินิจฉัยอาการ "เงียบไม่มี error" ได้เอง

## ภาพรวม: ข้อมูลเดินทางยังไง
```
unitree_mujoco (sim)                                        read_lowstate.py
  physics 500 Hz                                              │
  bridge RecurrentThread 1 ms ──publish──▶ DDS ──▶ [thread ของ SDK] handler(msg)  ← callback เก็บค่า + Lock
                     topic "rt/lowstate"   domain 1                     │
                     type  unitree_hg LowState_   บน lo (multicast)     ▼
                                                              [main thread] ตื่นทุก 0.5–1 s → อ่านค่า (Lock) → print
```

## ⚠️ กฎ
- แบบฝึกหัดทั้งหมด**อ่านอย่างเดียว** ไม่มีการส่งคำสั่ง
- งาน 1.7 ลองกับหุ่นจริงได้ (อ่านอย่างเดียว ปลอดภัย) เมื่อหุ่นแขวนรอก และต้องตั้ง network ถูกต้อง (`dds_basics.md`)
- อย่าเปิด sim สองตัวพร้อมกัน

## โน้ตในโฟลเดอร์นี้
| ไฟล์ | อ่านเมื่อ |
|---|---|
| `dds_basics.md` | ก่อน 1.1: DDS, domain, topic, type, multicast, `rt/`, ต่อหุ่นจริง |
| `lowstate_fields.md` | ก่อน 1.4: LowState มีอะไร, slot map, หน่วย, ค่าใน sim กับหุ่นจริง |
| `threading_and_lock.md` | ก่อน 1.3: thread, race condition, Lock |
| `python_notes.md` | เมื่อติด syntax: callback, class, type hints, f-string, argparse, หา API เอง |
| `debug_checklist.md` | เมื่อไม่มีข้อมูลเข้า + งาน 1.8 (ทำให้พัง) |
| vault `01 Concepts/` | `DDS and Domains`, `LowState and LowCmd`, `Joint Map and Slots` |

## สคริปต์
| โฟลเดอร์ | อะไร |
|---|---|
| `scripts/skelatons/read_lowstate_skeleton.py` | โครงให้เติมเอง TODO 1.2–1.7 ในไฟล์เดียว |
| `scripts/complete/` | เฉลยแยกไฟล์ตามงาน (`t1_2_hello.py` … `read_lowstate.py`) พร้อม comment ละเอียด |
| `scripts/read_lowstate.py` | ไฟล์ที่คุณเขียนเอง |

## งาน
| งาน | ทำอะไร | แนวคิด | สถานะ |
|---|---|---|---|
| **1.1** เปิด sim | `~/g1_study/start_sim.sh` เห็นหุ่นห้อยด้วย elastic band | domain 1, `lo`, multicast | ✅ |
| **1.2** hello | พิมพ์ทุกครั้งที่ได้ LowState | `ChannelFactoryInitialize`, `ChannelSubscriber`, callback | ✅ |
| **1.3** Hz | นับข้อความต่อวินาที พิมพ์ทุก 1 s | thread, `Lock`, `time.monotonic()` | ✅ ~905 Hz |
| **1.4** ศอกซ้าย | มุม slot 18 เป็นองศา ลากแขนดูค่าเปลี่ยน | `motor_state[i].q`, rad→deg, `None` | ✅ +69.3° |
| **1.5** ตาราง 23 ข้อต่อ | ชื่อ, q, dq, อุณหภูมิ ทุก 0.5 s | dict slot→ชื่อ, เก็บทั้ง msg, f-string จัดคอลัมน์ | ⬜ |
| **1.6** IMU | roll/pitch/yaw เป็นองศา + `mode_machine` | `imu_state.rpy`, เช็ค = 4 | ⬜ |
| **1.7** argparse | `--network` / `--domain` ใช้กับหุ่นจริงได้ | argparse, sim เป็นค่าเริ่มต้น, ป้ายบอก SIM/REAL | ⬜ |
| **1.8** ทำให้พัง | domain ผิด / ปิด multicast `lo` / topic ผิด / type ผิด | อาการเงียบไม่มี error | ⬜ |

### เกณฑ์ผ่าน
- 1.5: ตาราง 23 แถวพอดี (ไม่มี slot 13, 14, 20, 21, 27, 28) อัพเดททับที่เดิม ลากแขนแล้วแถวที่ถูกต้องเปลี่ยน
- 1.6: ก้ม/เอียงหุ่นใน MuJoCo แล้ว pitch/roll เปลี่ยนถูกแกน · `mode_machine` แสดง 4
- 1.7: ไม่ใส่ flag = sim · `--network enp43s0` = domain 0 ให้เอง · บรรทัดแรกบอกชัดว่า SIM หรือ REAL
- 1.8: ทุกการทดลองมีคำทายกับผลจริง และอธิบายได้ว่าทำไมไม่มี error

## บันทึกการทาย (เขียนลงแผนใน vault)
| งาน | ทายว่า | ผลจริง | ถ้าต่าง ทำไม |
|---|---|---|---|
| 1.3 Hz | (ไม่ได้ทาย) | ~905 Hz | sim ตั้งไว้ 1000 Hz แต่ทำงาน+นอน 1 ms ต่อรอบ |
| 1.4 ศอกตอนห้อย | 40° | +69.3° | ไม่มีใครคุม ข้อต่อหยุดที่ friction (`frictionloss 0.2`) ชนะแรงโน้มถ่วง |
| 1.5 dq ตอนห้อยนิ่ง | | | |
| 1.6 yaw ตอนเริ่ม sim | | | |
| 1.8 domain ผิด | | | |
| 1.8 ปิด multicast | | | |

## คำถามทวน (ตอบโดยไม่เปิดโน้ต)
1. DDS คืออะไร ต่างจากการเรียกฟังก์ชันตรงๆ อย่างไร
2. `ChannelFactoryInitialize(domain, iface)` สองค่านี้คืออะไร ทำไม sim ใช้ 1 แต่หุ่นจริงใช้ 0
3. callback ถูกเรียกเมื่อไหร่ อยู่ thread เดียวกับ `main` ไหม
4. ทำไม LowState มี 35 ช่องมอเตอร์ แต่หุ่นเรามี 23 ข้อต่อ ช่องไหนว่าง
5. ทำไมต้องเปิด multicast บน `lo` แต่หุ่นจริงไม่ต้อง
6. ระบุ 4 สาเหตุที่ทำให้โปรแกรม "เงียบไม่มี error"

## สรุปของฉัน (เขียนเอง)
- วันที่ 1:
- วันที่ 2:
- วันที่ 3:
