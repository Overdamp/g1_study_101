#!/usr/bin/env bash
# prepare_seed.sh: เตรียม checkpoint P3b สำหรับ fine-tune ในสัปดาห์ 5 (พร้อมใช้ ไม่ใช่ skeleton)
# ก็อป model_15998.pt (4.9 MB) จาก repo หลัก → ~/g1_study/week5/logs/rsl_rl/g1_23dof_velocity/p3b_seed/
# อ่านอย่างเดียวจาก repo หลัก ไม่แก้ของเดิม
set -euo pipefail
SRC="$HOME/nvidia/unitree/unitree_rl_mjlab/logs/rsl_rl/g1_23dof_velocity/phase3b_seed/model_15998.pt"
DST="$HOME/g1_study/week5/logs/rsl_rl/g1_23dof_velocity/p3b_seed"
[ -f "$SRC" ] || { echo "ไม่พบ $SRC" >&2; exit 1; }
mkdir -p "$DST"
if [ -f "$DST/model_15998.pt" ]; then
  echo "มีอยู่แล้ว: $DST/model_15998.pt"
else
  cp "$SRC" "$DST/"
  echo "ก็อปแล้ว: $DST/model_15998.pt"
fi
md5sum "$SRC" "$DST/model_15998.pt" | awk '{print $1, $2}'
