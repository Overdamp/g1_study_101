# ONNX ใน Python

## ONNX คืออะไร
ไฟล์ที่เก็บ "กราฟการคำนวณ" ของ neural network แบบไม่ผูกกับ framework เทรนด้วย PyTorch แล้ว export เป็น `.onnx` จากนั้นรันได้ทั้ง C++ (g1_ctrl ใช้ `OrtRunner`) และ Python (`onnxruntime`) ได้ผลเหมือนกัน

ใน `policy.onnx` ของเรามี **normalizer + MLP** อยู่ในตัวแล้ว (vault `Deploy Contract.md`) ป้อน obs ดิบ (ที่คูณ scale ตาม deploy.yaml แล้ว) ได้เลย ไม่ต้อง normalize เอง

## env
`conda activate g1_sdk` มี `onnxruntime` 1.23.2 และ numpy อยู่แล้ว (ตรวจแล้ว 10/11)

## ข้อมูลของ v0 (ตรวจจากไฟล์จริง)
```
path:   ~/nvidia/unitree/unitree_rl_mjlab/deploy/robots/g1_23dof/config/policy/velocity/v0/exported/policy.onnx
input:  name = "obs",     shape = [1, 80],  type = float32
output: name = "actions", shape = [1, 23]
metadata (custom_metadata_map):
  joint_names, joint_stiffness, joint_damping, default_joint_pos,
  action_scale, observation_names, command_names, run_path
```
`observation_names` = `base_ang_vel, projected_gravity, command, phase, joint_pos, joint_vel, actions` (ชื่อฝั่งเทรน) ซึ่งตรงกับ term ใน deploy.yaml ตามลำดับ: `base_ang_vel, projected_gravity, velocity_commands, gait_phase, joint_pos_rel, joint_vel_rel, last_action`

## API ที่ต้องใช้ (ชื่อ ไม่ใช่เฉลย)
| ทำอะไร | API |
|---|---|
| เปิดไฟล์ | `onnxruntime.InferenceSession(path)` |
| ดู input/output | `session.get_inputs()`, `session.get_outputs()` แต่ละตัวมี `.name`, `.shape`, `.type` |
| ดู metadata | `session.get_modelmeta().custom_metadata_map` (dict: str → str คั่นด้วย `,`) |
| รัน | `session.run(None, {"obs": x})` คืน list ของ output |

## กับดักที่เจอบ่อย
| พลาด | อาการ |
|---|---|
| ป้อน `float64` (ค่าเริ่มต้นของ numpy) | error ว่า type ไม่ตรง ต้องใช้ `np.float32` |
| ป้อน shape `(80,)` | error ว่า rank ไม่ตรง ต้องใช้ `(1, 80)` |
| ลืม `[0]` ตอนดึง output | ได้ list ของ array แทน array |
| metadata เป็น string | ต้อง `split(",")` แล้วแปลงเป็น float เอง |
| เปิด session ทุก step | ช้ามาก ให้เปิดครั้งเดียวตอนเริ่มโปรแกรม |

## ทดลองก่อนเขียนจริง (ใน `python`)
1. obs เป็น 0 ทั้งหมด → action เป็นเท่าไหร่ (ทายก่อน: 0 ไหม? ทำไม)
2. เรียก 2 ครั้งด้วย obs เดิม → ได้ค่าเดิมไหม (policy เป็น deterministic ไหม)
3. เปลี่ยน obs แค่ตัวเดียว (เช่น `projected_gravity` x จาก 0 เป็น 0.1) → action ตัวไหนเปลี่ยนมากที่สุด

## งาน 4.1: ตารางเทียบ (เติมเอง)
| field | deploy.yaml | ONNX metadata | ตรงไหม | ถ้าไม่ตรง ใครถูก / มีผลไหม |
|---|---|---|---|---|
| ชื่อ/ลำดับข้อต่อ | (ดูจาก `joint_ids_map` + `Joint Map and Slots.md`) | `joint_names` | | |
| stiffness | | `joint_stiffness` | | |
| damping | | `joint_damping` | | |
| default pose | `default_joint_pos` / `actions.offset` | `default_joint_pos` | | |
| action scale | `actions.JointPositionAction.scale` | `action_scale` | | |
| ลำดับ obs | `observations` (ลำดับ key) | `observation_names` | | |
| ขนาด obs | รวมมิติเอง | input shape | | |

ใบ้: ลองคำนวณเป็น % ว่าแต่ละคู่ต่างกันเท่าไหร่ แล้วดูว่า repo มีเครื่องมือตรวจ (`scripts/gain_check.py`) ที่ใช้ tolerance เท่าไหร่
