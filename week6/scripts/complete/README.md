# สัปดาห์ 6: ฉบับสมบูรณ์ (เฉลย)

> โครงให้ฝึกเขียนเองอยู่ใน `../skelatons/` · โฟลเดอร์นี้คือเฉลย · ทุกไฟล์อ่าน log อย่างเดียว

| ไฟล์ | งาน | อะไร |
|---|---|---|
| `pdlib.py` | 6.2–6.4, 6.6 | `align`, `pd_terms`, `fit`, `rms`, `corr`, `window`, `best_delay`, `read_csv`, `load_joint` + เทสต์ 12 ข้อ · ตั้งที่อ่านข้อมูลได้ด้วย `W6_DATA` |
| `explore.py` | 6.1 | ตรวจข้อมูล (อัตรา, เวลาไม่ถอยหลัง, t ซ้ำ, gap, kp/kd/mode, ช่วง step) + กราฟ `explore_<ชื่อ>.png` |
| `torque_compare.py` | 6.3 | แรงบิดที่ควรเป็น vs tau_est: corr, rms, offset ช่วงค้าง + กราฟ `torque_<ชื่อ>.png` |
| `fit.py` | 6.5–6.7 | delay ดีที่สุด + fit 3 แบบ + เทียบ pd_check + ตารางสรุปหลายข้อต่อ |
| `break_test.py` | 6.8 | ตัด D / delay 0, 15 ms / ทั้งไฟล์ + offset / kd × 2 |
| `report_example.md` | 6.9 | ตัวอย่างรายงานด้วยตัวเลขจริง (เขียนของตัวเองก่อนแล้วค่อยเปิด) |

## รัน
```bash
cd ~/g1_study/week6/scripts && ./cut_logs.sh          # ตัด 3 ข้อต่อลง week6/data (~2 s, ไฟล์ละ 25 MB)
conda activate unitree_rl_mjlab
cd complete
python pdlib.py                                       # เทสต์
python explore.py kneeL
python torque_compare.py kneeL
python fit.py kneeL elbowR elbowL
python break_test.py kneeL
```

## ผลทดสอบกับ log จริง (10/11/2026)
| ข้อต่อ | kp x | kd x | offset | delay | pd_check (รันกับไฟล์เดียวกัน) |
|---|---|---|---|---|---|
| เข่าซ้าย | 0.934 | 0.864 | −0.282 | 3 ms | 0.93 / 0.86 / −0.28 |
| ศอกซ้าย | 0.982 | 0.878 | −0.124 | 3 ms | 0.97 / 0.88 / −0.13 |
| ศอกขวา | 0.951 | 0.841 | +0.144 | 3 ms | 0.96 / 0.84 / +0.15 |
ต่างจาก pd_check ไม่เกิน 0.012 ✅ · เทสต์ 12/12 ✅ · ทั้งชุดรันไม่ถึง 2 วินาที

## เจอระหว่างทำ (แก้ docs / skeleton แล้ว)
- **fit ทั้งไฟล์ไม่มี offset ไม่ได้ "ต่ำ" เสมอ:** ศอกซ้าย (offset −0.12) ได้ **1.17** ศอกขวา (offset +0.14) ได้ 0.70 ทิศของการเพี้ยนขึ้นกับเครื่องหมายของ offset (แก้ใน `least_squares.md`, `interpreting_results.md`)
- **ค่าอ้างอิงของศอก:** pd_check กับไฟล์ที่ตัดแล้วได้ศอกซ้าย 0.97 (vault บันทึก 0.96) และได้ offset ที่แน่นอนแล้ว (แก้ใน `JOINTS` ของ skeleton และ docs)
- **เวลาใน log มีค่าซ้ำ** (เข่า 8 จุด, ศอกขวา 2 จุด) ไม่ใช่ข้อมูลเสีย: CSV บันทึก `t` แค่ทศนิยม 4 ตำแหน่ง (0.1 ms) และ tick ยังเพิ่มขึ้นปกติ `explore.py` จึงแยกตรวจ "ถอยหลัง" กับ "ซ้ำ"
- matplotlib ไม่มีฟอนต์ไทย ข้อความในกราฟจึงใช้ภาษาอังกฤษ
- **ตัด D ออกจาก fit ทำให้ kp x ตกเหลือ 0.33–0.60** (omitted variable bias) ส่งผลแรงที่สุดในทุกการทดลอง
