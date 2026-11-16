# โมดูล M: ฉบับสมบูรณ์ (เฉลย)

> โครงให้ฝึกเขียนเองอยู่ใน `../skelatons/` · ใช้ `python3` ของระบบ (ไม่ใช่ conda) · ไม่ใช้ DDS ไม่ชนกับ sim

| ไฟล์ | งาน | อะไร |
|---|---|---|
| `g1mj.py` | ทั้งหมด | load / build_model (MjSpec) / save_xml / slot_table / motor_q,dq,tau / load_deploy / set_pose / pd_ctrl / ElasticBand / projected_gravity / foot_forces / to_lowstate / run (viewer หรือ headless) + เทสต์ 17 ข้อ |
| `m1_inspect.py` | M1 | ขนาดโมเดล, ตาราง joint / actuator (= slot) / ข้อต่อหลอก / sensor |
| `m2_pose.py` | M2 | ตั้งท่า default, binary search ความสูงที่เท้าแตะพื้น, ก้ม → projected gravity เทียบ Rᵀg |
| `m3_band.py` | M3 | หนังยาง (แปลจาก main.cc) + viewer ปุ่ม 9/7/8 |
| `m4_pd.py` | M4 | PD แบบ bridge · `--drop` ปล่อยหนังยาง · `--elbow-step` วัด rise/overshoot |
| `m5_mjcf.py` | M5 | `--sweep` frictionloss × เวลา · `--save` เขียน XML · `--xml` โหลดไฟล์ที่แก้มือ |
| `m6_contact.py` | M6 | แรงเท้า + หนังยาง = mg · ตาราง contact · IMU vs qpos (lag 1 step) · accelerometer = +g |
| `m7_policy.py` | M7 | policy v0 ใน MuJoCo ล้วน (ใช้ week4 obs.py) · `--step` ขั้นบันได · `--timestep` |

## รัน
```bash
cd ~/g1_study/weekM_mujoco/scripts/complete
python3 g1mj.py                                  # เทสต์ 17/17
python3 m1_inspect.py
python3 m2_pose.py --pitch 10 --view
python3 m3_band.py                               # หน้าต่าง (Space / 9 / 7 / 8)
python3 m4_pd.py --drop 3
python3 m4_pd.py --elbow-step --headless
python3 m5_mjcf.py --sweep                       # ~10 วินาที
python3 m6_contact.py                            # กด C, F ในหน้าต่าง
python3 m7_policy.py                             # เดิน 0.5 m/s
python3 m7_policy.py --headless --step 0.03
```

## ผลทดสอบ (13/11/2026, mujoco 3.14.0)
| สคริปต์ | ผล |
|---|---|
| `g1mj.py` | 17/17 PASS |
| `m2` | pelvis แตะพื้นที่ 0.784 m (ท่า default) · ก้ม 10° → projected gravity (0.174, 0, −0.985) ตรงกับ Rᵀg |
| `m3` | pelvis นิ่ง 1.33 m (สูตร 3 − 335/200 = 1.33 ✅) · ศอก +64.7° ที่ 4 s |
| `m4 --drop 3` | ห้อยอยู่: error ข้อต่อ max 3.2° · ปล่อยแล้วเอียง 15° ที่ 4 s, ล้มนอนที่ 4.5 s |
| `m4 --elbow-step` | rise 114 ms (ขึ้น) / 150 ms (ลง) · ขาลงค้าง 94% (แรงโน้มถ่วง+แรงเสียดทาน vs kp 14.3) · kd 0 → overshoot +65–73% |
| `m5 --sweep` | 0.2: 64.3° (1 s) → 68.7° (90 s) · 0.1 ไหลลงจาก 71.7° → 69.2° · ทุกค่าเข้าหา ~69° |
| `m6` | L 84.8 + R 84.9 + หนังยาง 164.7 = 334.4 N (mg 334.9) · 8 contact · sensor lag 1e-4 หายหลัง mj_forward |
| `m7` | พื้นเรียบ 4.55 m ใน 10 s ไม่ล้ม · step 1, 2 cm ผ่าน · 3, 5, 8 cm ล้มที่ ~3.3 s · timestep 0.005 เดินได้ 4.79 m · หมุน 0.8 rad/s ได้จริง ~0.6 rad/s |
| viewer | `m3`, `m7` เปิดหน้าต่าง real-time ได้ (ต้องมี `sleep(0.5)` ตอนจบ ไม่งั้น segfault) |

## เจอระหว่างทำ
- **ปริศนา +69.3° (งาน 1.4) คลายแล้ว:** frictionloss ของ MuJoCo เป็น soft constraint ศอกจึงค่อยๆ ไหลเข้าหาจุดสมดุลของแรงโน้มถ่วง (~69°) ช้าๆ ไม่ได้ค้างนิ่งจริง
- **หนังยางของ unitree_mujoco วัดระยะจาก pelvis แต่ดึงที่ torso_link** และไม่มีเงื่อนไขสายหย่อน (length ยาวเกิน = ดันลง)
- **PD ค้างท่า ≠ ทรงตัว:** gain เดียวกับตอนเทรนยังล้มภายใน 1.5 s เมื่อไม่มีหนังยาง → งานทรงตัวเป็นของ policy
- **v0 สะดุดขั้น 3 cm** (เทรนพื้นเรียบ ไม่มี height scan) → สอดคล้องกับที่ stairs_blind ต้อง curriculum บันได 0–8 cm และยังติดที่ level ต่ำ
- `sensordata` ช้ากว่า qpos 1 step → PD ใน bridge (และใน `pd_ctrl` ของเรา) ใช้ q ที่ช้า 2 ms
