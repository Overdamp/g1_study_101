# สัปดาห์ 3: ฉบับสมบูรณ์ (เฉลย)

> โครงให้ฝึกเขียนเองอยู่ใน `../skelatons/` ส่วนโฟลเดอร์นี้คือเฉลยที่ใส่ comment ภาษาไทยไว้ละเอียด
> ⚠️ sim เท่านั้น · ไม่แก้ repo หลัก · ห้ามรัน mini_fsm พร้อม g1_ctrl

| ไฟล์ | งาน | อะไร |
|---|---|---|
| `mini_fsm.py` | 3.2–3.4 | FSM ใน Python: Passive ↔ Hold → Wave (ramp 1 s) + timeout → Passive (ใช้ `common.py` จาก week2) |
| `State_HoldPose.h` | 3.7 | state ใหม่ของ g1_ctrl: H3 เริ่มจากท่าปัจจุบัน, H4 gain จาก yaml, H7 ramp kp ตาม `ramp_s` |
| `config_holdpose.yaml` | 3.7 | gain ตอนเทรน 29 ช่อง + `ramp_s: 1.0` + transitions |
| `apply_holdpose.py` | 3.7 | ใส่ทั้งหมดลงสำเนาในคำสั่งเดียว: ก็อป `.h` + แก้ `main.cpp` (include, คีย์ o/p) + แก้ `config.yaml` (3 จุด) · รันซ้ำได้ · ปฏิเสธถ้าเป็น repo หลัก |

## วิธีใช้
```bash
# 3.2–3.4
conda activate g1_sdk
python ~/g1_study/week3/scripts/complete/mini_fsm.py         # คีย์ o / w / p แล้ว Enter

# 3.5 + 3.7
~/g1_study/week3/scripts/setup_copy.sh                         # สำเนา + git init + build (ใส่ flag ของ SDK ให้)
python ~/g1_study/week3/scripts/complete/apply_holdpose.py     # ใส่ HoldPose ลงสำเนา
~/g1_study/week3/scripts/setup_copy.sh build                   # build ใหม่
cd ~/g1_study/week3/deploy/robots/g1_23dof/build
env -u CYCLONEDDS_URI LD_LIBRARY_PATH=/opt/unitree_robotics/lib ./g1_ctrl   # sim: o = HoldPose, p = Passive
git -C ~/g1_study/week3/deploy diff                            # ดูว่าแก้อะไรไปบ้าง
```

## จุดที่ตัดสินใจต่างจาก skeleton / g1_ctrl
| เรื่อง | ทำแบบนี้ | เหตุผล |
|---|---|---|
| mini_fsm: ตำแหน่งของ timeout | **แรกสุด**ใน checks | ถ้าเกิดพร้อมกับการกดคีย์ ความปลอดภัยต้องชนะ (g1_ctrl ใส่ไว้ท้าย) |
| mini_fsm: LowState หาย | ยัง tick ต่อด้วย state ล่าสุด ไม่หยุดโปรแกรม | ให้ FSM เข้า Passive เอง และพอ sim กลับมาก็ยังอยู่ใน Passive |
| HoldPose: q เป้าหมาย | จาก `lowstate` (มุมจริง) | ถูกต้องไม่ว่าเข้ามาจาก state ไหน (ถ้าเข้าจาก Passive จะเท่ากับ q ในคำสั่งอยู่แล้ว) |
| HoldPose: gain | อ่านใน ctor ครั้งเดียว | เหมือน state อื่น (แก้ yaml แล้วต้องเปิด g1_ctrl ใหม่) |
| HoldPose: ramp | kd เต็มทันที, kp ไล่ 0 → เต็ม | kd หน่วงอย่างเดียว ไม่ดึงไปไหน จึงปลอดภัยตั้งแต่ต้น |
| ปุ่มรีโมทเข้า HoldPose | `LT + down` | `LT + up` เป็นของ FixStand อยู่แล้ว |

## ทดสอบแล้ว (10/11/2026, ไม่มี sim จริง)
**mini_fsm.py** กับ sim ปลอม (LowState บน lo + จำลองศอก 1 ข้อ) ป้อนคีย์ตามเวลา:
`Passive → (o) Hold → (w) Wave → (p) Passive → (o) Hold → sim หยุด → Passive (LowState หาย)` ✅ ศอกค้างตอน Hold, แกว่งตอน Wave

**HoldPose** ทำสำเนาบน scratchpad → `apply_holdpose.py` (รัน 2 รอบ: รอบสองข้ามทุกจุด) → build ผ่าน → รัน g1_ctrl กับ LowState ปลอม กดคีย์ผ่าน pty:
```
DDS: domain 1 on lo (SIM, keyboard on)
Initializing State_HoldPose ...
FSM: Change state from Passive to HoldPose
HoldPose: holding current pose (kp ramp 1.0 s)
FSM: Change state from HoldPose to Passive
```
kp ใน `rt/lowcmd`: Passive 0 → HoldPose +0.3 s ศอก 4.28 / เข่า 29.6 → +1.5 s ศอก 14.3 / เข่า 99.1 → กด p กลับเป็น 0 ✅
`apply_holdpose.py` กับ path ของ repo หลัก → ปฏิเสธ ✅

ยังไม่ได้ทดสอบกับ unitree_mujoco จริง (แผนทดสอบ T1–T8 ใน `week3/docs/holdpose_spec.md`)

## เจอระหว่างทำ
`cmake ..` เฉยๆ build g1_ctrl ไม่ผ่าน (`go2.h: No such file or directory`) ต้องส่ง `-DCMAKE_CXX_FLAGS="-I/opt/unitree_robotics/include -I/opt/unitree_robotics/include/ddscxx"` และ linker flags (ค่าจาก `CMakeCache.txt` ของ build จริง) ซึ่งแก้ไว้แล้วใน `setup_copy.sh` และ `week3/docs/build_and_run.md`
