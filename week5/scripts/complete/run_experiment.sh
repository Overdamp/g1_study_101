#!/usr/bin/env bash
# run_experiment.sh: fine-tune P3b แบบ control / ทดลอง ด้วยคำสั่งเดียวกันเป๊ะ (งาน 5.4–5.5, 5.8) ฉบับสมบูรณ์
#
#   ./run_experiment.sh smoke      5 iteration (ทดสอบ + จับเวลา)
#   ./run_experiment.sh control    300 iteration ไม่เปลี่ยนอะไร
#   ./run_experiment.sh exp        300 iteration + EXP_OVERRIDE
#   ./run_experiment.sh break      100 iteration + BREAK_OVERRIDE (สลับเครื่องหมาย)
#
# เปลี่ยน override ได้ด้วยตัวแปรแวดล้อม โดยไม่ต้องแก้ไฟล์:
#   EXP_OVERRIDE="--env.rewards.track-linear-velocity.weight=2.0" ./run_experiment.sh exp
# ต้อง: conda activate unitree_rl_mjlab · รัน ../prepare_seed.sh ก่อน (ครั้งเดียว)
set -euo pipefail

MODE="${1:?ใช้: $0 smoke|control|exp|break}"
REPO="$HOME/nvidia/unitree/unitree_rl_mjlab"
WORK="${WORK:-$HOME/g1_study/week5}"
NUM_ENVS="${NUM_ENVS:-1024}"
SEED="${SEED:-42}"
EXP_OVERRIDE="${EXP_OVERRIDE:---env.rewards.action-rate-l2.weight=-0.2}"     # ตัวเลือก A (นุ่มขึ้น) ค่าเริ่มต้น
BREAK_OVERRIDE="${BREAK_OVERRIDE:---env.rewards.action-rate-l2.weight=0.05}"  # กลับเครื่องหมาย: ให้รางวัลกับการกระตุก

case "$MODE" in
  smoke)   ITERS=5;   EXTRA="" ;;
  control) ITERS=300; EXTRA="" ;;
  exp)     ITERS=300; EXTRA="$EXP_OVERRIDE" ;;
  break)   ITERS=100; EXTRA="$BREAK_OVERRIDE" ;;
  *) echo "โหมดไม่รู้จัก: $MODE" >&2; exit 1 ;;
esac
ITERS="${ITERS_OVERRIDE:-$ITERS}"

# ---------------- ตรวจก่อนเทรน ----------------
python -c "import mjlab" 2>/dev/null || { echo "ใช้ env ผิด: conda activate unitree_rl_mjlab" >&2; exit 1; }
SEED_CKPT="$WORK/logs/rsl_rl/g1_23dof_velocity/p3b_seed/model_15998.pt"
[ -f "$SEED_CKPT" ] || { echo "ไม่มี $SEED_CKPT: รัน ../prepare_seed.sh ก่อน" >&2; exit 1; }
if pgrep -x unitree_mujoco >/dev/null || pgrep -x g1_ctrl >/dev/null; then
  echo "ปิด sim / g1_ctrl ก่อน (GPU 6 GB ใช้ร่วมกัน)" >&2; exit 1
fi
FREE_GB=$(df -BG --output=avail "$HOME" | tail -1 | tr -dc 0-9)
[ "$FREE_GB" -ge 10 ] || { echo "ดิสก์เหลือ ${FREE_GB} GB (< 10) ลบ run เก่าก่อน" >&2; exit 1; }

# ---------------- เทรน ----------------
cd "$WORK"                  # train.py เขียน log ไปที่ ./logs (นับจาก current directory)
STAMP=$(date +%H%M%S)
LOG="$WORK/train_${MODE}_${STAMP}.log"
echo "[$MODE] iters=$ITERS envs=$NUM_ENVS seed=$SEED override='${EXTRA}'"
echo "        log → $WORK/logs/rsl_rl/g1_23dof_velocity/   stdout → $LOG"
# shellcheck disable=SC2086   (EXTRA ว่างได้ ต้องแตกคำ)
CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}" python "$REPO/scripts/train.py" Unitree-G1-23Dof-Flat \
  --env.scene.num-envs="$NUM_ENVS" \
  --agent.resume=True --agent.load-run=p3b_seed --agent.load-checkpoint=model_15998.pt \
  --agent.max-iterations="$ITERS" \
  --agent.seed="$SEED" \
  --agent.logger=tensorboard \
  --agent.run-name="$MODE" \
  $EXTRA 2>&1 | tee "$LOG"

RUN=$(ls -td "$WORK"/logs/rsl_rl/g1_23dof_velocity/*/ | grep -v p3b_seed | head -1)
echo
echo "run: $RUN"
ls -la "$RUN"policy.onnx 2>/dev/null || echo "(ยังไม่มี policy.onnx: save ทุก 100 iteration และตอนจบ)"
echo "ต่อไป: python $(dirname "$0")/eval_policy.py eval $MODE ${RUN}policy.onnx   (env g1_sdk)"
