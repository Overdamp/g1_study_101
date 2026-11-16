"""my_terms_skeleton.py: term ที่เราเขียนเอง (obs / reward / termination): โครงให้เติม · เฉลย ../complete/my_terms.py

กติกาของ term (ดู mjlab/managers/manager_base.py:17–61)
  - ฟังก์ชันรับ `env` ตัวแรกเสมอ ที่เหลือคือ keyword จาก `params` ใน cfg
  - คืน tensor ที่มิติแรก = num_envs ทุก env พร้อมกัน (ห้ามวน for ทีละ env)
      obs → (N, k)   reward → (N,)   termination → (N,) bool
  - ถ้า params มี SceneEntityCfg manager จะ resolve ชื่อ → index ให้ตอนสร้าง (asset_cfg.site_ids ฯลฯ)
  - term แบบ class: manager สร้าง instance ด้วย (cfg=..., env=...) ครั้งเดียว แล้วเรียก __call__ ทุก step
    ถ้ามี reset(env_ids) จะถูกเรียกตอน env นั้น reset

ค่าที่คืนตอนนี้เป็นศูนย์ขนาดถูกต้อง เพื่อให้ env สร้างได้ก่อนเติม
"""
from __future__ import annotations

import torch

from mjlab.managers.scene_entity_config import SceneEntityCfg

ROBOT = SceneEntityCfg("robot")


# ---------------------------------------------------------------- observation
def base_height(env, asset_cfg: SceneEntityCfg = ROBOT) -> torch.Tensor:
    """ความสูง pelvis จากพื้น (N, 1)"""
    # TODO: robot = env.scene[asset_cfg.name] · ความสูง = robot.data.root_link_pos_w[:, 2]
    #       ระวังมิติ: ต้องคืน (N, 1) ไม่ใช่ (N,)  → ใช้ slice 2:3
    return torch.zeros(env.num_envs, 1, device=env.device)


# ---------------------------------------------------------------- reward
def feet_too_close(env, min_dist: float, asset_cfg: SceneEntityCfg = ROBOT) -> torch.Tensor:
    """ค่าปรับเมื่อเท้า 2 ข้างใกล้กันเกิน min_dist (แนวราบ) → (N,) ≥ 0"""
    # TODO: feet = robot.data.site_pos_w[:, asset_cfg.site_ids, :2]   → (N, 2, 2)
    #       dist = ระยะ xy ระหว่างเท้า 0 กับเท้า 1 · คืน clamp(min_dist − dist, min=0)
    return torch.zeros(env.num_envs, device=env.device)


class vx_ema_error:
    """term แบบ class: เก็บ EMA ของ vx ต่อ env แล้วลงโทษ |EMA − คำสั่ง vx|"""

    def __init__(self, cfg, env):
        # TODO: self.alpha = cfg.params.get("alpha", 0.05) · self.ema = zeros(num_envs) บน env.device
        self.ema = torch.zeros(env.num_envs, device=env.device)

    def __call__(self, env, command_name: str, alpha: float = 0.05) -> torch.Tensor:
        # TODO: vx = env.scene["robot"].data.root_link_lin_vel_b[:, 0]
        #       self.ema = (1 − α)·ema + α·vx · cmd = env.command_manager.get_command(command_name)[:, 0]
        #       คืน |ema − cmd|
        return torch.zeros(env.num_envs, device=env.device)

    def reset(self, env_ids=None):
        # TODO: ตั้ง self.ema[env_ids] = 0 (env_ids None = ทุก env → slice(None))
        pass


# ---------------------------------------------------------------- termination
def pelvis_too_low(env, min_height: float, asset_cfg: SceneEntityCfg = ROBOT) -> torch.Tensor:
    """จบ episode ถ้า pelvis ต่ำกว่า min_height → (N,) bool"""
    # TODO: root_link_pos_w[:, 2] < min_height
    return torch.zeros(env.num_envs, dtype=torch.bool, device=env.device)
