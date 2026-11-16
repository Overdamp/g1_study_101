# Skeleton สัปดาห์ 2 (PD control, sim เท่านั้น)

ทำตามลำดับ แต่ละไฟล์ต่อยอดจากไฟล์ก่อนหน้า (ก็อปส่วนที่เขียนเสร็จแล้วมาใช้ต่อได้)
ไฟล์ทั้งหมด**รันได้ตั้งแต่แรกและไม่มีตัวแดงใน IDE** (ยังไม่ทำอะไร พิมพ์บอกว่ายังไม่ได้เติม) ค่าที่ต้องเติมใส่ไว้เป็น `None  # TODO`

| ลำดับ | ไฟล์ | งาน | ส่ง lowcmd? |
|---|---|---|---|
| 1 | `watch_lowcmd_skeleton.py` | 2.2 (ตัวฟัง) / 2.8 | ❌ ฟังอย่างเดียว |
| 2 | `send_zero_skeleton.py` | 2.1–2.2 | ✅ ทุกค่า 0 |
| 3 | `damping_skeleton.py` | 2.3 | ✅ kp 0, kd > 0 |
| 4 | `hold_elbow_skeleton.py` | 2.4, 2.8 | ✅ ศอกค้าง |
| 5 | `step_elbow_skeleton.py` | 2.5–2.6 | ✅ step + บันทึก CSV |
| 6 | `analyze_step_skeleton.py` | 2.6–2.7 | ❌ วิเคราะห์ CSV |

## ⚠️ ความปลอดภัย
- ทุกไฟล์ที่ส่ง lowcmd มี **`safety_guard()` เขียนไว้ให้แล้ว** (ไม่ใช่ TODO) ซึ่งจะหยุดโปรแกรมถ้า interface ไม่ใช่ `lo` หรือ domain ไม่ใช่ 1 **ห้ามลบ ห้ามแก้**
- ห้ามรัน 2 ไฟล์ที่ส่ง lowcmd พร้อมกัน (ตัวฟัง `watch_lowcmd` รันคู่ได้)
- ห้ามรันพร้อม g1_ctrl

## รัน
```bash
conda activate g1_sdk
~/g1_study/start_sim.sh                      # terminal 1
python <ไฟล์>.py                             # terminal 2  (ส่งคำสั่ง)
python watch_lowcmd_skeleton.py              # terminal 3  (ฟัง ถ้าต้องการ)
```
`analyze_step_skeleton.py` ถ้าจะพล็อตกราฟ ใช้ `conda activate unitree_rl_mjlab` (env `g1_sdk` ไม่มี matplotlib)

## อ่านประกอบ
`week2/docs/README.md` (งานและเกณฑ์ผ่าน) · `lowcmd_structure.md` · `pd_control.md` · `sim_vs_real.md`
ตัวอย่าง SDK: `~/nvidia/unitree/unitree_sdk2_python/example/g1/low_level/g1_low_level_example.py`
