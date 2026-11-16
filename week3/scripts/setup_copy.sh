#!/usr/bin/env bash
# setup_copy.sh: ทำสำเนา g1_ctrl ไว้ที่ ~/g1_study/week3/deploy แล้ว build (งาน 3.5)
# อ่านอย่างเดียวจาก repo หลัก ไม่แก้อะไรใน unitree_rl_mjlab (ดู week3/docs/build_and_run.md)
#   ./setup_copy.sh          ทำสำเนา (ครั้งเดียว) + git init + build
#   ./setup_copy.sh build    build อย่างเดียว (หลังแก้โค้ด)
set -euo pipefail

SRC="$HOME/nvidia/unitree/unitree_rl_mjlab/deploy"
DST="$HOME/g1_study/week3/deploy"
ROBOT="$DST/robots/g1_23dof"

if [ "${1:-}" != "build" ]; then
  if [ -e "$DST" ]; then
    echo "มี $DST อยู่แล้ว (ไม่ทับ) ถ้าจะเริ่มใหม่ ให้ลบเองก่อน หรือใช้: $0 build" >&2
    exit 1
  fi
  mkdir -p "$DST/robots"
  cp -r "$SRC/include" "$DST/"
  rsync -a --exclude build "$SRC/robots/g1_23dof" "$DST/robots/"
  ln -s "$SRC/thirdparty" "$DST/thirdparty"           # 40 MB ใช้ร่วม อ่านอย่างเดียว
  git -C "$DST" init -q
  printf 'robots/g1_23dof/build/\nthirdparty\n' > "$DST/.gitignore"
  git -C "$DST" add -A
  git -C "$DST" -c user.name=Overdamp -c user.email=study@local commit -qm "copy of unitree_rl_mjlab/deploy (unmodified)"
  echo "สำเนาพร้อม: $DST (commit แรก = ของเดิมไม่แก้ ใช้ git diff ดูสิ่งที่แก้ภายหลัง)"
fi

mkdir -p "$ROBOT/build"
cd "$ROBOT/build"
# CMakeLists.txt ไม่ได้ใส่ path ของ unitree_sdk2 ไว้ ต้องส่งผ่าน flag (ค่าเดียวกับ CMakeCache.txt ของ build จริงใน repo)
cmake .. \
  -DCMAKE_CXX_FLAGS="-I/opt/unitree_robotics/include -I/opt/unitree_robotics/include/ddscxx" \
  -DCMAKE_EXE_LINKER_FLAGS="-L/opt/unitree_robotics/lib -Wl,-rpath,/opt/unitree_robotics/lib" > /dev/null
make -j"$(nproc)"
echo
echo "build เสร็จ: $ROBOT/build/g1_ctrl"
echo "รันกับ sim (ห้ามใส่ --network enp43s0):"
echo "  cd $ROBOT/build && env -u CYCLONEDDS_URI LD_LIBRARY_PATH=/opt/unitree_robotics/lib ./g1_ctrl"
