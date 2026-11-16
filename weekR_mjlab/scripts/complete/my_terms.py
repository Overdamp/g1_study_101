"""my_terms.py: term ที่เราเขียนเอง (obs / reward / termination) ฉบับสมบูรณ์ ใช้ใน R5

กติกาของ term (ดู mjlab/managers/manager_base.py:17–61)
  - ฟังก์ชันรับ `env` ตัวแรกเสมอ ที่เหลือคือ keyword จาก `params` ใน cfg
  - คืน tensor ที่มิติแรก = num_envs ทุก env พร้อมกัน (ห้ามวน for ทีละ env)
      obs → (N, k)   reward → (N,)   termination → (N,) bool
  - ถ้า params มี SceneEntityCfg manager จะ resolve ชื่อ → index ให้ตอนสร้าง (asset_cfg.site_ids ฯลฯ)
  - term แบบ class: manager สร้าง instance ด้วย (cfg=..., env=...) ครั้งเดียว แล้วเรียก __call__ ทุก step
    ถ้ามี reset(env_ids) จะถูกเรียกตอน env นั้น reset
"""
from __future__ import annotations

import torch

from mjlab.managers.scene_entity_config import SceneEntityCfg

ROBOT = SceneEntityCfg("robot")


# ---------------------------------------------------------------- observation
def base_height(env, asset_cfg: SceneEntityCfg = ROBOT) -> torch.Tensor:
    """ความสูง pelvis จากพื้น (N, 1) · หุ่นจริงวัดตรงๆ ไม่ได้ → ใส่ได้แค่ใน critic ถ้าจะ deploy"""
    robot = env.scene[asset_cfg.name]
    return robot.data.root_link_pos_w[:, 2:3]          # 2:3 (ไม่ใช่ 2) เพื่อคงมิติเป็น (N, 1)


# ---------------------------------------------------------------- reward
def feet_too_close(env, min_dist: float, asset_cfg: SceneEntityCfg = ROBOT) -> torch.Tensor:
    """ค่าปรับเมื่อเท้า 2 ข้างใกล้กันเกิน min_dist (แนวราบ) → (N,) ≥ 0 · ใช้กับ weight ติดลบ"""
    robot = env.scene[asset_cfg.name]
    feet = robot.data.site_pos_w[:, asset_cfg.site_ids, :2]   # (N, 2 เท้า, xy)
    dist = torch.norm(feet[:, 0] - feet[:, 1], dim=-1)         # (N,)
    return torch.clamp(min_dist - dist, min=0.0)


class vx_ema_error:
    """term แบบ class: เก็บค่าเฉลี่ยเคลื่อนที่ (EMA) ของ vx ต่อ env แล้วลงโทษ |EMA − คำสั่ง|

    ต่างจาก track_linear_velocity ที่ดูทีละ step → term นี้ไม่สนการแกว่งในก้าวเดียว สนแค่ "เฉลี่ยแล้วถึงไหม"
    """

    def __init__(self, cfg, env):
        self.alpha = cfg.params.get("alpha", 0.05)           # ~1/alpha step ≈ 20 step = 0.4 s
        self.ema = torch.zeros(env.num_envs, device=env.device)

    def __call__(self, env, command_name: str, alpha: float = 0.05) -> torch.Tensor:
        del alpha  # ใช้ค่าที่เก็บไว้ตอน __init__
        vx = env.scene["robot"].data.root_link_lin_vel_b[:, 0]
        self.ema = (1 - self.alpha) * self.ema + self.alpha * vx
        cmd = env.command_manager.get_command(command_name)[:, 0]
        return torch.abs(self.ema - cmd)

    def reset(self, env_ids=None):
        if env_ids is None:
            env_ids = slice(None)
        self.ema[env_ids] = 0.0


# ---------------------------------------------------------------- termination
def pelvis_too_low(env, min_height: float, asset_cfg: SceneEntityCfg = ROBOT) -> torch.Tensor:
    """จบ episode ถ้า pelvis ต่ำกว่า min_height → (N,) bool"""
    robot = env.scene[asset_cfg.name]
    return robot.data.root_link_pos_w[:, 2] < min_height
