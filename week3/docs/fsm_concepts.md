# FSM (Finite State Machine): แนวคิด

## FSM คืออะไร
โปรแกรมที่ **อยู่ได้ทีละ state** แต่ละ state มีพฤติกรรมของตัวเอง และมี **เงื่อนไข (transition)** ที่บอกว่าจะย้ายไป state ไหน

ตัวอย่างในชีวิตจริง: ไฟจราจร (แดง → เขียว → เหลือง → แดง) ซึ่งอยู่ได้ทีละสีเท่านั้น และเปลี่ยนเมื่อหมดเวลา

## ส่วนประกอบของ state หนึ่งตัว
| ส่วน | ทำเมื่อไหร่ | ใช้ทำอะไร | ตัวอย่างใน g1_ctrl |
|---|---|---|---|
| `enter()` | **ครั้งเดียว** ตอนเพิ่งเข้า state | ตั้งค่าเริ่มต้น: gain, จดท่าเริ่ม, จดเวลาเริ่ม | FixStand: ตั้ง kp/kd, จด `q0`, `t0` |
| `run()` | **ทุกรอบ** (1 ms) ตอนอยู่ใน state | งานต่อเนื่อง: คำนวณเป้าหมายรอบนี้ | FixStand: interpolate จาก q0 ไป qs ตามเวลา |
| `exit()` | ครั้งเดียว ตอนกำลังออก | เก็บกวาด | (ใน g1_ctrl ส่วนใหญ่ว่าง) |
| transitions | เช็คหลัง `run()` ทุกรอบ | "ถ้า ... ให้ไป state ..." | FixStand: LT + B → Passive, RT + A → Velocity |

**หลักการแยก:** ถ้าทำซ้ำทุกรอบแล้วผิด (เช่นจด `t0` ใหม่ทุกรอบ เวลาจะไม่เดิน) ต้องอยู่ใน `enter` ถ้าต้องอัพเดทตามเวลาหรือตาม state ให้อยู่ใน `run`

## loop หลัก (หัวใจของ FSM)
```
ทุก 1 ms:
    current.pre_run()      # อ่าน state ล่าสุด, อ่านปุ่ม
    current.run()          # คำนวณคำสั่ง
    current.post_run()     # ส่ง lowcmd (+ CRC)
    for (เงื่อนไข, ปลายทาง) in current.checks:      # เรียงตามลำดับ
        if เงื่อนไข():
            current.exit(); current = ปลายทาง; current.enter()
            break                                    # เปลี่ยนได้ครั้งเดียวต่อรอบ
```
นี่คือ `CtrlFSM::run_()` ทั้งฟังก์ชัน (`deploy/include/FSM/CtrlFSM.h`) ใน mini FSM ภาษา Python (งาน 3.2) ให้เขียนโครงเดียวกันนี้

## state ของ g1_ctrl
```
             (L2 + ↑ / u)            (R2 + A / v)
  Passive ───────────────► FixStand ───────────────► Velocity (policy)
   ▲   ▲                       │                         │
   │   └────(L2 + B / p)───────┴─────────────────────────┘
   │
   └── ทุก state: LowState ขาด > 100 ms → Passive
       Velocity: เอียง > 0.85 rad → Passive
```
(Handover ไม่แสดงในภาพนี้ ดู vault `g1_ctrl FSM.md`)

| state | gain | `enter` | `run` |
|---|---|---|---|
| Passive | kp 0, kd 2.5–6 | ตั้ง kp=0, kd จาก config | คัดลอก q จริงเป็น q คำสั่ง |
| FixStand | kp 40–200 | ตั้ง gain, จด q0 (ท่าปัจจุบัน), t0 | interpolate q0 → ท่ายืนใน 3 s แล้วค้าง |
| Velocity | จาก `deploy.yaml` | โหลด/รีเซ็ต policy | อ่าน obs → policy → q คำสั่ง (+ soft start 0.5 s) |

## ทำไม Passive เป็น "ที่พัก" ที่ปลอดภัยที่สุด
1. **kp = 0:** ไม่มีสปริงดึงไปไหน หุ่นไม่ทำท่าแรงๆ เอง
2. **kd > 0:** ยังมีความหนืด ถ้าล้ม ข้อต่อจะไม่หมุนอิสระเร็วๆ (ต่างจาก zero torque)
3. **ทุกเส้นทางกลับมาที่นี่ได้:** ปุ่ม LT + B จากทุก state + timeout + เอียงเกิน
4. **เป็น state แรกตอนเปิดโปรแกรม** (`states[0]`)

### ทำไม Passive คัดลอก q จริงเป็นคำสั่งทุกรอบ ทั้งที่ kp = 0
ตอนนี้ kp = 0 ค่า q ในคำสั่งจึงไม่มีผลอะไร แต่**รอบที่เปลี่ยนไป FixStand** จะเกิดลำดับนี้:
- `FixStand::enter()` ตั้ง kp = 100 ทันที แล้วจด `q0` จาก **q ในคำสั่ง**
- ถ้า q ในคำสั่งเป็นค่าเก่า (หรือ 0) → kp สูง × ระยะห่างมาก = หุ่นกระตุกแรง
- เพราะ Passive คัดลอก q จริงไว้ตลอด q ในคำสั่งจึง = ท่าปัจจุบันพอดี → เริ่มอย่างนุ่มนวล

นี่คือหลักเดียวกับงาน 2.4 (q_des = มุมปัจจุบันก่อนเปิด kp)

## transition ที่ดีควรมีอะไร
| หลัก | ใน g1_ctrl |
|---|---|
| ทางออกฉุกเฉินจากทุก state | LT + B → Passive, timeout → Passive |
| ห้ามข้ามขั้นที่อันตราย | Passive → Velocity ตรงๆ ไม่ได้ ต้องผ่าน FixStand |
| ใช้ "กดลง" (edge) ไม่ใช่ "กดค้าง" (level) | `.on_pressed` ถ้าใช้แบบกดค้าง state จะเปลี่ยนซ้ำทุก ms |
| เงื่อนไขชนกัน เลือกตัวที่ปลอดภัย | เรียงตามชื่อ: `Passive` < `Velocity` → ชนกันจะไป Passive |

## Python ↔ g1_ctrl (ใช้ตอนทำ 3.2)
| แนวคิด | Python (mini_fsm.py) | g1_ctrl (C++) |
|---|---|---|
| state | `class Hold(State)` | `class State_FixStand : public FSMState` |
| เมธอด | `def enter(self)` | `void enter()` (virtual) |
| ข้อมูลร่วม | ตัวแปรของ class / object ที่ส่งให้ทุก state | `static lowcmd`, `static lowstate` ใน FSMState |
| เงื่อนไข | list ของ `(lambda: key == 'o', 'Hold')` | `registered_checks`: `vector<pair<function<bool()>, int>>` |
| loop | `while True: ... time.sleep(0.002)` | `RecurrentThread` 1 ms เรียก `run_()` |
| เลือก state เริ่ม | `current = states['Passive']` | `states[0]` (ตัวแรกใน `_:` ของ config) |

## คำถามเช็ค
1. ถ้าเผลอเอาการจด `t0` ไปไว้ใน `run()` แทน `enter()` FixStand จะทำตัวยังไง
2. ทำไม transition ต้องใช้ `.on_pressed` แทนการเช็คว่า "ปุ่มกำลังถูกกดอยู่"
3. ถ้าจะเพิ่ม state `Wave` อยากให้เข้าได้จาก `Hold` เท่านั้น ไม่ใช่จาก `Passive` ต้องแก้ตรงไหน
