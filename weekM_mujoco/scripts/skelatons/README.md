# โมดูล M: โครงให้เติม (skeleton)

> เฉลยอยู่ที่ `../complete/` · docs อยู่ที่ `../../docs/` · ใช้ `python3` ของระบบ

## ลำดับ
1. อ่าน `docs/README.md` + ทำแบบฝึก GUI ใน `docs/gui.md` (M0)
2. เติม `g1mj_skeleton.py` **ทีละส่วนตามงาน** แล้วรันเทสต์บ่อยๆ:
   ```bash
   cd ~/g1_study/weekM_mujoco/scripts/skelatons
   python3 g1mj_skeleton.py      # ตอนเริ่ม: PASS 4 ข้อ (ส่วนที่ให้ไว้แล้ว) FAIL 13 → ครบ 17/17
   ```
   | TODO | งาน | เทสต์ที่จะผ่าน |
   |---|---|---|
   | `slot_table`, `motor_q/dq/tau` | M1 | slot_table (3 ข้อ) |
   | `set_pose`, `projected_gravity` | M2 | set_pose + sensor (4 ข้อ) |
   | `ElasticBand.force / apply` | M3 | ElasticBand (2 ข้อ) |
   | `pd_ctrl` | M4 | pd_ctrl (1 ข้อ) |
   | `foot_forces` | M6 | foot_forces (1 ข้อ) |
   | `to_lowstate` | M7 | to_lowstate (2 ข้อ) |
3. ทำ `m1_inspect.py` → `m7_policy.py` ตามลำดับ แต่ละไฟล์มี "ทายก่อนรัน" ที่หัวไฟล์ **จดคำตอบ + % ก่อนรัน**

## ส่วนที่ให้ไว้แล้ว (อ่านให้เข้าใจ ไม่ต้องเขียน)
`load`, `build_model` (MjSpec), `save_xml`, `load_deploy`, `run` (viewer passive + headless), `view_static`, `ElasticBand.key`

## ถ้าติด
| อาการ | ดูที่ |
|---|---|
| `Cannot find module mujoco` ใน VS Code | เลือก interpreter `/usr/bin/python3` |
| `ModuleNotFoundError: mujoco` ตอนรัน | conda เปิดอยู่ → `conda deactivate` |
| ตั้ง qpos แล้ว xpos / sensor ไม่เปลี่ยน | ลืม `mujoco.mj_forward(m, d)` |
| ค่าที่เก็บไว้เปลี่ยนเอง | ลืม `.copy()` (d.qpos / d.sensordata เป็น view) |
| มุมข้อต่อผิดตัว | ใช้ index ของ joint แทน slot → ดู `python_api.md` หัวข้อ 3 "กับดัก" |
| หน้าต่างปิดแล้ว Segmentation fault | ปกติถ้าไม่มี `sleep` ตอนจบ (`run` ใส่ให้แล้ว) |
