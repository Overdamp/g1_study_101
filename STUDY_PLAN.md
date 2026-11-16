# แผนการเรียน G1 23-DoF: 6 สัปดาห์ จาก "รันตาม" เป็น "เขียนเอง"

> **ตัวจริงของแผน** (checkbox, บันทึกการทาย, ช่องสรุป) อยู่ที่ Obsidian vault:
> `~/nvidia/unitree/g1_knowledge/05 Study/Study Plan.md`
> ไฟล์นี้เป็น**ภาพรวม**สำหรับดูเร็วๆ ใน repo ถ้าข้อมูลขัดกัน ให้ยึดตาม vault
> อัพเดทล่าสุด: 10/11/2026

## ภาพรวม 6 สัปดาห์

```
สัปดาห์ 1  อ่านข้อมูลหุ่น        rt/lowstate ──▶ โปรแกรมเรา          (อ่านอย่างเดียว)
สัปดาห์ 2  สั่งข้อต่อเดียว        โปรแกรมเรา ──▶ rt/lowcmd ──▶ sim     (PD control)
สัปดาห์ 3  สถานะของ controller    FSM: Passive → HoldPose → ...       (g1_ctrl)
สัปดาห์ 4  policy                observation ──▶ policy.onnx ──▶ action
สัปดาห์ 5  เทรน                  reward ──▶ เทรน ──▶ vel_eval
สัปดาห์ 6  ข้อมูลจริง             log หุ่นจริง ──▶ ระบุค่า kp / offset
```

แต่ละสัปดาห์ต่อยอดจากสัปดาห์ก่อน: อ่าน state ได้ (1) → สั่งได้ (2) → จัดลำดับการสั่งได้ (3) → ให้ policy สั่งแทน (4) → สร้าง policy เอง (5) → เทียบกับหุ่นจริง (6)

| สัปดาห์ | หัวข้อ | สิ่งที่ได้ (เขียนเอง) | สถานะ |
|---|---|---|---|
| **1** | DDS และข้อมูลหุ่น | `week1/read_lowstate.py` | 🟡 กำลังทำ (1.1–1.4 เสร็จ) |
| 2 | PD control | `week2/` สั่งศอกซ้ายข้อเดียวใน sim | ⚪ ร่าง (มี docs แล้ว) |
| 3 | FSM | mini FSM (Python) + `State_HoldPose` ใน g1_ctrl สำเนา | ⚪ ร่าง (มี docs แล้ว) |
| 4 | Policy | obs builder + shadow mode เทียบ q_des กับ g1_ctrl | ⚪ ร่าง (มี docs แล้ว) |
| 5 | เทรน | fine-tune P3b: control vs เปลี่ยน reward 1 ตัว | ⚪ ร่าง (มี docs แล้ว) |
| 6 | วิเคราะห์ข้อมูลจริง | `pd_check` แบบง่ายจาก log 3/11 | ⚪ ร่าง (มี docs แล้ว) |

สัปดาห์ 2–6 จะลงรายละเอียดหลังจบสัปดาห์ก่อนหน้า

---

## สัปดาห์ 1: DDS และข้อมูลหุ่น 🟡
**เป้าหมาย:** เขียนโปรแกรมอ่าน `rt/lowstate` จาก sim ได้เอง และเข้าใจว่าข้อมูลเดินทางมาถึงโปรแกรมได้อย่างไร
**ไฟล์:** `week1/scripts/read_lowstate.py` (งานของเรา) · `week1/scripts/skelatons/` (โครง TODO 1.2–1.7) · `week1/scripts/complete/` (เฉลยแยกตามงาน t1_2 … read_lowstate.py) · `week1/docs/` (README, dds_basics, lowstate_fields, threading_and_lock, python_notes, debug_checklist)

| งาน | ทำอะไร | แนวคิดที่ได้ | สถานะ |
|---|---|---|---|
| 1.1 | เปิด sim `./start_sim.sh` | domain 1 บน `lo`, multicast, elastic band | ✅ |
| 1.2 | พิมพ์ทุกครั้งที่ได้ LowState | `ChannelFactoryInitialize`, `ChannelSubscriber`, callback | ✅ |
| 1.3 | นับ Hz พิมพ์ทุก 1 s | thread, `Lock`, `time.monotonic()` | ✅ ~905 Hz |
| 1.4 | มุมศอกซ้าย (slot 18) เป็นองศา | `motor_state[i].q`, rad→deg, `None` = ยังไม่มีข้อมูล | ✅ +69.3° |
| 1.5 | ตาราง 23 ข้อต่อ (q, dq, temp) ทุก 0.5 s | slot map (dict), เก็บ `msg` ทั้งก้อน, f-string จัดคอลัมน์ | ⬜ |
| 1.6 | IMU roll/pitch/yaw + `mode_machine` | `imu_state`, `mode_machine` = 4 | ⬜ |
| 1.7 | `--network` / `--domain` (argparse) ใช้กับหุ่นจริงได้ | argparse, หุ่นจริง `enp43s0` domain 0 (อ่านอย่างเดียว) | ⬜ |
| 1.8 | ทำให้พัง: domain ผิด / ปิด multicast | อาการ "เงียบไม่มี error" | ⬜ |

**คำถามทวน** (ตอบโดยไม่เปิดโน้ต)
1. DDS คืออะไร ต่างจากการเรียกฟังก์ชันตรงๆ อย่างไร
2. `ChannelFactoryInitialize(domain, iface)` สองค่านี้คืออะไร ทำไม sim ใช้ 1 แต่หุ่นจริงใช้ 0
3. callback ถูกเรียกเมื่อไหร่ อยู่ thread เดียวกับ `main` ไหม
4. ทำไม LowState มี 35 ช่องมอเตอร์ แต่หุ่นเรามี 23 ข้อต่อ ช่องไหนว่าง
5. ทำไมต้องเปิด multicast บน `lo` แต่หุ่นจริงไม่ต้อง

**เรื่องที่คุยไปแล้ว:** `rt/` = ROS topic · multicast = discovery ("ตะโกนถาม") · `unitree_hg` (G1) vs `unitree_go` · topic/domain/type ผิด = เงียบไม่มี error · type hints ไม่บังคับตอนรัน · `idlc` = IDL compiler · `rclpy` = ROS Client Library for Python

---

## สัปดาห์ 2: PD control ⚪ (ร่าง)
**เป้าหมาย:** ส่ง `rt/lowcmd` ให้ข้อต่อเดียวขยับใน sim และเข้าใจว่า kp / kd ทำอะไรทางฟิสิกส์
**docs:** `week2/docs/` (README = งาน 2.1–2.8, `lowcmd_structure.md`, `pd_control.md`, `sim_vs_real.md`)
- ส่งคำสั่งให้ศอกซ้ายขยับแบบ step ใน sim (ข้อต่ออื่น damping) ต้องคำนวณ CRC
- คำนวณ `tau = kp(q_des − q) + kd(dq_des − dq)` เอง เทียบกับ `tau_est`
- ลอง kp 5 / 14.3 / 40 วัด rise time และ overshoot
- ต่อยอดจากสัปดาห์ 1: lock ใช้กัน LowCmd ถูกส่งตอนเขียนไปได้ครึ่งเดียว
- ⚠️ **sim เท่านั้น** ห้ามส่ง `rt/lowcmd` ไปหุ่นจริงจากแบบฝึกหัด
- คำถามทวน: kp กับ kd ต่างกันอย่างไร ทำไม kp สูงไปแล้วสั่น

## สัปดาห์ 3: FSM ⚪ (ร่าง, มี docs แล้ว)
**เป้าหมาย:** เข้าใจว่า controller จริงเปลี่ยนสถานะ (Passive → ยืน → เดิน) อย่างไร
- **docs:** `week3/docs/` (README = งาน 3.1–3.8: mini FSM ใน Python → build สำเนา g1_ctrl → `State_HoldPose`)
- เพิ่ม state `HoldPose` ใน g1_ctrl **สำเนาใน `~/g1_study/week3/deploy/`** (ไม่แก้ repo หลัก) ทดสอบใน sim
- อ่านประกอบ: vault `g1_ctrl FSM.md`, `Soft Start.md`, `FSM Code Walkthrough`

## สัปดาห์ 4: Policy ⚪ (ร่าง, มี docs แล้ว)
**เป้าหมาย:** สร้าง observation เองจาก LowState แล้วให้ policy คำนวณ action
- **docs:** `week4/docs/` (README = งาน 4.1–4.8: อ่าน contract → obs builder → shadow mode เทียบกับ g1_ctrl → ให้ Python คุมใน sim)
- โหลด `policy.onnx` ใน Python สร้าง observation เองจาก lowstate เทียบผลกับ g1_ctrl
- อ่านประกอบ: vault `Observations.md`, `Observation History.md`, `Action Scale.md`, `Deploy Contract.md`

## สัปดาห์ 5: เทรน ⚪ (ร่าง, มี docs แล้ว)
**เป้าหมาย:** เข้าใจว่า reward เปลี่ยนพฤติกรรมของ policy อย่างไร
- **docs:** `week5/docs/` (README = งาน 5.1–5.8: อ่าน reward → baseline → control vs ทดลอง (fine-tune P3b 300 iter, override ผ่าน CLI) → vel_eval)
- แก้ reward 1 ตัว เทรนสั้น ทายผลก่อน แล้วเทียบด้วย `vel_eval`

## สัปดาห์ 6: วิเคราะห์ข้อมูลจริง ⚪ (ร่าง, มี docs แล้ว)
**เป้าหมาย:** ใช้ log หุ่นจริงหาว่า sim กับหุ่นจริงต่างกันตรงไหน
- **docs:** `week6/docs/` (README = งาน 6.1–6.9: ตัดช่วง log → จับคู่เวลา → least squares + offset → delay → 3 ข้อต่อ → รายงาน + ทบทวนคอร์ส)
- เขียน `pd_check` แบบง่ายเองจาก log 3/11 (least squares + offset)
- อ่านประกอบ: vault `Armature and Gains.md`, `PD Control.md`

## โมดูล M: MuJoCo (เสริม ทำคู่กับสัปดาห์ไหนก็ได้) ⚪
**เป้าหมาย:** ใช้ GUI คล่อง · เขียน Python API เอง · แก้ MJCF เป็น (หุ่น G1 23-DoF ตัวเดิม ไม่มี DDS)
- **docs:** `weekM_mujoco/docs/` (README = งาน M0–M8 · `gui.md` ปุ่ม/แผง · `python_api.md` MjModel/MjData/qpos/sensor · `mjcf.md` โครง XML + MjSpec)
- **scripts:** `skelatons/` (g1mj_skeleton.py + เทสต์ 17 ข้อ, m1–m7) · `complete/` (เฉลย ทดสอบแล้ว)
- M3 + M4 = เขียน unitree_mujoco ส่วนที่ไม่ใช่ DDS เอง · M5 ไขปริศนาศอก +69.3° ของงาน 1.4 · M7 รัน policy v0 โดยไม่มี g1_ctrl
- ใช้ `python3` ของระบบ (ไม่ใช่ conda)

## โมดูล R: mjlab manager-based (เสริม ทำก่อน/คู่กับสัปดาห์ 5) ⚪
**เป้าหมาย:** อ่าน `env_cfgs.py` แล้วรู้ว่าแต่ละบรรทัดเปลี่ยนอะไรตอนเทรน · เขียน obs/reward/termination เอง · ประกอบ `train.py` เองได้
- **docs:** `weekR_mjlab/docs/` (README = งาน R0–R9 · `01` ภาพรวม/1 step · `02` config 3 ชั้น + registry + CLI · `03` manager ทีละตัว · `04` เขียน term · `05` runner/PPO/checkpoint/ONNX)
- **scripts:** `skelatons/` (rlib_skeleton.py + เทสต์ 18 ข้อ, r1–r8, my_terms) · `complete/` (เฉลย ทดสอบกับ env จริงบน GPU แล้ว)
- R3 ตามรอย `env.step()` จริง · R5 เพิ่ม term เอง + เห็นว่าทำไม resume พังเมื่อ actor obs เปลี่ยน · R7 obs ของ env vs `obs.py` week4 (phase ต่าง 1 step) · R8 เทรนจิ๋ว / resume P3b
- ใช้ `conda activate unitree_rl_mjlab` · ต้องมี GPU ว่าง (อย่ารันตอน session งานหลักเทรน)

## โมดูล I: Isaac Lab 3.0 + Newton (เสริม ทำหลังโมดูล R) ⚪
**เป้าหมาย:** ใช้ Newton เองได้ (Model/State/Control/Solver) · รู้ว่า Isaac Lab ต่อกับ Newton ยังไง (preset, NewtonManager, decimation ใน CUDA graph) · รัน cross-sim และเทรนบน Newton ได้
- **docs:** `weekI_isaaclab/docs/` (README = งาน N1–N5, I1–I6 + ผล + findings · `01` ภาพรวม/ชั้นซอฟต์แวร์ · `02` Newton ล้วน · `03` Isaac Lab บน Newton · `04` cross-sim + เทรน · `05` manager vs Direct)
- **scripts:** `skelatons/` (ilib_skeleton.py + เทสต์ 16 ข้อ, n1–n5, i1–i4 · สร้างจาก complete ด้วย `make_skeletons.py`) · `complete/` (เฉลย ทดสอบแล้วบน GPU)
- N3 Newton GPU vs MuJoCo C + implicit vs explicit PD · N4 พารามิเตอร์ solver · I2 ลำดับ joint PhysX (BFS) vs Newton (DFS) · I3 v0 เดินใน PhysX/Newton เทียบ MuJoCo
- I5 task manager-based ของเราเอง (obs ตรง deploy → P3b เดินจาก obs ของ env, term/class term/DR เอง) · I6 task เดียวกันแบบ Direct + เทียบทีละ term + เทรน/fine-tune P3b ด้วย rsl_rl
- ใช้ `source ~/g1_study/weekI_isaaclab/env.sh` (env_isaaclab: Isaac Sim 6.0, newton 1.2) · ห้าม `uv sync` · GPU ว่าง

---

## วิธีเรียน

**กติกา 5 ข้อ**
1. เขียนเองก่อนดูของที่มี ติดเกิน 20 นาทีค่อยขอคำใบ้
2. ทายก่อนรัน แล้วจดลง "บันทึกการทาย" ใน vault
3. จบแต่ละวัน สรุปด้วยคำของตัวเอง 3–5 บรรทัด
4. ทำให้พังแล้วซ่อม เปลี่ยนทีละอย่าง
5. ทวนคำถามของสัปดาห์ก่อนที่ +1, +3, +7 วัน

**คำสั่งที่ใช้กับ Claude**
| พิมพ์ | ได้อะไร |
|---|---|
| `ใบ้ 1` | ทิศทาง: ไปดูไฟล์ไหน แนวคิดอะไร |
| `ใบ้ 2` | ชื่อฟังก์ชัน / โครงสร้าง |
| `ใบ้ 3` | โค้ดบางส่วนให้ต่อเอง |
| `รีวิว <ไฟล์>` | ชี้จุดผิดพร้อมเหตุผล ไม่แก้ให้ |
| `เฉลย` | คำตอบเต็มพร้อม comment ละเอียด + คำถามเช็ค 2–3 ข้อ |

**ทางลัดเมื่อเวลาน้อย:** ขอ `เฉลย` อ่าน comment ให้เข้าใจ ตอบคำถามเช็ค แล้วลองเขียนใหม่จาก skeleton (`week1/read_lowstate_skeleton.py`) โดยไม่เปิดเฉลย

## แหล่งอ้างอิง
| อะไร | ที่ไหน |
|---|---|
| ตัวอย่าง SDK | `~/nvidia/unitree/unitree_sdk2_python/example/` (`helloworld/`, `g1/low_level/`) |
| นิยาม message | `unitree_sdk2py/idl/unitree_hg/msg/dds_/` (`_LowState_.py`, `_MotorState_.py`, `_IMUState_.py`, `_LowCmd_.py`) |
| โค้ดโปรเจกต์ ("เฉลยระดับโปร") | `~/nvidia/unitree/unitree_rl_mjlab/deploy/robots/g1_23dof/scripts/` |
| โน้ตแนวคิด | vault `01 Concepts/` (`DDS and Domains`, `LowState and LowCmd`, `Joint Map and Slots`, `PD Control`) |
| sim source | `~/nvidia/unitree/unitree_mujoco/simulate/src/` (`main.cc` ปุ่ม elastic band, `unitree_sdk2_bridge.h` อัตราส่ง) |

## ปุ่มใน sim
| ปุ่ม | ผล |
|---|---|
| `7` / `↑` | หดสายยาง หุ่นลอยขึ้น |
| `8` / `↓` | ปล่อยสายยาง หุ่นลงต่ำ |
| `9` | เปิด/ปิดสายยาง |
| `Backspace` | รีเซ็ตท่า |
| ดับเบิลคลิก + `Ctrl` + คลิกขวาลาก | ดึงชิ้นส่วนของหุ่น |
