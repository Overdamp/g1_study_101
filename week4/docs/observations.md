# Observation 80 ตัว: ทีละ term

อ้างอิงโค้ด: `deploy/include/unitree_articulation.h` (`update()`) และ `deploy/include/isaaclab/envs/mdp/observations/observations.h`
ลำดับ = ลำดับ key ใน `observations:` ของ `v0/params/deploy.yaml` (ทุก term `scale` = 1, `clip` = null, `history_length` = 1)

| # | term | มิติ | index | มาจาก | หน่วย |
|---|---|---|---|---|---|
| 1 | `base_ang_vel` | 3 | 0–2 | `imu_state.gyroscope` | rad/s (กรอบลำตัว) |
| 2 | `projected_gravity` | 3 | 3–5 | คำนวณจาก `imu_state.quaternion` | ไม่มีหน่วย (เวกเตอร์ยาว 1) |
| 3 | `velocity_commands` | 3 | 6–8 | จอย / คีย์บอร์ด (vx, vy, wz) | m/s, m/s, rad/s |
| 4 | `gait_phase` | 2 | 9–10 | นาฬิกาใน g1_ctrl (sin, cos) | – |
| 5 | `joint_pos_rel` | 23 | 11–33 | `motor_state[slot].q − default_joint_pos` | rad |
| 6 | `joint_vel_rel` | 23 | 34–56 | `motor_state[slot].dq` | rad/s |
| 7 | `last_action` | 23 | 57–79 | action **ดิบ** ของ step ก่อน | – |
| | **รวม** | **80** | | | |

## ลำดับข้อต่อ: `joint_ids_map`
```yaml
joint_ids_map: [0,1,2,3,4,5,6,7,8,9,10,11,12,15,16,17,18,19,22,23,24,25,26]
```
index ของ policy `i` → slot ของ SDK `joint_ids_map[i]` เช่น policy index 16 → slot 18 = ศอกซ้าย
```cpp
// unitree_articulation.h
data.joint_pos[i] = lowstate->msg_.motor_state()[data.joint_ids_map[i]].q();
```
ใน Python: วน `joint_ids_map` แล้วดึง `msg.motor_state[slot]` ซึ่งเป็นวิธีเดียวกับ dict `G1_23DOF_JOINTS` ในงาน 1.5 (ลำดับ key เหมือนกันพอดี)
⚠️ งาน 4.8 (ก): ถ้าใช้ slot 0–22 ตรงๆ ตั้งแต่ index 13 เป็นต้นไปจะผิดหมด (slot 13, 14 ไม่มีข้อต่อ)

## 1. `base_ang_vel`
ความเร็วเชิงมุมของลำตัว (กราน) ในกรอบของตัวหุ่นเอง เอามาจาก gyro ตรงๆ:
```cpp
data.root_ang_vel_b[i] = lowstate->msg_.imu_state().gyroscope()[i];
```
ยืนนิ่ง ≈ (0, 0, 0) ตอนเทรนมี noise ±0.2 rad/s

## 2. `projected_gravity`: เวกเตอร์แรงโน้มถ่วงในกรอบลำตัว
**แนวคิด:** "ถ้าฉันเป็นหุ่น แรงโน้มถ่วงชี้ไปทางไหนเมื่อเทียบกับตัวฉัน"
- ยืนตรง: แรงโน้มถ่วงชี้ลงตรงๆ = **(0, 0, −1)**
- ก้มไปข้างหน้า: แรงโน้มถ่วงเริ่มชี้ไปทาง "หน้า" ของตัวหุ่น → x เปลี่ยน
- เอียงซ้ายขวา: y เปลี่ยน

**ทำไมใช้แทน roll/pitch:** ไม่มีปัญหามุมวนรอบ (±180°) และไม่ขึ้นกับ yaw (หันไปทางไหน gravity ในกรอบลำตัวก็เหมือนเดิม) policy จึงเรียนรู้ได้ง่ายกว่า

**โค้ด C++:**
```cpp
data.root_quat_w = Eigen::Quaternionf(q[0], q[1], q[2], q[3]);       // (w, x, y, z)
data.projected_gravity_b = data.root_quat_w.conjugate() * GRAVITY_VEC_W;   // GRAVITY_VEC_W = (0,0,−1)
```
quaternion ของ IMU Unitree เรียงเป็น **(w, x, y, z)** ส่วน `conjugate()` ทำหน้าที่หมุนเวกเตอร์จากกรอบโลกเข้ากรอบลำตัว

**สูตรสำหรับ Python** (หมุน (0,0,−1) ด้วย R(q)ᵀ):
```
gx = −2·(x·z − w·y)
gy = −2·(y·z + w·x)
gz = −(1 − 2·(x² + y²))
```
**เทสต์ตัวเอง:** q = (1, 0, 0, 0) (ไม่หมุน) ต้องได้ (0, 0, −1) · ความยาวของผลลัพธ์ต้องเท่ากับ 1 เสมอ
**ทิศทาง (vault `Observations.md`):** pitch+ ↔ gyro y+ ↔ gravity x+ · roll+ ↔ gyro x+ ↔ gravity y− (ตรวจกับหุ่นจริง 28/10) → ทดสอบใน sim ในงาน 4.5

## 3. `velocity_commands`
คำสั่งความเร็ว (vx, vy, wz) ถูก clamp ตาม `commands.base_velocity.ranges` ใน deploy.yaml (vx −0.5..1.0, vy −0.5..0.5, wz −1..1)
- หุ่นจริง: จากจอยใน `wireless_remote` ของ LowState
- sim: g1_ctrl ใช้คีย์บอร์ดแทน (`keyboard_velocity_commands` ใน `State_RLBase.cpp` มี smoothing) **โปรแกรมเราจึงอ่านค่านี้จาก DDS ไม่ได้** → shadow mode ให้ใช้ cmd = 0 (ไม่กดปุ่มเดิน)

## 4. `gait_phase`: นาฬิกาจังหวะก้าว
```cpp
global_phase = fmod(global_phase + step_dt / period, 1.0);    // period = 0.6 s
obs = (sin(2π·phase), cos(2π·phase));
if (|cmd| < 0.1) obs = (0, 0);                               // ยืนนิ่ง → ปิดนาฬิกา
```
- ทุก step ของ policy phase เดินหน้า 0.02/0.6 = 1/30 รอบ ครบรอบใน 30 step = 0.6 s
- ตอนยืนนิ่ง (cmd เล็ก) เป็น (0, 0) เพื่อให้ policy รู้ว่า "ไม่ต้องย่ำเท้า"
- phase เดินตลอดเวลาแม้ obs จะเป็น 0 (เราจึงไม่รู้ phase ของ g1_ctrl ถ้ามันเคยเดินมาก่อน → shadow mode ให้เทียบตอน cmd = 0)

## 5. `joint_pos_rel`
```
joint_pos_rel[i] = q[i] − default_joint_pos[i]
default_joint_pos = [-0.1,0,0,0.3,-0.2,0, -0.1,0,0,0.3,-0.2,0, 0, 0.35,0.18,0,0.87,0, 0.35,-0.18,0,0.87,0]
```
ยืนในท่า default พอดี → 0 ทั้งหมด (ท่าเดียวกับ `qs` ของ FixStand ใน config.yaml)
⚠️ งาน 4.8 (ข): ลืมลบ default → policy คิดว่าหุ่นอยู่ผิดท่า เช่นเข่าต่างไป 0.3 rad ศอกต่างไป 0.87 rad

## 6. `joint_vel_rel`
`dq` ของแต่ละข้อต่อตรงๆ (default velocity = 0 จึงไม่ต้องลบอะไร) ตอนเทรนมี noise ±1.5 rad/s

## 7. `last_action`
action ที่ **ONNX คืนมาใน step ก่อน (ค่าดิบ ก่อนคูณ scale)**
```cpp
auto data = env->action_manager->action();      // raw action
```
step แรกหลัง reset = 0 ทั้งหมด (นี่คือเหตุผลหนึ่งที่ step แรกกระตุก จึงต้องมี Soft Start)
⚠️ งาน 4.8 (ง): ถ้าใส่ q_des (หลังคูณ scale + offset) แทน policy จะเห็นค่าที่ไม่เคยเจอตอนเทรน

## ค่าที่ควรเห็นตอนยืนนิ่งในท่า default (ใช้เขียนเทสต์ 4.2)
| term | ค่า |
|---|---|
| `base_ang_vel` | ≈ (0, 0, 0) |
| `projected_gravity` | ≈ (0, 0, −1) |
| `velocity_commands` | (0, 0, 0) |
| `gait_phase` | (0, 0) |
| `joint_pos_rel` | ≈ 0 × 23 |
| `joint_vel_rel` | ≈ 0 × 23 |
| `last_action` | step แรก 0 × 23 |

## คำถามเช็ค
1. policy index 13 คือข้อต่ออะไร slot เท่าไหร่
2. หุ่นหันหน้าไปทางเหนือกับทางใต้ ยืนตรงเหมือนกัน `projected_gravity` ต่างกันไหม แล้ว yaw ของ IMU ต่างกันไหม
3. ถ้าป้อน cmd = (0.05, 0, 0) gait_phase จะเป็นอะไร
