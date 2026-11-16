# เทรน: คำสั่งและขั้นตอน (fine-tune จาก P3b)

## หลักการ
- **ไม่แก้โค้ด**: `train.py` ใช้ tyro ทุก field ของ config override จาก command line ได้ เช่น `--env.rewards.action-rate-l2.weight -0.2`
- **log ไม่ลง repo หลัก**: `train.py` เขียน log ไปที่ `logs/rsl_rl/<experiment>/<เวลา>/` **นับจาก current directory** (`scripts/train.py` บรรทัด 149) ถ้ารันจาก `~/g1_study/week5` log จะลงที่ `~/g1_study/week5/logs/`
- **resume จาก P3b**: ต้องมี checkpoint อยู่ใน `logs/rsl_rl/g1_23dof_velocity/<ชื่อ run>/`

## 0. env
```bash
use_conda                      # ถ้าหา conda ไม่เจอ
conda activate unitree_rl_mjlab     # ไม่ใช่ g1_sdk (ดู vault Environments Map.md)
```
conda env นี้ติดตั้ง repo แบบ editable อยู่แล้ว `import src` จึงใช้โค้ดของ `~/nvidia/unitree/unitree_rl_mjlab` (ไม่ต้องตั้ง PYTHONPATH เพราะเราไม่ได้แก้โค้ด)

## 1. เตรียมโฟลเดอร์ + checkpoint P3b (ครั้งเดียว)
```bash
mkdir -p ~/g1_study/week5/logs/rsl_rl/g1_23dof_velocity/p3b_seed
cp ~/nvidia/unitree/unitree_rl_mjlab/logs/rsl_rl/g1_23dof_velocity/phase3b_seed/model_15998.pt \
   ~/g1_study/week5/logs/rsl_rl/g1_23dof_velocity/p3b_seed/          # 4.9 MB
```
(repo หลักทำ `phase3b_seed/` ไว้แบบเดียวกันอยู่แล้ว เราก็อปมาใช้ ไม่ได้แก้ของเดิม)

## 2. ทดสอบว่ารันได้ (5 iteration)
```bash
cd ~/g1_study/week5
REPO=~/nvidia/unitree/unitree_rl_mjlab
python $REPO/scripts/train.py Unitree-G1-23Dof-Flat \
  --env.scene.num-envs=1024 \
  --agent.resume=True --agent.load-run=p3b_seed --agent.load-checkpoint=model_15998.pt \
  --agent.max-iterations=5 \
  --agent.logger=tensorboard \
  --agent.run-name=smoke
```
เช็ค:
- log ใหม่อยู่ใต้ `~/g1_study/week5/logs/rsl_rl/g1_23dof_velocity/` (ไม่ใช่ใน repo หลัก)
- มี `[INFO] Training with: device=cuda:0`
- จด**เวลาต่อ iteration** ไว้ใช้ประมาณ run จริง (อ้างอิง: P3b บนเครื่องนี้ ~1.2 s/iter)
- ถ้า GPU memory ไม่พอ: ลด `--env.scene.num-envs=512` (แต่ต้องใช้ค่าเดียวกันทั้ง control และทดลอง)

option ที่ใช้ทั้งหมด (`--agent.resume`, `load-run`, `load-checkpoint`, `max-iterations`, `run-name`, `seed`, `logger`) ตรวจกับ `--help` แล้ว (10/11)

## 3. run ควบคุม (5.4)
คำสั่งเดียวกับข้อ 2 แต่ `--agent.max-iterations=300` (~6 นาที) และไม่เปลี่ยน reward

## 4. run ทดลอง (5.5)
คำสั่งเดียวกับข้อ 3 **เป๊ะ** เพิ่ม override แค่ 1 ตัว เช่น
```bash
  --env.rewards.action-rate-l2.weight=-0.2
```
**ทุกอย่างอื่นต้องเท่ากัน:** num-envs, iterations, checkpoint เริ่มต้น, seed (ค่าเริ่มต้น 42)

## 5. ตรวจว่า config ต่างกันแค่ที่ตั้งใจ
แต่ละ run จะ dump config ไว้ที่ `<run>/params/env.yaml` และ `agent.yaml`
```bash
diff <control>/params/env.yaml <ทดลอง>/params/env.yaml          # ควรต่างกันแค่ weight ที่เปลี่ยน
diff <control>/params/env.yaml ~/nvidia/unitree/unitree_rl_mjlab/logs/rsl_rl/g1_23dof_velocity/2026-10-22_17-02-19/params/env.yaml
#     ↑ เทียบกับ run P3b จริง: config ปัจจุบันของ branch ยังเหมือนตอนเทรน P3b ไหม
```
ถ้ามีจุดต่างที่ไม่ได้ตั้งใจ ให้บันทึกไว้ อาจอธิบายผลที่แปลกได้

## 6. ผลลัพธ์อยู่ไหน
```
~/g1_study/week5/logs/rsl_rl/g1_23dof_velocity/<เวลา>/
├── model_16000.pt, model_16100.pt, ...    ← checkpoint ทุก 100 iter (เลขต่อจาก 15998)
├── policy.onnx                             ← export ทุกครั้งที่ save (ตัวล่าสุด) + metadata
├── params/env.yaml, agent.yaml
└── events.out.tfevents.*                   ← TensorBoard
```
`policy.onnx` อยู่ที่ราก run (`VelocityOnPolicyRunner.save` ใน `src/tasks/velocity/rl/runner.py`)
**`deploy.yaml` ไม่ถูกสร้างอัตโนมัติ** แต่เพราะเราเปลี่ยนแค่ reward (obs/action/gain/default pose เท่าเดิม) จึงใช้ `v0/params/deploy.yaml` ของ P3b ได้ ต้องยืนยันด้วย `gain_check` ก่อน (`evaluation.md`)

## 7. หลังทำเสร็จ
- ลบ run ที่ไม่ใช้ (ดิสก์เหลือน้อย) เก็บไว้แค่ `policy.onnx` + `params/` + tfevents ก็พอ
- จดในบันทึกการทดลอง (README) ว่าใช้คำสั่งอะไร เวลาเท่าไหร่

## แก้ปัญหา
| อาการ | สาเหตุ / ทางแก้ |
|---|---|
| `ModuleNotFoundError: mjlab` | ใช้ env ผิด ต้อง `unitree_rl_mjlab` |
| หา checkpoint ไม่เจอ | ไม่ได้รันจาก `~/g1_study/week5` หรือชื่อ `load-run` ไม่ตรงกับชื่อโฟลเดอร์ |
| `CUDA out of memory` | ปิด sim/g1_ctrl/เบราว์เซอร์ที่ใช้ GPU หรือลด num-envs (ทั้งสอง run) |
| ไม่มี `device=cuda` | `CUDA_VISIBLE_DEVICES` ว่าง (train.py ใช้ CPU ถ้าตัวแปรนี้ว่าง) ลอง `CUDA_VISIBLE_DEVICES=0 python ...` |
| จอค้างตอนจบ | vault `Training Practice.md`: ถ้ามี `model_<last>.pt` + `policy.onnx` เวลาตรงกัน กด Ctrl-C ได้ |
| ชื่อ override ผิด | tyro จะ error พร้อมเสนอชื่อที่ใกล้เคียง ใช้ `-` ไม่ใช่ `_` ในชื่อ term |
