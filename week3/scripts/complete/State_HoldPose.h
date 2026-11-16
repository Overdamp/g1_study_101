// State_HoldPose.h: ค้างทุกข้อต่อไว้ที่ท่าตอนกดเข้า ด้วย gain จาก config (งาน 3.7) ฉบับสมบูรณ์
//
// ไฟล์ปลายทาง: ~/g1_study/week3/deploy/robots/g1_23dof/include/State_HoldPose.h  (สำเนาเท่านั้น)
// ติดตั้งอัตโนมัติ: week3/scripts/complete/apply_holdpose.sh  (ก็อปไฟล์นี้ + แก้ main.cpp + config.yaml)
// สเปค H1–H7: week3/docs/holdpose_spec.md
// ⚠️ รันกับ sim เท่านั้น (ไม่ใส่ --network) ห้ามใช้ binary ที่แก้เองกับหุ่นจริง

#pragma once

#include <algorithm>
#include <string>
#include <vector>

#include "FSM/FSMState.h"

class State_HoldPose : public FSMState
{
public:
    State_HoldPose(int state, std::string state_string = "HoldPose")
    : FSMState(state, state_string)       // แม่: อ่าน transitions จาก yaml + เติม timeout → Passive ให้เอง (H6)
    {
        // H4: gain จาก config อ่านครั้งเดียวตอนเปิดโปรแกรม (แก้ yaml แล้วต้องเปิด g1_ctrl ใหม่ เหมือน state อื่น)
        auto cfg = param::config["FSM"][state_string];
        kp_ = cfg["kp"].as<std::vector<float>>();
        kd_ = cfg["kd"].as<std::vector<float>>();
        if (cfg["ramp_s"]) ramp_s_ = cfg["ramp_s"].as<float>();   // H7 (ไม่มี key = ไม่ ramp)

        if (kp_.size() != kd_.size()) {
            spdlog::error("HoldPose: kp ({}) and kd ({}) sizes differ; using the shorter one", kp_.size(), kd_.size());
            const size_t n = std::min(kp_.size(), kd_.size());
            kp_.resize(n);
            kd_.resize(n);
        }
    }

    void enter()
    {
        // H3: เป้าหมาย = ท่าปัจจุบัน
        // ใช้มุมจริงจาก lowstate (ไม่ใช่ q ในคำสั่งเดิม): ถ้าเข้าจาก Passive สองค่านี้เท่ากันอยู่แล้ว
        // (Passive::run คัดลอก q จริงเป็นคำสั่งทุกรอบ) แต่ lowstate ถูกต้องเสมอไม่ว่าเข้ามาจาก state ไหน
        const size_t n = std::min(kp_.size(), lowcmd->msg_.motor_cmd().size());
        for (size_t i = 0; i < n; ++i) {
            auto & motor = lowcmd->msg_.motor_cmd()[i];          // & = แก้ของจริงใน lowcmd
            motor.q() = lowstate->msg_.motor_state()[i].q();
            motor.dq() = 0;
            motor.tau() = 0;
            motor.kd() = kd_[i];                                 // kd เต็มตั้งแต่แรก: หน่วงอย่างเดียว ไม่ดึงไปไหน ปลอดภัย
            motor.kp() = (ramp_s_ > 0) ? 0.0f : kp_[i];          // H7: เริ่ม kp ที่ 0 แล้วให้ run() ค่อยๆ เพิ่ม
        }
        t0_ = now_s();
        spdlog::info("HoldPose: holding current pose (kp ramp {:.1f} s)", ramp_s_);
    }

    void run()
    {
        // ไม่มี ramp: ไม่ต้องทำอะไร q/kp/kd ที่ตั้งใน enter ค้างอยู่ใน lowcmd และ post_run() ส่งทุก 1 ms
        if (ramp_s_ <= 0) return;
        const float alpha = static_cast<float>(std::clamp((now_s() - t0_) / ramp_s_, 0.0, 1.0));
        const size_t n = std::min(kp_.size(), lowcmd->msg_.motor_cmd().size());
        for (size_t i = 0; i < n; ++i) {
            lowcmd->msg_.motor_cmd()[i].kp() = alpha * kp_[i];
        }
    }

    void exit()
    {
        // ไม่ต้องทำ: Passive::enter() ตั้ง kp = 0 ให้เอง
    }

private:
    static double now_s() { return (double)unitree::common::GetCurrentTimeMillisecond() * 1e-3; }

    std::vector<float> kp_;
    std::vector<float> kd_;
    double ramp_s_ = 0.0;
    double t0_ = 0.0;
};

REGISTER_FSM(State_HoldPose)
