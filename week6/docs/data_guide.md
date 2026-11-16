# ข้อมูล: log หุ่นจริง 3/11/2026

## ที่มา
วันที่ 3/11 หุ่นแขวนรอก รัน `sysid_motion.py --gains train` (gain ตอนเทรน: แขน kp 14.3 / kd 0.9, เข่า 99.1 / 6.3) สั่ง **step** ทีละข้อต่อ: +A → 0 → −A → 0 ช่วงละ 1.5 s (vault `Sysid Motion.md`)
ระหว่างนั้นอัด 2 topic พร้อมกันบนเครื่องเดียวกัน:
- `lowstate_monitor.py --log` → `g1_state_*.csv`
- `lowcmd_monitor.py --log` → `g1_cmd_*.csv`
และ `sysid_motion.py --segments` บันทึกช่วงเวลาของแต่ละ test → `sysid_seg_*.csv`

## ไฟล์ (อยู่ใน `~/`, **อ่านอย่างเดียว**)
| run | ข้อต่อ (slot) | state | cmd | segments | ช่วง step (t0 → t1) |
|---|---|---|---|---|---|
| sysid1 | ศอกซ้าย (18), A 0.2 rad | `g1_state_20261103_sysid1.csv` **1.4 GB**, 900 s | `g1_cmd_20261103_sysid1.csv` 10 MB, 14 s | `sysid_seg_20261103_light.csv` | 36245.67 → 36251.67 |
| sysid2 | ศอกขวา (25), A 0.2 rad | `..._sysid2.csv` 300 MB, 190 s | `..._sysid2.csv` 10 MB | `sysid_seg_20261103_lightR.csv` | 36495.00 → 36501.00 |
| sysid3 | เข่าซ้าย (3), A 0.15 rad | `..._sysid3.csv` 95 MB, 60 s | `..._sysid3.csv` 10 MB | `sysid_seg_20261103_kneeL.csv` | 36696.23 → 36702.23 |
| sysid4 | (ทดสอบ L2 + B หยุดกลางคัน) | `..._sysid4.csv` | `..._sysid4.csv` | `sysid_seg_20261103_kneeL_stop.csv` | – |

**เริ่มที่ sysid3 (เข่าซ้าย)** เพราะไฟล์เล็กที่สุด และแรงบิดใหญ่ (kp 99.1) ทำให้ fit ง่าย จากนั้นค่อยไปศอก (kp 14.3 แรงบิดเล็ก offset จะมีผลมาก)

## คอลัมน์
**state** (`lowstate_monitor.py`): `t, tick, mode_machine, mode_pr, quat_w..z, gyro_x..z, q0..q28, dq0..dq28, tau0..tau28, temp0..temp28`
- `tau<i>` = **`tau_est`** แรงบิดที่มอเตอร์ประมาณเองจากกระแส (ไม่ใช่แรงบิดที่สั่ง)
- slot 0–28 (29 ช่อง) เหมือนสัปดาห์ 1 ส่วน slot ที่ไม่มีข้อต่อจะเป็น 0

**cmd** (`lowcmd_monitor.py`): `t, mode_machine, mode_pr, q0..q28, dq0..dq28, kp0..kp28, kd0..kd28, tau0..tau28, mode0..mode28`
- `q<i>` = q_des, `dq<i>` = dq_des, `tau<i>` = tau_ff (feed-forward), `kp`, `kd` ตามที่ส่ง

**segments**: `test, slot, kind, amp, t0, t1, completed` (slot −1 = ช่วง ramp/hold ไม่ใช่การทดสอบ)

## เวลา `t`
- ทั้งสามไฟล์ใช้ `time.monotonic()` **ของเครื่องเดียวกัน** จึงเทียบกันได้ตรงๆ (ค่าประมาณ 36,000 s คือเวลานับตั้งแต่บูตเครื่อง ไม่ใช่เวลานาฬิกา)
- state ~1 kHz, cmd ~530–560 Hz (Python) อัตราไม่เท่ากัน → ต้องจับคู่ (`alignment_and_delay.md`)
- cmd มีแค่ช่วงที่ sysid รัน (~14 s) ส่วน state อัดยาวกว่านั้นมาก

## ตัดช่วงมาไว้ใน `week6/data/` (แนะนำ)
อ่านไฟล์ 1.4 GB ทั้งก้อนช้าและกินแรม ตัดเฉพาะช่วงที่ cmd มีข้อมูล (บวกขอบ 1 s) ด้วย awk:
```bash
mkdir -p ~/g1_study/week6/data && cd ~/g1_study/week6/data
cut3() {  # <ต้นฉบับ> <t_start> <t_end> <ปลายทาง>
  awk -F, -v a="$2" -v b="$3" 'NR==1 || ($1>=a && $1<=b)' "$1" > "$4"
}
cut3 ~/g1_state_20261103_sysid3.csv 36690 36706 kneeL_state.csv
cp   ~/g1_cmd_20261103_sysid3.csv              kneeL_cmd.csv
cp   ~/sysid_seg_20261103_kneeL.csv            kneeL_seg.csv
```
ช่วงเวลาของ sysid1/sysid2 ให้ดูจากแถวแรกและแถวสุดท้ายของไฟล์ cmd (`sed -n 2p`, `tail -1`) แล้วตัด state ให้ครอบช่วงนั้น
**ทายก่อน:** ไฟล์ state ที่ตัดแล้วจะมีกี่แถว (ใบ้: ~1 kHz × กี่วินาที)

## อ่านเข้า numpy
```python
import numpy as np
hdr = open(path).readline().strip().split(",")
data = np.loadtxt(path, delimiter=",", skiprows=1)        # ไฟล์ที่ตัดแล้วเล็ก โหลดทั้งก้อนได้
col = {name: i for i, name in enumerate(hdr)}
t   = data[:, col["t"]]
q3  = data[:, col["q3"]]                                    # เข่าซ้าย
```
(`pd_check.py` ใช้ `usecols` เลือกเฉพาะคอลัมน์ ช่วยให้อ่านไฟล์ใหญ่ได้ ดู `read_csv` ในไฟล์นั้น)

## ตรวจความถูกต้องก่อนวิเคราะห์ (6.1)
- `kp3` ใน cmd ระหว่างช่วง step = 99.1 ไหม · `kp18` = 14.3 ไหม (gain ตอนเทรน)
- `mode3` = 1 ไหม
- `t` ของ state เรียงเพิ่มขึ้นตลอดไหม (มี gap ใหญ่ไหม ดู `np.diff(t).max()`)
- ช่วง step: q_des กระโดด +0.15 → 0 → −0.15 → 0 รอบท่ายืนจริงไหม

## คำถามเช็ค
1. ทำไมต้องอัด lowstate กับ lowcmd บนเครื่องเดียวกัน
2. `tau` ในไฟล์ state กับ `tau` ในไฟล์ cmd คือคนละอย่าง ต่างกันยังไง
3. ถ้า state มี gap 60 ms ตรงกลางช่วง step จะกระทบ fit ยังไง
