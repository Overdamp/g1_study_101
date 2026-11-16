"""m1_inspect.py: สำรวจ MjModel ของ G1 23-DoF (งาน M1) โครงให้เติม

รัน:  python3 m1_inspect.py
ก่อนเริ่ม: เติม slot_table / motor_q ใน g1mj_skeleton.py ให้เทสต์ "slot_table" ผ่าน

ทายก่อนรัน (จดลงบันทึกการทาย): nq = ?  nv = ?  nu = ?  (หุ่นมี 23 ข้อต่อ)
เฉลย: ../complete/m1_inspect.py
"""

import mujoco
import numpy as np

from g1mj_skeleton import XML, load, slot_table

JNT_TYPE = {0: "free", 1: "ball", 2: "slide", 3: "hinge"}


def sizes(m, d) -> None:
    print(f"== {XML.name}")
    # TODO 1: พิมพ์ m.nbody, m.njnt, m.ngeom, m.nu, m.nsensor, m.nq, m.nv
    # TODO 2: พิมพ์ m.opt.timestep (กี่ Hz?) และมวลรวม m.body_subtreemass[0]
    # TODO 3: นับ hinge เอง (np.sum(m.jnt_type == 3)) แล้วอธิบาย nq = 7 + ?, nv = 6 + ?  ทำไม 7 กับ 6 ต่างกัน
    pass


def joints(m, d) -> None:
    print("\n== joint (ลำดับใน XML)")
    for j in range(m.njnt):
        # TODO 4: ต่อ 1 แถว: j, m.joint(j).name, JNT_TYPE[m.jnt_type[j]], m.jnt_qposadr[j], m.jnt_dofadr[j],
        #         np.degrees(m.jnt_range[j]) (ถ้า m.jnt_limited[j]), m.dof_frictionloss[dofadr], m.dof_armature[dofadr]
        pass


def actuators(m, d) -> None:
    tab = slot_table(m)
    print("\n== actuator (index = slot ของ LowState)")
    for i in range(m.nu):
        # TODO 5: i, m.actuator(i).name, tab.names[i], tab.qadr[i], tab.ctrlrange[i]
        # TODO 6: ทำเครื่องหมาย "หลอก" ถ้า body ของ joint นั้นอยู่สูง > 10 m:
        #         m.body(m.jnt_bodyid[tab.joint_id[i]]).pos[2] > 10
        pass
    # คำถาม: slot 13 อยู่ที่ qpos ตำแหน่งไหน ทำไมไม่ใช่ 20


def dummies(m, d) -> None:
    mujoco.mj_forward(m, d)
    print("\n== ข้อต่อหลอก")
    # TODO 7: วน body b = 1..m.nbody−1 ที่ m.body_parentid[b] == 0 (ต่อกับ world) และไม่ใช่ "pelvis"
    #         พิมพ์ชื่อ, d.xpos[b], m.body_mass[b]  → ทำไม unitree_mujoco ต้องมี body พวกนี้
    pass


def sensors(m, d) -> None:
    print("\n== sensor")
    for s in range(m.nsensor):
        # TODO 8: m.sensor(s).name, mujoco.mjtSensor(m.sensor_type[s]).name, m.sensor_adr[s], m.sensor_dim[s]
        #         (29 ตัวแรกเยอะ: พิมพ์แค่ s < 3 หรือ s ≥ 87 ก็พอ)
        pass
    # คำถาม: bridge อ่าน q ของ slot i จาก sensordata[?]  dq จาก [?]  tau จาก [?]


def main():
    m, d = load()
    sizes(m, d)
    joints(m, d)
    actuators(m, d)
    dummies(m, d)
    sensors(m, d)


if __name__ == "__main__":
    main()
