#!/usr/bin/env bash
# I4: เทรน G1 23-DoF ใน Isaac Lab บน Newton (สั้นๆ ดูว่าวงจรครบ + อ่าน log ได้)
#
#   bash i4_train_newton.sh                 # Newton, 256 env, 10 iteration (~1 นาที)
#   bash i4_train_newton.sh physx           # PhysX เทียบความเร็ว
#   bash i4_train_newton.sh newton 1024 30  # backend, num_envs, iterations
#
# train.py ของ unitree_rl_lab เขียน log ที่ ./logs/rsl_rl/<task>/<วันเวลา>/ ของ "cwd" → cd ไป weekI_isaaclab ก่อน
# จึงได้ log ที่ ~/g1_study/weekI_isaaclab/logs/rsl_rl/ ไม่ไปรก repo หลัก
# ⚠ ใช้ GPU เต็ม: อย่ารันตอน session งานหลักเทรนอยู่ (nvidia-smi ก่อน)
set -euo pipefail
BACKEND=${1:-newton}
NUM_ENVS=${2:-256}
ITERS=${3:-10}
TASK=Unitree-G1-23dof-Velocity-Flat
RL_LAB=~/nvidia/unitree/unitree_rl_lab
PY=~/nvidia/IsaacLab-unitree/env_isaaclab/bin/python
export OMNI_KIT_ACCEPT_EULA=YES

EXTRA=()
if [ "$BACKEND" = "newton" ]; then EXTRA+=("presets=newton"); fi     # Hydra override ต่อท้ายสุด

cd ~/g1_study/weekI_isaaclab
echo "[I4] $TASK · $BACKEND · $NUM_ENVS env · $ITERS iteration → $(pwd)/logs/rsl_rl/"
env -u CONDA_PREFIX "$PY" "$RL_LAB/scripts/rsl_rl/train.py" --task "$TASK" --headless \
    --num_envs "$NUM_ENVS" --max_iterations "$ITERS" --seed 0 "${EXTRA[@]}" 2>&1 \
  | grep --line-buffered -E "Learning iteration|Mean reward|Mean episode length|Iteration time|Total timesteps|Episode_Reward/track_lin|Episode_Termination|Logging experiment|Error|Traceback" || true
echo "[I4] ดูกราฟ: tensorboard --logdir ~/g1_study/weekI_isaaclab/logs/rsl_rl"
