"""สร้าง skelatons/ จาก complete/ (รันซ้ำได้ ทับไฟล์ *_skeleton เดิม)

    python make_skeletons.py

กฎ: ในไฟล์ complete บล็อก
    # >>>TODO(tag) คำใบ้
    # STUB: โค้ดสำรอง        ← (ไม่บังคับ) บรรทัดที่จะใส่แทนใน skeleton
    ...เฉลย...
    # <<<TODO
จะกลายเป็น
    # TODO(tag) คำใบ้
    โค้ดสำรอง  หรือ  raise NotImplementedError("TODO(tag) คำใบ้")
"""
import re
from pathlib import Path

HERE = Path(__file__).parent
SRC, DST = HERE / "complete", HERE / "skelatons"

QUESTIONS = {
    "ilib": """ทายก่อนรัน (เขียนคำตอบลงกระดาษก่อน แล้วค่อยรันเทสต์เทียบ)
  1. free joint ของ pelvis กิน coordinate (joint_q) กี่ช่อง และ dof (joint_qd) กี่ช่อง ทำไมไม่เท่ากัน
  2. joint_q_start ของเข่าซ้ายคือเท่าไร (เข่าเป็น joint ตัวที่ 4 ของขาซ้าย)
  3. ทำไม capture() ต้องบันทึก 2 step ไม่ใช่ 1
""",
    "n1_model": """ทายก่อนรัน
  1. MJCF ของ mjlab มี armature / kp ของเข่าอยู่ในไฟล์ไหม (ค่าในไฟล์ดิบ = ?)
  2. shape 64 ชิ้น: ชิ้นไหนใช้ชน ชิ้นไหนใช้ดูอย่างเดียว · MuJoCo Warp จะได้ geom กี่ชิ้น
  3. actuator ที่ Newton สร้างให้ MuJoCo เป็นชนิดไหน (motor / position / general) และ biasprm = ?
""",
    "n2_pd_drop": """ทายก่อนรัน
  1. gain ×1 (ค่าเทรน) ยืนด้วย PD อย่างเดียวได้กี่วินาที · gain ×8 ล่ะ
  2. ทำไม gain สูงมากถึงยืนได้ แต่ policy ไม่ใช้ gain สูงแบบนั้น
  3. sag ของศอกที่ gain ×2 ควรเป็นกี่เท่าของ ×1
""",
    "n3_vs_mujoco": """ทายก่อนรัน
  1. A (Newton GPU) กับ B (MuJoCo C) ต่างกันประมาณเท่าไร: 0 / 1e-6 / 1e-3 / 1e-1 rad
  2. dt 0.02: implicit กับ explicit PD ตัวไหนพัง และพังเพราะอะไร
  3. frictionloss 0.2 ทำให้ final error ใหญ่ขึ้นหรือเล็กลง (เทียบ weekM ศอก +69°)
""",
    "n4_speed_solver": """ทายก่อนรัน
  1. 1024 world เร็วกว่า 1 world กี่เท่า (ต่อ env-step): 1× / 10× / 100× / 1000×
  2. CUDA graph เร็วกว่า eager กี่เท่าที่ 16 world
  3. พารามิเตอร์ตัวไหนใน B ทำให้หุ่นรูปปั้นล้ม: cone / iterations / ls_iterations / integrator / dt
""",
    "i1_presets": """ทายก่อนรัน
  1. `presets=newton` เปลี่ยน config กี่ที่ (PresetCfg กี่ตัว) และอะไรบ้าง
  2. ถ้าไม่ตั้ง integrator เอง MJWarpSolverCfg จะใช้อะไร
  3. policy v0 ของ mjlab กับ task Isaac นี้ obs เหมือนกันไหม
""",
    "i2_env_newton": """ทายก่อนรัน
  1. ลำดับ joint ของ Isaac (PhysX) กับ (Newton) เหมือนลำดับ policy ไหม
  2. 1 env.step() เรียก sim.step กี่ครั้ง: ปกติ / --fast-path
  3. Newton กับ PhysX ที่ 512 env อันไหนเร็วกว่า กี่ %
  4. geom ที่ใช้ชนใน Isaac (จาก USD) เหมือน mjlab (capsule) ไหม
""",
    "my_terms_isaac": """ทายก่อนเติม
  1. ใน Isaac Lab 3 `robot.data.root_pos_w` เป็น torch tensor ไหม (mjlab เป็น)
  2. G1 ใน USD มี site "left_foot" ไหม ถ้าไม่มีจะหาตำแหน่งเท้าจากอะไร
""",
    "contract_manager": """ทายก่อนเติม
  1. obs ของ critic สืบทอดจาก PolicyCfg แล้วเพิ่ม 2 term: term ของ actor อยู่ช่วง index ไหนของ critic
  2. ถ้าลืม preserve_order=True ใน SceneEntityCfg ของ joint จะพังบน backend ไหน
""",
    "i5_manager_terms": """ทายก่อนรัน
  1. P3b เดินใน task manager ของเราได้ไหม ทั้งที่ไม่เคยเห็น Isaac/Newton · vx ที่คำสั่ง 0.5 ≈ ?
  2. reward ตัวไหนต่างระหว่างศูนย์กับ P3b มากที่สุด
  3. friction DR 0–0.3 ค่าไปอยู่ใน Newton Model field ไหน
""",
    "contract_direct": """ทายก่อนเติม
  1. DirectRLEnv เรียก _apply_action กี่ครั้งต่อ env.step · _pre_physics_step กี่ครั้ง
  2. is_alive ใช้ reset_terminated ได้เพราะ _get_dones ถูกเรียกก่อนหรือหลัง _get_rewards
  3. หลัง _reset_idx ค่า projected_gravity_b ของ env ที่เพิ่ง reset สดหรือเก่า
""",
    "i6_compare": """ทายก่อนรัน
  1. obs ของ manager กับ Direct ที่ step 0 ต่างกันเท่าไร · step 299 ล่ะ
  2. Direct เร็วกว่า manager กี่ % ตอนไม่มี reset · ตอน reset เยอะ
""",
    "i6_train": """ทายก่อนรัน
  1. เริ่มจากศูนย์ 10 iteration: Mean reward บวกหรือลบ · ถ้า --init-p3b ล่ะ
  2. ทำไมโหลด actor ของ P3b ได้แต่ critic ไม่ได้
""",
    "i3_cross_sim": """ทายก่อนรัน
  1. v0 เดิน 0.4 m/s ใน PhysX / Newton ได้กี่ % ของคำสั่ง (MuJoCo 97%)
  2. engine ไหนจะใกล้ MuJoCo ที่สุด และเพราะอะไร
""",
}


def convert(text: str, name: str) -> str:
    out, i, lines = [], 0, text.splitlines()
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^(\s*)# >>>TODO(\(.*?\))?\s*(.*)$", line)
        if not m:
            out.append(line)
            i += 1
            continue
        ind, tag, hint = m.group(1), m.group(2) or "", m.group(3)
        out.append(f"{ind}# TODO{tag} {hint}".rstrip())
        stub = []
        i += 1
        while not re.match(r"^\s*# <<<TODO", lines[i]):
            s = re.match(r"^(\s*)# STUB: ?(.*)$", lines[i])
            if s:
                stub.append(s.group(1) + s.group(2))
            i += 1
        i += 1  # ข้าม <<<TODO
        out.extend(stub or [f"{ind}raise NotImplementedError({('TODO' + tag + ' ' + hint)!r})"])
    s = "\n".join(out) + "\n"
    # import โมดูลของเราเอง → ตัว skeleton (ชื่อเดิมเป็น alias ให้โค้ดที่เหลือไม่ต้องแก้)
    for mod in MODULES:
        s = re.sub(rf"^(\s*)import {mod}\b(?: as (\w+))?", lambda m: f"{m.group(1)}import {mod}_skeleton as "
                   f"{m.group(2) or mod}", s, flags=re.M)
    s = s.replace("import contract_manager as M, contract_direct as D, ilib",
                  "import contract_manager_skeleton as M, contract_direct_skeleton as D, ilib_skeleton as ilib")
    for script in ("i5_manager_terms", "i6_direct_env"):
        s = s.replace(f'"{script}.py"', f'"{script}_skeleton.py"')
    # ใส่คำถามต่อจาก docstring แรก
    q = QUESTIONS.get(name)
    if q:
        end = s.index('"""', s.index('"""') + 3)
        s = s[:end] + "\n[skeleton] " + q + s[end:]
    return s


MODULES = ["ilib", "contract_common", "contract_manager", "contract_direct", "my_terms_isaac"]


def main():
    DST.mkdir(exist_ok=True)
    for p in sorted(SRC.glob("*.py")):
        name = p.stem
        dst = DST / f"{name}_skeleton.py"
        dst.write_text(convert(p.read_text(), name))
        n = p.read_text().count(">>>TODO")
        print(f"  {dst.name:28s} TODO {n}")
    for p in SRC.glob("*.sh"):                    # สคริปต์ shell = ตัวเรียกใช้ ไม่มี TODO → คัดลอก
        (DST / p.name).write_text(p.read_text())
        (DST / p.name).chmod(0o755)
        print(f"  {p.name:28s} (คัดลอก)")


if __name__ == "__main__":
    main()
