#!/usr/bin/env bash
# cut_logs.sh: ตัดช่วง log หุ่นจริง 3/11 มาไว้ใน week6/data/ (พร้อมใช้ ไม่ใช่ skeleton) (งาน 6.1)
# อ่านไฟล์ต้นฉบับใน ~/ อย่างเดียว ไม่แก้ ไม่ย้าย
# ตัด state ให้ครอบช่วงที่ cmd มีข้อมูล ±1 s (ไฟล์ state ของ sysid1 ยาว 900 s / 1.4 GB แต่ cmd มีแค่ 14 s)
#   ./cut_logs.sh            ทั้ง 3 ข้อต่อ
#   ./cut_logs.sh kneeL      ข้อต่อเดียว (kneeL | elbowL | elbowR)
set -euo pipefail
OUT="$HOME/g1_study/week6/data"
mkdir -p "$OUT"

# ชื่อ → run, segments
declare -A RUN=([elbowL]=sysid1 [elbowR]=sysid2 [kneeL]=sysid3)
declare -A SEG=([elbowL]=light [elbowR]=lightR [kneeL]=kneeL)

cut_one() {
  local name="$1" run="${RUN[$1]}" seg="${SEG[$1]}"
  local state="$HOME/g1_state_20261103_${run}.csv" cmd="$HOME/g1_cmd_20261103_${run}.csv"
  local segf="$HOME/sysid_seg_20261103_${seg}.csv"
  for f in "$state" "$cmd" "$segf"; do [ -f "$f" ] || { echo "ไม่พบ $f" >&2; return 1; }; done
  local t0 t1
  t0=$(sed -n 2p "$cmd" | cut -d, -f1)
  t1=$(tail -1 "$cmd" | cut -d, -f1)
  awk -F, -v a="$t0" -v b="$t1" 'NR==1 || ($1 >= a-1 && $1 <= b+1)' "$state" > "$OUT/${name}_state.csv"
  cp "$cmd" "$OUT/${name}_cmd.csv"
  cp "$segf" "$OUT/${name}_seg.csv"
  printf '%-7s cmd %.1f → %.1f s  state %6d แถว  (%s)\n' "$name" "$t0" "$t1" \
    "$(($(wc -l < "$OUT/${name}_state.csv") - 1))" "$(du -h "$OUT/${name}_state.csv" | cut -f1)"
}

if [ $# -ge 1 ]; then
  cut_one "$1"
else
  for n in kneeL elbowR elbowL; do cut_one "$n"; done     # elbowL ช้าสุด (อ่านไฟล์ 1.4 GB)
fi
echo "→ $OUT"
