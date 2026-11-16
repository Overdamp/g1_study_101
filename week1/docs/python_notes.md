# Python ที่ใช้ในสัปดาห์ 1 (และวิธีหาเองเมื่อไม่รู้ syntax)

## หา API เอง: 3 แหล่ง
1. **ตัวอย่างที่ใกล้ที่สุด:** `~/nvidia/unitree/unitree_sdk2_python/example/helloworld/subscriber.py` (subscriber ที่สั้นที่สุด) และ `example/g1/low_level/g1_low_level_example.py` (G1 จริง) ให้อ่านแล้วตอบว่า import อะไร, ทำอะไรก่อน subscribe, ข้อมูลเข้ามาทางไหน
2. **source ของ SDK:** ตามบรรทัด import ไปที่ไฟล์ เช่น `unitree_sdk2py/core/channel.py` จะเห็น `ChannelSubscriber(name, type)`, `Init(handler, queueLen)`
3. **ถาม Python:** ใน `python` หรือ `ipython`
   ```python
   help(ChannelSubscriber)      # signature + docstring
   dir(msg)                     # มี field อะไร
   type(msg.motor_state[0])     # เป็น class อะไร
   ```

## REPL (`python` แบบโต้ตอบ)
- กด Enter จริงๆ เพื่อขึ้นบรรทัดใหม่ (`\` ไม่ได้แปลว่าขึ้นบรรทัด)
- prompt `...` = ยังอยู่ใน block ให้เยื้อง 4 ช่อง แล้วกด Enter บรรทัดว่างเพื่อจบ block

## callback
```python
def on_lowstate(msg):          # ฟังก์ชันที่ "ฝาก" ไว้
    print("ได้ข้อความแล้ว")

sub.Init(on_lowstate, 10)      # ส่งตัวฟังก์ชัน ไม่มีวงเล็บ
# sub.Init(on_lowstate(), 10)  ← ผิด: เรียกทันที แล้วส่ง None เข้าไป
```
SDK เป็นคนเรียก `on_lowstate(msg)` ทุกครั้งที่มีข้อความ **จาก thread ของ SDK เอง** ไม่ใช่ thread ของ `main`
แบบอื่นคือ **polling** (`sub.Read()`) ที่ตัวอย่าง helloworld ใช้ ซึ่งเราต้องวนดึงข้อมูลเอง

## ทำไม `main` ต้องมี `while True: time.sleep(...)`
ถ้า `main` ทำขั้น 1–3 แล้วจบ โปรแกรมจะปิดทันที callback ไม่ทันได้ทำงาน (g1_ctrl ก็จบ `main()` ด้วย `while(true) sleep(1)` เหมือนกัน)

## class + `self`
```python
class LowStateReader:
    def __init__(self):            # เรียกตอนสร้าง object
        self.count = 0             # attribute ของ object
    def handler(self, msg):        # method: self = object ตัวนั้น
        self.count += 1            # ต้องมี self. ไม่งั้นเป็นตัวแปรท้องถิ่น

reader = LowStateReader()
sub.Init(reader.handler, 10)       # ส่ง method ของ object (ไม่มีวงเล็บ)
```
**`count += 1` (ไม่มี `self.`) → `UnboundLocalError`:** Python เห็นว่ามีการ assign ใน method จึงถือว่า `count` เป็นตัวแปรท้องถิ่น แต่ยังไม่เคยกำหนดค่า (ถ้าใช้ตัวแปร global ต้องประกาศ `global count`)

## type hints
```python
def render(s: dict, limits: dict) -> str:   # s เป็น dict, คืน str
```
- `->` = ชนิดของค่าที่คืน (ไม่ใช่ arrow function ของ JS · ตัวที่ใกล้ arrow function คือ `lambda`)
- **Python ไม่บังคับ** ตอนรัน: `def f() -> str: return 42` รันผ่าน คืน 42 ไม่มี error (ทดลองแล้วในงาน)
- มีไว้ให้คนอ่าน + IDE/`mypy` ช่วยเช็ค

## `None` = ยังไม่มีข้อมูล
```python
self.elbow_q = None            # ดีกว่า 0: แยก "ยังไม่มีข้อมูล" กับ "มุม 0°" ออกจากกัน
...
if q is None:
    print("no LowState yet")   # math.degrees(None) → TypeError
```

## f-string จัดรูปแบบ
| เขียน | ผล | ใช้ |
|---|---|---|
| `f"{x:.1f}"` | `69.3` | ทศนิยม 1 |
| `f"{x:+.1f}"` | `+69.3` | แสดงเครื่องหมายเสมอ |
| `f"{x:8.3f}"` | `   1.209` | กว้าง 8 (เลขตรงคอลัมน์) |
| `f"{name:<28}"` | ชิดซ้าย กว้าง 28 | ชื่อข้อต่อ |
| `f"{slot:>4}"` | ชิดขวา กว้าง 4 | เลข slot |
| `f"{v:#010x}"` | `0x8fc2257d` | เลขฐาน 16 |

## argparse (งาน 1.7)
```python
import argparse
p = argparse.ArgumentParser(description="...")
p.add_argument("--network", default="lo", help="lo = sim, enp43s0 = หุ่นจริง")
p.add_argument("--domain", type=int, default=None)    # ไม่ใส่ type → ได้ str "0" ไม่ใช่ int 0
args = p.parse_args()
args.network, args.domain
```
- `python x.py --help` แสดงวิธีใช้ให้อัตโนมัติ
- `dest=` เปลี่ยนชื่อ attribute เช่น `--break` เป็นคำสงวน จึงใช้ `dest="break_mode"`

## เวลา
| ฟังก์ชัน | ใช้ |
|---|---|
| `time.sleep(s)` | หยุดรอ (ได้อย่างน้อย s วินาที ไม่ตรงเป๊ะ) |
| `time.monotonic()` | นาฬิกาที่เดินหน้าอย่างเดียว ใช้วัดช่วงเวลา (ไม่ถอยหลังตอนปรับเวลาเครื่อง) |
| `time.time()` | เวลานาฬิกาจริง (ใช้บันทึก ไม่ใช่วัดช่วง) |

## ANSI ล้างจอ (1.5)
`print("\033[H\033[2J" + text)` เลื่อน cursor ไปมุมบนซ้ายแล้วล้างจอ ตารางจะวาดทับที่เดิม

## import ที่ IDE แอบเติม
ถ้าเห็นบรรทัดแปลกๆ อย่าง `from numpy.core import function_base` โผล่ขึ้นมาทั้งที่ไม่ได้ใช้ มักเป็น auto-import ของ IDE ให้ลบทิ้ง (ทำให้เกิด DeprecationWarning)
และตั้ง interpreter ของ IDE เป็น env `g1_sdk` (VS Code: Ctrl+Shift+P → Python: Select Interpreter) IDE จะได้หา `unitree_sdk2py` เจอ
