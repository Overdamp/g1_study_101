# g1_ctrl: สถาปัตยกรรม FSM

อ้างอิงหลักแบบไล่ทีละบรรทัด: vault `04 Code Map/FSM Code Walkthrough.md`
ไฟล์นี้สรุปเป็นภาพรวมสำหรับงาน 3.5–3.8 (repo: `~/nvidia/unitree/unitree_rl_mjlab`, branch `phase3-delay-dr`)

## แผนที่ไฟล์
```
deploy/
├── include/                      ← ใช้ร่วมกับหุ่นทุกรุ่น (Unitree)
│   ├── FSM/
│   │   ├── BaseState.h           แม่แบบ state + มาโคร REGISTER_FSM
│   │   ├── FSMState.h            แม่ชั้น 2: อ่าน transitions จาก yaml, timeout, ส่ง lowcmd
│   │   ├── CtrlFSM.h             ตัวคุม: สร้าง state จาก config, loop 1 kHz, เปลี่ยน state
│   │   ├── State_Passive.h       damping
│   │   ├── State_FixStand.h      ไล่เข้าท่ายืน
│   │   └── State_RLBase.h        รัน policy (ตัวจริงอยู่ใน robots/g1_23dof/src/)
│   ├── param.h                   อ่าน config.yaml + argument
│   ├── LinearInterpolator.h      ใช้ใน FixStand
│   └── unitree_joystick_dsl.hpp  แปลงข้อความ "LT + up.on_pressed" เป็นฟังก์ชัน
└── robots/g1_23dof/              ← เฉพาะหุ่นเรา
    ├── main.cpp                  entry point: domain/network, เช็ค lowcmd ซ้อน, mode_machine, สร้าง FSM
    ├── config/config.yaml        state ที่เปิดใช้ (`_:`), transitions, gain, ท่ายืน
    ├── include/State_Handover.h  ตัวอย่าง state ที่ "เราเพิ่มเอง" ← ใช้เป็นแบบในงาน 3.7
    ├── src/State_RLBase.cpp      policy + soft start + เช็คเอียง
    └── CMakeLists.txt
```

## ลำดับการทำงาน
```
[ก่อน main]  #include "State_X.h"  →  REGISTER_FSM(State_X) ลงทะเบียน "State_X" ลงใน map
     │
main()
  1. take_domain_arg()            ตัด --domain ออกจาก argv
  2. param::helper()              อ่าน --network และโหลด config.yaml ที่อยู่ข้าง binary
  3. ChannelFactory::Init(domain, network)       ← เหมือน ChannelFactoryInitialize ใน Python
  4. init_fsm_state()
       - ฟัง rt/lowcmd 0.2 s → ถ้ามีคนส่งอยู่แล้ว: log critical (แต่ไม่ exit!)
       - สร้าง lowcmd (publisher), lowstate (subscriber)
       - wait_for_connection() → set_timeout_ms(100)
  5. mode_machine = 4 → check_mode_machine() ไม่ตรง = exit
  6. CtrlFSM(config["FSM"])
       - วน `_:` → จับคู่ id ↔ ชื่อ
       - วนอีกรอบ → หา "State_" + type ใน map → สร้าง object (ctor ของ FSMState อ่าน transitions)
  7. (เฉพาะ lo) เพิ่มคีย์ h / p สำหรับ Handover
  8. fsm->start()  → states[0].enter() → RecurrentThread 1 ms เรียก run_()
  9. while(true) sleep(1)           ← main ไม่ทำอะไร งานจริงอยู่ใน thread  (เหมือน read_lowstate.py!)
```

## กลไกลงทะเบียน state (`REGISTER_FSM`)
ปัญหาคือ config เขียนชื่อ state เป็น**ข้อความ** (`type: RLBase`) แต่โปรแกรมต้องสร้าง **object ของ class** ขึ้นมา จะแปลงจากชื่อเป็น class ได้ยังไง

```cpp
REGISTER_FSM(State_Passive)
```
มาโครนี้ขยายออกมาเป็น 2 อย่าง:
1. ฟังก์ชันโรงงาน `__factory_State_Passive(id, name)` ทำหน้าที่ `make_shared<State_Passive>(id, name)`
2. **object static** ที่ constructor ของมันรัน**ก่อน `main()`** และใส่ `"State_Passive" → โรงงาน` ลงใน map

เทียบกับ Python ได้ประมาณนี้:
```python
FSM_MAP = {}
def register(cls):            # decorator
    FSM_MAP[cls.__name__] = cls
    return cls

@register
class State_Passive(FSMState): ...
```

**ผลที่ตามมา:** ถ้าไม่ `#include "State_X.h"` ใน `main.cpp` โค้ดลงทะเบียนก็จะไม่ถูก compile เข้ามา ตอนเริ่มโปรแกรมจะได้ `FSM: Unknown FSM type X` ข้อนี้คืองาน 3.8 (ก)

## transitions จาก config กลายเป็นโค้ดได้ยังไง
```yaml
FixStand:
  transitions:
    Passive: LT + B.on_pressed
    Velocity: RT + A.on_pressed
```
ใน constructor ของ `FSMState`:
1. อ่านเป็น `std::map<string,string>` ซึ่ง**เรียงตามชื่อปลายทาง** (A→Z) ไม่ได้เรียงตามลำดับในไฟล์
2. แต่ละข้อความถูก Parse + Compile (`unitree_joystick_dsl.hpp`) ให้กลายเป็นฟังก์ชันที่คืน `bool`
3. ใส่ลง `registered_checks` เป็นคู่ `(ฟังก์ชัน, id ปลายทาง)`
4. ถ้าเป็น sim จะเติมคีย์บอร์ดตาม**คู่ที่เขียนตายตัวไว้**: Passive→FixStand=`u`, FixStand→Velocity=`v`, (FixStand|Velocity)→Passive=`p`
5. สุดท้ายเติม `timeout → Passive` ให้ทุก state

⚠️ คีย์บอร์ดของ state ใหม่ **ไม่มีให้อัตโนมัติ** ต้องเพิ่มเองใน `main.cpp` แบบเดียวกับที่ทำให้ Handover (`h` / `p`) นี่เป็นส่วนหนึ่งของงาน 3.7

## ข้อมูลที่ทุก state ใช้ร่วมกัน
```cpp
static std::unique_ptr<LowCmd_t>  lowcmd;    // คำสั่งก้อนเดียว ทุก state เขียนลงที่นี่
static std::shared_ptr<LowState_t> lowstate; // state ล่าสุด
static std::shared_ptr<Keyboard>   keyboard;
```
- `static` แปลว่ามีชุดเดียว ทุก state เห็นตัวเดียวกัน
- ค่าที่ state ก่อนหน้าตั้งไว้ **ยังค้างอยู่** ถ้า state ใหม่ไม่ได้เขียนทับ เช่น `mode = 1` ตั้งครั้งเดียวใน ctor ของ Passive แล้วใช้ไปตลอด
- `lowcmd` เป็น `RealTimePublisher` (`/opt/unitree_robotics/include/unitree/dds_wrapper/`) ข้างในมี mutex ของมันเอง
  - `post_run()` เรียก `lowcmd->unlockAndPublish()` ซึ่ง**ไม่ได้ส่งเอง** แค่ปลด lock และบอกว่า "msg_ พร้อมแล้ว"
  - ก่อนส่งจริง wrapper จะเรียก `pre_communication()` ที่คำนวณ CRC ให้ (`robots/g1/g1_pub.h`) เราจึงไม่ต้องคำนวณ CRC เองเหมือนใน Python สัปดาห์ 2
  - แนวคิดเดียวกับ `Lock` ในงาน 1.3: ฝั่งเขียน (FSM) กับฝั่งส่ง ไม่แตะ msg พร้อมกัน
- `check_mode_machine()`: ถ้า LowState ส่ง `mode_machine = 0` จะถือว่าเป็น sim และให้ผ่าน แต่ sim ของเราส่ง 4 (23-DoF) ตาม `unitree_sdk2_bridge.h`

## gotchas (สรุปจาก walkthrough ข้อ 10)
| เรื่อง | ผล |
|---|---|
| state เริ่มต้น = ตัวแรกใน `_:` | อย่าย้าย Passive ออกจากบรรทัดแรก (งาน 3.8 ข) |
| เงื่อนไขเรียงตามชื่อปลายทาง | ถ้าเป็นจริงพร้อมกัน ตัวที่ชื่อมาก่อนชนะ (งาน 3.8 ง) |
| `static auto kp = ...` ใน `enter()` | อ่าน config ครั้งแรกครั้งเดียว แก้ yaml ระหว่างรันไม่มีผล (งาน 3.8 ค) |
| เช็ค lowcmd ซ้อนแล้ว**ไม่ exit** | `exit(0)` ถูก comment ไว้ ต้องเช็คเองก่อนเปิดโปรแกรม |
| timeout ป้องกันได้แค่ขาเข้า | ถ้าเน็ตขาดทั้งไปและกลับ คำสั่ง Passive ก็ไปไม่ถึงหุ่น |
| `run()` ของ state ใหม่ช้ากว่า `enter()` 1 รอบ | 1 ms แรกส่งค่าที่ `enter()` ตั้งไว้ |
| include = ลงทะเบียน | ลืม include → `Unknown FSM type` |

## คำถามเช็ค
1. `main()` ของ g1_ctrl จบด้วย `while(true) sleep(1)` ทำไม (เทียบกับ `read_lowstate.py`)
2. ถ้าเพิ่ม `HoldPose: id: 5` ใน `_:` แต่ไม่ได้เขียน `transitions` ของ HoldPose เลย จะออกจาก HoldPose ได้ทางไหนบ้าง
3. ถ้า state ใหม่ไม่ได้ตั้ง `mode` ของมอเตอร์ จะใช้ค่าอะไร มาจากไหน
