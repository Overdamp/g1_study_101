# Skeleton สัปดาห์ 5 (เทรน)

| ลำดับ | ไฟล์ | งาน | env | ทำอะไร |
|---|---|---|---|---|
| – | `runlog.py` | – | – | **ให้ไว้แล้ว**: อ่าน `env.yaml` / `agent.yaml` ของ run (มี tag ของ Python ที่ `yaml.safe_load` อ่านไม่ได้), หา run |
| – | `../prepare_seed.sh` | 5.4 | – | **พร้อมใช้**: ก็อป checkpoint P3b มาไว้ใน `week5/logs/.../p3b_seed/` |
| 1 | `reward_table_skeleton.py` | 5.1 | `unitree_rl_mjlab` | ตาราง reward ทุก term จาก config ของ run จริง |
| 2 | `read_tb_skeleton.py` | 5.2, 5.6 | `unitree_rl_mjlab` | อ่าน TensorBoard เป็นตัวเลข เทียบหลาย run ข้างกัน |
| 3 | `eval_policy_skeleton.py` | 5.3, 5.6 | `g1_sdk` | `eval`: gain_check + vel_eval (+ hang, ยืน) → results.json · `compare`: ตาราง baseline/control/ทดลอง |
| 4 | `run_experiment_skeleton.sh` | 5.4, 5.5, 5.8 | `unitree_rl_mjlab` | เทรน smoke / control / exp / break ด้วยคำสั่งเดียวกัน (มีตัวตรวจก่อนเทรนให้แล้ว) |
| 5 | `diff_configs_skeleton.py` | 5.4 | `unitree_rl_mjlab` | เทียบ config 2 run: ต่างกันแค่ที่ตั้งใจไหม |

## ลำดับการทำ
```bash
cd ~/g1_study/week5/scripts/skelatons
conda activate unitree_rl_mjlab
python reward_table_skeleton.py                     # 5.1  (P3b)
python read_tb_skeleton.py                          # 5.2  (P3b)
conda activate g1_sdk
python eval_policy_skeleton.py eval baseline <v0 policy.onnx>       # 5.3
conda activate unitree_rl_mjlab
../prepare_seed.sh
./run_experiment_skeleton.sh smoke                  # จับเวลา
./run_experiment_skeleton.sh control                # 5.4
./run_experiment_skeleton.sh exp                    # 5.5 (ตั้ง EXP_OVERRIDE ก่อน + ทายผลก่อน)
python diff_configs_skeleton.py <control_run> <exp_run>
python read_tb_skeleton.py                          # 5.6
conda activate g1_sdk
python eval_policy_skeleton.py eval control <control_run>/policy.onnx
python eval_policy_skeleton.py eval exp_a   <exp_run>/policy.onnx
python eval_policy_skeleton.py compare baseline control exp_a       # 5.6
```

## สถานะ
- ทุกไฟล์ Python รันได้ตั้งแต่แรก (พิมพ์ว่ายังไม่ได้เติมแล้วจบ) และ `runlog.load_env_yaml()` ทดสอบกับ run P3b แล้ว (อ่านได้ 16 reward term)
- `run_experiment_skeleton.sh` ยังไม่เทรนจนกว่าจะเติมคำสั่ง train (TODO 5.4) ตัวตรวจก่อนเทรนจะหยุดถ้า: env ผิด, ไม่มี seed, sim/g1_ctrl เปิดอยู่, ดิสก์ < 10 GB, ยังไม่ตั้ง override

## ⚠️ กฎ
- ไม่แก้ repo หลัก (เปลี่ยน reward ผ่าน CLI เท่านั้น) · log ลง `~/g1_study/week5/logs/`
- policy ที่เทรนในสัปดาห์นี้ห้ามขึ้นหุ่นจริง
- ดิสก์ `/home` เหลือน้อย (~41 GB) ลบ run ที่ไม่ใช้
