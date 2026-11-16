# แก้ `main.cpp` ของสำเนา (งาน 3.7)

ไฟล์: `~/g1_study/week3/deploy/robots/g1_23dof/main.cpp` (สำเนาเท่านั้น)

## 1. include (ลงทะเบียน state)
บนสุด ต่อจาก `#include "State_Handover.h"`:
```cpp
// TODO [3.7] #include "..."   ← ชื่อไฟล์ที่ก็อป skeleton ไปวาง
```
ถ้าลืม: เปิดโปรแกรมแล้วจะขึ้น `FSM: Unknown FSM type HoldPose` (งาน 3.8 ก ให้ลองลืมดูก่อนว่า error ตอน compile หรือตอนรัน)

## 2. คีย์บอร์ดใน sim
คู่คีย์ `u` / `v` / `p` ใน `FSMState.h` **เขียนตายตัวไว้** state ใหม่จึงไม่มีคีย์ให้อัตโนมัติ ต้องเพิ่มเองแบบเดียวกับที่ทำให้ Handover

หาบล็อกนี้ใน `main.cpp` (ราวบรรทัด 103–118):
```cpp
if (FSMState::keyboard_fsm_shortcuts_enabled && FSMStringMap.right.count("Handover")) {
    int passive = FSMStringMap.right.at("Passive");
    int handover = FSMStringMap.right.at("Handover");
    auto key_is = [](std::string k) { ... };
    for (auto & s : fsm->states) {
        if (s->isState(passive)) s->registered_checks.emplace_back(key_is("h"), handover);
        if (s->isState(handover)) s->registered_checks.emplace_back(key_is("p"), passive);
    }
}
```
เพิ่มบล็อกใหม่**ต่อจากบล็อกนี้** (ก่อน `fsm->start();`):
```cpp
// TODO [3.7] ถ้าเป็น sim และมี state "HoldPose" ใน FSMStringMap:
//   int passive  = ...;
//   int holdpose = ...;
//   ใช้ lambda key_is แบบเดียวกัน (ประกาศใหม่ในบล็อกนี้ หรือย้ายของเดิมออกมาใช้ร่วม)
//   วน fsm->states:
//     Passive  → เพิ่ม (key_is("o"), holdpose)
//     HoldPose → เพิ่ม (key_is("p"), passive)
```
คำถาม:
1. ทำไมเงื่อนไข `if (FSMState::keyboard_fsm_shortcuts_enabled ...)` ถึงสำคัญ (นึกถึงหุ่นจริง)
2. คีย์ที่เพิ่มตรงนี้ไปต่อท้าย `registered_checks` **หลัง** timeout ถ้ากด `o` พร้อมกับที่ LowState หาย จะไป state ไหน

## 3. ข้อความช่วยเหลือ (ไม่บังคับ)
ในส่วน `std::cout << "Simulation keyboard: ..."` เพิ่ม `[o] HoldPose (from Passive)` ให้รู้ว่ามีคีย์นี้

## ตรวจหลังแก้
```bash
cd ~/g1_study/week3/deploy && git diff          # ควรเห็นแค่ 3 ไฟล์: main.cpp, config.yaml, State_HoldPose.h (ใหม่)
cd robots/g1_23dof/build && make -j$(nproc)
```
แผนทดสอบ T1–T8 อยู่ใน `week3/docs/holdpose_spec.md`
