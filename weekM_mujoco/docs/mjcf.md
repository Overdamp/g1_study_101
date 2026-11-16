# MJCF: อ่านและแก้ไฟล์ XML ของหุ่น

> ไฟล์ที่ใช้: `~/nvidia/unitree/unitree_mujoco/unitree_robots/g1/scene_23dof.xml` (include `g1_23dof.xml`)
> **ห้ามแก้ไฟล์ใน unitree_mujoco** (repo หลัก + sim ทุกสัปดาห์ใช้อยู่) ให้แก้สำเนาใน `weekM_mujoco/models/` หรือแก้ด้วย MjSpec
> เอกสารเต็ม: https://mujoco.readthedocs.io/en/stable/XMLreference.html

## 1. โครงสร้างไฟล์ของ G1
```xml
<mujoco model="g1_23dof">
  <compiler angle="radian" meshdir="meshes"/>      <!-- มุมเป็น rad · mesh หาจากโฟลเดอร์ meshes ข้างไฟล์ -->
  <default>                                         <!-- ค่า default แบ่งเป็น class -->
    <default class="arm_motor">
      <joint damping="0.05" armature="0.01" frictionloss="0.2"/>
    </default> ...
  </default>
  <asset> <mesh name="pelvis" file="pelvis.STL"/> ... </asset>
  <worldbody>                                       <!-- tree ของ body -->
    <body name="pelvis" pos="0 0 0.793">
      <site name="imu"/>                            <!-- จุดอ้างอิงของ sensor IMU -->
      <inertial pos=... mass="3.813" diaginertia=.../>
      <joint name="floating_base_joint" type="free"/>     <!-- ลอยอิสระ 6 DoF → qpos 7 ตัว -->
      <geom type="mesh" contype="0" conaffinity="0" group="1" mesh="pelvis"/>   <!-- เห็นแต่ไม่ชน -->
      <geom type="mesh" mesh="pelvis"/>                                          <!-- ชน (group 0) -->
      <body name="left_hip_pitch_link" pos=...>
        <joint name="left_hip_pitch_joint" axis="0 1 0" range="-2.5307 2.8798" class="leg_motor"/>
        ... (ลูกต่อไปเรื่อยๆ)
  </worldbody>
  <actuator>  <motor name="left_hip_pitch" joint="left_hip_pitch_joint" ctrlrange="-88 88"/> ... </actuator>
  <sensor>    <jointpos .../> <jointvel .../> <jointactuatorfrc .../> <framequat .../> <gyro .../> ... </sensor>
</mujoco>
```
`scene_23dof.xml` = `<include file="g1_23dof.xml"/>` + พื้น (`<geom name="floor" type="plane">`) + แสง + skybox

## 2. element ที่ต้องรู้
| element | สำคัญอย่างไรกับหุ่นเรา |
|---|---|
| `body pos` | ตำแหน่งเทียบกับ body แม่ (ไม่ใช่กรอบโลก) · ลูกขยับตามแม่ |
| `joint` | ข้อต่อระหว่าง body กับแม่ · `axis` แกนหมุน · `range` ลิมิต (rad) |
| `joint damping` | แรงหน่วงต้านความเร็ว (Nm·s/rad) ของข้อต่อเอง (นอกเหนือจาก kd ของ PD) |
| `joint armature` | ความเฉื่อยของโรเตอร์มอเตอร์ (kg·m²) ผ่านเกียร์ · ทำให้ข้อต่อ "หนัก" ขึ้น |
| `joint frictionloss` | แรงเสียดทานแบบคูลอมบ์ (Nm) แรงบิดน้อยกว่านี้ = ไม่ขยับ (แต่ soft: ไหลช้าๆ ได้ → M5) |
| `geom contype / conaffinity` | 0/0 = ไม่ชนอะไร (ไว้ให้เห็นอย่างเดียว) |
| `geom group` | กลุ่มสำหรับเปิด/ปิดใน viewer (ปุ่ม 0–5) |
| `inertial` | มวล + ความเฉื่อย ถ้าไม่ใส่ คำนวณจาก geom (`density`) |
| `site` | จุดอ้างอิงไม่มีมวล ใช้วาง sensor / วัดตำแหน่ง |
| `motor` | actuator ที่ `ctrl` = แรงบิดตรงๆ (PD ทำนอก MuJoCo: ใน bridge หรือในโค้ดเรา) |
| `position` | actuator ที่มี PD ในตัว (`kp`) · mjlab ใช้แบบนี้ตอนเทรน · unitree_mujoco ไม่ใช้ |

## 3. สิ่งที่แปลกในไฟล์ G1 23-DoF (ลองหาเองใน XML)
1. **ข้อต่อหลอก 6 ตัว** (บรรทัด ~311–341): `<body name="waist_roll" pos="0 0 20">` มวล 1 g ต่อกับ world ลอยสูง 20 m เพื่อให้มี actuator/sensor ครบ 29 slot เหมือนหุ่น 29-DoF → LowState/LowCmd ใช้โครงเดียวกันได้
2. **ทุก link มี mesh 2 ชุด**: ชุด `contype="0" group="1"` ไว้แสดง อีกชุดไว้ชน (mesh เดียวกัน)
3. **actuator เป็น `motor` ทั้งหมด**: MuJoCo ไม่รู้จัก kp/kd ของเรา → PD อยู่ใน bridge (`ctrl = tau + kp·e + kd·ė`)
4. **site imu** อยู่ที่ pelvis (0,0,0) → `imu_quat` = `qpos[3:7]` พอดี · มี `secondary_imu` ที่ torso ด้วย (มี noise)

## 4. วิธีแก้ที่ 1: MjSpec (แก้ด้วยโค้ด ไม่ต้องยุ่งกับไฟล์)
```python
spec = mujoco.MjSpec.from_file(str(XML))           # อ่าน XML (ตาม include + meshdir ให้)
spec.joint("left_elbow_joint").frictionloss = 0.0  # แก้ค่า
spec.worldbody.add_geom(name="step", type=mujoco.mjtGeom.mjGEOM_BOX,
                        size=[1.5, 1.0, 0.025], pos=[2.5, 0, 0.025])     # size = ครึ่งความยาว!
spec.option.timestep = 0.005
m = spec.compile()                                 # ได้ MjModel ใหม่
d = mujoco.MjData(m)
print(spec.to_xml()[:300])                         # ดู XML ที่ได้
```
ใช้ใน `g1mj.build_model()` · ข้อดี: ทำซ้ำได้, กวาดค่าหลายค่าในลูปได้ (M5 `--sweep`), ไฟล์ต้นฉบับไม่เปลี่ยน

## 5. วิธีแก้ที่ 2: แก้ไฟล์ XML ด้วยมือ
1. สร้างสำเนาที่โหลดได้จากทุกที่: `python3 m5_mjcf.py --save my_g1` → `weekM_mujoco/models/my_g1.xml`
   (`save_xml` ตั้ง `meshdir` เป็น path เต็มให้ เพราะถ้าก็อปไฟล์เปล่าๆ ไปที่อื่น mesh จะหาไม่เจอ → error `resource not found`)
2. เปิดไฟล์ใน VS Code หา `left_elbow_joint` แก้ `frictionloss="0.2"` เป็นค่าอื่น
3. เปิดดู: `python3 -m mujoco.viewer --mjcf=$HOME/g1_study/weekM_mujoco/models/my_g1.xml` (แก้ไฟล์แล้วกด Reload ในแผง Simulation)
4. ทดลอง: `python3 m5_mjcf.py --xml ../../models/my_g1.xml`

⚠️ ไฟล์จาก `to_xml()` ขยาย default class ออกมาแล้ว ค่า `frictionloss` อาจอยู่บน `<joint>` แต่ละตัวโดยตรง ไม่ได้อยู่ใน `<default>`

## 6. แบบฝึก MJCF
ทายก่อนทุกข้อ แล้วค่อยแก้และรันเพื่อตรวจ:
1. เปลี่ยน `armature` ของศอกจาก 0.01 → 0.1: rise time ใน `m4 --elbow-step` จะยาวขึ้นหรือสั้นลง (แก้ใน `build_model(armature=...)` ได้)
2. เพิ่มกล่องสูง 3 cm ในฉาก (`--step 0.03`) แล้วเปิดดูใน viewer
3. เปลี่ยน `ctrlrange` ของศอกเป็น ±2 Nm (แก้ XML ด้วยมือ) → step ศอกใน `m4` ยังไปถึงไหม เพราะอะไร
4. เปลี่ยน `gravity` ใน `<option>` เป็นของดวงจันทร์ (−1.62) → หนังยางยืดเท่าไร (M3)
5. (อ่านอย่างเดียว) mjlab ใช้ MJCF คนละไฟล์ตอนเทรน: `~/nvidia/unitree/unitree_rl_mjlab/src/assets/robots/unitree_g1/xmls/g1_23dof.xml`
   และกำหนด actuator ในโค้ด `g1_23dof_constants.py` (`BuiltinPositionActuatorCfg` = PD ในตัว, `ARMATURE_*` คำนวณจากเกียร์)
   เทียบกับ unitree_mujoco (`motor` + armature 0.01 ทุกข้อ): ต่างกันตรงไหนบ้าง แล้วนี่คือส่วนหนึ่งของ sim2sim gap ไหม
