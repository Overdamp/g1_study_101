# ทำสำเนา g1_ctrl, build, รันกับ sim

## ทำไมต้องทำสำเนา
- กติกาของ g1_study คือ**ไม่แก้ repo หลัก** เพราะ binary ใน `unitree_rl_mjlab/deploy/robots/g1_23dof/build/` คือตัวที่ใช้กับหุ่นจริง
- g1_ctrl อ่าน `config.yaml` จาก `<โฟลเดอร์ binary>/../config/` (ดู `deploy/include/param.h` ฟังก์ชัน `load_config_file`) ถ้ามีสำเนาทั้งโฟลเดอร์ config ก็จะแยกจากของจริงโดยสมบูรณ์

## 1. ทำสำเนา (ครั้งเดียว)
CMake อ้างอิง `../../include` และ `../../thirdparty` จาก `robots/g1_23dof` จึงต้องรักษาโครงโฟลเดอร์ไว้แบบเดิม:
```bash
SRC=~/nvidia/unitree/unitree_rl_mjlab/deploy
DST=~/g1_study/week3/deploy
mkdir -p $DST/robots
cp -r $SRC/include $DST/                                         # 164 KB
rsync -a --exclude build $SRC/robots/g1_23dof $DST/robots/       # ~12 MB (มี policy)
ln -s $SRC/thirdparty $DST/thirdparty                            # 40 MB ใช้ร่วมกันได้ ไม่ต้องก็อป (อ่านอย่างเดียว)
```
ได้โครงแบบนี้:
```
~/g1_study/week3/deploy/
├── include/            ← สำเนา (แก้ได้)
├── thirdparty -> ...   ← symlink (ห้ามแก้)
└── robots/g1_23dof/    ← สำเนา (แก้ได้)
```
แนะนำให้ `git init` ใน `~/g1_study/week3/deploy` แล้ว commit ก่อนแก้ จะได้ `git diff` ดูได้ว่าตัวเองแก้อะไรไปบ้าง

## 2. build
```bash
cd ~/g1_study/week3/deploy/robots/g1_23dof
mkdir -p build && cd build
cmake .. \
  -DCMAKE_CXX_FLAGS="-I/opt/unitree_robotics/include -I/opt/unitree_robotics/include/ddscxx" \
  -DCMAKE_EXE_LINKER_FLAGS="-L/opt/unitree_robotics/lib -Wl,-rpath,/opt/unitree_robotics/lib"
make -j$(nproc)
```
⚠️ **ต้องมี 2 flag นี้** `CMakeLists.txt` ไม่ได้ใส่ path ของ unitree_sdk2 ไว้ ถ้าใช้ `cmake ..` เฉยๆ จะเจอ `fatal error: unitree/dds_wrapper/robots/go2/go2.h: No such file or directory` (ค่าเดียวกับใน `CMakeCache.txt` ของ build จริงใน repo · ทดสอบแล้ว 10/11: build ใช้ ~26 s ด้วย -j20)
หรือใช้ `week3/scripts/setup_copy.sh` (ใส่ flag ให้แล้ว)
ได้ `build/g1_ctrl` ครั้งแรกใช้เวลาไม่ถึงนาที (`-j20`) ครั้งต่อไปจะ build แค่ไฟล์ที่เปลี่ยน
- ไฟล์ state เป็น `.h` ที่ include จาก `main.cpp` ถ้าแก้ `.h` แล้ว `make` จะ build `main.cpp` ใหม่เอง
- ถ้าแก้แค่ `config.yaml` **ไม่ต้อง build ใหม่** แต่ต้องเปิด g1_ctrl ใหม่

## 3. รันกับ sim
**terminal 1: sim** (ตัวเดียว)
```bash
~/g1_study/start_sim.sh
```
**terminal 2: g1_ctrl สำเนา**
```bash
cd ~/g1_study/week3/deploy/robots/g1_23dof/build
env -u CYCLONEDDS_URI LD_LIBRARY_PATH=/opt/unitree_robotics/lib ./g1_ctrl
```
- ไม่ใส่ `--network` = `lo` + domain 1 = sim (`main.cpp` ตั้งค่าเริ่มต้นไว้) ⚠️ **ห้ามใส่ `--network enp43s0` กับสำเนา**
- ต้องเห็น `DDS: domain 1 on lo (SIM, keyboard on)` ถ้าเห็นคำว่า `REAL ROBOT` ให้กด Ctrl+C ทันที
- คีย์บอร์ดจะทำงานเมื่อ **terminal ของ g1_ctrl ถูกเลือกอยู่** (ไม่ใช่หน้าต่าง MuJoCo)

## 4. ทดสอบ state เดิม (งาน 3.5)
| คีย์ | ผล | log ที่ควรเห็น |
|---|---|---|
| `u` | Passive → FixStand (ไล่เข้าท่ายืน 3 s) | `FSM: Change state from Passive to FixStand` |
| `p` | → Passive | `... to Passive` |
| `v` | FixStand → Velocity (policy) | `... to Velocity` |

- ทดสอบ FixStand ด้วย elastic band (หุ่นห้อย) ได้เลย
- ⚠️ **Velocity ตอนห้อย** policy บางตัวเตะขา (vault `g1_ctrl FSM.md`) ถ้าจะลอง Velocity ให้ทำตามคำแนะนำที่ g1_ctrl พิมพ์ออกมา: Pause MuJoCo → Load key 0 (stand_ready) → กด `u` แล้ว `v` → Run หรือข้ามไปก่อนก็ได้ งานสัปดาห์นี้ไม่ได้ต้องใช้ Velocity
- ปิด g1_ctrl: Ctrl+C

## 5. แก้ปัญหา
| อาการ | สาเหตุ / ทางแก้ |
|---|---|
| ค้างที่ `Waiting for connection to robot...` | sim ไม่ได้เปิด / multicast `lo` ปิด / `CYCLONEDDS_URI` ค้าง (เช็คลิสต์เดียวกับสัปดาห์ 1) |
| `The other process is using the lowcmd channel` | มีโปรแกรมอื่นส่ง lowcmd อยู่ (mini_fsm.py? g1_ctrl อีกตัว?) ปิดก่อน ⚠️ g1_ctrl **ไม่หยุดเอง** |
| `Unmatched robot type.` | `mode_machine` ไม่ใช่ 4: sim เปิด scene 29-DoF หรือเปล่า |
| `FSM: Unknown FSM type X` | ลืม `#include "State_X.h"` ใน `main.cpp` หรือชื่อ `type` ใน yaml ไม่ตรงกับชื่อ class (ไม่ต้องมี `State_` นำหน้าใน yaml) |
| `FSM State_'X' not found in FSMStringMap!` | transitions อ้างชื่อ state ที่ไม่ได้อยู่ใน `_:` |
| `error while loading shared libraries` | ลืม `LD_LIBRARY_PATH=/opt/unitree_robotics/lib` |
| `go2.h: No such file or directory` ตอน make | ลืม `-DCMAKE_CXX_FLAGS=...` ตอน cmake (ลบ `build/` แล้ว cmake ใหม่พร้อม flag) |
| `cmake` หา `onnxruntime` ไม่เจอ | symlink `thirdparty` ผิดที่ เช็ค `ls ~/g1_study/week3/deploy/thirdparty/` |
| `yaml-cpp: bad conversion` | จำนวนค่าใน list ไม่ครบ หรือ indent ผิดใน `config.yaml` |

## 6. ดู log ย้อนหลัง
g1_ctrl ใช้ spdlog พิมพ์ออกจอ ถ้าอยากเก็บไว้ดูทีหลัง: `./g1_ctrl 2>&1 | tee run.log`
