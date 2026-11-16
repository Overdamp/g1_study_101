# Skeleton สัปดาห์ 3 (FSM)

| ไฟล์ | งาน | ภาษา | ใช้ยังไง |
|---|---|---|---|
| `mini_fsm_skeleton.py` | 3.2–3.4 | Python | เติม TODO แล้วรันกับ sim: Passive ↔ Hold → Wave + timeout |
| `State_HoldPose_skeleton.h` | 3.7 | C++ | ก็อปไปที่ `week3/deploy/robots/g1_23dof/include/State_HoldPose.h` แล้วเติม TODO |
| `config_holdpose_skeleton.yaml` | 3.7 | YAML | 3 จุดที่ต้องเพิ่มใน `config.yaml` ของสำเนา |
| `main_cpp_changes_skeleton.md` | 3.7 | C++ | include + คีย์ `o` / `p` ใน `main.cpp` ของสำเนา |
| `../setup_copy.sh` | 3.5 | bash | **พร้อมใช้** (ไม่ใช่ skeleton): ทำสำเนา g1_ctrl + git init + build |

## ลำดับที่แนะนำ
1. อ่าน `week3/docs/fsm_concepts.md` → วาดแผนภาพ state ของ g1_ctrl (3.1)
2. `mini_fsm_skeleton.py` (3.2 → 3.3 → 3.4) ได้แนวคิด FSM ด้วย Python ก่อน
3. `../setup_copy.sh` แล้วรันสำเนากับ sim กด `u` / `p` (3.5)
4. อ่านโค้ด FSM ของ g1_ctrl + ตอบแบบฝึกหัดใน vault walkthrough (3.6)
5. HoldPose: `State_HoldPose_skeleton.h` + yaml + main.cpp (3.7) แล้วทำให้พัง (3.8)

## สถานะของ skeleton
- `mini_fsm_skeleton.py` รันได้ตั้งแต่แรก (พิมพ์ว่ายังไม่ได้เติมแล้วจบ) ใช้ `common.py` ของ `week2/scripts/complete/` (มี `safety_guard` ในตัว)
- `State_HoldPose_skeleton.h` **compile ผ่านตั้งแต่แรก** ถ้ายังไม่เติมอะไร state นี้จะไม่ตั้ง gain (ยังหนืดเหมือน Passive) จึงปลอดภัย
- `config_holdpose_skeleton.yaml` เป็น YAML ที่ถูกต้อง ค่า `kp: []`, `kd: []` (ไม่ตั้ง gain) ก็ปลอดภัยเช่นกัน

## ⚠️ ความปลอดภัย
- `mini_fsm` และ g1_ctrl สำเนา: sim เท่านั้น ห้ามรันพร้อมกัน (2 โปรแกรมส่ง lowcmd)
- g1_ctrl สำเนา: **ห้ามใส่ `--network enp43s0`** ต้องเห็น `DDS: domain 1 on lo (SIM, keyboard on)` ตอนเริ่ม
- ไม่แก้ repo หลัก (`~/nvidia/unitree/unitree_rl_mjlab`) แก้เฉพาะใน `~/g1_study/week3/deploy/`
