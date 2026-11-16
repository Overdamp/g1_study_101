# LowState: มีอะไรบ้าง

ที่มา: `~/nvidia/unitree/unitree_sdk2_python/unitree_sdk2py/idl/unitree_hg/msg/dds_/_LowState_.py`, `_MotorState_.py`, `_IMUState_.py`

## โครงสร้าง
```
LowState_
├── version[2]          uint32
├── mode_pr             uint8     โหมดข้อเท้า (0 = PR pitch/roll)
├── mode_machine        uint8     รุ่นหุ่น (23-DoF = 4, 29-DoF = 5)
├── tick                uint32    ตัวนับ (sim: เวลา sim เป็น ms)
├── imu_state           IMUState_
│   ├── quaternion[4]   float32   (w, x, y, z)
│   ├── gyroscope[3]    float32   rad/s  ความเร็วเชิงมุมของลำตัว
│   ├── accelerometer[3] float32  m/s²
│   ├── rpy[3]          float32   rad    roll, pitch, yaw
│   └── temperature     int16     °C
├── motor_state[35]     MotorState_     ← slot 0..34 (G1 ใช้ 0..28)
│   ├── mode            uint8
│   ├── q               float32   rad    มุมข้อต่อ (encoder)
│   ├── dq              float32   rad/s  ความเร็ว
│   ├── ddq             float32   rad/s² ความเร่ง
│   ├── tau_est         float32   Nm     แรงบิดประมาณจากกระแส (คลาด ±10–20%)
│   ├── temperature[2]  int16     °C     อุณหภูมิ 2 จุด
│   ├── vol             float32   V      แรงดัน (~52 V) · 0 = มอเตอร์ไม่ตอบ
│   ├── sensor[2], motorstate (flag error, 0 = ปกติ), reserve[4]
├── wireless_remote[40] uint8     ปุ่มรีโมท (bytes)
├── reserve[4]
└── crc                 uint32
```

เข้าถึงใน Python:
```python
msg.motor_state[18].q              # มุมศอกซ้าย [rad]
msg.motor_state[18].temperature    # list 2 ค่า → [0] = จุดแรก
msg.imu_state.rpy[1]               # pitch [rad]
msg.mode_machine                   # 4
```
ดูเองด้วย `help(LowState_)`, `dir(msg.motor_state[0])`

## slot map (23-DoF)
| slot | ข้อต่อ | | slot | ข้อต่อ |
|---|---|---|---|---|
| 0 | left_hip_pitch | | 15 | left_shoulder_pitch |
| 1 | left_hip_roll | | 16 | left_shoulder_roll |
| 2 | left_hip_yaw | | 17 | left_shoulder_yaw |
| 3 | left_knee | | **18** | **left_elbow** |
| 4 | left_ankle_pitch | | 19 | left_wrist_roll |
| 5 | left_ankle_roll | | ~~20, 21~~ | (wrist pitch/yaw ไม่มี) |
| 6 | right_hip_pitch | | 22 | right_shoulder_pitch |
| 7 | right_hip_roll | | 23 | right_shoulder_roll |
| 8 | right_hip_yaw | | 24 | right_shoulder_yaw |
| 9 | right_knee | | **25** | **right_elbow** |
| 10 | right_ankle_pitch | | 26 | right_wrist_roll |
| 11 | right_ankle_roll | | ~~27, 28~~ | (wrist pitch/yaw ไม่มี) |
| 12 | waist_yaw | | | |
| ~~13, 14~~ | (waist roll/pitch ล็อก) | | | |

**ทำไม 35 ช่อง แต่ใช้ 23:** message ชุด `unitree_hg` ออกแบบให้ใช้ร่วมกับหุ่นหลายรุ่น (เผื่อไว้ 35) ส่วน G1 ใช้ slot 0–28 ตามรุ่น 29-DoF และรุ่น 23-DoF ไม่มีเอว roll/pitch กับข้อมือ pitch/yaw จึงว่าง 6 ช่อง
**วิธีวนในโค้ด:** ใช้ dict `{slot: ชื่อ}` แล้ววน `.items()` จะได้ครบ 23 ข้อต่อและข้ามช่องว่างไปเอง (`range(23)` จะผิดตั้งแต่ slot 13)

## หน่วยและการแปลง
| ค่า | หน่วย | แปลง |
|---|---|---|
| q, rpy | rad | `math.degrees(x)` หรือ `x * 180 / math.pi` |
| dq, gyroscope | rad/s | |
| tau_est | Nm | |
| temperature | °C (จำนวนเต็ม) | |

## sim กับหุ่นจริงต่างกันยังไง
| field | sim (unitree_mujoco) | หุ่นจริง |
|---|---|---|
| อัตรา | ~905 Hz (วัดในงาน 1.3: bridge ตั้งไว้ 1 ms ต่อรอบ แต่ทำงาน+นอน) | ~1000–1056 Hz (~350 Hz ตอนเพิ่งบูต) |
| `mode_machine` | 4 (ดูจากชื่อ scene ว่ามี "23") | 4 |
| `temperature` | 0 (ไม่จำลองความร้อน) | 32–54 °C |
| `vol` | 0 ทุกตัว | ~52 V · 0 บางตัว = มอเตอร์ offline |
| `imu_state.rpy` | คำนวณจาก quaternion ของ sim | จาก IMU จริง |
| `wireless_remote` | ว่าง (ไม่มีรีโมท) | ปุ่มรีโมท |
| `tick` | เวลา sim / 1 ms | ตัวนับของ board |

**ใช้แยก sim/จริงได้:** `vol` = 0 ทุกตัว → sim (สคริปต์ของ repo ใช้หลักนี้)

## IMU: roll / pitch / yaw
| | หมุนรอบแกน | หุ่นทำท่า |
|---|---|---|
| roll `rpy[0]` | x (หน้า) | เอียงซ้าย/ขวา |
| pitch `rpy[1]` | y (ซ้าย) | ก้ม/เงย |
| yaw `rpy[2]` | z (บน) | หันซ้าย/ขวา |
- yaw ไม่มีจุดอ้างอิงที่แน่นอน (ไม่มีเข็มทิศ) มันขึ้นกับว่าเริ่มนับตอนไหน ส่วน roll/pitch อ้างอิงกับแรงโน้มถ่วง
- หุ่นจริง 28/10: ยืนตรง gyro bias ≤ 0.0014 rad/s (vault `Real Robot Results.md`)
- สัปดาห์ 4: policy ไม่ได้ใช้ rpy แต่ใช้ `projected_gravity` ที่คำนวณจาก quaternion

## ค่าที่เคยวัด (ใช้เทียบ)
| ค่า | ผล |
|---|---|
| sim Hz | ~905 (1.3) |
| ศอกซ้ายห้อยใน sim | +69.3° (1.4) |
| หุ่นจริง LowState | 1044 Hz, gap สูงสุด 60 ms (28/10) |
| หุ่นจริง encoder noise | ~0.0001 rad |
| หุ่นจริงอุณหภูมิ | 36–51 °C (28/10), ≤ 54 °C (3/11) |

## คำถามเช็ค
1. `msg.motor_state[13].q` ใน sim กับหุ่นจริงจะได้ค่าอะไร
2. ทำไม `temperature` ต้องเขียน `[0]`
3. ถ้าเห็น `vol` = 0 แค่ slot 25 และ 26 แต่ตัวอื่น ~52 V แปลว่าอะไร (vault `Incident Motors 25-26.md`)
