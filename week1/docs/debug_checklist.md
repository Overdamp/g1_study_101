# ไม่มีข้อมูลเข้า: เช็คลิสต์ + งาน 1.8 (ทำให้พัง)

## อาการ "เงียบไม่มี error"
DDS ถือว่า "ยังไม่มีใครส่ง" เป็นเรื่องปกติ (publisher อาจเปิดทีหลัง) subscriber จึงรอไปเรื่อยๆ โดยไม่มีวันรู้ว่าเราตั้งค่าผิด
ถ้าโปรแกรมนับ Hz ได้ **0** หรือขึ้น `no LowState yet` ให้ไล่ตามลำดับนี้ (เร็ว → ช้า):

| # | เช็ค | คำสั่ง | แก้ |
|---|---|---|---|
| 1 | sim เปิดอยู่จริงไหม | `pgrep -a unitree_mujoco` | `~/g1_study/start_sim.sh` |
| 2 | multicast บน `lo` | `ip link show lo` ต้องมี `MULTICAST` | `sudo ip link set lo multicast on` |
| 3 | domain ตรงไหม | โค้ด vs `~/g1_study/sim/config.yaml` (`domain_id: 1`) | แก้ให้ตรง |
| 4 | interface ตรงไหม | โค้ด vs config (`interface: "lo"`) | แก้ให้ตรง |
| 5 | ชื่อ topic | `"rt/lowstate"` ทุกตัวอักษร (ไม่มี `/` นำหน้า ไม่มี `_`) | |
| 6 | type | `unitree_hg` `LowState_` (ไม่ใช่ `unitree_go`) | |
| 7 | `CYCLONEDDS_URI` | `echo $CYCLONEDDS_URI` | `env -u CYCLONEDDS_URI python ...` |
| 8 | Python env | `which python` ต้องมี `g1_sdk` | `use_conda` แล้ว `conda activate g1_sdk` |
| 9 | เก็บ subscriber ไว้ไหม | ตัวแปร `sub` ยังอยู่ ไม่ได้สร้างในฟังก์ชันที่จบไปแล้ว | เก็บไว้ใน `main` / `self` |
| 10 | callback พัง | error ใน handler พิมพ์ traceback **ครั้งเดียว** (`Exception in thread ...`) แล้ว thread ของ SDK ตาย ไม่ถูกเรียกอีก แต่ `main` ยังรันต่อ | เลื่อนจอขึ้นไปหา traceback แรก (`channel.py` `__ChannelReaderThreadFunc` ไม่มี try ครอบ) |

ข้อ 8 ไม่ใช่อาการเงียบ (จะเห็น `ModuleNotFoundError`) แต่เจอบ่อยมาก
ข้อ 10 เจอจริงในงาน: `read_lowstate.py` ใช้ `LEFT_ELBOW` ที่ไม่ได้ประกาศ ทำให้ handler error ตั้งแต่ข้อความแรก → thread ของ SDK ตาย → `self.elbow_q` เป็น `None` ตลอด → `main` พิมพ์ `no LowState yet` ทั้งที่ sim เปิดอยู่

**ใช้ตำแหน่งที่นับช่วยวินิจฉัย:** ถ้านับใน handler ก่อนบรรทัดที่พัง Hz จะเป็น 1 ครั้งแล้วเป็น 0 ตลอด (thread ตาย) ถ้า Hz = 0 ตั้งแต่ต้นโดยไม่มี traceback → ปัญหาอยู่ที่ข้อ 1–7

## งาน 1.8: ทำให้พัง (ทายก่อนทุกข้อ)
ใช้ `scripts/complete/read_lowstate.py` ซึ่งรับ `--domain` / `--network` ได้ หรือใช้ไฟล์ของตัวเอง

### ก. domain ผิด
```bash
python read_lowstate.py --domain 0          # sim อยู่ domain 1
```
ทาย: error / ค้าง / พิมพ์อะไร → ผลจริง → ทำไม

### ข. ปิด multicast ของ `lo` ⚠️ (กระทบโปรแกรม DDS อื่นในเครื่อง ปิดทุกอย่างก่อน)
```bash
sudo ip link set lo multicast off
python read_lowstate.py                     # sim เปิดอยู่
sudo ip link set lo multicast on            # อย่าลืมเปิดคืน!
```
ทายด้วยว่า: ถ้าปิด multicast **ระหว่าง**ที่ทั้งสองโปรแกรมเจอกันแล้ว ข้อมูลจะหยุดไหม (discovery เกิดแค่ตอนเริ่ม)
หมายเหตุ: `start_sim.sh` จะไม่ยอมเปิดถ้า multicast ปิด

### ค. ชื่อ topic ผิด
แก้เป็น `"lowstate"` หรือ `"rt/low_state"` ในสำเนาของไฟล์

### ง. type ผิด
import `LowState_` จาก `unitree_sdk2py.idl.unitree_go.msg.dds_` แทน `unitree_hg`

### จ. เปิดโปรแกรมก่อน sim
รัน `read_lowstate.py` ก่อน แล้วค่อยเปิด sim → ข้อมูลจะเข้ามาเองไหม หรือต้องรันใหม่

### ตารางผล
| การทดลอง | ทาย | ผลจริง | ทำไมไม่มี error |
|---|---|---|---|
| ก. domain 0 | | | |
| ข. multicast off | | | |
| ข2. ปิดระหว่างทำงาน | | | |
| ค. topic ผิด | | | |
| ง. type unitree_go | | | |
| จ. เปิดก่อน sim | | | |

## บทเรียนสำหรับหุ่นจริง
- ถ้าลืม `--network enp43s0` → โปรแกรมไปฟัง sim (หรือเงียบ) ไม่ข้ามไปหุ่น **นี่คือเหตุผลที่ตั้งให้ sim เป็นค่าเริ่มต้น**
- แต่ถ้า sim เปิดค้างไว้ในวันทดสอบแล้วลืม flag → จะได้ข้อมูลจาก sim ทั้งที่คิดว่าเป็นหุ่น (PASS หลอก) จึงต้องพิมพ์ป้าย `SIM` / `REAL ROBOT` ไว้ที่บรรทัดแรกเสมอ (งาน 1.7)
