# สคริปต์สัปดาห์ 2: ฉบับสมบูรณ์ (เฉลย)

> โครงให้ฝึกเขียนเองอยู่ใน `../skelatons/` ส่วนโฟลเดอร์นี้คือเฉลยที่ใส่ comment ภาษาไทยไว้ละเอียด
> ⚠️ **sim เท่านั้น** ทุกสคริปต์ที่ส่ง lowcmd ผ่าน `common.safety_guard()` ซึ่งจะหยุดโปรแกรมถ้าไม่ใช่ `lo` + domain 1

| ไฟล์ | งาน | ส่ง lowcmd | ทำอะไร |
|---|---|---|---|
| `common.py` | – | – | ส่วนที่ใช้ร่วมกัน: `safety_guard`, `StateReader`, `fill_damping`, `run_control_loop` (500 Hz + CRC + timeout 100 ms) |
| `watch_lowcmd.py` | 2.2, 2.8 | ❌ | ฟัง `rt/lowcmd` พิมพ์ Hz, mode, q/kp/kd ของ slot, crc |
| `send_zero.py` | 2.2 | ✅ | kp = kd = tau = 0 ทุกข้อต่อ |
| `damping.py` | 2.3 | ✅ | kp 0, kd ของ Passive × `--kd-scale` |
| `hold_elbow.py` | 2.4, 2.8 | ✅ | ค้างศอกซ้ายที่มุมตอนเริ่ม · `--break no_crc / mode0 / zero` |
| `step_elbow.py` | 2.5–2.6 | ✅ | step +amp → กลับ → damping, บันทึก CSV |
| `analyze_step.py` | 2.6–2.7 | ❌ | rise / overshoot / ss error + เทียบ tau กับ `tau_est` + กราฟ `step_compare.png` |

## ต่างจาก skeleton ตรงไหน
skeleton ให้ "ก็อปโครงจาก send_zero" ไปทุกไฟล์ เพื่อให้เขียนเองครบทุกบรรทัด ส่วนฉบับนี้ **refactor** ส่วนที่ซ้ำไปไว้ใน `common.py` แต่ละไฟล์จึงเหลือแค่ `build_cmd()` ที่ต่างกันจริง เทียบกันได้ตรงๆ:

| skeleton | ฉบับสมบูรณ์ |
|---|---|
| `StateReader` ในทุกไฟล์ | `common.StateReader` (+ เก็บเวลาไว้เช็ค timeout) |
| loop 500 Hz + CRC ใน `main()` | `common.run_control_loop(build_cmd)` |
| damping ทุก slot | `common.fill_damping(cmd, state)` |
| print ทุก 0.5 s | `common.Every(0.5)` |

สิ่งที่เพิ่มจาก skeleton: **หยุดเองถ้า LowState หายเกิน 100 ms** (แนวคิดเดียวกับ g1_ctrl ที่เข้า Passive สัปดาห์ 3)

## รัน
```bash
conda activate g1_sdk
cd ~/g1_study/week2/scripts/complete
~/g1_study/start_sim.sh                       # terminal 1 (sim)
python hold_elbow.py                          # terminal 2 (ส่งคำสั่ง ทีละตัว)
python watch_lowcmd.py                        # terminal 3 (ฟัง รันคู่ได้)
```
ต้องรันจากโฟลเดอร์นี้ หรือเรียก path เต็มก็ได้ (Python หา `common.py` จากโฟลเดอร์เดียวกับสคริปต์)

งาน 2.6:
```bash
python step_elbow.py --kp 5    --kd 0.3 --out step_kp5.csv
python step_elbow.py --kp 14.3 --kd 0.9 --out step_kp14.csv
python step_elbow.py --kp 40   --kd 2.5 --out step_kp40.csv
python step_elbow.py --kp 14.3 --kd 0   --out step_kd0.csv
conda activate unitree_rl_mjlab               # มี matplotlib
python analyze_step.py step_kp5.csv step_kp14.csv step_kp40.csv step_kd0.csv
```

## หยุดโปรแกรม (Ctrl+C) แล้วเกิดอะไร
| สคริปต์ | ตอนหยุด | sim ทำอะไรต่อ |
|---|---|---|
| `send_zero`, `damping` | หยุดส่งทันที | ใช้คำสั่งสุดท้ายต่อไป (ปล่อยอิสระ / หนืด) |
| `hold_elbow` | **ตั้งใจ**ไม่ส่ง damping ก่อนออก (งาน 2.8 ค) | ศอกยังค้าง kp อยู่ ใช้ `damping.py` ถ้าต้องการปล่อย |
| `step_elbow` | ถ้าจบเองจะส่ง damping 1 s ก่อนออก ถ้า Ctrl+C กลางทาง จะเซฟ CSV แต่ไม่ส่ง damping | ตามคำสั่งสุดท้าย |

## ทดสอบแล้ว (10/11/2026)
ตอนทดสอบไม่มี sim จริงเปิดอยู่ จึงใช้ sim ปลอมใน scratchpad ที่ส่ง LowState บน `lo` domain 1 และจำลองศอก 1 ข้อด้วยสูตร PD:
- `send_zero`: ส่ง 500 Hz, `watch_lowcmd` เห็น ~500 Hz, kp 0, `mode_machine` 4 ✅
- `hold_elbow`: จดเป้าตอนเริ่ม, error < 0.2°, `--break no_crc` รันได้ ✅
- `damping`, `step_elbow` 4 ชุด gain, เซฟ CSV ~3500 แถว, timeout 100 ms ทำงานตอน sim ปลอมปิด ✅
- `analyze_step`: ตาราง + กราฟ (env `unitree_rl_mjlab`) และข้ามการพล็อตอย่างปลอดภัยใน `g1_sdk` ✅

**ตัวเลขจาก sim ปลอมใช้แทนผลจริงไม่ได้** (โมเดลศอกเป็นของสมมติ) ต้องรันกับ `start_sim.sh` เองแล้วเทียบกับที่ทาย
