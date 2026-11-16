# วัดผล policy: `gain_check` + `vel_eval`

## 1. `gain_check.py`: ใช้ deploy.yaml ของ v0 กับ policy ใหม่ได้ไหม
```bash
conda activate g1_sdk
S=~/nvidia/unitree/unitree_rl_mjlab/deploy/robots/g1_23dof/scripts
```
`gain_check.py` รับ**โฟลเดอร์ policy** (`exported/policy.onnx` + `params/deploy.yaml`) จึงต้องจัดโฟลเดอร์ใน week5 ให้มีโครงเดียวกัน:
```bash
P=~/g1_study/week5/policies/exp_a           # ตั้งชื่อเอง
mkdir -p $P/exported $P/params
cp <run>/policy.onnx $P/exported/
cp ~/nvidia/unitree/unitree_rl_mjlab/deploy/robots/g1_23dof/config/policy/velocity/v0/params/deploy.yaml $P/params/
python $S/gain_check.py $P
```
ต้องขึ้น `PASS` ถ้าไม่ผ่าน แปลว่า config ฝั่งเทรนต่างจาก P3b (ดู `training_workflow.md` ข้อ 5)

## 2. `vel_eval.py`: วัดการติดตามความเร็ว (headless)
```bash
python $S/vel_eval.py --policy $P/exported/policy.onnx --deploy $P/params/deploy.yaml
python $S/vel_eval.py --policy $P/exported/policy.onnx --deploy $P/params/deploy.yaml --cases "0,0,0" --hang
```
**มันทำอะไร** (docstring ของไฟล์): จำลอง state Velocity ของ g1_ctrl บนโมเดล `scene_g1_23dof.xml` ใช้ obs/action ตาม deploy.yaml, policy 50 Hz, PD 500 Hz, ข้อต่อที่ policy ไม่ได้คุมค้างด้วย gain ของ FixStand **ไม่มี DDS delay**

| option | ใช้ |
|---|---|
| ไม่ใส่ `--cases` | 8 case: vx 0.4 / 0.8 / 1.0, wz ±0.5 / 1.0, (0.4, 0, 0.5), vy 0.3 |
| `--cases "vx,vy,wz;..."` | กำหนดเอง เช่น `"0,0,0"` = ยืนนิ่ง |
| `--hang` | ยกลำตัวลอย 1.3 m เหมือนแขวนรอก (ใช้กับ `0,0,0`) ดูว่าเตะขาไหม |
| `--no-smooth` | คำสั่งเปลี่ยนแบบ step เหมือนจอยจริง |

## 3. ค่าอ้างอิงของ P3b (vault `Sim2Sim Evaluation.md`)
| คำสั่ง | P3b (% ของคำสั่ง) |
|---|---|
| vx 0.4 | 97 |
| vx 0.8 | 74 |
| vx 1.0 | 41 |
| wz ±0.5 | 69 |
| vy 0.3 | 59 |
| ยืน (joint vel std / yaw std) | 0 / 0 |
| แขวน | นิ่ง |

งาน 5.3: รันเองแล้วเทียบกับตารางนี้ ถ้าไม่ตรง ให้หาว่าเพราะอะไร (คนละไฟล์ onnx? `policy.onnx` กับ `policy_phase3b_16000.onnx` ใน v0 คือตัวเดียวกันไหม? เทียบ md5 ดู)

## 4. ตารางผล (งาน 5.6)
| คำสั่ง | baseline (v0) | control (+300, ไม่เปลี่ยน) | ทดลอง (+300, เปลี่ยน ___) |
|---|---|---|---|
| vx 0.4 | | | |
| vx 0.8 | | | |
| vx 1.0 | | | |
| wz +0.5 | | | |
| wz −0.5 | | | |
| vy 0.3 | | | |
| ยืน | | | |
| แขวน | | | |
| gain_check | PASS | | |

## 5. เทียบให้ยุติธรรม
- **ผลของการทดลอง = ทดลอง − control** ไม่ใช่ ทดลอง − baseline เพราะ fine-tune เฉยๆ ก็อาจเปลี่ยนผลได้ (DR สุ่ม, normalizer อัพเดท, curriculum)
- ต่างกัน 1–3% อาจเป็นแค่ noise ถ้าอยากมั่นใจ ให้รันซ้ำด้วย seed อื่น (`--agent.seed=43`) ทั้ง control และทดลอง
- ดูกราฟ `Episode_Reward/<term ที่เปลี่ยน>` ใน TensorBoard ประกอบ: term ที่ weight เพิ่ม ค่าของมันควรถูกกดลง (ถ้าเป็นโทษ) หรือดันขึ้น (ถ้าเป็นรางวัล)
- 300 iteration สั้นมากเมื่อเทียบกับ 16,000 ผลอาจเล็ก ถ้าผลเป็น 0 ก็เป็นข้อสรุปที่มีค่า (บอกว่าต้องเทรนนานกว่านี้ หรือ term นี้มีผลน้อย)

## 6. ทำไมคะแนนดีแล้วยังไม่ขึ้นหุ่นจริง
ก่อนจะขึ้นหุ่นจริง vault `Training Practice.md` กำหนดว่าต้องผ่าน 3 ขั้นนี้ก่อน:
1. `gain_check` PASS
2. `vel_eval` ความเร็ว + ยืน + `--hang`
3. `sim2sim_policy.sh` กับ g1_ctrl จริง (โค้ด C++, DDS)

และต้องทำใน **session งานหลัก** พร้อมขั้นตอนวันทดสอบ (vault `Test Day Procedure.md`) **ไม่ใช่ใน g1_study**

## คำถามเช็ค
1. `vel_eval` ไม่มี DDS delay แต่หุ่นจริงมี ~3 ms ผลบนหุ่นจริงน่าจะดีกว่าหรือแย่กว่า
2. ถ้า run ทดลองได้ vx 1.0 = 60% และ control = 55% ส่วน baseline = 41% ผลของการเปลี่ยน reward คือเท่าไหร่
3. ทำไม `--hang` สำคัญ ทั้งที่หุ่นไม่ได้เดินกลางอากาศจริง
