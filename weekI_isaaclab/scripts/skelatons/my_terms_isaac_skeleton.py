"""my_terms_isaac.py: term ที่เราเขียนเองสำหรับ manager ของ Isaac Lab 3 (I5)

เทียบกับ weekR `my_terms.py` (mjlab) แทบบรรทัดต่อบรรทัด · ต่างกัน 3 อย่าง:
  1. ข้อมูลหุ่นใน Isaac Lab 3 เป็น warp array → ต้อง `.torch` ก่อนใช้กับ torch
       mjlab:  robot.data.root_link_pos_w[:, 2]        Isaac:  robot.data.root_pos_w.torch[:, 2]
  2. term แบบ class ต้องสืบทอด `ManagerTermBase` (mjlab ใช้ class ธรรมดาได้) · reset รับ env_ids
  3. G1 ใน USD ไม่มี site "left_foot" แบบ MJCF → ใช้ body `*_ankle_roll_link` แทน (body_ids)

กติกาเดิม: `env` ตัวแรก · ที่เหลือมาจาก params · obs (N, k) · reward (N,) · termination (N,) bool · ห้ามวน for ทีละ env

[skeleton] ทายก่อนเติม
  1. ใน Isaac Lab 3 `robot.data.root_pos_w` เป็น torch tensor ไหม (mjlab เป็น)
  2. G1 ใน USD มี site "left_foot" ไหม ถ้าไม่มีจะหาตำแหน่งเท้าจากอะไร
"""
from __future__ import annotations

import torch
from isaaclab.managers import ManagerTermBase, SceneEntityCfg

ROBOT = SceneEntityCfg("robot")


# ---------------------------------------------------------------- observation
def gait_phase(env, period: float, command_name: str) -> torch.Tensor:
    """(sin, cos) ของนาฬิกาก้าวเดิน (N, 2) · ยืน (|cmd| < 0.1) = (0, 0)

    เหมือน mjlab `mdp.phase` ทุกบรรทัด: เวลาใน episode = episode_length_buf × step_dt
    """
    # TODO(I5) global_phase = (episode_length_buf·step_dt mod period)/period → [sin 2πφ, cos 2πφ] · ยืน → 0
    raise NotImplementedError('TODO(I5) global_phase = (episode_length_buf·step_dt mod period)/period → [sin 2πφ, cos 2πφ] · ยืน → 0')


def base_height(env, asset_cfg: SceneEntityCfg = ROBOT) -> torch.Tensor:
    """ความสูง pelvis (N, 1) · หุ่นจริงวัดไม่ได้ → ใส่ critic อย่างเดียว"""
    # TODO(I5) root_pos_w.torch[:, 2:3]  (2:3 ให้คงมิติ (N, 1))
    raise NotImplementedError('TODO(I5) root_pos_w.torch[:, 2:3]  (2:3 ให้คงมิติ (N, 1))')


# ---------------------------------------------------------------- reward
def feet_too_close(env, min_dist: float, asset_cfg: SceneEntityCfg = ROBOT) -> torch.Tensor:
    """max(0, min_dist − ระยะเท้าซ้าย-ขวาแนวราบ) (N,) · body_ids มาจาก SceneEntityCfg(body_names=...)"""
    robot = env.scene[asset_cfg.name]
    # TODO(I5) feet = body_pos_w.torch[:, asset_cfg.body_ids, :2] → ระยะระหว่าง 2 เท้า → clamp(min_dist − d, min=0)
    raise NotImplementedError('TODO(I5) feet = body_pos_w.torch[:, asset_cfg.body_ids, :2] → ระยะระหว่าง 2 เท้า → clamp(min_dist − d, min=0)')


class vx_ema_error(ManagerTermBase):
    """term แบบ class: EMA ของ vx ต่อ env แล้วลงโทษ |EMA − cmd_vx|

    Isaac Lab สร้าง instance ด้วย (cfg, env) ครั้งเดียว · เรียก __call__(env, **params) ทุก step
    · เรียก reset(env_ids) ใน RewardManager.reset ตอน env นั้นจบ episode
    """

    def __init__(self, cfg, env):
        super().__init__(cfg, env)                     # เก็บ self.cfg, self._env
        self.alpha = cfg.params.get("alpha", 0.05)
        self.ema = torch.zeros(env.num_envs, device=env.device)

    def __call__(self, env, command_name: str, alpha: float = 0.05) -> torch.Tensor:
        # TODO(I5) vx = root_lin_vel_b.torch[:, 0] → ema = (1−α)ema + α·vx → |ema − cmd[:, 0]|
        raise NotImplementedError('TODO(I5) vx = root_lin_vel_b.torch[:, 0] → ema = (1−α)ema + α·vx → |ema − cmd[:, 0]|')

    def reset(self, env_ids=None):
        self.ema[slice(None) if env_ids is None else env_ids] = 0.0


# ---------------------------------------------------------------- termination
def pelvis_too_low(env, min_height: float, asset_cfg: SceneEntityCfg = ROBOT) -> torch.Tensor:
    # TODO(I5) root_pos_w.torch[:, 2] < min_height
    raise NotImplementedError('TODO(I5) root_pos_w.torch[:, 2] < min_height')
