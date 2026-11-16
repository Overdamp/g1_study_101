# สคริปต์สัปดาห์ 1: ฉบับสมบูรณ์ (เฉลย)

> โครงให้ฝึกเขียนเองอยู่ที่ `../skelatons/read_lowstate_skeleton.py` (TODO 1.2–1.7 ในไฟล์เดียว)
> ทุกสคริปต์**อ่านอย่างเดียว** (ไม่มี publisher) ปลอดภัยกับ sim และหุ่นจริง

แต่ละไฟล์ต่อยอดจากไฟล์ก่อนหน้า เปิดคู่กันดูได้ว่าเพิ่มอะไร:

| ไฟล์ | งาน | เพิ่มอะไรจากไฟล์ก่อน |
|---|---|---|
| `t1_2_hello.py` | 1.2 | subscriber 4 ขั้น + callback ที่ print ทุกข้อความ |
| `t1_3_hz.py` | 1.3 | class เก็บตัวนับ + `Lock` + main พิมพ์ Hz ทุก 1 s (callback ไม่ print แล้ว) |
| `t1_4_elbow.py` | 1.4 | เก็บมุมศอกล่าสุด (`None` = ยังไม่มีข้อมูล) + แปลงเป็นองศา |
| `t1_5_table.py` | 1.5 | เก็บทั้งก้อน `msg` + dict slot→ชื่อ + ตาราง 23 ข้อต่อวาดทับที่เดิม |
| `t1_6_imu.py` | 1.6 | `format_imu()`: roll/pitch/yaw, gyro, `mode_machine` (import ตารางจาก `t1_5_table.py`) |
| `read_lowstate.py` | 1.2–1.7 | ตัวเต็ม: `--network` / `--domain` / `--period` / `--once`, ป้าย SIM/REAL, gap, vol |

## รัน
```bash
conda activate g1_sdk
cd ~/g1_study/week1/scripts/complete
~/g1_study/start_sim.sh                  # terminal อื่น
python t1_3_hz.py
python read_lowstate.py                  # sim (ค่าเริ่มต้น: lo, domain 1)
python read_lowstate.py --once           # พิมพ์ครั้งเดียวแล้วจบ
python read_lowstate.py --domain 0       # งาน 1.8 ก: domain ผิด
python read_lowstate.py --network enp43s0     # หุ่นจริง (domain 0 ให้เอง) หุ่นแขวนรอก + ตั้ง IP แล้ว
```

## ทดสอบแล้ว (10/11/2026)
ตอนทดสอบไม่มี sim จริงเปิดอยู่ จึงใช้ตัวส่ง LowState ปลอมบน `lo` domain 1 (ศอก 1.2095 rad, pitch 0.2 rad, yaw 0.5 rad):
- 1.2 print ทุกข้อความ · 1.3 นับ Hz ได้ · 1.4 ศอก +69.3° · 1.5 ตาราง 23 แถว · 1.6 pitch +11.5°, yaw +28.6°, mode_machine 4 ✅
- `read_lowstate.py --once` ตารางครบ + "vol = 0 ทุกตัว → ข้อมูลจาก sim" ✅
- `--domain 0` → ป้ายเตือน + `0.0 Hz (no LowState yet)` ไม่มี error ✅ (ตรงกับงาน 1.8)
- ตัวส่งปลอมส่งได้ ~650 Hz (Python) ส่วน sim จริงได้ ~905 Hz
- ยังไม่ได้ทดสอบกับ sim จริงและหุ่นจริง

## เทียบกับเครื่องมือของ repo
"เฉลยระดับโปร": `~/nvidia/unitree/unitree_rl_mjlab/deploy/robots/g1_23dof/scripts/lowstate_monitor.py` (มีบันทึก CSV, ใช้เป็นฐานของสคริปต์อื่น) ลองเปิดคู่กับ `read_lowstate.py` ดูว่าโครงเหมือนกันตรงไหน
