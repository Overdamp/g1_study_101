// State_HoldPose_skeleton.h: โครงของ state ใหม่ใน g1_ctrl (งาน 3.7)
//
// วิธีใช้:
//   1. ทำสำเนา g1_ctrl ก่อน (week3/scripts/setup_copy.sh หรือ week3/docs/build_and_run.md)
//   2. ก็อปไฟล์นี้ไปที่  ~/g1_study/week3/deploy/robots/g1_23dof/include/State_HoldPose.h
//   3. แก้ main.cpp + config.yaml ตาม main_cpp_changes_skeleton.md และ config_holdpose_skeleton.yaml
//   4. build แล้วรันกับ sim (ไฟล์นี้ compile ผ่านตั้งแต่แรก: ยังไม่ทำอะไร = ทำตัวเหมือน state ว่าง)
// สเปค: week3/docs/holdpose_spec.md (H1–H7) · ตัวอย่างที่ควรเปิดคู่: State_FixStand.h, State_Passive.h, State_Handover.h
// ⚠️ ทำในสำเนาเท่านั้น และรันกับ sim (ไม่ใส่ --network) ห้ามใช้ binary ที่แก้เองกับหุ่นจริง

#pragma once

#include <string>
#include <vector>

#include "FSM/FSMState.h"

class State_HoldPose : public FSMState
{
public:
    State_HoldPose(int state, std::string state_string = "HoldPose")
    : FSMState(state, state_string)       // ctor ของแม่: อ่าน transitions จาก yaml + เติม timeout → Passive
    {
        // TODO [3.7 H4] อ่าน gain จาก config (ไม่ hard-code):
        //   param::config["FSM"][state_string]["kp"]  แปลงเป็น std::vector<float>  เก็บลง kp_
        //   เหมือนกันกับ kd → kd_
        //   ใบ้: ดู State_FixStand ctor/enter ว่าใช้ .as<...>() ยังไง
        //   คำถาม: อ่านใน ctor (ครั้งเดียวตอนเปิดโปรแกรม) กับอ่านใน enter แบบ static ต่างกันยังไง
        // TODO [3.7] ถ้า kp_.size() ไม่เท่ากับ kd_.size() ให้ spdlog::error(...) (กัน yaml พิมพ์ผิด)
    }

    void enter()
    {
        // TODO [3.7 H3] เป้าหมาย = ท่าปัจจุบัน (ห้ามกระตุก)
        //   วน i ตั้งแต่ 0 ถึง kp_.size():
        //     auto & motor = lowcmd->msg_.motor_cmd()[i];      ← ต้องมี & (ไม่งั้นแก้สำเนา ไม่มีผลกับ lowcmd จริง)
        //     motor.q() = ???      lowstate->msg_.motor_state()[i].q()  หรือ  motor.q() เดิม? (holdpose_spec.md ข้อ 1)
        //     motor.dq() = 0;  motor.tau() = 0;
        //     motor.kp() = kp_[i];  motor.kd() = kd_[i];
        //   (ไม่มี H7) ตั้ง kp เต็มเลย · (มี H7) ตั้ง kp = 0 ก่อน แล้วให้ run() ค่อยๆ เพิ่ม
        // TODO [3.7 H7] จดเวลาเริ่ม:  t0_ = (double)unitree::common::GetCurrentTimeMillisecond() * 1e-3;  (ดู State_FixStand)
        // TODO [3.7] spdlog::info("HoldPose: holding current pose");   ← จะเห็นใน log ตอนเข้า
    }

    void run()
    {
        // ไม่มี H7: ว่างได้เลย (q, kp, kd ที่ตั้งใน enter ค้างอยู่ใน lowcmd และ post_run() ส่งให้ทุก 1 ms)
        // TODO [3.7 H7] ramp: alpha = min(1, (เวลาตอนนี้ − t0_) / 1.0)
        //               ทุก i: kp() = alpha * kp_[i]   (kd ตั้งเต็มตั้งแต่แรกได้ไหม? ทำไม)
    }

    void exit()
    {
        // ไม่ต้องทำอะไร: state ถัดไป (Passive) ตั้ง kp = 0 ใน enter() ของมันเอง
    }

private:
    std::vector<float> kp_;
    std::vector<float> kd_;
    double t0_ = 0.0;
};

REGISTER_FSM(State_HoldPose)   // ลงทะเบียนชื่อ "State_HoldPose" (ต้อง #include ไฟล์นี้ใน main.cpp ด้วย ไม่งั้น Unknown FSM type)
