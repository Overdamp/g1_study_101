# C++ เท่าที่ต้องใช้อ่านไฟล์ FSM (สำหรับคนถนัด Python)

ทุกตัวอย่างเอามาจากโค้ด g1_ctrl จริง

## 1. ไฟล์ `.h` / `#include` / `#pragma once`
```cpp
#pragma once                 // กัน include ซ้ำ (Python import ซ้ำได้อยู่แล้ว ไม่ต้องมี)
#include "FSMState.h"        // ≈ from FSMState import *   (ก็อปเนื้อไฟล์มาวางตรงนี้จริงๆ)
#include <spdlog/spdlog.h>   // <...> = ไลบรารีภายนอก, "..." = ไฟล์ในโปรเจกต์
```
ไฟล์ FSM เขียนทุกอย่างไว้ใน `.h` เลย (header-only) จึงแค่ include ก็ใช้ได้ ไม่ต้องเพิ่มใน `CMakeLists.txt`

## 2. class และการสืบทอด
```cpp
class State_Passive : public FSMState        // class State_Passive(FSMState):
{
public:                                      // เข้าถึงได้จากข้างนอก (Python: ทุกอย่าง public)
    State_Passive(int state, std::string state_string = "Passive")   // def __init__(self, state, state_string="Passive"):
    : FSMState(state, state_string)          //     super().__init__(state, state_string)
    { ... }

    void enter() { ... }                     // def enter(self) -> None:
private:
    double t0_;                              // self._t0  (ต้องประกาศ type ล่วงหน้า)
};
```
- `void` = ไม่คืนค่า
- ชื่อลงท้าย `_` (`t0_`, `qs_`) เป็นธรรมเนียมว่าเป็น member ของ class
- ใน method ไม่ต้องเขียน `this->` (เทียบกับ `self.`) ใช้ชื่อตรงๆ ได้เลย

## 3. `virtual`: override ได้
```cpp
class BaseState {
    virtual void enter() {}     // ค่าเริ่มต้น: ไม่ทำอะไร  ลูกเขียนทับได้
};
```
Python override ได้ทุก method อยู่แล้ว ส่วน C++ ต้องประกาศ `virtual` ในคลาสแม่ ถึงจะเรียกเวอร์ชันของลูกผ่าน pointer ของแม่ได้ (`currentState->enter()`)

## 4. ตัวแปรและ type
```cpp
int id = 3;
float t = 0.5f;
auto kp = ...;                         // ให้ compiler เดา type เอง (คล้าย Python)
std::vector<float> q0;                 // list[float]
q0.push_back(1.0);                     // q0.append(1.0)
q0.size()                              // len(q0)
std::vector<std::vector<float>> qs_;   // list[list[float]]
std::map<std::string, std::string> m;  // dict[str, str]  แต่เรียงตาม key เสมอ!
std::string s = "Passive";
```

## 5. reference `&`: แก้ของจริง ไม่ใช่สำเนา
```cpp
auto & motor = lowcmd->msg_.motor_cmd()[i];   // motor เป็น "ชื่อเล่น" ของช่องจริง
motor.kp() = 0;                               // แก้ใน lowcmd จริง
```
ถ้าไม่มี `&` (`auto motor = ...`) จะได้**สำเนา** การแก้ `motor` จะไม่มีผลกับ lowcmd จริงเลย ไม่มี error ด้วย ระวังให้ดี
(Python: object เป็น reference อยู่แล้ว เลยไม่ค่อยเจอปัญหานี้)

## 6. pointer และ `->`
```cpp
std::shared_ptr<LowState_t> lowstate;    // pointer ที่นับจำนวนผู้ใช้ ลบตัวเองเมื่อไม่มีใครใช้
std::unique_ptr<LowCmd_t> lowcmd;        // pointer ที่มีเจ้าของคนเดียว
lowstate->msg_                           // เข้าถึง member ผ่าน pointer ใช้ ->  (object ตรงๆ ใช้ .)
std::make_shared<State_Passive>(id, name)  // สร้าง object ≈ State_Passive(id, name)
```

## 7. getter/setter แบบ `kp()`
```cpp
motor.kp() = 0;          // ตั้งค่า
float k = motor.kp();    // อ่านค่า
```
message ของ CycloneDDS C++ ใช้ฟังก์ชันชื่อเดียวกับ field ซึ่งคืน reference มา จึงใช้ assign ได้ ส่วนใน Python เขียน `motor.kp = 0`

## 8. `static`
```cpp
static std::unique_ptr<LowCmd_t> lowcmd;   // ใน class: ทุก object ใช้ตัวเดียวกัน (≈ class attribute)
static auto kp = param::config[...];       // ในฟังก์ชัน: สร้างครั้งแรกครั้งเดียว ครั้งต่อไปใช้ค่าเดิม
```
แบบที่สองคือเหตุผลที่แก้ `config.yaml` ระหว่างรันแล้วไม่มีผล

## 9. lambda
```cpp
[]()->bool { return lowstate->isTimeout(); }
[keyboard_key]()->bool { return keyboard->key() == keyboard_key; }
```
≈ `lambda: lowstate.is_timeout()` ส่วน `[...]` คือตัวแปรจากข้างนอกที่ lambda "จับ" เข้ามาใช้ (Python จับให้อัตโนมัติ)

## 10. `std::pair`, `std::function`
```cpp
std::vector<std::pair<std::function<bool()>, int>> registered_checks;
// ≈ registered_checks: list[tuple[Callable[[], bool], int]]
registered_checks.emplace_back(std::make_pair(func, fsm_id));   // .append((func, fsm_id))
registered_checks[i].first()      // เรียกฟังก์ชัน (ตัวแรกของคู่)
registered_checks[i].second       // id ปลายทาง (ตัวที่สอง)
```

## 11. อ่าน YAML (yaml-cpp)
```cpp
param::config["FSM"]["FixStand"]["kp"].as<std::vector<float>>()
// ≈ config["FSM"]["FixStand"]["kp"]  แล้วแปลงเป็น list[float]
param::config["FSM"]["Passive"]["mode"].IsDefined()   // ≈ "mode" in config[...]
```

## 12. log
```cpp
spdlog::info("FSM: Change state from {} to {}", a, b);   // ≈ logging.info(f"... {a} to {b}")
spdlog::warn(...); spdlog::critical(...);
```

## 13. มาโคร `#define`
ตัวประมวลผลก่อน compile (preprocessor) **แทนที่ข้อความ**ก่อนจะ compile `REGISTER_FSM(State_X)` จึงกลายเป็นโค้ดหลายบรรทัด และ `##` แปลว่าเอาข้อความมาต่อกันเป็นชื่อ (`__factory_##Derived` → `__factory_State_X`)

## ข้อผิดพลาดที่คนเขียน Python เจอบ่อย
| พลาด | อาการ |
|---|---|
| ลืม `;` | compile error ชี้บรรทัด**ถัดไป** |
| ลืม `&` ใน `auto & motor` | compile ผ่าน แต่ค่าไม่เปลี่ยน |
| ใช้ `.` กับ pointer (ต้อง `->`) | compile error |
| เทียบ string ด้วย `is` | C++ ใช้ `==` กับ `std::string` ได้เลย |
| index เกิน vector | ไม่มี IndexError เหมือน Python อาจได้ค่าขยะหรือ crash |
| ลืม `}` ปิด class + `;` ท้าย class | error แปลกๆ ในไฟล์อื่น |

## ฝึกอ่าน (ไม่ต้องเขียน)
เปิด `deploy/include/FSM/State_FixStand.h` แล้วแปลทุกบรรทัดเป็น Python ลงกระดาษ ถ้าแปลได้หมดก็พร้อมทำ 3.7
