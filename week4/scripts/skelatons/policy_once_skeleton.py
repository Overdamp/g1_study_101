"""policy_once_skeleton.py: ป้อน obs "ยืนนิ่งสมบูรณ์แบบ" เข้า policy 1 ครั้ง (งาน 4.3)  ❌ ไม่ต่อ DDS

ทายก่อนรัน: |action| สูงสุดประมาณเท่าไหร่ และ q_des ห่างท่า default แค่ไหน
ทดลองต่อ (onnx_basics.md): obs = 0 ทั้งหมด · เรียกซ้ำ obs เดิม · เปลี่ยน gravity x เป็น 0.1

รัน:  conda activate g1_sdk && python week4/scripts/skelatons/policy_once_skeleton.py
"""

import numpy as np

from obs_skeleton import GaitPhase, PolicyConfig, action_to_q_des, build_obs, fake_lowstate

# ชื่อข้อต่อตามลำดับ policy (= ลำดับ slot ใน joint_ids_map) ไว้พิมพ์ผล
NAMES = ["L_hip_p", "L_hip_r", "L_hip_y", "L_knee", "L_ank_p", "L_ank_r",
         "R_hip_p", "R_hip_r", "R_hip_y", "R_knee", "R_ank_p", "R_ank_r", "waist_y",
         "L_sh_p", "L_sh_r", "L_sh_y", "L_elbow", "L_wrist",
         "R_sh_p", "R_sh_r", "R_sh_y", "R_elbow", "R_wrist"]


def run_policy(session, obs: np.ndarray) -> np.ndarray:
    """obs (80,) → action (23,)"""
    # TODO [4.3] session.run(None, {"obs": obs[None, :]})[0][0]   ← ระวัง shape (1, 80) และ float32
    return np.zeros(23, dtype=np.float32)


def main():
    cfg = PolicyConfig()
    # TODO [4.3] สร้าง InferenceSession จาก cfg.onnx_path
    session = None

    msg = fake_lowstate(cfg)                         # ยืนท่า default นิ่ง ตั้งตรง
    gp = GaitPhase(cfg)
    obs = build_obs(msg, (0.0, 0.0, 0.0), np.zeros(23, np.float32), gp.step((0, 0, 0)), cfg)
    if session is None:
        print("policy_once: ยังไม่ได้เติม [4.3]")
        return

    action = run_policy(session, obs)
    q_des = action_to_q_des(action, cfg)
    # TODO [4.3] พิมพ์ตาราง: ชื่อ | action | q_des − default (องศา)
    # TODO [4.3] max |action|, ข้อต่อที่ action ใหญ่สุด
    # TODO [4.3] รันซ้ำ 10 step: ป้อน last_action = action รอบก่อน (obs อื่นเหมือนเดิม) action ลู่เข้าค่าคงที่ไหม
    # คำถาม: ถ้า action ใหญ่ทั้งที่ obs สมบูรณ์แบบ น่าจะผิดที่ obs หรือที่ policy (actions.md ท้ายไฟล์)


if __name__ == "__main__":
    main()
