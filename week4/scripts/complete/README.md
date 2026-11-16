# สัปดาห์ 4: ฉบับสมบูรณ์ (เฉลย)

> โครงให้ฝึกเขียนเองอยู่ใน `../skelatons/` · โฟลเดอร์นี้คือเฉลยที่ใส่ comment ภาษาไทยไว้
> ต้องรันจากโฟลเดอร์นี้ (หรือ path เต็ม) เพราะไฟล์อื่น import `obs.py`

| ไฟล์ | งาน | ต่อ DDS | ส่ง lowcmd | อะไร |
|---|---|---|---|---|
| `obs.py` | 4.2, 4.3, 4.6 | ❌ | ❌ | ไลบรารี: `PolicyConfig`, `projected_gravity`, `build_obs`, `GaitPhase`, `action_to_q_des`, `Policy` (ONNX) + เทสต์ 11 ข้อ |
| `inspect_policy.py` | 4.1 | ❌ | ❌ | input/output/metadata ของ ONNX + เทียบ deploy.yaml ด้วย tolerance เดียวกับ `gain_check.py` |
| `policy_once.py` | 4.3 | ❌ | ❌ | obs ยืนนิ่งสมบูรณ์แบบ → action · 20 step ต่อเนื่อง · ทดลอง obs 0 / ซ้ำ / gravity x |
| `shadow_mode.py` | 4.4–4.5, 4.8 | ✅ ฟัง | ❌ | เทียบ q_des กับ g1_ctrl · `--break order/nodefault/gravsign/lastaction_qdes/rate_1k` |
| `analyze_shadow.py` | 4.4–4.5 | ❌ | ❌ | error ต่อข้อต่อ, PASS/FAIL (< 0.01 rad), ช่วง gravity, กราฟ |
| `policy_runner.py` | 4.7 | ✅ | ✅ sim | Passive → Stand (3 s) → Policy (soft start 0.5 s) + timeout + เอียง + เช็ค g1_ctrl |

## ผลทดสอบ (10/11/2026, ไม่มี sim จริง)
**offline:** `obs.py` ผ่าน 11/11 · `inspect_policy.py`: ONNX `obs` [1,80] → `actions` [1,23], stiffness/damping/scale ต่างจาก deploy.yaml แค่การปัดเศษ (damping สูงสุด 1.64% ใน tolerance 6% ของ gain_check)
`policy_once.py` (ยืนนิ่งสมบูรณ์แบบ): step แรก max|action| 0.635 (ไหล่ซ้าย roll) → ลู่เข้า ~0.95 ใน ~10 step · deterministic · gravity x = 0.1 → ข้อเท้าเปลี่ยนมากสุด

**shadow mode กับ g1_ctrl ตัวจริง** (ก็อป binary + config ไป scratchpad แบบ `sim2sim_policy.sh`, LowState ปลอม, กด u → v ผ่าน pty):
| | mean \|error\| | แย่สุด |
|---|---|---|
| ปกติ | 0.0017 rad | เข่าขวา 0.0027 rad → **PASS ทุกข้อต่อ** ✅ |
| `--break order` | 0.299 rad | max 0.79 rad (FAIL ตามคาด) |

**policy_runner** กับ LowState ปลอม: ปฏิเสธเมื่อ g1_ctrl ส่ง lowcmd อยู่ ✅ · `g` จาก Passive ไม่มีผล · Stand ตั้ง kp เข่า 99.1 / ศอก 14.3 (slot 13 = 0) · `g` ก่อนครบ 3 s → "ยังยืนไม่ครบ" · Policy → `p` → Passive · LowState หาย → Passive ✅
(LowState ปลอมไม่ตอบสนองต่อคำสั่ง จึงทดสอบได้แค่ลอจิกและค่าที่ส่ง ไม่ได้ทดสอบว่าหุ่นยืน/เดินได้จริง)

## เจอระหว่างทำ
- **tolerance ของ `gain_check.py` ต่างกันตาม field:** gain 6%, scale 1%, default pose 1e-3 (ไม่ใช่ 1% ทุกตัวอย่างที่เขียนไว้ใน skeleton ตอนแรก แก้แล้ว)
- g1_ctrl เขียน log ลง `<proj>/log/log.txt` เวลาทดลองให้ก็อป binary + config ไปที่อื่นก่อน (ไม่รันใน repo)
