"""inspect_policy_skeleton.py: เปิด policy.onnx แล้วเทียบกับ deploy.yaml (งาน 4.1)  ❌ ไม่ต่อ DDS

1. พิมพ์ input / output (ชื่อ, shape, type) ของ ONNX
2. พิมพ์ metadata (custom_metadata_map)
3. เทียบทีละ field กับ deploy.yaml พร้อม % ที่ต่างกัน → เติมตารางใน week4/docs/onnx_basics.md

รัน:  conda activate g1_sdk && python week4/scripts/skelatons/inspect_policy_skeleton.py [--policy-dir <โฟลเดอร์ policy>]
"""

import argparse
from pathlib import Path

import numpy as np
import yaml

V0 = Path.home() / "nvidia/unitree/unitree_rl_mjlab/deploy/robots/g1_23dof/config/policy/velocity/v0"

# คู่ที่ต้องเทียบ: (ชื่อใน metadata, วิธีดึงจาก deploy.yaml)
PAIRS = [
    ("joint_stiffness", lambda d: d["stiffness"]),
    ("joint_damping", lambda d: d["damping"]),
    ("default_joint_pos", lambda d: d["default_joint_pos"]),
    ("action_scale", lambda d: d["actions"]["JointPositionAction"]["scale"]),
]


def load_session(onnx_path: Path):
    # TODO [4.1] import onnxruntime แล้วสร้าง InferenceSession (เปิดครั้งเดียว)
    return None


def print_io(session) -> None:
    # TODO [4.1] วน session.get_inputs() และ get_outputs(): พิมพ์ .name .shape .type
    # ทายก่อน: input มีกี่มิติ ชื่ออะไร (ดู week4/docs/observations.md)
    pass


def read_metadata(session) -> dict:
    # TODO [4.1] session.get_modelmeta().custom_metadata_map  (dict str → str)
    return {}


def to_floats(s: str) -> np.ndarray:
    """metadata เป็น string คั่นด้วย ',' → array"""
    # TODO [4.1]
    return np.array([])


def compare(meta: dict, deploy: dict) -> None:
    # TODO [4.1] วน PAIRS: a = to_floats(meta[key]), b = np.array(get(deploy))
    #            พิมพ์: ชื่อ, max |a − b|, max % ต่าง (เทียบกับ |a|), ผ่าน/ไม่ผ่านตาม tolerance ของ gain_check.py (เปิดดู CHECKS: gain 6%, scale 1%, default pose 1e-3)
    # TODO [4.1] เทียบลำดับ obs: meta["observation_names"] กับ list(deploy["observations"])  (ชื่อต่างกันแต่ลำดับควรตรง)
    # TODO [4.1] เทียบขนาด: รวมมิติ obs จาก deploy (scale ของแต่ละ term มีความยาว = มิติของ term) กับ input shape
    # คำถาม: ถ้าสองที่ต่างกัน g1_ctrl ใช้ตัวไหน (policy_pipeline.md)
    pass


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--policy-dir", type=Path, default=V0)
    args = p.parse_args()
    deploy = yaml.safe_load(open(args.policy_dir / "params" / "deploy.yaml"))
    session = load_session(args.policy_dir / "exported" / "policy.onnx")
    if session is None:
        print("inspect_policy: ยังไม่ได้เติม [4.1]")
        return
    print_io(session)
    meta = read_metadata(session)
    # TODO [4.1] พิมพ์ทุก key ของ meta (ตัดค่ายาวๆ ให้เหลือ ~80 ตัวอักษร)
    compare(meta, deploy)


if __name__ == "__main__":
    main()
