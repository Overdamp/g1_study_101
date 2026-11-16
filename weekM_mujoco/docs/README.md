# โมดูล M: MuJoCo (เสริม ทำคู่กับสัปดาห์ไหนก็ได้)

> เป้าหมาย: **ใช้ GUI คล่อง · เขียน Python API เอง · แก้ MJCF เป็น** โดยใช้หุ่น G1 23-DoF ตัวเดียวกับที่ใช้ทุกสัปดาห์
> ไม่มี DDS ไม่มีหุ่นจริง ปลอดภัย 100% (ทุกอย่างอยู่ใน process เดียว)

## ทำไมต้องเรียน
ตลอด 6 สัปดาห์ เราใช้ `unitree_mujoco` เป็นกล่องดำ (`start_sim.sh` แล้วคุยผ่าน DDS) แต่ข้างในมันมีแค่นี้:

```
loop ทุก 2 ms (timestep 0.002):
  ElasticBand → d.xfrc_applied[torso]                       (main.cc:488–500)
  ctrl[i] = tau + kp(q_des − sensordata[i]) + kd(dq_des − sensordata[i+29])   (bridge.h:183)
  mj_step(m, d)
  LowState.motor_state[i].q = sensordata[i] ...  → publish rt/lowstate          (bridge.h:192)
```

เมื่อจบโมดูลนี้ คุณจะเขียนส่วนที่ไม่ใช่ DDS ของ unitree_mujoco ขึ้นมาเองได้ (M3 + M4) และรัน policy ได้โดยไม่ต้องมี g1_ctrl (M7)

## งาน
| # | งาน | ไฟล์ | ทักษะ | ใช้กี่นาที |
|---|---|---|---|---|
| **M0** | ฝึก GUI: เปิดโมเดล, หมุนกล้อง, เลือก body, ลาก, ดู contact/แรง, slider | `gui.md` | GUI | 30 |
| **M1** | สำรวจ MjModel: ทำไม nq = 36, ข้อต่อหลอก 6 ตัว, actuator = slot | `m1_inspect.py` | API | 45 |
| **M2** | qpos / ท่าทาง / ความสูงที่เท้าแตะพื้น / quaternion → projected gravity | `m2_pose.py` | API | 45 |
| **M3** | step loop + viewer + หนังยาง (แปลจาก C++) | `m3_band.py` | API + GUI | 45 |
| **M4** | PD เองแบบ bridge · ปล่อยหนังยาง · step ศอก | `m4_pd.py` | API | 60 |
| **M5** | แก้ MJCF: MjSpec + แก้ไฟล์ด้วยมือ · frictionloss กับศอก +69.3° | `m5_mjcf.py` | MJCF | 60 |
| **M6** | contact, แรงที่เท้า, IMU sensor | `m6_contact.py` | API + GUI | 45 |
| **M7** | policy v0 ใน MuJoCo ล้วน · ขั้นบันได · timestep | `m7_policy.py` | ทั้งหมด | 60 |
| M8 (ท้าทาย) | เปลี่ยน `m7` ให้คุมด้วยคีย์บอร์ดใน viewer (key_callback → cmd) | เขียนเอง | | |

ลำดับแนะนำ: M0 → (เติม `g1mj_skeleton.py` ทีละส่วนไปพร้อม M1–M6) → M7

## ไฟล์
```
weekM_mujoco/
  docs/        README (ไฟล์นี้) · gui.md · python_api.md · mjcf.md
  scripts/
    skelatons/ g1mj_skeleton.py (ไลบรารี + เทสต์ 17 ข้อ) · m1–m7 (โครง TODO)
    complete/  g1mj.py · m1–m7 (เฉลย ทดสอบแล้ว)
  models/      XML ที่คุณเขียน/แก้เอง (สร้างตอนรัน m5 --save)
```

## สภาพแวดล้อม
- ใช้ **`python3` ของระบบ** (มี mujoco 3.14, onnxruntime, yaml, numpy) **ไม่ใช่** `conda activate g1_sdk`
  ถ้า conda เปิดอยู่: `conda deactivate` หรือพิมพ์ `/usr/bin/python3` ตรงๆ
- VS Code ขึ้นเส้นแดง `Cannot find module mujoco`: เลือก interpreter เป็น `/usr/bin/python3` (Ctrl+Shift+P → Python: Select Interpreter)
- ไม่ต้องเปิด `start_sim.sh` (ไม่ใช้ DDS) และไม่ชนกับ sim ที่เปิดอยู่
- ทุกสคริปต์มี `--headless` (ไม่เปิดหน้าต่าง วิ่งเร็วสุด) ถ้าไม่ใส่จะเปิด viewer แบบ real-time

## ผลจริงที่ได้ตอนเขียนเฉลย (13/11/2026) ใช้เทียบกับที่ทาย
| งาน | ผล |
|---|---|
| M1 | nq 36 = 7 + 29, nv 35 = 6 + 29, nu 29 · ข้อต่อหลอก 6 ตัว = body มวล 1 g ลอยที่ z = 20 m · slot 13 อยู่ที่ qpos[30] |
| M2 | ท่า default: pelvis 0.784 m ตอนเท้าแตะพื้น (ท่า q = 0: 0.792) · ก้ม 10° → gx = +0.174 |
| M3 | pelvis นิ่งที่ 1.33 m (= 3 − 335/200) · ศอกซ้าย +64.7° ที่ 4 s |
| M4 | ปล่อยหนังยางแล้ว PD อย่างเดียวล้มภายใน ~1.5 s · step ศอก rise ~115–150 ms · ตัด D: overshoot +65–73% |
| M5 | frictionloss 0.2: ศอก 64° (4 s) → 69° (90 s) **= ที่มาของ +69.3° ในงาน 1.4** (soft friction → creep) |
| M6 | เท้า L + R + หนังยาง = 334 N ≈ mg 335 N · contact 4 จุดต่อเท้า · accelerometer ยืนนิ่ง = +9.8 |
| M7 | พื้นเรียบ 0.5 m/s ไม่ล้ม 4.5 m/10 s · ขั้น 1–2 cm ผ่าน · **3 cm ขึ้นไปสะดุดล้ม** · timestep 0.005 ก็ยังเดินได้ |

## บั๊กที่เจอระหว่างเขียน (เอาไว้เรียน)
- `import mujoco.viewer` **ในฟังก์ชัน** ทำให้ `mujoco` กลายเป็นตัวแปร local ของฟังก์ชันนั้น → `NameError: free variable 'mujoco' referenced before assignment` (เรื่องเดียวกับคำถาม UnboundLocalError สัปดาห์ 1) แก้ด้วย `from mujoco import viewer as mjviewer`
- ปิด viewer แล้วโปรแกรมจบทันที → บางครั้ง `Segmentation fault` ตอนออก แก้ด้วย `time.sleep(0.5)` หลัง `with launch_passive(...)`
- `sensordata` หลัง `mj_step` ช้ากว่า `qpos` 1 step (sensor คำนวณก่อน integrate) → bridge ของ unitree_mujoco จึงมี delay ในตัว 2 ms

## เช็คลิสต์จบโมดูล
- [ ] อธิบายได้ว่า MjModel กับ MjData ต่างกันอย่างไร และอะไรอยู่ฝั่งไหน (มวล? qpos? ctrl? timestep?)
- [ ] หา qpos ของข้อต่อจาก "ชื่อ" ได้ 2 วิธี (`m.joint(name).qposadr` และผ่าน actuator/slot)
- [ ] บอกได้ว่า `mj_step` กับ `mj_forward` ต่างกันอย่างไร และเมื่อไรต้องเรียก `mj_forward`
- [ ] แก้ค่าในโมเดลได้ทั้งแบบ MjSpec และแบบแก้ XML แล้วโหลดใหม่
- [ ] ใน GUI: หยุด, step ทีละ 1, ลากหุ่น, เปิดดู contact force, เปิดแผง sensor ได้โดยไม่ต้องดูโน้ต
- [ ] อธิบายได้ว่า +69.3° ในงาน 1.4 มาจากไหน
