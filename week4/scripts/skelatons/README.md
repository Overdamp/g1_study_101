# Skeleton สัปดาห์ 4 (policy)

| ลำดับ | ไฟล์ | งาน | ต่อ DDS | ส่ง lowcmd |
|---|---|---|---|---|
| 1 | `inspect_policy_skeleton.py` | 4.1 | ❌ | ❌ |
| 2 | `obs_skeleton.py` | 4.2, 4.6, 4.8 | ❌ (ไลบรารี + เทสต์) | ❌ |
| 3 | `policy_once_skeleton.py` | 4.3 | ❌ | ❌ |
| 4 | `shadow_mode_skeleton.py` | 4.4–4.5, 4.8 | ✅ ฟังอย่างเดียว | ❌ |
| 5 | `analyze_shadow_skeleton.py` | 4.4–4.5 | ❌ | ❌ |
| 6 | `policy_runner_skeleton.py` | 4.7 (ท้าทาย) | ✅ | ✅ sim เท่านั้น |

## หัวใจของสัปดาห์: `obs_skeleton.py`
ไฟล์อื่น import ฟังก์ชันจากไฟล์นี้ (`build_obs`, `projected_gravity`, `GaitPhase`, `action_to_q_des`, `PolicyConfig`) **เติมให้เสร็จก่อน**
รันไฟล์นี้ตรงๆ = รัน**เทสต์ที่เขียนไว้ให้แล้ว** 11 ข้อ (gravity, ลำดับข้อต่อ, ศอกซ้ายอยู่ index 27, clamp, gait phase, action → q_des)
ตอนยังไม่เติม จะ FAIL หลายข้อ เติมจนขึ้น "ผ่านทั้งหมด ✅" ค่อยไปไฟล์ถัดไป

## ส่วนที่ให้ไว้แล้ว
- `PolicyConfig`: อ่าน `deploy.yaml` ของ v0 (joint_ids_map, default pose, scale, gain, step_dt, gait period)
- `fake_lowstate()`: LowState ปลอม "ยืนท่า default นิ่ง" สำหรับเทสต์และ 4.3
- `Latest` (shadow), `other_lowcmd_active()` (runner: กันรันพร้อม g1_ctrl)

## รัน
```bash
conda activate g1_sdk
cd ~/g1_study/week4/scripts/skelatons
python obs_skeleton.py                 # เทสต์
python inspect_policy_skeleton.py
python policy_once_skeleton.py
python shadow_mode_skeleton.py --seconds 15 --out shadow.csv     # g1_ctrl ต้องอยู่ใน Velocity (sim)
python analyze_shadow_skeleton.py shadow.csv
```
ต้องรันจากโฟลเดอร์นี้ (หรือเรียก path เต็ม) เพราะ import `obs_skeleton` จากโฟลเดอร์เดียวกัน

## ⚠️ ความปลอดภัย
- 4.1–4.6 ไม่ส่งอะไรเลย รันคู่กับ g1_ctrl ได้
- 4.7 ส่ง lowcmd: sim เท่านั้น (`safety_guard` ใน week2 common) และมีตัวเช็คว่าไม่มี g1_ctrl ส่งอยู่ ห้ามลบ
- policy_runner ห้ามใช้กับหุ่นจริงจาก session นี้
