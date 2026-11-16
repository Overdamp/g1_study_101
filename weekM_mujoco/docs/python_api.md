# Python API ของ MuJoCo (เฉพาะที่ใช้กับหุ่นเรา)

> ทุกตัวอย่างรันได้ใน `python3` (REPL) ลองพิมพ์ตามไปทีละบรรทัด และ**ทายผลก่อนกด Enter**
> เอกสารเต็ม: https://mujoco.readthedocs.io/en/stable/python.html และ `APIreference` (ชื่อฟังก์ชัน C = ชื่อใน Python)

## 1. MjModel กับ MjData
```python
import mujoco, numpy as np
m = mujoco.MjModel.from_xml_path("/home/luke/nvidia/unitree/unitree_mujoco/unitree_robots/g1/scene_23dof.xml")
d = mujoco.MjData(m)
```
| | MjModel `m` | MjData `d` |
|---|---|---|
| คืออะไร | ค่าที่ **ไม่เปลี่ยน** ระหว่างจำลอง (คอมไพล์จาก XML) | **สถานะ** ณ ตอนนี้ เปลี่ยนทุก step |
| ตัวอย่าง | `m.opt.timestep`, `m.body_mass`, `m.jnt_range`, `m.actuator_ctrlrange`, `m.dof_frictionloss` | `d.time`, `d.qpos`, `d.qvel`, `d.ctrl`, `d.sensordata`, `d.xpos`, `d.contact` |
| เทียบกับหุ่นจริง | สเปคของหุ่น (มวล, ลิมิต) | LowState + คำสั่ง ณ ตอนนี้ |

1 model ใช้กับหลาย data ได้ (mjlab ใช้ 4096 env = 4096 สถานะ แต่โมเดลเดียว)
แก้ `m` ได้สดๆ (เช่น `m.dof_frictionloss[22] = 0`) โดยไม่ต้องโหลดใหม่ แต่ถ้าจะเพิ่ม/ลบของ ต้องแก้ XML หรือใช้ MjSpec (ดู `mjcf.md`)

## 2. ขนาด และ qpos / qvel
| ค่า | หุ่นเรา | มาจาก |
|---|---|---|
| `m.nq` | 36 | free joint 7 (x y z + quaternion w x y z) + hinge 29 |
| `m.nv` | 35 | free joint 6 (vx vy vz + ωx ωy ωz) + hinge 29 |
| `m.nu` | 29 | actuator 29 ตัว (= slot ของ LowState) |

`nq ≠ nv` เพราะการหมุนใช้ quaternion 4 ตัว แต่ความเร็วเชิงมุมมี 3 ตัว → **index ใน qpos กับ qvel ของข้อต่อเดียวกันต่างกัน 1** (`qposadr = dofadr + 1`)

```python
d.qpos[0:3]   # ตำแหน่ง pelvis ในกรอบโลก
d.qpos[3:7]   # quaternion (w, x, y, z)  ← ลำดับเดียวกับ LowState imu.quaternion
d.qvel[0:3]   # ความเร็วเชิงเส้น กรอบโลก
d.qvel[3:6]   # ความเร็วเชิงมุม กรอบลำตัว (= gyro)
```

## 3. ชื่อ ↔ index (สำคัญที่สุด)
**อย่าเดาตัวเลข** ให้ค้นจากชื่อเสมอ
```python
m.joint("left_elbow_joint").qposadr     # array([23])  ตำแหน่งใน d.qpos
m.joint("left_elbow_joint").dofadr      # array([22])  ตำแหน่งใน d.qvel
m.joint("left_elbow_joint").id          # 17           ลำดับใน XML
d.joint("left_elbow_joint").qpos        # ค่ามุมเลย (view เข้าไปใน d.qpos)
m.actuator("left_elbow").trnid          # [17, -1]     actuator นี้ขับ joint id 17
d.sensor("imu_quat").data               # 4 ค่า
d.body("pelvis").xpos                   # ตำแหน่ง body กรอบโลก
mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, "step")   # −1 ถ้าไม่มี (ใช้เช็คว่ามีไหม)
```

### กับดักของ G1 23-DoF
ลำดับ joint ใน XML **ไม่ใช่** ลำดับ slot:
- joint id 1–23 = ข้อต่อจริง · id 24–29 = ข้อต่อหลอก (waist_roll, waist_pitch, wrist_pitch/yaw × 2) ประกาศไว้ท้ายไฟล์
- actuator ประกาศเรียงตาม slot 0–28 (รวมข้อต่อหลอกที่ slot 13, 14, 20, 21, 27, 28)
- ดังนั้น slot 13 → `qpos[30]` ไม่ใช่ `qpos[20]`

วิธีที่ถูก: `slot → actuator → joint → qposadr`
```python
jid = m.actuator_trnid[:, 0]           # joint ของ actuator 0..28
qadr = m.jnt_qposadr[jid]              # qpos index ของแต่ละ slot
d.qpos[qadr[18]]                       # ศอกซ้าย
```

## 4. sensor
```python
d.sensordata                       # array ยาว m.nsensordata (113) เรียงตามที่ประกาศใน XML
m.sensor_adr[i], m.sensor_dim[i]   # sensor ตัวที่ i อยู่ช่วงไหน
d.sensor("imu_gyro").data          # ใช้ชื่อสะดวกกว่า
```
G1 ประกาศไว้: jointpos 29 → jointvel 29 → jointactuatorfrc 29 → imu_quat 4 → imu_gyro 3 → imu_acc 3 → ...
bridge จึงอ่าน `q = sensordata[i]`, `dq = sensordata[i + 29]`, `tau_est = sensordata[i + 58]` (`unitree_sdk2_bridge.h:192–194`)

⚠️ `d.qpos`, `d.sensordata`, `d.xpos` เป็น **view** (ชี้ไปที่หน่วยความจำของ d) ถ้าจะเก็บค่าไว้ดูภายหลัง ใช้ `.copy()` ไม่งั้นค่าจะเปลี่ยนตามทุก step

## 5. ฟังก์ชันหลัก
| ฟังก์ชัน | ทำอะไร | ใช้เมื่อ |
|---|---|---|
| `mujoco.mj_step(m, d)` | 1 step: คำนวณแรง → integrate → `d.time += timestep` | ใน loop จำลอง |
| `mujoco.mj_forward(m, d)` | คำนวณทุกอย่างจาก qpos/qvel **โดยไม่เดินเวลา** (xpos, sensor, contact, แรง) | หลังเขียน qpos เอง (ตั้งท่า) |
| `mujoco.mj_resetData(m, d)` | กลับค่าเริ่มต้น (qpos0) | เริ่มใหม่ |
| `mujoco.mj_contactForce(m, d, i, f6)` | แรงของ contact ที่ i (6 ค่า, `f6[0]` = แรงตั้งฉาก) | M6 |
| `mujoco.mj_name2id / mj_id2name` | ชื่อ ↔ id | |

ลำดับใน `mj_step`: คำนวณ position-dependent (รวม **sensor**) → แรง → integrate → qpos ใหม่
ผลคือ หลัง `mj_step` แล้ว `sensordata` ยังเป็นของ **ก่อน** integrate (ช้ากว่า qpos 1 step) ← M6 วัดได้ต่างกัน ~1e-4

## 6. ใส่แรงจากภายนอก และสั่งมอเตอร์
```python
d.ctrl[18] = 1.5                                   # แรงบิด 1.5 Nm ที่ศอกซ้าย (actuator ชนิด motor)
d.xfrc_applied[m.body("torso_link").id, :3] = f    # แรง [N] กรอบโลก ที่ body (หนังยาง)
```
- `ctrl` ถูก clamp ด้วย `ctrlrange` อัตโนมัติ (ศอก ±25 Nm) → ค่าที่ให้จริงอ่านจาก sensor `jointactuatorfrc`
- `xfrc_applied` **ค้างอยู่** จนกว่าจะเขียนใหม่ (ไม่ถูกล้างทุก step)

## 7. viewer
```python
from mujoco import viewer as mjviewer             # ⚠️ อย่า "import mujoco.viewer" ในฟังก์ชัน (ดู README บั๊ก)
with mjviewer.launch_passive(m, d, key_callback=on_key) as v:
    while v.is_running():
        with v.lock():         # กันไม่ให้ viewer อ่าน d ระหว่างเราแก้
            mujoco.mj_step(m, d)
        v.sync()               # ส่งภาพ + รับการลาก/ปุ่ม
        time.sleep(...)        # หน่วงให้ real-time เอง (viewer ไม่ทำให้)
```
- `key_callback(keycode)` รับรหัส GLFW: ตัวเลข/ตัวพิมพ์ใหญ่ = ASCII (`'9'` = 57, Space = 32), ↑ = 265, ↓ = 264
- `mujoco.viewer.launch(m, d)` = แบบ managed (viewer step เอง โค้ดเราหยุดรอ) ใช้ดูอย่างเดียว

## 8. แบบฝึกใน REPL (ก่อน M1)
ทายก่อนทุกข้อ:
1. `m.body_subtreemass[0]` = ? (มวลรวม)
2. `d.qpos[:7]` ตอนเริ่ม = ?
3. `mujoco.mj_step(m, d)` 500 ครั้ง แล้ว `d.time` = ? `d.qpos[2]` ขึ้นหรือลง?
4. `m.opt.timestep = 0.005` แล้ว step อีก 500 ครั้ง `d.time` เพิ่มเท่าไร
5. `d.sensor("imu_acc").data` ตอนกำลังตก (ยังไม่แตะพื้น) = ?
