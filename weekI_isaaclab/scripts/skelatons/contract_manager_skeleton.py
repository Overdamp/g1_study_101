"""contract_manager.py: I5: task G1 23-DoF แบบ manager-based ที่ obs ตรงสัญญา deploy ของ mjlab

วิธีสร้าง: เริ่มจาก config ของ task Unitree (`Unitree-G1-23dof-Velocity-Flat`) ที่มีหุ่น/ฉาก/ฟิสิกส์ครบ
แล้ว "แทน" ส่วน MDP ทั้งหมดด้วยของเรา (obs, actions, commands, rewards, terminations, events, curriculum)
→ ได้ task ใหม่โดยไม่แก้ repo หลักสักบรรทัด (แบบเดียวกับ weekR R5 ที่แก้ cfg ของ mjlab)

    from contract_manager import make_cfg
    cfg = make_cfg(num_envs=16, preset="newton", fixed_cmd=(0.5, 0, 0), corruption=False)
    env = gym.make(TASK_ID, cfg=cfg)

ใช้ใน: i5_manager_terms.py, i6_compare.py, i6_train.py

[skeleton] ทายก่อนเติม
  1. obs ของ critic สืบทอดจาก PolicyCfg แล้วเพิ่ม 2 term: term ของ actor อยู่ช่วง index ไหนของ critic
  2. ถ้าลืม preserve_order=True ใน SceneEntityCfg ของ joint จะพังบน backend ไหน
"""
from __future__ import annotations

import gymnasium as gym
import isaaclab.envs.mdp as mdp
from isaaclab.managers import EventTermCfg as EventTerm
from isaaclab.managers import ObservationGroupCfg as ObsGroup
from isaaclab.managers import ObservationTermCfg as ObsTerm
from isaaclab.managers import RewardTermCfg as RewTerm
from isaaclab.managers import SceneEntityCfg
from isaaclab.managers import TerminationTermCfg as DoneTerm
from isaaclab.utils import configclass
from isaaclab.utils.noise import UniformNoiseCfg as Unoise

import contract_common_skeleton as C
import ilib_skeleton as ilib
import my_terms_isaac_skeleton as my

TASK_ID = "WeekI-G1-Contract-Manager"
if TASK_ID not in gym.registry:
    # entry point = ManagerBasedRLEnv ธรรมดา · config ส่งตอน gym.make(cfg=...) จึงไม่ต้องมี env_cfg_entry_point
    gym.register(id=TASK_ID, entry_point="isaaclab.envs:ManagerBasedRLEnv", disable_env_checker=True)

# joint ตามลำดับ policy เสมอ (ไม่พึ่งลำดับของ backend: PhysX = BFS)
JOINTS = SceneEntityCfg("robot", joint_names=ilib.POLICY_JOINTS, preserve_order=True)


# ================================================================ observations
@configclass
class PolicyCfg(ObsGroup):
    """ลำดับ field = ลำดับใน vector (Isaac ต่อ term ตามลำดับที่ประกาศ) = ลำดับ deploy.yaml"""
    # TODO(I5) ประกาศ 7 term ตามลำดับ deploy.yaml (base_ang_vel … last_action) ใช้ my.gait_phase และ JOINTS
    raise NotImplementedError('TODO(I5) ประกาศ 7 term ตามลำดับ deploy.yaml (base_ang_vel … last_action) ใช้ my.gait_phase และ JOINTS')

    def __post_init__(self):
        self.enable_corruption = True          # ใส่ noise (make_cfg(corruption=False) ปิด)
        self.concatenate_terms = True
        self.history_length = 0                # 0 = ไม่มี history (mjlab v0 ใช้ 1 เฟรม)


@configclass
class CriticCfg(PolicyCfg):
    """สืบทอด → term ของ actor มาก่อนตามลำดับ แล้วต่อด้วย privileged 2 ตัว"""
    base_lin_vel = ObsTerm(func=mdp.base_lin_vel)
    base_height = ObsTerm(func=my.base_height)

    def __post_init__(self):
        super().__post_init__()
        self.enable_corruption = False         # critic เห็นค่าจริง (asymmetric actor-critic แบบ mjlab)


@configclass
class ObservationsCfg:
    policy: PolicyCfg = PolicyCfg()
    critic: CriticCfg = CriticCfg()


# ================================================================ actions / commands
@configclass
class ActionsCfg:
    JointPositionAction = mdp.JointPositionActionCfg(
        asset_name="robot", joint_names=ilib.POLICY_JOINTS, preserve_order=True,
        scale=C.SCALE, use_default_offset=True,      # q_des = default + scale·a (ต่อ joint, สูตร mjlab)
    )


@configclass
class CommandsCfg:
    base_velocity = mdp.UniformVelocityCommandCfg(
        asset_name="robot",
        resampling_time_range=(C.RESAMPLE_S, C.RESAMPLE_S),
        rel_standing_envs=0.0, rel_heading_envs=0.0, heading_command=False, debug_vis=False,
        ranges=mdp.UniformVelocityCommandCfg.Ranges(**C.CMD_RANGES, heading=None),
    )


# ================================================================ rewards
FEET = SceneEntityCfg("robot", body_names=C.FEET, preserve_order=True)


@configclass
class RewardsCfg:
    track_lin_vel_xy_exp = RewTerm(func=mdp.track_lin_vel_xy_exp, weight=C.REWARD_W["track_lin_vel_xy_exp"],
                                   params={"std": C.STD, "command_name": "base_velocity"})
    track_ang_vel_z_exp = RewTerm(func=mdp.track_ang_vel_z_exp, weight=C.REWARD_W["track_ang_vel_z_exp"],
                                  params={"std": C.STD, "command_name": "base_velocity"})
    lin_vel_z_l2 = RewTerm(func=mdp.lin_vel_z_l2, weight=C.REWARD_W["lin_vel_z_l2"])
    ang_vel_xy_l2 = RewTerm(func=mdp.ang_vel_xy_l2, weight=C.REWARD_W["ang_vel_xy_l2"])
    flat_orientation_l2 = RewTerm(func=mdp.flat_orientation_l2, weight=C.REWARD_W["flat_orientation_l2"])
    action_rate_l2 = RewTerm(func=mdp.action_rate_l2, weight=C.REWARD_W["action_rate_l2"])
    joint_pos_limits = RewTerm(func=mdp.joint_pos_limits, weight=C.REWARD_W["joint_pos_limits"],
                               params={"asset_cfg": JOINTS})
    is_alive = RewTerm(func=mdp.is_alive, weight=C.REWARD_W["is_alive"])
    # TODO(I5) ลงทะเบียน term ของเรา 2 ตัว: feet_too_close (params min_dist, asset_cfg=FEET) และ vx_ema_error (class)
    raise NotImplementedError('TODO(I5) ลงทะเบียน term ของเรา 2 ตัว: feet_too_close (params min_dist, asset_cfg=FEET) และ vx_ema_error (class)')


# ================================================================ terminations / events
@configclass
class TerminationsCfg:
    time_out = DoneTerm(func=mdp.time_out, time_out=True)          # time_out=True → truncated (PPO bootstrap)
    bad_orientation = DoneTerm(func=mdp.bad_orientation, params={"limit_angle": C.TILT_LIMIT})
    pelvis_too_low = DoneTerm(func=my.pelvis_too_low, params={"min_height": C.MIN_PELVIS})


@configclass
class EventsCfg:
    # reset: ท่า default ที่ origin ของ env (range 0 = ไม่สุ่ม เพื่อให้เทียบกับ Direct ได้ตรง)
    reset_base = EventTerm(func=mdp.reset_root_state_uniform, mode="reset",
                           params={"pose_range": {}, "velocity_range": {}})
    reset_joints = EventTerm(func=mdp.reset_joints_by_offset, mode="reset",
                             params={"position_range": (0.0, 0.0), "velocity_range": (0.0, 0.0)})


@configclass
class EmptyCfg:
    pass


def joint_friction_event(lo: float = 0.0, hi: float = 0.3) -> EventTerm:
    """DR ของ frictionloss ต่อข้อ (Newton เขียนลง Model.joint_friction = N·m) · ครอบ 0.2 ของ unitree_mujoco"""
    # TODO(I5) EventTerm(func=mdp.randomize_joint_parameters, mode="startup", params friction_distribution_params, operation "abs")
    raise NotImplementedError('TODO(I5) EventTerm(func=mdp.randomize_joint_parameters, mode="startup", params friction_distribution_params, operation "abs")')


# ================================================================ ประกอบ
def make_cfg(num_envs: int = 16, preset: str = "newton", fixed_cmd=None, corruption: bool = True,
             friction_dr: tuple[float, float] | None = None, push: bool = False, seed: int = 0):
    """config ของ contract task (manager) · fixed_cmd=(vx, vy, wz) ล็อกคำสั่ง (ใช้ตอนวัด/เทียบ)"""
    import unitree_rl_lab.tasks  # noqa: F401
    from isaaclab_tasks.utils.hydra import resolve_presets
    from isaaclab_tasks.utils.parse_cfg import load_cfg_from_registry

    cfg = load_cfg_from_registry(ilib.TASK_FLAT, "env_cfg_entry_point")   # หุ่น + ฉาก + sim ของ Unitree
    cfg = resolve_presets(cfg, {preset})
    cfg.scene.num_envs = num_envs
    cfg.scene.contact_forces = None          # ไม่มี reward ใช้ → ปิดให้เร็ว (และเทียบกับ Direct ได้ยุติธรรม)
    cfg.seed = seed
    cfg.episode_length_s = C.EPISODE_S

    # TODO(I5) แทนส่วน MDP ทั้ง 7 ด้วยของเรา: observations, actions, commands, rewards, terminations, events, curriculum
    raise NotImplementedError('TODO(I5) แทนส่วน MDP ทั้ง 7 ด้วยของเรา: observations, actions, commands, rewards, terminations, events, curriculum')

    if not corruption:
        cfg.observations.policy.enable_corruption = False
    if fixed_cmd is not None:
        vx, vy, wz = fixed_cmd
        cfg.commands.base_velocity.ranges = mdp.UniformVelocityCommandCfg.Ranges(
            lin_vel_x=(vx, vx), lin_vel_y=(vy, vy), ang_vel_z=(wz, wz), heading=None)
    if friction_dr is not None:
        cfg.events.joint_friction = joint_friction_event(*friction_dr)
    if push:
        cfg.events.push_robot = EventTerm(func=mdp.push_by_setting_velocity, mode="interval",
                                          interval_range_s=(5.0, 5.0),
                                          params={"velocity_range": {"x": (-0.5, 0.5), "y": (-0.5, 0.5)}})
    return cfg
