"""R6: event (domain randomization) และ curriculum: ใครเปลี่ยนอะไร เมื่อไร ฉบับสมบูรณ์

  python r6_events_curriculum.py

สิ่งที่ควรเห็น
  1. startup: สุ่มครั้งเดียวตอนสร้าง env → แต่ละ env ได้มวล torso, friction เท้า, frictionloss, kp ต่างกัน
     (ค่าเก็บใน env.sim.model ซึ่งมีมิติแรก = num_envs หลัง expand_model_fields)
  2. reset: ทุกครั้งที่ env reset → ตำแหน่ง/ทิศเริ่มต้นสุ่มใหม่ (reset_base) · delay ของ actuator สุ่มใหม่
  3. interval: push_robot ผลักทุก 5–6 s ต่อ env (นับถอยหลังแยกกัน) → ความเร็วกระโดด
  4. curriculum: commands_vel ดู common_step_counter (นับ step ของ env, ไม่คูณ num_envs) → 24 step/iteration
     stage "step": 5000*24 = iteration 5000 · และใช้ `>` → ที่ counter 0 ยังไม่เข้า stage แรก
"""
import contextlib
import io

import torch

import rlib


def main():
    cfg = rlib.load_cfg(rlib.FLAT, 4)
    with contextlib.redirect_stdout(io.StringIO()):
        env = rlib.make_env(cfg)
    robot, m, m0 = env.scene["robot"], env.sim.model, env.sim.mj_model   # m = ต่อ env (GPU), m0 = ต้นฉบับ (CPU)
    ix = robot.indexing

    # ---- 1. startup
    torso = ix.body_ids[robot.body_names.index("torso_link")].item()
    foot = ix.geom_ids[robot.geom_names.index("left_foot1_collision")].item()
    knee_j = robot.joint_names.index("left_knee_joint")
    knee_dof = ix.joint_v_adr[knee_j].item()
    knee_act = ix.ctrl_ids[robot.actuator_names.index("left_knee_joint")].item() \
        if "left_knee_joint" in robot.actuator_names else ix.ctrl_ids[knee_j].item()
    fields = [
        ("torso mass [kg]", m.body_mass[:, torso], m0.body_mass[torso], "torso_mass_payload add −1..+3.5"),
        ("foot friction", m.geom_friction[:, foot, 0], m0.geom_friction[foot, 0], "foot_friction abs 0.3..1.6"),
        ("knee frictionloss", m.dof_frictionloss[:, knee_dof], m0.dof_frictionloss[knee_dof], "joint_friction abs 0..0.3"),
        ("knee damping", m.dof_damping[:, knee_dof], m0.dof_damping[knee_dof], "joint_damping abs 0..0.1"),
        ("knee kp", m.actuator_gainprm[:, knee_act, 0], m0.actuator_gainprm[knee_act, 0], "motor_pd_gains ×0.85..1.15"),
    ]
    print("[1] startup event: ค่าที่แต่ละ env ได้ (สุ่มครั้งเดียว ตลอดการเทรน)\n")
    rows = [(name, f"{float(base):.3f}", *[f"{float(v):.3f}" for v in vals], note) for name, vals, base, note in fields]
    rlib.print_table(rows, ["field", "XML", "env0", "env1", "env2", "env3", "event"])
    print("→ policy เดียวต้องเดินได้ทุกแบบ = robust ต่อหุ่นจริงที่ค่าไม่ตรง XML")

    # ---- 2. reset
    print("\n[2] reset event: ตำแหน่งเริ่ม (x, y) และ yaw ต่อ env หลัง reset 2 ครั้ง")
    for k in range(2):
        env.reset()
        pos = robot.data.root_link_pos_w[:, :2] - env.scene.env_origins[:, :2]
        yaw = robot.data.heading_w
        print(f"  reset {k + 1}: " + " · ".join(f"({p[0]:+.2f},{p[1]:+.2f}) {y:+.2f}rad" for p, y in zip(pos.tolist(), yaw.tolist())))

    # ---- 3. interval
    em = env.event_manager
    left = em._interval_term_time_left[0]
    print(f"\n[3] interval: push_robot นับถอยหลังต่อ env [s]: {[round(x, 2) for x in left.tolist()]}")
    # ใช้ policy P3b ประคองให้ยืน/เดิน (action ศูนย์ล้มก่อนถึงเวลาผลัก แล้ว reset ตั้งเวลาใหม่)
    actor = rlib.ActorMLP(device=env.device)
    obs = env.observation_manager.compute()
    first = int(torch.argmin(left))
    prev_left = left[first].item()
    for i in range(int(7.0 / env.step_dt)):
        v = robot.data.root_link_lin_vel_w[first].clone()
        with torch.no_grad():
            obs, *_ = env.step(actor(obs["actor"]))
        now_left = em._interval_term_time_left[0][first].item()
        if now_left > prev_left:                       # เวลานับถอยหลังเด้งขึ้น = เพิ่งยิง event (หรือ env reset)
            # event เขียนความเร็วลง sim หลัง step นี้คำนวณเสร็จ → เห็นผลใน step ถัดไป
            with torch.no_grad():
                obs, *_ = env.step(actor(obs["actor"]))
            after = robot.data.root_link_lin_vel_w[first]
            print(f"  env {first}: ที่ t = {(i + 1) * env.step_dt:.2f} s เวลาเด้งเป็น {now_left:.2f} s · "
                  f"v ก่อน {[round(x, 2) for x in v.tolist()]} → step ถัดไป {[round(x, 2) for x in after.tolist()]} m/s")
            break
        prev_left = now_left

    # ---- 4. curriculum
    tw = env.command_manager.get_term("twist").cfg
    print("\n[4] curriculum commands_vel (เปลี่ยน ranges ของคำสั่งตอน reset)")
    for counter in (0, 1, 5000 * 24, 5000 * 24 + 1):
        env.common_step_counter = counter
        env.reset()
        print(f"  common_step_counter {counter:>7} (iteration ~{counter // 24:>5}): lin_vel_x {tw.ranges.lin_vel_x}"
              f" lin_vel_y {tw.ranges.lin_vel_y}")
    print("  (counter 0 ได้ ranges ตั้งต้นของ cfg (-1, 2) เพราะ stage แรกใช้ `counter > 0`)")
    env.close()


if __name__ == "__main__":
    main()
