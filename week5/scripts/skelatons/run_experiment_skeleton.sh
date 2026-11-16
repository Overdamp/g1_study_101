#!/usr/bin/env bash
# run_experiment_skeleton.sh: fine-tune P3b แบบ control / ทดลอง ด้วยคำสั่งเดียวกันเป๊ะ (งาน 5.4–5.5, 5.8)
#
#   ./run_experiment_skeleton.sh smoke                5 iteration (ทดสอบว่ารันได้ + จับเวลา)
#   ./run_experiment_skeleton.sh control              300 iteration ไม่เปลี่ยนอะไร
#   ./run_experiment_skeleton.sh exp                  300 iteration + override 1 ตัว (ตั้งใน EXP_OVERRIDE)
#   ./run_experiment_skeleton.sh break                100 iteration สลับเครื่องหมาย (5.8)
#
# ต้อง: conda activate unitree_rl_mjlab · รัน ../prepare_seed.sh ก่อน (ครั้งเดียว)
# ส่วน "ตรวจก่อนเทรน" เขียนไว้ให้แล้ว (ความปลอดภัย/กันพลาด) ส่วน TODO คือสิ่งที่ต้องตัดสินใจเอง
set -euo pipefail

MODE="${1:?ใช้: $0 smoke|control|exp|break}"
REPO="$HOME/nvidia/unitree/unitree_rl_mjlab"
WORK="$HOME/g1_study/week5"
NUM_ENVS=1024             # ต้องเท่ากันทุก run (ถ้า GPU ไม่พอ ลดเป็น 512 ทั้ง control และ exp)
SEED=42

# TODO [5.5] เลือก override 1 ตัว (week5/docs/README.md ตัวเลือก A–D) ห้ามมีหลายตัว
#   เช่น  EXP_OVERRIDE="--env.rewards.action-rate-l2.weight=-0.2"
EXP_OVERRIDE=""
# TODO [5.8] สลับเครื่องหมาย weight 1 ตัว เช่น  BREAK_OVERRIDE="--env.rewards.action-rate-l2.weight=0.05"
BREAK_OVERRIDE=""

# TODO [5.4] จำนวน iteration ของแต่ละโหมด (อ้างอิง ~1.2 s/iter บนเครื่องนี้ ดูเวลาจริงจาก smoke)
case "$MODE" in
  smoke)   ITERS=5;   EXTRA="" ;;
  control) ITERS=300; EXTRA="" ;;
  exp)     ITERS=300; EXTRA="$EXP_OVERRIDE" ;;
  break)   ITERS=100; EXTRA="$BREAK_OVERRIDE" ;;
  *) echo "โหมดไม่รู้จัก: $MODE" >&2; exit 1 ;;
esac

# ---------------- ตรวจก่อนเทรน (ให้ไว้แล้ว) ----------------
python -c "import mjlab" 2>/dev/null || { echo "ใช้ env ผิด: conda activate unitree_rl_mjlab" >&2; exit 1; }
SEED_CKPT="$WORK/logs/rsl_rl/g1_23dof_velocity/p3b_seed/model_15998.pt"
[ -f "$SEED_CKPT" ] || { echo "ไม่มี $SEED_CKPT: รัน ../prepare_seed.sh ก่อน" >&2; exit 1; }
if pgrep -x unitree_mujoco >/dev/null || pgrep -x g1_ctrl >/dev/null; then
  echo "ปิด sim / g1_ctrl ก่อน (GPU 6 GB ใช้ร่วมกัน)" >&2; exit 1
fi
FREE_GB=$(df -BG --output=avail "$HOME" | tail -1 | tr -dc 0-9)
[ "$FREE_GB" -ge 10 ] || { echo "ดิสก์เหลือ ${FREE_GB} GB (< 10) ลบ run เก่าก่อน" >&2; exit 1; }
if [ "$MODE" = exp ] && [ -z "$EXP_OVERRIDE" ]; then echo "ยังไม่ได้ตั้ง EXP_OVERRIDE (TODO 5.5)" >&2; exit 1; fi
if [ "$MODE" = break ] && [ -z "$BREAK_OVERRIDE" ]; then echo "ยังไม่ได้ตั้ง BREAK_OVERRIDE (TODO 5.8)" >&2; exit 1; fi

# ---------------- เทรน ----------------
cd "$WORK"                 # สำคัญ: train.py เขียน log ไปที่ ./logs (นับจาก current directory)
RUN_NAME="$MODE"
echo "[$MODE] iters=$ITERS envs=$NUM_ENVS seed=$SEED override='${EXTRA}'  log → $WORK/logs/"
# TODO [5.4] เขียนคำสั่ง train ให้ครบ (week5/docs/training_workflow.md ข้อ 2):
#   python "$REPO/scripts/train.py" Unitree-G1-23Dof-Flat \
#     --env.scene.num-envs=... --agent.resume=True --agent.load-run=... --agent.load-checkpoint=... \
#     --agent.max-iterations=... --agent.seed=... --agent.logger=tensorboard --agent.run-name=... $EXTRA
#   แล้ว tee log ลงไฟล์ด้วย (เช่น "$WORK/train_$MODE.log") จะได้ดูย้อนหลังได้
echo "run_experiment: ยังไม่ได้เติมคำสั่ง train [5.4]"

# TODO [5.4] หลังจบ: พิมพ์ path ของ run ล่าสุด และ policy.onnx ของมัน (ls -td "$WORK"/logs/rsl_rl/g1_23dof_velocity/*/ | head -1)
# ทายก่อนรัน control: vel_eval ของ control จะต่างจาก baseline ไหม (fine-tune 300 iter ≈ 2% ของการเทรนทั้งหมด)
