#!/usr/bin/env python3
"""apply_holdpose.py: ใส่ State_HoldPose ลงในสำเนา g1_ctrl (งาน 3.7) ฉบับสมบูรณ์

ทำ 3 อย่างในสำเนา (ค่าเริ่มต้น ~/g1_study/week3/deploy) แล้วจบ (ไม่ build ให้):
  1. ก็อป State_HoldPose.h → robots/g1_23dof/include/
  2. main.cpp: #include + คีย์ o (Passive → HoldPose) / p (HoldPose → Passive) เฉพาะ sim + ข้อความช่วยเหลือ
  3. config.yaml: HoldPose ใน _:, ทางไป HoldPose ใน Passive, บล็อก HoldPose (gain ตอนเทรน, ramp 1 s)
รันซ้ำได้ (ข้ามจุดที่ใส่แล้ว) · ปฏิเสธถ้า path เป็น repo หลัก

ใช้:  python apply_holdpose.py [<โฟลเดอร์ deploy ของสำเนา>]
แล้ว: cd <สำเนา>/robots/g1_23dof/build && make -j$(nproc)   (หรือ ../../setup_copy.sh build)
"""

import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_DEPLOY = (Path.home() / "nvidia/unitree/unitree_rl_mjlab/deploy").resolve()

INCLUDE_ANCHOR = '#include "State_Handover.h"\n'
INCLUDE_LINE = '#include "State_HoldPose.h"\n'

START_ANCHOR = "    fsm->start();\n"
KEY_BLOCK = '''    // HoldPose keys (g1_study week3, loopback sim only): [o] Passive -> HoldPose, [p] HoldPose -> Passive.
    // The shared FSMState keys only know u / v / p for the original states, so new states add their own here.
    if (FSMState::keyboard_fsm_shortcuts_enabled && FSMStringMap.right.count("HoldPose")) {
        int passive = FSMStringMap.right.at("Passive");
        int holdpose = FSMStringMap.right.at("HoldPose");
        auto key_is = [](std::string k) {
            return [k]()->bool {
                return FSMState::keyboard && FSMState::keyboard->on_pressed &&
                       FSMState::keyboard->key() == k;
            };
        };
        for (auto & s : fsm->states) {
            if (s->isState(passive)) s->registered_checks.emplace_back(key_is("o"), holdpose);
            if (s->isState(holdpose)) s->registered_checks.emplace_back(key_is("p"), passive);
        }
    }
'''
HELP_ANCHOR = '        std::cout << "Simulation keyboard: [u] FixStand, [v] Velocity, [p] Passive, [h] Handover (from Passive).\\n";\n'
HELP_LINE = '        std::cout << "HoldPose (g1_study): [o] HoldPose (from Passive), [p] back to Passive.\\n";\n'

YAML_ENABLED_ANCHOR = "    Handover:\n      id: 4\n"
YAML_ENABLED = "    HoldPose:\n      id: 5\n"
YAML_PASSIVE_ANCHOR = "      Handover: LB(1s) + RB(1s) + start.on_pressed\n"
YAML_PASSIVE = "      HoldPose: LT + down.on_pressed\n"
YAML_BLOCK_ANCHOR = "  Velocity:\n    transitions:"


def yaml_block() -> str:
    """บล็อก HoldPose: จาก config_holdpose.yaml (ตั้งแต่บรรทัด '  HoldPose:' จนจบไฟล์) + บรรทัดว่าง"""
    text = (HERE / "config_holdpose.yaml").read_text()
    start = text.index("\nFSM:\n") + len("\nFSM:\n")       # ข้าม comment ด้านบน (มีคำว่า HoldPose ด้วย)
    return text[start:].rstrip() + "\n\n"


def insert_after(text: str, anchor: str, new: str, what: str) -> str:
    if new in text:
        print(f"  = {what}: มีแล้ว")
        return text
    if anchor not in text:
        raise SystemExit(f"หาตำแหน่งไม่เจอ ({what}): {anchor.strip()!r}")
    print(f"  + {what}")
    return text.replace(anchor, anchor + new, 1)


def insert_before(text: str, anchor: str, new: str, what: str, marker: str) -> str:
    """แทรก new ก่อน anchor · marker = ข้อความที่บอกว่าใส่ไปแล้ว (กันแทรกซ้ำเมื่อรันซ้ำ)"""
    if marker in text:
        print(f"  = {what}: มีแล้ว")
        return text
    if anchor not in text:
        raise SystemExit(f"หาตำแหน่งไม่เจอ ({what}): {anchor.strip()!r}")
    print(f"  + {what}")
    return text.replace(anchor, new + anchor, 1)


def main():
    dst = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else Path.home() / "g1_study/week3/deploy"
    dst = dst.resolve()
    if dst == REPO_DEPLOY or REPO_DEPLOY in dst.parents:
        raise SystemExit("[safety] นี่คือ repo หลัก ห้ามแก้ ใช้กับสำเนาเท่านั้น")
    robot = dst / "robots/g1_23dof"
    if not (robot / "main.cpp").exists():
        raise SystemExit(f"ไม่พบ {robot / 'main.cpp'}: ทำสำเนาก่อน (week3/scripts/setup_copy.sh)")

    print(f"สำเนา: {dst}")
    shutil.copy2(HERE / "State_HoldPose.h", robot / "include/State_HoldPose.h")
    print("  + include/State_HoldPose.h")

    main_cpp = robot / "main.cpp"
    s = main_cpp.read_text()
    s = insert_after(s, INCLUDE_ANCHOR, INCLUDE_LINE, "main.cpp #include")
    s = insert_before(s, START_ANCHOR, KEY_BLOCK, "main.cpp คีย์ o/p", marker="FSMStringMap.right.count(\"HoldPose\")")
    s = insert_after(s, HELP_ANCHOR, HELP_LINE, "main.cpp ข้อความช่วยเหลือ")
    main_cpp.write_text(s)

    cfg = robot / "config/config.yaml"
    y = cfg.read_text()
    y = insert_after(y, YAML_ENABLED_ANCHOR, YAML_ENABLED, "config.yaml _: HoldPose")
    y = insert_after(y, YAML_PASSIVE_ANCHOR, YAML_PASSIVE, "config.yaml Passive → HoldPose")
    y = insert_before(y, YAML_BLOCK_ANCHOR, yaml_block(), "config.yaml บล็อก HoldPose", marker="  HoldPose:\n    transitions:")
    cfg.write_text(y)

    print("\nเสร็จ ต่อไป:")
    print(f"  cd {robot}/build && make -j$(nproc)")
    print(f"  env -u CYCLONEDDS_URI LD_LIBRARY_PATH=/opt/unitree_robotics/lib ./g1_ctrl     (sim, ห้ามใส่ --network)")
    print(f"  git -C {dst} diff      ← ดูว่าแก้อะไรไปบ้าง")


if __name__ == "__main__":
    main()
