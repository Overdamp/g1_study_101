"""I2: สร้าง env ของ Isaac Lab บน Newton แล้วเปิดดูข้างใน

    python i2_env_newton.py                    # Newton (MJWarp), 4 env
    python i2_env_newton.py --physx            # PhysX เทียบ (ลำดับ joint / ความเร็ว)
    python i2_env_newton.py --fast-path        # Newton + use_newton_actuators=True (decimation อยู่ใน CUDA graph)
    python i2_env_newton.py --num-envs 512 --steps 100     # วัดความเร็วจริงจัง

พิมพ์:
  1. physics manager / solver ที่ถูกเลือก (+ ค่าใน mjw_model.opt ที่ MuJoCo Warp เห็นจริง)
  2. Newton Model: world, body, dof, shape และชนิด geom ที่ได้จาก USD (เทียบกับ MJCF ของ mjlab)
  3. ลำดับ joint ของ Isaac vs ลำดับ policy → permutation ที่ deploy ต้องใช้
  4. kp/kd/armature/effort ที่อยู่ใน Newton Model จริง vs ilib (สูตร mjlab)
  5. 1 env.step() เรียกฟิสิกส์กี่ครั้ง (decimation อยู่ใน Python หรือใน graph)
  6. เวลา env.step() ต่อครั้ง
  7. --save-mjcf: เขียน MJCF ที่ Newton สร้างให้ MuJoCo Warp ลง logs/isaac_generated.xml

[skeleton] ทายก่อนรัน
  1. ลำดับ joint ของ Isaac (PhysX) กับ (Newton) เหมือนลำดับ policy ไหม
  2. 1 env.step() เรียก sim.step กี่ครั้ง: ปกติ / --fast-path
  3. Newton กับ PhysX ที่ 512 env อันไหนเร็วกว่า กี่ %
  4. geom ที่ใช้ชนใน Isaac (จาก USD) เหมือน mjlab (capsule) ไหม
"""
import argparse
import sys
from pathlib import Path

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser()
parser.add_argument("--physx", action="store_true", help="ใช้ PhysX แทน Newton")
parser.add_argument("--fast-path", action="store_true", help="sim.use_newton_actuators=True")
parser.add_argument("--num-envs", type=int, default=4)
parser.add_argument("--steps", type=int, default=50)
parser.add_argument("--save-mjcf", action="store_true")
AppLauncher.add_app_launcher_args(parser)
parser.set_defaults(headless=True, visualizer="none")
args = parser.parse_args()
app = AppLauncher(args).app          # ← ต้องเปิด app ก่อน import อะไรของ isaaclab ที่แตะ USD/ฟิสิกส์

# ---------------------------------------------------------------- หลังจากนี้ import ได้
import time  # noqa: E402

import gymnasium as gym  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
import ilib_skeleton as ilib  # noqa: E402
import unitree_rl_lab.tasks  # noqa: E402,F401  ← ลงทะเบียน Unitree-G1-23dof-*
from isaaclab_tasks.utils.hydra import resolve_presets  # noqa: E402
from isaaclab_tasks.utils.parse_cfg import load_cfg_from_registry  # noqa: E402


def _scalar(x):
    """ค่าใน mjw_model.opt บางตัวเป็น warp array (แยกต่อ world) → เอาค่าแรก"""
    return float(x.numpy().ravel()[0]) if hasattr(x, "numpy") else x


def _pm_name():
    """ชื่อคลาส physics manager ที่ทำงานจริง (cfg เก็บเป็น string "{DIR}.mjwarp_manager:..." แล้ว resolve ทีหลัง)"""
    if args.physx:
        from isaaclab_physx.physics import PhysxManager
        return PhysxManager.__name__
    from isaaclab_newton.physics import NewtonManager
    return type(NewtonManager._solver).__name__ + " ใน " + ".".join(
        c.__name__ for c in NewtonManager.__subclasses__()) if NewtonManager._solver else "NewtonManager"


def make_cfg():
    cfg = load_cfg_from_registry(ilib.TASK_FLAT, "env_cfg_entry_point")
    # TODO(I2) เลือก preset: resolve_presets(cfg, {"newton"}) หรือ {"physx"}
    raise NotImplementedError('TODO(I2) เลือก preset: resolve_presets(cfg, {"newton"}) หรือ {"physx"}')
    cfg.scene.num_envs = args.num_envs
    cfg.seed = 0
    # ปิดของที่ไม่เกี่ยว ให้ดูฟิสิกส์ชัดๆ: การผลัก, สุ่ม friction, curriculum
    cfg.events.push_robot = None
    cfg.events.physics_material = None
    cfg.events.add_base_mass = None
    cfg.curriculum.lin_vel_cmd_levels = None
    if args.fast_path:
        cfg.sim.use_newton_actuators = True
    if args.save_mjcf and not args.physx:
        cfg.sim.physics.solver_cfg.save_to_mjcf = str(ilib.LOGS / "isaac_generated.xml")
    return cfg


def main():
    cfg = make_cfg()
    print(f"\n[1] physics cfg: {type(cfg.sim.physics).__name__}"
          + ("" if args.physx else f" · solver_cfg {type(cfg.sim.physics.solver_cfg).__name__}"))
    env = gym.make(ilib.TASK_FLAT, cfg=cfg)
    u = env.unwrapped
    print(f"    physics manager = {_pm_name()}")
    print(f"    physics_dt {u.physics_dt} · decimation {u.cfg.decimation} · step_dt {u.step_dt}")
    print(f"    _physics_handles_decimation = {u._physics_handles_decimation}")

    robot = u.scene["robot"]
    names = list(robot.joint_names)

    if not args.physx:
        from isaaclab_newton.physics import NewtonManager as NM  # noqa: N814

        model = NM.get_model()
        solver = NM._solver
        opt = solver.mjw_model.opt
        print(f"    solver = {type(solver).__name__} · integrator {int(opt.integrator)} (3 = implicitfast) · "
              f"cone {int(opt.cone)} (0 = pyramidal) · iterations {int(opt.iterations)} · "
              f"ls_iterations {int(opt.ls_iterations)}")
        print(f"    NewtonCfg: num_substeps {NM._num_substeps} · solver_dt {NM._solver_dt} · use_cuda_graph {u.cfg.sim.physics.use_cuda_graph}")

        # ------------------------------------------------ [2] Model
        print(f"\n[2] Newton Model: world {model.world_count} · body {model.body_count} · joint {model.joint_count} "
              f"· dof {model.joint_dof_count} · shape {model.shape_count}")
        # TODO(I2) นับชนิด geom (model.shape_type) ของหุ่นตัวแรก แล้วเทียบกับ MJCF ของ mjlab (capsule/sphere)
        raise NotImplementedError('TODO(I2) นับชนิด geom (model.shape_type) ของหุ่นตัวแรก แล้วเทียบกับ MJCF ของ mjlab (capsule/sphere)')
        print("    (mjlab MJCF: collision เป็น capsule/sphere 30+ ชิ้น · USD ของ Unitree: mesh จาก STL)")

    # ---------------------------------------------------- [3] ลำดับ joint
    print("\n[3] ลำดับ joint")
    # TODO(I3) perm[i] = index ใน Isaac ของ POLICY_JOINTS[i] · same = ลำดับเหมือนกันทุกตัว
    raise NotImplementedError('TODO(I3) perm[i] = index ใน Isaac ของ POLICY_JOINTS[i] · same = ลำดับเหมือนกันทุกตัว')
    print(f"    Isaac ({'PhysX' if args.physx else 'Newton'}) 6 ตัวแรก: {names[:6]}")
    print(f"    policy 6 ตัวแรก:              {ilib.POLICY_JOINTS[:6]}")
    print(f"    เหมือนกันทั้งหมด? {same} · perm (policy→isaac) = {perm}")

    # ---------------------------------------------------- [4] gain ที่ sim เห็นจริง
    print("\n[4] gain ใน sim (env 0) เทียบสูตร mjlab (ilib)")
    kp = robot.data.joint_stiffness.torch[0].cpu().numpy() if hasattr(robot.data.joint_stiffness, "torch") \
        else robot.data.joint_stiffness[0].cpu().numpy()
    kd = robot.data.joint_damping.torch[0].cpu().numpy() if hasattr(robot.data.joint_damping, "torch") \
        else robot.data.joint_damping[0].cpu().numpy()
    rows = []
    for pi, n in enumerate(ilib.POLICY_JOINTS):
        ii = perm[pi]
        rows.append(dict(joint=n, kp_sim=float(kp[ii]), kp_mjlab=float(ilib.KP[pi]),
                         kd_sim=float(kd[ii]), kd_mjlab=float(ilib.KD[pi])))
    ilib.print_table(rows[:6] + rows[12:14], fmt={c: "{:.3f}" for c in ("kp_sim", "kp_mjlab", "kd_sim", "kd_mjlab")})
    dk = max(abs(r["kp_sim"] - r["kp_mjlab"]) for r in rows)
    print(f"    max |kp_sim − kp_mjlab| = {dk:.2e}")
    if not args.physx:
        ke = model.joint_target_ke.numpy().reshape(model.world_count, -1)[0]
        arm = model.joint_armature.numpy().reshape(model.world_count, -1)[0]
        lim = model.joint_effort_limit.numpy().reshape(model.world_count, -1)[0]
        # dof 0–5 = free joint ของ pelvis · ต่อจากนั้นคือ joint ตามลำดับ Isaac
        print(f"    Newton model.joint_target_ke[world0][6:9] = {ke[6:9].round(3)} "
              f"· armature {arm[6:9].round(4)} · effort_limit {lim[6:9]}")

    # ---------------------------------------------------- [5] ฟิสิกส์กี่ครั้งต่อ env.step
    print("\n[5] 1 env.step() เรียกฟิสิกส์กี่ครั้ง")
    with torch.inference_mode():      # gym บังคับ reset ก่อน step · ทำใน inference_mode ให้ buffer ชนิดเดียวกับตอน step
        env.reset()
    sim = u.sim
    calls = {"sim.step": 0}
    orig = sim.step

    def counted(*a, **k):
        calls["sim.step"] += 1
        return orig(*a, **k)

    # TODO(I5) แทน sim.step ด้วย counted ชั่วคราว → env.step(action ศูนย์) 1 ครั้ง → คืนของเดิม
    raise NotImplementedError('TODO(I5) แทน sim.step ด้วย counted ชั่วคราว → env.step(action ศูนย์) 1 ครั้ง → คืนของเดิม')
    if not args.physx:
        # Newton เขียน dt ลง mjw_model.opt.timestep ทุกครั้งที่ step (ใน XML ที่ save ไว้ยังเป็น 0.002 ค่าเริ่มของ MuJoCo)
        print(f"    mjw_model.opt.timestep หลัง step = {_scalar(opt.timestep):.4f}")
    print(f"    sim.step ถูกเรียก {calls['sim.step']} ครั้ง "
          f"({'decimation อยู่ในฟิสิกส์/CUDA graph' if calls['sim.step'] == 1 else 'decimation วนใน Python'})")

    # ---------------------------------------------------- [6] เวลา
    with torch.inference_mode():
        env.step(act)
        torch.cuda.synchronize()
        t0 = time.time()
        for _ in range(args.steps):
            env.step(act)
        torch.cuda.synchronize()
    el = (time.time() - t0) / args.steps
    print(f"\n[6] env.step() เฉลี่ย {el * 1e3:.2f} ms ({args.num_envs} env) → {args.num_envs / el:,.0f} env-step/s")
    z = robot.data.root_pos_w.torch[:, 2] if hasattr(robot.data.root_pos_w, "torch") else robot.data.root_pos_w[:, 2]
    print(f"    pelvis z หลัง {args.steps + 2} step ด้วย action ศูนย์ (= ยืน PD ท่า default): {z.cpu().numpy().round(3)}")
    if args.save_mjcf and not args.physx:
        print(f"\n[7] MJCF ที่ Newton สร้าง: {ilib.LOGS / 'isaac_generated.xml'}")
    env.close()


if __name__ == "__main__":
    main()
    app.close()
