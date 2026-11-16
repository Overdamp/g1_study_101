"""m1_inspect.py: สำรวจ MjModel ของ G1 23-DoF (งาน M1) ฉบับสมบูรณ์

รัน:  python3 m1_inspect.py              (ทุกตาราง)
      python3 m1_inspect.py --joints     (เฉพาะตาราง joint)

คำถามที่ไฟล์นี้ตอบ:
  - ทำไม nq = 36 แต่ nv = 35 และ nu = 29 (ไม่ใช่ 23)
  - actuator index ตรงกับ slot ของ LowState ไหม
  - ข้อต่อหลอก 6 ตัวคืออะไร อยู่ที่ไหน
"""

import argparse

import mujoco
import numpy as np

from g1mj import XML, load, slot_table

JNT_TYPE = {0: "free", 1: "ball", 2: "slide", 3: "hinge"}
QPOS_SIZE = {0: 7, 1: 4, 2: 1, 3: 1}       # free = pos 3 + quat 4
QVEL_SIZE = {0: 6, 1: 3, 2: 1, 3: 1}       # free = lin 3 + ang 3


def sizes(m, d) -> None:
    print(f"== {XML.name}")
    print(f"  nbody {m.nbody}  njnt {m.njnt}  ngeom {m.ngeom}  nu {m.nu}  nsensor {m.nsensor} (nsensordata {m.nsensordata})")
    print(f"  timestep {m.opt.timestep} s ({1 / m.opt.timestep:.0f} Hz)  gravity {m.opt.gravity}")
    print(f"  มวลรวม {m.body_subtreemass[0]:.2f} kg  (body_subtreemass[0] = world รวมทุกอย่าง)")
    # nq / nv นับจาก joint จริง ให้เห็นที่มา
    nq = sum(QPOS_SIZE[t] for t in m.jnt_type)
    nv = sum(QVEL_SIZE[t] for t in m.jnt_type)
    n_hinge = int(np.sum(m.jnt_type == 3))
    print(f"  nq {m.nq} = free 7 + hinge {n_hinge}  (นับเองได้ {nq})")
    print(f"  nv {m.nv} = free 6 + hinge {n_hinge}  (นับเองได้ {nv})  ← quaternion 4 ตัว แต่ความเร็วเชิงมุมมี 3")


def joints(m, d) -> None:
    print("\n== joint (ลำดับใน XML)")
    print(f"{'id':>3} {'name':<28} {'type':<5} {'qadr':>4} {'dadr':>4} {'range [deg]':>17} {'fric':>5} {'arm':>5} {'damp':>5}")
    for j in range(m.njnt):
        t = int(m.jnt_type[j])
        da = m.jnt_dofadr[j]
        lo, hi = np.degrees(m.jnt_range[j]) if m.jnt_limited[j] else (np.nan, np.nan)
        rng = f"{lo:+7.1f}..{hi:+7.1f}" if m.jnt_limited[j] else "ไม่จำกัด"
        print(f"{j:>3} {m.joint(j).name:<28} {JNT_TYPE[t]:<5} {m.jnt_qposadr[j]:>4} {da:>4} {rng:>17} "
              f"{m.dof_frictionloss[da]:>5.2f} {m.dof_armature[da]:>5.2f} {m.dof_damping[da]:>5.2f}")


def actuators(m, d) -> None:
    tab = slot_table(m)
    print("\n== actuator (index = slot ของ LowState)")
    print(f"{'slot':>4} {'actuator':<22} {'joint':<28} {'qadr':>4} {'ctrlrange [Nm]':>15}")
    for i in range(m.nu):
        mark = "  ← หลอก" if m.body(m.jnt_bodyid[tab.joint_id[i]]).pos[2] > 10 else ""
        lo, hi = tab.ctrlrange[i]
        print(f"{i:>4} {m.actuator(i).name:<22} {tab.names[i]:<28} {tab.qadr[i]:>4} {lo:>+7.0f}..{hi:<+6.0f}{mark}")
    print("  ※ ลำดับ joint ใน XML (id 24–29 = หลอก) ไม่เท่ากับลำดับ slot → ต้อง map ผ่าน actuator_trnid เสมอ")


def dummies(m, d) -> None:
    mujoco.mj_forward(m, d)
    print("\n== ข้อต่อหลอก: body ที่ไม่ได้ต่อกับหุ่น")
    for b in range(1, m.nbody):
        if m.body_parentid[b] == 0 and m.body(b).name != "pelvis":
            print(f"  {m.body(b).name:<18} parent=world  xpos={d.xpos[b]}  mass={m.body_mass[b]:g} kg")
    print("  → unitree_mujoco ใช้ 23-DoF ส่ง LowState 29 slot เหมือน 29-DoF ช่องที่ไม่มีข้อต่อจึงเป็น body ลอยฟ้า 1 g")


def sensors(m, d) -> None:
    print("\n== sensor (จัดกลุ่มตามชนิด)")
    groups = {}
    for s in range(m.nsensor):
        groups.setdefault(mujoco.mjtSensor(m.sensor_type[s]).name, []).append(s)
    for typ, ids in groups.items():
        if len(ids) > 2:                     # กลุ่มใหญ่เรียงติดกัน: แสดงเป็นช่วง
            a0, a1 = m.sensor_adr[ids[0]], m.sensor_adr[ids[-1]] + m.sensor_dim[ids[-1]]
            print(f"  {typ:<22} {len(ids):>3} ตัว  sensordata[{a0}:{a1}]  {m.sensor(ids[0]).name} … {m.sensor(ids[-1]).name}")
        else:                                # IMU: แสดงทีละตัว (ไม่ได้อยู่ติดกัน)
            for s in ids:
                a = m.sensor_adr[s]
                print(f"  {typ:<22}   1 ตัว  sensordata[{a}:{a + m.sensor_dim[s]}]  {m.sensor(s).name}")
    print(f"  bridge อ่าน q = sensordata[i], dq = [i+{m.nu}], tau = [i+{2 * m.nu}]  (unitree_sdk2_bridge.h:192–194)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--joints", action="store_true")
    args = ap.parse_args()
    m, d = load()
    if args.joints:
        joints(m, d)
        return
    sizes(m, d)
    joints(m, d)
    actuators(m, d)
    dummies(m, d)
    sensors(m, d)


if __name__ == "__main__":
    main()
