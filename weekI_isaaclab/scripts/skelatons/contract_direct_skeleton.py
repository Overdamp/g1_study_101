"""contract_direct.py: I6: contract task เดียวกับ I5 แต่เขียนแบบ Direct (DirectRLEnv) ทุกบรรทัดเอง

manager-based (I5)                        Direct (ไฟล์นี้)
----------------------------------------  ------------------------------------------------------
ObsTerm ×7 → ObservationManager           _get_observations(): torch.cat 7 ก้อนเอง + noise เอง
JointPositionActionCfg → ActionManager    _pre_physics_step() + _apply_action(): q_des = default + scale·a
UniformVelocityCommandCfg → CommandMgr    _resample_commands(): สุ่มเอง + ตัวจับเวลา 10 s
RewTerm ×10 → RewardManager               _get_rewards(): คิด 10 term inline, ×weight×dt, เก็บ log เอง
DoneTerm ×3 → TerminationManager          _get_dones(): (died, time_out)
EventTerm reset → EventManager            _reset_idx(): เขียน root/joint state ลง sim เอง
class term vx_ema_error (ManagerTermBase) self._ema + ล้างใน _reset_idx

ลำดับใน DirectRLEnv.step (direct_rl_env.py):
  _pre_physics_step(a) → (_apply_action → write_data_to_sim → sim.step → scene.update) × decimation
  → episode_length_buf++ → _get_dones → _get_rewards → _reset_idx(จบแล้ว) → [interval events] → _get_observations
ต่างจาก manager ตรงที่ไม่มี command_manager.compute ให้ → เราอัปเดตคำสั่งเองใน _get_observations (ก่อนสร้าง obs)

[skeleton] ทายก่อนเติม
  1. DirectRLEnv เรียก _apply_action กี่ครั้งต่อ env.step · _pre_physics_step กี่ครั้ง
  2. is_alive ใช้ reset_terminated ได้เพราะ _get_dones ถูกเรียกก่อนหรือหลัง _get_rewards
  3. หลัง _reset_idx ค่า projected_gravity_b ของ env ที่เพิ่ง reset สดหรือเก่า
"""
from __future__ import annotations

import importlib
import math

import gymnasium as gym
import isaaclab.sim as sim_utils
import torch
from isaaclab.assets import Articulation, ArticulationCfg
from isaaclab.envs import DirectRLEnv, DirectRLEnvCfg
from isaaclab.scene import InteractiveSceneCfg
from isaaclab.sim import SimulationCfg
from isaaclab.terrains import TerrainImporterCfg
from isaaclab.utils import configclass

import contract_common_skeleton as C
import ilib_skeleton as ilib

TASK_ID = "WeekI-G1-Contract-Direct"

# ของจาก repo Unitree (อ่านอย่างเดียว): หุ่น 23-DoF + preset ฟิสิกส์ (physx / newton)
_g1_23 = importlib.import_module("unitree_rl_lab.tasks.locomotion.robots.g1.23dof.velocity_env_cfg")
_g1_29 = importlib.import_module("unitree_rl_lab.tasks.locomotion.robots.g1.29dof.velocity_env_cfg")

_GROUND = sim_utils.RigidBodyMaterialCfg(friction_combine_mode="multiply", restitution_combine_mode="multiply",
                                         static_friction=1.0, dynamic_friction=1.0)


@configclass
class G1ContractDirectEnvCfg(DirectRLEnvCfg):
    # ---- ที่ DirectRLEnv บังคับ
    decimation: int = 4
    episode_length_s: float = C.EPISODE_S
    action_space: int = 23
    observation_space: int = sum(C.POLICY_DIMS)                          # 80
    state_space: int = sum(C.POLICY_DIMS) + sum(C.CRITIC_EXTRA_DIMS)     # 84 (critic)
    sim: SimulationCfg = SimulationCfg(dt=0.005, render_interval=4, physics=_g1_29.PhysicsCfg(),
                                       physics_material=_GROUND)
    scene: InteractiveSceneCfg = InteractiveSceneCfg(num_envs=16, env_spacing=2.5, replicate_physics=True)
    # ---- ของเรา (Direct ไม่มี container บังคับ ใส่ field อะไรก็ได้)
    robot: ArticulationCfg = _g1_23.G1_23DOF_CFG.replace(prim_path="/World/envs/env_.*/Robot")
    terrain: TerrainImporterCfg = TerrainImporterCfg(prim_path="/World/ground", terrain_type="plane",
                                                     collision_group=-1, physics_material=_GROUND, debug_vis=False)
    corruption: bool = True
    fixed_cmd: tuple | None = None


class G1ContractDirectEnv(DirectRLEnv):
    cfg: G1ContractDirectEnvCfg

    # ================================================================ สร้าง
    def __init__(self, cfg: G1ContractDirectEnvCfg, render_mode=None, **kwargs):
        super().__init__(cfg, render_mode, **kwargs)      # เรียก _setup_scene, สร้าง sim, gym spaces
        N, dev = self.num_envs, self.device
        # index ตามชื่อ (ไม่พึ่งลำดับ backend) · preserve_order = เรียงตามลิสต์ที่ให้
        self._jids, _ = self._robot.find_joints(ilib.POLICY_JOINTS, preserve_order=True)
        self._feet, _ = self._robot.find_bodies(C.FEET, preserve_order=True)
        self._jids = torch.tensor(self._jids, device=dev)
        self._scale = torch.tensor([C.SCALE[n] for n in ilib.POLICY_JOINTS], device=dev)
        self._default = self._robot.data.default_joint_pos.torch[:, self._jids].clone()
        self._actions = torch.zeros(N, 23, device=dev)
        self._prev_actions = torch.zeros(N, 23, device=dev)
        self._q_des = self._default.clone()
        self._cmd = torch.zeros(N, 3, device=dev)
        self._cmd_time_left = torch.zeros(N, device=dev)
        self._ema = torch.zeros(N, device=dev)
        self.term_names = list(C.REWARD_W)
        self._w = torch.tensor([C.REWARD_W[n] for n in self.term_names], device=dev)
        self.step_reward = torch.zeros(N, len(self.term_names), device=dev)   # func × weight ล่าสุด (เทียบกับ manager)
        self._episode_sums = torch.zeros(N, len(self.term_names), device=dev)

    def _setup_scene(self):
        """สร้างของในฉาก (DirectRLEnv เรียกตอนสร้าง sim) · manager ทำส่วนนี้จาก InteractiveSceneCfg ให้"""
        # TODO(I6) Articulation(cfg.robot) → scene.articulations["robot"] · terrain → clone_environments · แสง
        raise NotImplementedError('TODO(I6) Articulation(cfg.robot) → scene.articulations["robot"] · terrain → clone_environments · แสง')

    # ================================================================ action
    def _pre_physics_step(self, actions: torch.Tensor):
        """1 ครั้งต่อ env.step: เก็บ action, คิด q_des (= JointPositionAction.process_actions)"""
        # TODO(I6) prev ← actions เดิม · actions ← ใหม่ · q_des = default + scale·a
        raise NotImplementedError('TODO(I6) prev ← actions เดิม · actions ← ใหม่ · q_des = default + scale·a')

    def _apply_action(self):
        """decimation ครั้งต่อ env.step (ก่อน sim.step ทุกครั้ง) · ImplicitActuator → solver ทำ PD เอง"""
        self._robot.set_joint_position_target_index(target=self._q_des, joint_ids=self._jids)

    # ================================================================ คำสั่ง
    def _resample_commands(self, env_ids: torch.Tensor):
        n = len(env_ids)
        if self.cfg.fixed_cmd is not None:
            self._cmd[env_ids] = torch.tensor(self.cfg.fixed_cmd, device=self.device, dtype=torch.float32)
        else:
            for k, key in enumerate(("lin_vel_x", "lin_vel_y", "ang_vel_z")):
                lo, hi = C.CMD_RANGES[key]
                self._cmd[env_ids, k] = torch.empty(n, device=self.device).uniform_(lo, hi)
        self._cmd_time_left[env_ids] = C.RESAMPLE_S

    def _update_commands(self):
        self._cmd_time_left -= self.step_dt
        ids = (self._cmd_time_left <= 0.0).nonzero(as_tuple=False).squeeze(-1)
        if len(ids) > 0:
            self._resample_commands(ids)

    # ================================================================ obs
    def _get_observations(self) -> dict:
        self._update_commands()                     # manager: command_manager.compute() ก่อน obs
        d = self._robot.data
        t = self.episode_length_buf * self.step_dt
        phi = (t % C.PERIOD) / C.PERIOD
        phase = torch.stack([torch.sin(2 * math.pi * phi), torch.cos(2 * math.pi * phi)], dim=1)
        phase = torch.where((torch.linalg.norm(self._cmd, dim=1) < C.STAND_CMD).unsqueeze(1),
                            torch.zeros_like(phase), phase)
        # TODO(I6) dict ของ 7 term ตามลำดับ deploy: gyro, gravity, cmd, phase, q − default, qd, last action
        raise NotImplementedError('TODO(I6) dict ของ 7 term ตามลำดับ deploy: gyro, gravity, cmd, phase, q − default, qd, last action')
        clean = torch.cat([terms[k] for k in C.POLICY_TERMS], dim=-1)
        if self.cfg.corruption:
            terms = {k: v + (torch.rand_like(v) * 2 - 1) * C.NOISE[k] if k in C.NOISE else v for k, v in terms.items()}
        policy = torch.cat([terms[k] for k in C.POLICY_TERMS], dim=-1)
        critic = torch.cat([clean, d.root_lin_vel_b.torch, d.root_pos_w.torch[:, 2:3]], dim=-1)
        return {"policy": policy, "critic": critic}

    # ================================================================ reward
    def _get_rewards(self) -> torch.Tensor:
        d = self._robot.data
        v, w, g = d.root_lin_vel_b.torch, d.root_ang_vel_b.torch, d.projected_gravity_b.torch
        q = d.joint_pos.torch[:, self._jids]
        lim = d.soft_joint_pos_limits.torch[:, self._jids]
        feet = d.body_pos_w.torch[:, self._feet, :2]
        self._ema = (1 - C.EMA_ALPHA) * self._ema + C.EMA_ALPHA * v[:, 0]
        # TODO(I6) 10 term (ค่า func ยังไม่คูณ weight) ตามนิยามใน contract_common.REWARD_W
        raise NotImplementedError('TODO(I6) 10 term (ค่า func ยังไม่คูณ weight) ตามนิยามใน contract_common.REWARD_W')
        self.step_reward = torch.stack([raw[n] for n in self.term_names], dim=1) * self._w   # (N, 10)
        self._episode_sums += self.step_reward * self.step_dt
        return self.step_reward.sum(1) * self.step_dt              # = RewardManager.compute(dt)

    # ================================================================ done
    def _get_dones(self) -> tuple[torch.Tensor, torch.Tensor]:
        d = self._robot.data
        # TODO(I6) time_out = episode_length_buf ≥ max_episode_length · died = เอียง > TILT_LIMIT หรือ pelvis < MIN_PELVIS
        raise NotImplementedError('TODO(I6) time_out = episode_length_buf ≥ max_episode_length · died = เอียง > TILT_LIMIT หรือ pelvis < MIN_PELVIS')

    # ================================================================ reset
    def _reset_idx(self, env_ids):
        if env_ids is None or len(env_ids) == self.num_envs:
            env_ids = torch.arange(self.num_envs, device=self.device)
        # log ก่อนล้าง (manager: reward_manager.reset → extras["Episode_Reward/..."])
        log = {f"Episode_Reward/{n}": self._episode_sums[env_ids, k].mean() / self.max_episode_length_s
               for k, n in enumerate(self.term_names)}
        log["Episode_Termination/time_out"] = self.reset_time_outs[env_ids].sum().item()
        log["Episode_Termination/died"] = self.reset_terminated[env_ids].sum().item()
        self.extras["log"] = log
        self._episode_sums[env_ids] = 0.0

        self._robot.reset(env_ids)
        super()._reset_idx(env_ids)                  # scene.reset, events(reset), episode_length_buf = 0
        # TODO(I6) เขียนท่า default ลง sim: root pose (+ env origin), root velocity 0, joint pos default, joint vel 0
        raise NotImplementedError('TODO(I6) เขียนท่า default ลง sim: root pose (+ env origin), root velocity 0, joint pos default, joint vel 0')
        self._actions[env_ids] = 0.0
        self._prev_actions[env_ids] = 0.0
        self._q_des[env_ids] = self._default[env_ids]
        self._ema[env_ids] = 0.0
        self._resample_commands(env_ids)


if TASK_ID not in gym.registry:
    gym.register(id=TASK_ID, entry_point=f"{__name__}:G1ContractDirectEnv", disable_env_checker=True)


def make_cfg(num_envs: int = 16, preset: str = "newton", fixed_cmd=None, corruption: bool = True, seed: int = 0):
    from isaaclab_tasks.utils.hydra import resolve_presets

    cfg = G1ContractDirectEnvCfg()
    cfg = resolve_presets(cfg, {preset})          # sim.physics: PresetCfg → NewtonCfg / PhysxCfg
    cfg.scene.num_envs = num_envs
    cfg.fixed_cmd = fixed_cmd
    cfg.corruption = corruption
    cfg.seed = seed
    return cfg
