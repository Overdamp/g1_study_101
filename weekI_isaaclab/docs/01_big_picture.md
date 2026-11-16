# 01: ภาพรวม: Isaac Lab 3.0, PhysX, Newton, MuJoCo Warp อยู่ตรงไหน

## 1. ชั้นของซอฟต์แวร์ (ล่างขึ้นบน)
```
             ┌──────────── งานของเรา: task G1 23-DoF (unitree_rl_lab) ────────────┐
             │  ManagerBasedRLEnvCfg: scene, obs, actions, rewards, events ...   │   ← หน้าตาเหมือน mjlab มาก
             └───────────────────────────────┬────────────────────────────────────┘
 Isaac Lab   isaaclab (core: managers, assets, sensors, envs)                        ← ไม่ผูกกับ engine
             ├── isaaclab_physx   → PhysxManager  → PhysX 5 (Isaac Sim / Omniverse, GPU)
             └── isaaclab_newton  → NewtonManager → Newton
                                                    ├── SolverMuJoCo  → MuJoCo Warp (GPU)   ← ที่เราใช้
                                                    ├── SolverXPBD, SolverFeatherstone, SolverKamino ...
 Kit/USD     Isaac Sim: USD stage, GUI, RTX render (PhysX ต้องใช้ · Newton ใช้แค่อ่าน USD + ภาพ)
```
- **Newton** = physics library โอเพนซอร์ส (NVIDIA + Google DeepMind + Disney) เขียนด้วย **Warp** (Python → CUDA kernel)
  มี "solver" หลายตัวให้เลือก แต่ใช้ Model/State/Control เดียวกัน
- **SolverMuJoCo** = แปลง Model ของ Newton เป็นโมเดลของ **MuJoCo Warp** (MuJoCo เวอร์ชัน GPU ของ DeepMind) แล้วให้มันคำนวณ
  → ฟิสิกส์ "แบบ MuJoCo" ทุกอย่าง (contact soft, implicitfast, armature) แต่ข้อมูลอยู่ในรูป Newton
- **mjlab** (ที่เราเทรน P3b) ก็ใช้ MuJoCo Warp เหมือนกัน แต่เรียกตรงๆ ไม่ผ่าน Newton

## 2. ทางเดินของ 1 physics step: 3 stack ที่เราเจอ
```
mjlab:              MJCF ──mujoco.MjSpec──▶ mjw_model ──mjwarp.step──▶ qpos/qvel
Isaac Lab + Newton: USD ──add_usd──▶ Newton Model ──SolverMuJoCo──▶ mjw_model ──mjwarp.step──▶ Newton State
Isaac Lab + PhysX:  USD ──Kit/PhysX parser──▶ PhysX articulation (TGS solver) ──▶ tensor view
unitree_mujoco:     MJCF ──MuJoCo C (CPU, float64)──▶ mj_step  + PD คิดเองใน bridge (explicit)
```
**สิ่งที่ต่างจริง** ระหว่าง mjlab กับ Isaac/Newton ไม่ใช่คณิตของ solver (ตัวเดียวกัน) แต่คือ **โมเดลที่ป้อน**:
| | mjlab | Isaac Lab + Newton |
|---|---|---|
| ไฟล์หุ่น | `g1_23dof.xml` (MJCF) | `g1_23dof_rev_1_0.usd` (USD ของ Unitree) |
| geom ที่ใช้ชน (I2/N1) | capsule 29 + sphere 2 | convex mesh 20 + cylinder 4 + sphere 8 |
| ลำดับ joint | DFS ของ XML | DFS ของ USD → **ตรงกับ policy** (PhysX = BFS ไม่ตรง) |
| gain / armature | สูตร `J·ω²` ใน Python | สูตรเดียวกัน (task 23dof `.replace()`) |
| solver option | ของ mjlab | `PhysicsCfg.newton` ของ task (njmax 95, ls 15, implicitfast) |

## 3. ทำไมเราสนใจ Newton
1. **cross-sim**: เอา policy จาก mjlab ไปเดินใน engine อื่น ถ้าผลใกล้กัน = policy ไม่ได้ "โกง" ฟิสิกส์ของ MuJoCo (I3)
2. **ความเร็ว**: Newton ที่ 512 env เร็วกว่า PhysX ~43% ใน env เดียวกัน (I2) และเทรนเร็วกว่า ~40% (I4)
3. **อ่านโค้ดได้**: Newton + MuJoCo Warp เป็น Python/Warp ทั้งหมด เปิดดูได้ทุกบรรทัด (PhysX เป็น binary)
4. **Isaac Lab 3.0** ทำให้ Newton เป็น backend ทางการ สลับด้วย `presets=newton` คำเดียว (I1)

## 4. ข้อจำกัดที่เจอแล้ว (env_isaaclab: Isaac Sim 6.0 + newton 1.2)
| เรื่อง | สถานะ |
|---|---|
| terrain generator (ขั้นบันได, rough) | Newton ยังไม่รองรับ → task Rough โยน ValueError ใช้ได้แค่ `-Flat` (`validate_config` ใน 29dof cfg) |
| สุ่ม friction | Newton ใช้ค่า `mu` เดียว (ไม่มี static/dynamic แยก) → event `newton_randomize_rigid_body_material` |
| Kit GUI / อัดวิดีโอ | พังบน Isaac Sim 6.0 → ดูด้วย `--visualizer newton` (viewer ของ Newton เอง) |
| `uv sync` ใน env_isaaclab | ทำ isaacsim หาย → ติดตั้งเพิ่มด้วย `uv pip install --no-deps` เท่านั้น |

## 5. env ที่ใช้ในโมดูลนี้
`~/nvidia/IsaacLab-unitree/env_isaaclab` (uv venv) ← session งานหลักทำ cross-sim ไว้แล้วและทดสอบว่าใช้ได้
| ของ | รุ่น |
|---|---|
| Isaac Lab | 3.0 (worktree `IsaacLab-unitree`, commit 207f319d9) |
| Isaac Sim | 6.0.0 |
| newton / warp / mujoco | 1.2.0 / 1.13 / 3.8.1 |
| torch | 2.10 cu128 |
`~/nvidia/IsaacLab/.venv` (Isaac Lab 3.0 มาตรฐาน, Isaac Sim 6.2, newton 1.6.1) มีอีกตัวแต่ **unitree_rl_lab ไม่ได้ติดตั้งในนั้น** → ไม่ใช้

## คำถามเช็ค
1. SolverMuJoCo ของ Newton กับ mjlab ใช้ "เครื่องคิดเลข" ตัวเดียวกันไหม · แล้วทำไมผล cross-sim Newton กับ MuJoCo ยังต่างกันได้ ~5 pp
2. ถ้าจะเทรน Rough (ขั้นบันได) ใน Isaac Lab ต้องใช้ backend ไหน
3. deploy (g1_ctrl) ต้องรู้ไหมว่า policy ถูกเทรนด้วย engine อะไร · ต้องรู้อะไรแทน
