# DDS พื้นฐาน (เท่าที่ต้องใช้กับ G1)

## DDS คืออะไร
**Data Distribution Service** ระบบส่งข้อความแบบ publish/subscribe ที่ Unitree SDK และ ROS 2 ใช้ (ตัวที่เราใช้คือ **CycloneDDS**)

| เรียกฟังก์ชันตรงๆ | DDS (publish/subscribe) |
|---|---|
| ผู้เรียกต้องรู้จักผู้ถูกเรียก | ผู้ส่งกับผู้รับไม่รู้จักกัน รู้แค่ "ชื่อ topic" |
| 1 ต่อ 1 | 1 ส่ง หลายรับได้ (monitor หลายตัวฟังพร้อมกัน) |
| รอผลตอบกลับ | ส่งแล้วไปต่อ ไม่รอ |
| อีกฝั่งไม่อยู่ = error | อีกฝั่งไม่อยู่ = **เงียบ** (รอไปเรื่อยๆ) |

เปรียบเหมือนสถานีวิทยุ: sim "ออกอากาศ" ที่คลื่น `rt/lowstate` ใครเปิดรับคลื่นนี้ก็ได้ยิน คนออกอากาศไม่รู้ว่ามีกี่คนฟัง

## 4 อย่างที่ต้องตรงกันถึงจะได้ยินกัน
| อย่าง | ของเรา (sim) | หุ่นจริง | ถ้าไม่ตรง |
|---|---|---|---|
| **domain** (ห้อง) | 1 | 0 | เงียบ |
| **interface** (การ์ดเครือข่าย) | `lo` | `enp43s0` | เงียบ / error ถ้าการ์ดไม่มีอยู่ |
| **ชื่อ topic** | `"rt/lowstate"` | เหมือนกัน | เงียบ |
| **type** ของ message | `unitree_hg` `LowState_` | เหมือนกัน | เงียบ (ใช้ `unitree_go` = ผิด) |

ในโค้ด:
```python
ChannelFactoryInitialize(domain, iface)               # ห้อง + การ์ด
sub = ChannelSubscriber("rt/lowstate", LowState_)     # ชื่อ topic + type
sub.Init(handler, 10)                                 # ฝาก callback, คิว 10
```

## domain: ห้องคนละห้อง
- เลข 0–232 โปรแกรมคนละ domain มองไม่เห็นกันเลย แม้อยู่เครื่องเดียวกัน
- หุ่นจริงใช้ 0 (ค่าตายตัวของหุ่น) sim ของเราตั้งเป็น 1 (`~/g1_study/sim/config.yaml: domain_id: 1`)
- ข้อดีของการแยก: ลืม flag แล้วไม่ข้ามไปหาหุ่นจริงโดยไม่ตั้งใจ (กั้นสองชั้นด้วย interface + domain, vault `DDS and Domains.md`)

## multicast: "ตะโกนถาม" (discovery)
ตอนเปิดโปรแกรม เรายังไม่รู้ว่า sim อยู่ที่ IP/port ไหน DDS จึงแก้ด้วยการ:
1. ทุกโปรแกรม**ตะโกน** (multicast) ไปที่กลุ่มที่ตกลงกันไว้ว่า "ฉันอยู่ domain 1 มี topic นี้"
2. คนที่ฟังอยู่ได้ยิน แล้วรู้ที่อยู่ของกันและกัน
3. จากนั้นส่งข้อมูลจริงหากัน

**`lo` (loopback)** = การ์ดเสมือนที่วนกลับเข้าเครื่องตัวเอง โดยปกติไม่เปิด multicast → ตะโกนแล้วไม่มีเสียง → หากันไม่เจอ **ไม่มี error**
```bash
ip link show lo                       # ต้องมี MULTICAST ใน <...>
sudo ip link set lo multicast on      # เปิด (หายทุกครั้งที่รีบูต)
```
| ส่วน | ความหมาย |
|---|---|
| `sudo` | ต้องใช้สิทธิ์ root |
| `ip link` | จัดการตัวการ์ด (layer 2) · `ip addr` = IP · `ip route` = เส้นทาง |
| `set lo multicast on` | เปิด flag MULTICAST ให้ `lo` |

ส่วน `enp43s0` (การ์ดจริงที่ต่อกับหุ่น) เปิด multicast ไว้ตั้งแต่แรก แพ็กเก็ตบน `lo` ไม่ออกนอกเครื่อง เปิดค้างไว้จึงไม่มีความเสี่ยงด้านความปลอดภัย

## `rt/` ย่อมาจากอะไร
**ROS topic** ROS 2 ใช้ DDS เหมือนกันและเติม prefix ให้ชื่อ topic ใน DDS: `rt/` = topic, `rq/` = service request, `rr/` = service reply
Unitree ตั้งชื่อ `rt/lowstate` เพื่อให้ ROS 2 เห็นเป็น `/lowstate` ทันที ส่วนเราใช้ SDK คุยกับ DDS ตรงๆ จึงต้องพิมพ์ชื่อเต็มเอง

## type ของ message มาจากไหน
```
LowState_.idl  ──idlc (IDL compiler)──▶  unitree_sdk2py/idl/unitree_hg/msg/dds_/_LowState_.py
```
- IDL = ภาษากลางที่ใช้นิยาม message ไฟล์เดียวสร้างได้ทั้ง C++ (sim, g1_ctrl) และ Python (เรา) ทั้งสองฝั่งจึงคุยกันได้
- เทียบกับ ROS 2: ไฟล์ `.msg` + `colcon build` สร้างโค้ดแบบเดียวกัน (ROS 2 เองก็แปลง `.msg` เป็น `.idl` อยู่เบื้องหลัง)
- `typename="unitree_hg.msg.dds_.LowState_"` ใน class คือชื่อที่ใช้จับคู่ฝั่งส่งกับฝั่งรับ
- หาว่าต้อง import อะไร: ดูตัวอย่างของหุ่นรุ่นเดียวกัน (`example/g1/low_level/g1_low_level_example.py` บรรทัด 9) หรือ `grep -rn "rt/lowstate" example/g1/`

## ลำดับชั้น (เทียบ ROS 2)
```
rclpy / rclcpp (ROS Client Library)       unitree_sdk2py ← เราอยู่ตรงนี้
         rcl (C)                                 │
         rmw (ROS MiddleWare)                    │
              CycloneDDS ◀──────────────────────┘
```

## ต่อหุ่นจริง (งาน 1.7)
```bash
sudo ip addr add 192.168.123.123/24 dev enp43s0    # IP ของเรา วงเดียวกับหุ่น (192.168.123.x)
sudo ip link set enp43s0 up
ping 192.168.123.161                               # หุ่น
```
(ทางลัดในเครื่องนี้: `g1net` ทำทั้งหมดนี้ + เปิด multicast ของ `lo`, vault `Environments Map.md`)
ในโค้ดใช้ `ChannelFactoryInitialize(0, "enp43s0")` **ไม่ต้องใส่ IP ของหุ่น** เพราะ discovery หาให้เอง แต่ต้องบอกการ์ด เพราะเครื่องมีหลายการ์ด (`lo`, `enp43s0`, WiFi) ถ้าเลือกผิดก็ตะโกนผิดห้อง

## `CYCLONEDDS_URI`
ตัวแปรจาก ROS ที่บอก CycloneDDS ให้ใช้การ์ดไหน ถ้าค้างอยู่จะขัดกับที่ SDK สั่ง ทำให้หากันไม่เจอหรือ crash แก้ด้วย `env -u CYCLONEDDS_URI python ...`

## คำถามเช็ค
1. ถ้าพิมพ์ topic เป็น `"lowstate"` (ไม่มี `rt/`) โปรแกรมจะ error ไหม เพราะอะไร
2. ทำไมโปรแกรมไม่ต้องรู้ IP ของหุ่น แต่ต้องรู้ชื่อการ์ด
3. ถ้าใช้ type `unitree_go` LowState_ กับ G1 จะเกิดอะไร
