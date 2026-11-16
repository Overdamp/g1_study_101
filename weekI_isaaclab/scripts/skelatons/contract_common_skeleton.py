"""contract_common.py: ค่าที่ I5 (manager-based) และ I6 (Direct) ใช้ร่วมกัน

"contract task" = task G1 23-DoF ใน Isaac Lab ที่ obs ของ actor ตรงกับสัญญา deploy ของ mjlab (deploy.yaml ของ v0)
→ policy P3b ที่เทรนใน mjlab ใช้ได้ทันทีจาก observation ของ env เอง (ไม่ต้องสร้าง obs ข้างนอกแบบ play_deploy_onnx)
I5 สร้าง task นี้ด้วย manager (แก้ config) · I6 เขียน task เดียวกันแบบ Direct (เขียนเองทุกบรรทัด)
แล้ว I6_compare ตรวจว่า obs / reward ของสองแบบเท่ากันทีละ term
"""
from __future__ import annotations

import ilib_skeleton as ilib

# ---------------------------------------------------------------- obs ของ actor (ลำดับ = deploy.yaml)
POLICY_TERMS = ["base_ang_vel", "projected_gravity", "velocity_commands", "gait_phase",
                "joint_pos_rel", "joint_vel_rel", "last_action"]
POLICY_DIMS = [3, 3, 3, 2, 23, 23, 23]          # รวม 80
CRITIC_EXTRA = ["base_lin_vel", "base_height"]  # critic = actor + 3 + 1 = 84
CRITIC_EXTRA_DIMS = [3, 1]
PERIOD = 0.6                                     # gait_phase.params.period ใน deploy.yaml
STAND_CMD = 0.1                                  # |cmd| < 0.1 → phase = (0, 0) (เหมือน mjlab mdp.phase)
# noise ตอนเทรน (เหมือน mjlab actor_terms) · ปิดได้ด้วย corruption=False
NOISE = {"base_ang_vel": 0.2, "projected_gravity": 0.05, "joint_pos_rel": 0.01, "joint_vel_rel": 1.5}

# ---------------------------------------------------------------- reward (ชื่อ = ชื่อฟังก์ชันใน isaaclab.envs.mdp ถ้ามี)
REWARD_W = {
    "track_lin_vel_xy_exp": 1.0,     # exp(−|cmd_xy − v_xy|² / std²)
    "track_ang_vel_z_exp": 0.5,      # exp(−(cmd_wz − wz)² / std²)
    "lin_vel_z_l2": -2.0,            # vz²
    "ang_vel_xy_l2": -0.05,          # wx² + wy²
    "flat_orientation_l2": -5.0,     # gx² + gy²
    "action_rate_l2": -0.05,         # |a − a_prev|²
    "joint_pos_limits": -5.0,        # เกิน soft limit เท่าไร (rad)
    "is_alive": 0.15,                # 1 ถ้ายังไม่ล้ม
    "feet_too_close": -5.0,          # (ของเรา) max(0, min_dist − ระยะเท้า xy)
    "vx_ema_error": -1.0,            # (ของเรา, class) |EMA(vx) − cmd_vx|
}
STD = 0.5
MIN_FEET = 0.15
EMA_ALPHA = 0.05
FEET = ["left_ankle_roll_link", "right_ankle_roll_link"]

# ---------------------------------------------------------------- termination
TILT_LIMIT = 0.8                                 # rad (bad_orientation ของ task Unitree)
MIN_PELVIS = 0.45                                # m  (ของเรา pelvis_too_low)

# ---------------------------------------------------------------- คำสั่ง (ranges จาก deploy.yaml commands)
CMD_RANGES = {"lin_vel_x": (-0.5, 1.0), "lin_vel_y": (-0.5, 0.5), "ang_vel_z": (-1.0, 1.0)}
RESAMPLE_S = 10.0

# ---------------------------------------------------------------- action (สูตร mjlab)
SCALE = {n: float(s) for n, s in zip(ilib.POLICY_JOINTS, ilib.SCALE)}
EPISODE_S = 20.0
