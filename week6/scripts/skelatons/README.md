# Skeleton สัปดาห์ 6 (วิเคราะห์ข้อมูลหุ่นจริง)

ทุกไฟล์**อ่าน log อย่างเดียว** ไม่ต่อหุ่น ไม่ต่อ DDS

| ลำดับ | ไฟล์ | งาน | ทำอะไร |
|---|---|---|---|
| 0 | `../cut_logs.sh` | 6.1 | **พร้อมใช้**: ตัดช่วง log 3/11 จาก `~/` มาไว้ `week6/data/` (ไม่แตะต้นฉบับ) |
| 1 | `pdlib_skeleton.py` | 6.2–6.4, 6.6 | **ไลบรารีหลัก** `align`, `pd_terms`, `fit`, `rms`, `corr`, `window`, `best_delay` + เทสต์ 12 ข้อด้วยข้อมูลปลอม |
| 2 | `explore_skeleton.py` | 6.1 | ตรวจข้อมูล + พล็อต q / q_des / tau_est |
| 3 | `torque_compare_skeleton.py` | 6.3 | tau ที่ควรเป็น vs tau_est |
| 4 | `fit_skeleton.py` | 6.5–6.7 | หา delay + fit 3 แบบ + เทียบ pd_check · ครบ 3 ข้อต่อ |
| 5 | `break_skeleton.py` | 6.8 | ความไวของวิธี (ตัด D, delay ผิด, ไม่ตัดช่วง, kd × 2) |
| 6 | `report_template.md` | 6.9 | แม่แบบรายงาน + ทบทวน 6 สัปดาห์ |

## หัวใจ: `pdlib_skeleton.py`
รันตรงๆ = เทสต์ 12 ข้อ (ไม่ต้องมีข้อมูลจริง): zero-order hold, P/D/y, fit กู้ค่า 0.93 / 0.86 / −0.28 คืนได้, offset สำคัญตอนแรงบิดเล็ก, omitted variable bias, window
เติมจนขึ้น "ผ่านทั้งหมด ✅" ก่อน แล้วค่อยไปไฟล์อื่น

ส่วนที่ให้ไว้แล้ว: `read_csv` (อ่านเฉพาะคอลัมน์ที่ใช้), `load_joint`, ตาราง `JOINTS` (slot, kp, ค่าอ้างอิงของ pd_check)

## รัน
```bash
cd ~/g1_study/week6/scripts
./cut_logs.sh kneeL                     # เริ่มที่เข่า (ไฟล์เล็ก, แรงบิดใหญ่) · ไม่ใส่ชื่อ = ทั้ง 3 (elbowL อ่านไฟล์ 1.4 GB ช้า)
conda activate unitree_rl_mjlab         # numpy + matplotlib (g1_sdk ไม่มี matplotlib)
cd skelatons
python pdlib_skeleton.py                # เทสต์
python explore_skeleton.py kneeL
python torque_compare_skeleton.py kneeL
python fit_skeleton.py kneeL
python break_skeleton.py kneeL
python fit_skeleton.py kneeL elbowR elbowL      # 6.7 (หลัง ./cut_logs.sh ครบ)
```

## ค่าที่ควรได้ (เข่าซ้าย, ช่วง step + offset)
`pd_check --segments` (รันซ้ำ 10/11): kp x **0.93**, kd x **0.86**, offset **−0.28 Nm**, delay **3 ms**, corr 1.00
