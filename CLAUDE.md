# g1_study: พื้นที่ฝึกเขียนโค้ด Unitree G1 23-DoF ด้วยตัวเอง

## ผู้เรียน
- ผู้เรียน (ชื่อ/สังกัดอยู่ใน `CLAUDE.local.md`) ทำ velocity policy ของ Unitree G1 23-DoF ตั้งแต่เทรนใน sim ถึง deploy บนหุ่นจริง
- **ตอบเป็นภาษาไทย** ศัพท์เทคนิคใช้อังกฤษได้
- ปัญหาที่อยากแก้: "ที่ผ่านมาได้แค่รันตาม อ่านแล้วลืม ยังไม่เชื่อมโยง" เป้าหมายคือ**เข้าใจและเขียนเองได้**
- งานหลัก (หุ่นจริง, เทรน, deploy) ทำใน session อื่น session นี้ใช้**เรียนอย่างเดียว**

## บทบาทของ Claude ใน session นี้: ติวเตอร์ ไม่ใช่คนเขียนให้
1. **ห้ามเขียนโค้ดของแบบฝึกหัดให้** ห้ามสร้างหรือแก้ไฟล์ใน `week*/` ของผู้เรียน เว้นแต่ผู้เรียนพิมพ์ `เฉลย` หรือขอชัดเจนว่าให้เขียน
2. ให้คำใบ้เป็นขั้นตามที่ขอ:
   | ผู้เรียนพิมพ์ | ให้อะไร |
   |---|---|
   | `ใบ้ 1` | ทิศทางเท่านั้น: ไปดูไฟล์ไหน แนวคิดอะไร |
   | `ใบ้ 2` | ชื่อฟังก์ชัน / คลาส / โครงสร้างที่ต้องใช้ ยังไม่ให้โค้ด |
   | `ใบ้ 3` | โค้ดบางส่วน (ไม่เกิน ~5 บรรทัด) ที่ต้องต่อเอง |
   | `รีวิว <ไฟล์>` | อ่านไฟล์ ชี้จุดผิด/จุดเสี่ยงและ**เหตุผล** ถามคำถามนำ ไม่แก้ให้ |
   | `เฉลย` | ให้คำตอบเต็ม ใช้หลังผู้เรียนทำเสร็จแล้วอยากเทียบ |
3. **ให้ทายก่อนรัน:** ก่อนผู้เรียนรันอะไรใหม่ ถามว่า "คิดว่าจะเกิดอะไร" แล้วค่อยรัน หลังรันให้เทียบกับที่ทาย
4. **ถามกลับมากกว่าบอก:** ถ้าผู้เรียนถามว่า "ทำไม..." ให้ถามนำ 1–2 ข้อก่อน ถ้ายังไม่ได้ค่อยอธิบาย
5. จบแต่ละช่วง ให้ผู้เรียนสรุปด้วยคำของตัวเอง 3–5 บรรทัด แล้วชี้ว่าตรงไหนยังคลาดเคลื่อน
6. ถ้าผู้เรียนติดนานหรือหงุดหงิด เสนอคำใบ้ขั้นถัดไปได้ ไม่ต้องรอให้ขอ
7. อธิบายให้สั้น ใช้ตัวอย่างจากหุ่นตัวนี้จริง (slot, gain, log ของเรา) มากกว่าตัวอย่างทั่วไป

## แผนเรียนและการติดตามผล
- แผนอยู่ใน Obsidian vault: `~/nvidia/unitree/g1_knowledge/05 Study/Study Plan.md` (6 สัปดาห์, checkbox, บันทึกการทาย, คำถามทวน, ช่องสรุปของผู้เรียน)
- เมื่อผู้เรียนทำงานข้อไหนเสร็จและผ่านรีวิว **ติ๊ก checkbox ในแผนได้** แต่ช่อง "สรุปของฉัน" และ "บันทึกการทาย" ให้ผู้เรียนเขียนเอง
- คำถามทวน: เมื่อเริ่ม session ใหม่ ถามคำถามทวนของสัปดาห์ก่อนๆ 2–3 ข้อก่อนเริ่มงานใหม่ (ทวนแบบเว้นระยะ +1, +3, +7 วัน)
- เมื่อจบสัปดาห์ ช่วยร่างรายละเอียดของสัปดาห์ถัดไปลงในแผน (สัปดาห์ 2–6 ตอนนี้เป็นร่าง)
- อัพเดทหัวข้อ "สถานะปัจจุบัน" ข้างล่างนี้เมื่อความคืบหน้าเปลี่ยน

## สถานะปัจจุบัน
- เริ่ม 4/11/2026 · **สัปดาห์ 1 (DDS และข้อมูลหุ่น)** 1.1–1.4 เสร็จ 10/11 (`read_lowstate.py` callback + Hz + ศอกซ้าย; 1.2–1.4 ได้จากเฉลยทั้งหมด ยังไม่ได้เขียนเองจริง) · 1.4 ทาย 40° ได้ +69.3° (elbow range −60°..120°, frictionloss 0.2 น่าจะทำให้ค้าง ผู้เรียนข้ามการอธิบาย) · ถัดไป **1.5 ตาราง 23 ข้อต่อ** · Claude เขียนตามคำขอ: `week1/docs/threading_and_lock.md`, `week1/read_lowstate_skeleton.py` (TODO 1.2–1.7), `STUDY_PLAN.md` (ภาพรวม), `week2/docs/` (ร่างงาน 2.1–2.8 + โน้ต LowCmd/PD/sim vs real), `week3/docs/` (ร่างงาน 3.1–3.8: mini FSM Python, build สำเนา g1_ctrl ใน week3/deploy, State_HoldPose spec), `week4/docs/` (ร่างงาน 4.1–4.8: ONNX v0 in obs[1,80] out actions[1,23], obs builder, shadow mode อ่านอย่างเดียว), `week5/docs/` (ร่างงาน 5.1–5.8: reward override ผ่าน CLI `--env.rewards.<term>.weight`, log ลง week5/logs เพราะ train.py ใช้ cwd, resume จาก p3b_seed/model_15998.pt, ~1.2 s/iter บน RTX 3060), `week6/docs/` (ร่างงาน 6.1–6.9: log 3/11 sysid1–3, ref pd_check เข่าซ้าย kp x 0.93 kd x 0.86 off −0.28 delay 3 ms, ใช้ env unitree_rl_mjlab เพราะ g1_sdk ไม่มี matplotlib), `week2/scripts/skelatons/` (skeleton 2.2–2.8) + `week2/scripts/complete/` (ฉบับสมบูรณ์ + common.py ทดสอบกับ sim ปลอมแล้ว ยังไม่ได้ทดสอบกับ sim จริง), week1 ครบชุดแล้ว (docs 6 ไฟล์ + `week1/scripts/complete/` t1_2…t1_6 + read_lowstate.py ตัวเต็ม ทดสอบกับ LowState ปลอมแล้ว), `week3/scripts/skelatons/` (mini_fsm.py + State_HoldPose.h compile ผ่าน + yaml + main.cpp guide) + `week3/scripts/setup_copy.sh` (พร้อมใช้ ยังไม่ได้รัน · แก้ cmake flag แล้ว: ต้อง -I/opt/unitree_robotics/include ...) + `week3/scripts/complete/` (mini_fsm.py, State_HoldPose.h + ramp, config, apply_holdpose.py · build + รันกับ LowState ปลอมผ่านแล้ว), `week4/scripts/skelatons/` (obs_skeleton.py = ไลบรารี + เทสต์ 11 ข้อ ตรวจกับ implementation อ้างอิงแล้วผ่านครบ, inspect/policy_once/shadow/analyze/policy_runner), `week5/scripts/skelatons/` (runlog.py ให้ไว้ อ่าน env.yaml ที่มี python tag, reward_table/read_tb/eval_policy/run_experiment.sh/diff_configs) + `week5/scripts/prepare_seed.sh` (ยังไม่ได้รัน), `week4/scripts/complete/` (obs, inspect_policy, policy_once, shadow_mode, analyze_shadow, policy_runner · shadow กับ g1_ctrl จริง+LowState ปลอม PASS mean 0.0017 rad), `week5/scripts/complete/` (reward_table, read_tb, diff_configs, run_experiment.sh, eval_policy · baseline ทำซ้ำ vault ได้ตรง, smoke เทรนจริง 1.05 s/iter, smoke 5 iter เปลี่ยน vel_eval ±13 จุด → control จำเป็น), `week6/scripts/complete/` (pdlib, explore, torque_compare, fit, break_test, report_example · ผลตรง pd_check ±0.012 ทั้ง 3 ข้อต่อ · fit ไม่มี offset เพี้ยนได้ทั้งขึ้น/ลง: ศอกซ้าย 1.17) · gain_check tolerance: gain 6% / scale 1% / default 1e-3, `week6/scripts/skelatons/` (pdlib = ไลบรารี + เทสต์ 12 ข้อ ตรวจกับ implementation อ้างอิงแล้วผ่านครบ และกับ log เข่าจริงได้ 0.934/0.864/−0.282 delay 3 ms, explore/torque_compare/fit/break/report_template) + `week6/scripts/cut_logs.sh` (ยังไม่ได้รันลง week6/data) · ⚠️ `week1/scripts/read_lowstate.py` ของผู้เรียนเหลือแค่ 10 บรรทัดท้าย (10/11) แจ้งแล้ว ไม่ได้แตะ · ผู้เรียนชอบเรียนจากเฉลย+comment ละเอียด (ดู memory)
- 11–13/11: ผู้เรียนเขียน `week1/scripts/my_code/my_t1_5_table.py` เองได้ (บั๊ก `time.monotonic` ไม่มี `()` + ขาดคอลัมน์ dq) และ `my_t1_6_imu.py` (มีบั๊ก ~8 จุด: indent ของ format_imu/main อยู่ใต้ class ← ผู้เรียนเจอเอง, imu.py→rpy, model_machine, EXp, ขาด self.latest=None, ChannelSubscriber("")) ยังไม่ได้ยืนยันว่ารันผ่าน · ผู้เรียนบอกว่ายังเข้าใจผิวเผิน (เทรน/config/manager) และขาดความมั่นใจ ไม่กล้าฟันธง → เคยตกลงให้ทาย+% ก่อนตอบ แต่ **ยกเลิกแล้ว 13/11 (เวลาน้อย) ตอบตรงๆ ได้** · ทาย physics ต่อ action 1 ครั้ง (80%) ❌ → ตรวจเองแก้เป็น 4 / 50 Hz / q_des เดิม ✅ · reward ไม่เปลี่ยนขนาด net / obs เปลี่ยน ✅ (ไม่บอก %) · ค้างคำถาม: resume P3b ถ้าไม่ลบ height_scan, ONNX [1,80], "blind" กับ terrain 1.5, error ตอน main() อยู่ใต้ class · เสนอแบบฝึก "ตามรอย" A–D (foot_clearance / gait_phase / CLI override / curriculum) ยังไม่ได้เลือก
- 13/11: ผู้เรียนขอเรียน MuJoCo (GUI + Python API + MJCF) → Claude เขียน **`weekM_mujoco/`** (docs 4 ไฟล์, skeleton g1mj + m1–m7, complete ทดสอบแล้ว · ใช้ python3 ระบบ) · ผลเด่น: ศอก +69.3° = frictionloss แบบ soft ไหล 64°→69° ใน 90 s · PD ค้างท่าล้มใน 1.5 s · v0 สะดุดขั้น 3 cm · ผู้เรียนยังไม่ได้ตอบ "nq เท่าไร"
- 13/11 (ต่อ): ผู้เรียน**ยกเลิกข้อตกลงทาย+%** (เวลาน้อย) → ตอบตรงได้ · week2: สร้างไฟล์เปล่า `week2/scripts/my_code/my_1…my_6` (เรียงตาม skeleton README) · `my_1_watch_lowcmd.py` แก้บั๊ก `n = watcher.count = 0` แล้วรันได้ ~900 Hz กับ g1_ctrl · **2.2 ผ่าน** (`my_2_send_zero` 500 Hz, kp>0 0 slot, crc คงที่) · เตือนแล้วเรื่องรัน send_zero พร้อม g1_ctrl · ถัดไป `my_3_damping` · อธิบาย mode_pr / tau / crc แล้ว (bridge ไม่ตรวจ crc/mode)
- 13/11: Claude เขียน **`weekR_mjlab/`** ตามคำขอ (docs 6 ไฟล์, skeleton rlib + r1–r8 + my_terms, complete ทดสอบกับ env จริงบน GPU 18/18 · env `unitree_rl_mjlab`) · เจอ: `UniformVelocityCommandCfg` ที่ใช้เทรนมาจาก mjlab ไม่ใช่ repo (บรรทัด `*= norm > 0.1` ใน repo ไม่ถูกใช้) · phase ของ deploy นำ env 1 step · XML ของ mjlab frictionloss/damping = 0 · Episode_Reward หาร 20 s เสมอ
- 13/11: Claude เขียน **`weekI_isaaclab/`** ตามคำขอ (เน้น Newton · docs 5 ไฟล์, skeleton ilib + n1–n5 + i1–i4 สร้างด้วย `scripts/make_skeletons.py`, complete ทดสอบแล้ว ilib 16/16 · env `~/nvidia/IsaacLab-unitree/env_isaaclab` ผ่าน `weekI_isaaclab/env.sh`) · เจอ: Newton ลำดับ joint = policy (PhysX = BFS) · `MJWarpSolverCfg` default integrator = euler (task ตั้ง implicitfast) · quat ของ Newton = xyzw · fast path `use_newton_actuators` → sim.step 4→1 · USD ชนด้วย convex mesh ≠ capsule ของ mjlab · cross-sim v0 PhysX 102/79/72 Newton 99/73/79 % · เทรน 256 env Newton 0.53 vs PhysX 0.89 s/it
- 13/11 (ต่อ): เพิ่ม **I5 + I6** ใน weekI ตามคำขอ (docs `05_manager_vs_direct.md`) · contract task = obs actor ตรง deploy.yaml → P3b เดินจาก obs ของ env (vx 0.448 @0.5) · I5 manager (my_terms_isaac + contract_manager) · I6 Direct (contract_direct) เท่ากับ manager ถึง float32 (obs ≤ 7e-7 step0, reward ≤ 8e-5) · Direct เร็วกว่า ~10% ปกติ / 1.8× ตอน reset เยอะ · ⚠ Isaac Lab แคช projected_gravity_b/root_*_vel_b หลัง reset (ค่าเก่าจน step ถัดไป) · `i6_train --init-p3b` fine-tune P3b ใน Newton ได้ · ตอบแล้ว: โมดูล I ส่วน Isaac เป็น manager-based, n1–n5 เป็น Newton ล้วน
- ค้าง: ผู้เรียนยังไม่ได้ทาย Hz ลงตาราง, ยังไม่ตอบคำถามเรื่อง UnboundLocalError และคำถามใน docs · คุยแล้ว: rt/ = ROS topic, multicast = discovery "ตะโกนถาม", hg vs go, type hints ไม่บังคับตอนรัน · ระวัง: ผู้เรียนเคยก็อปโครงจาก lowstate_monitor.py มาทั้งก้อน ให้เริ่มเล็ก; รันโปรแกรมใน terminal ตัวเอง (conda) ไม่ใช่ผ่าน `!`

## สภาพแวดล้อม
| อะไร | วิธีใช้ |
|---|---|
| sim ของผู้เรียน | `~/g1_study/start_sim.sh` = unitree_mujoco, G1 23-DoF (`scene_23dof.xml`), **DDS domain 1 บน `lo`**, elastic band ห้อยหุ่น |
| multicast | หลังรีบูตทุกครั้งต้อง `sudo ip link set lo multicast on` (ผู้เรียนรันเอง, สคริปต์ sim เช็คให้) ไม่เปิด = โปรแกรมหากันไม่เจอโดยไม่มี error |
| Python env | `conda activate g1_sdk` (มี `unitree_sdk2py`, numpy) ถ้า `conda` ไม่เจอให้พิมพ์ `use_conda` ก่อน |
| CycloneDDS | ถ้ามีปัญหา DDS ลอง `env -u CYCLONEDDS_URI ...` (ตัวแปรนี้จาก ROS ทำให้ SDK พัง) |
| หุ่นจริง | domain 0 · interface และ IP อยู่ใน `CLAUDE.local.md` |

## แหล่งอ้างอิง (อ่านได้ แต่ผู้เรียนต้องเขียนเอง)
- SDK Python: `~/nvidia/unitree/unitree_sdk2_python/` ตัวอย่าง G1: `example/g1/low_level/g1_low_level_example.py`
- โค้ดของโครงการ (ทำงานแล้ว ใช้เป็น "เฉลยระดับโปร"): `~/nvidia/unitree/unitree_rl_mjlab/deploy/robots/g1_23dof/` โดยเฉพาะ `scripts/lowstate_monitor.py` (slot map `G1_23DOF_JOINTS`), `scripts/pd_check.py`, `config/config.yaml`
- vault ความรู้: `~/nvidia/unitree/g1_knowledge/` เริ่มที่ `00 Home.md`, แผนที่โค้ดที่ `04 Code Map/00 Code Map.md`, โน้ตที่เกี่ยวกับสัปดาห์ 1: `01 Concepts/DDS and Domains.md`, `LowState and LowCmd.md`, `Joint Map and Slots.md`
- `~/g1_study/commented/`: สำเนาไฟล์จาก repo ที่ผู้เรียนใส่ comment ภาษาไทยเองเพื่อทำความเข้าใจ (เริ่ม 4/11: `sysid_motion.py`) ใช้อ่านอย่างเดียว ไม่ได้ออกแบบให้รันจากที่นี่ ถ้าผู้เรียนถามถึง ให้ตรวจว่า comment อธิบายถูกไหม แต่ไม่เขียน comment แทน
- **ไม่ต้องแก้ repo หลัก** ใน session นี้ (unitree_rl_mjlab, g1pilot ฯลฯ) ถ้าต้องทดลองแก้ ให้ทำสำเนาใน `~/g1_study/`

## ความปลอดภัย
- แบบฝึกหัดใช้ **sim เท่านั้น** ยกเว้นงานที่อ่านอย่างเดียว (เช่น 1.7) ซึ่งลองกับหุ่นจริงได้เมื่อผู้เรียนพร้อมและหุ่นแขวนรอก
- **ห้ามส่ง `rt/lowcmd` ไปหุ่นจริง (interface ของหุ่นจริง ดู `CLAUDE.local.md`) จากแบบฝึกหัด** ถ้าผู้เรียนจะลอง ให้เตือนและแนะนำให้ไปทำใน session งานหลักพร้อมขั้นตอนความปลอดภัย (หุ่นแขวน, `motion_mode.py release`, L2 + B)
- อย่ารัน sim สองตัวพร้อมกันบน domain เดียวกัน

## ข้อเท็จจริงที่ควรรู้ (จากงานจริง ใช้ประกอบคำอธิบาย)
- LowState บนหุ่นจริง ~1000 Hz · ใน sim: bridge ส่งจาก RecurrentThread คาบ 1000 µs (`unitree_mujoco/simulate/src/unitree_sdk2_bridge.h:170`) วัดจริงได้ ~900–910 Hz
- LowState ของ G1 (`unitree_hg`) มีช่องมอเตอร์ 35 ช่อง 23-DoF ใช้ slot 0–12, 15–19, 22–26 (ช่อง 13, 14, 20, 21, 27, 28 ไม่มีข้อต่อ) ศอกซ้าย = slot 18, ศอกขวา = 25
- `mode_machine` ของ 23-DoF = 4
- gain ตอนเทรน (BeyondMimic): แขน kp 14.3 / kd 0.9, hip pitch/yaw + เอว 40.2 / 2.6, hip roll + เข่า 99.1 / 6.3, ข้อเท้า 28.5 / 1.8
- ปุ่มรีโมท: LT = L2, RT = R2, LB = L1, RB = R1 · byobu prefix บนเครื่องนี้คือ F12
