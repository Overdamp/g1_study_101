"""runlog.py: ตัวช่วยอ่านไฟล์ของ run (เหมือนใน skelatons/) ใช้ร่วมกับ reward_table / diff_configs / read_tb

- load_env_yaml(run_dir): อ่าน <run>/params/env.yaml (มี tag ของ Python เช่น python/tuple ซึ่ง yaml.safe_load อ่านไม่ได้)
- find_runs(...): หาโฟลเดอร์ run
"""

from pathlib import Path

import yaml

REPO_LOGS = Path.home() / "nvidia/unitree/unitree_rl_mjlab/logs/rsl_rl/g1_23dof_velocity"
WEEK5_LOGS = Path.home() / "g1_study/week5/logs/rsl_rl/g1_23dof_velocity"
P3B_RUN = REPO_LOGS / "2026-10-22_17-02-19"          # run ที่ได้ P3b (อ่านอย่างเดียว)


class _Loader(yaml.SafeLoader):
    """SafeLoader ที่ยอมรับ tag python/* ทุกแบบ โดยแปลงเป็น list / dict / str ธรรมดา (ไม่รันโค้ดใดๆ)"""


def _any_python_tag(loader, suffix, node):
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node, deep=True)
    if isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node, deep=True)
    return loader.construct_scalar(node)


_Loader.add_multi_constructor("tag:yaml.org,2002:python/", _any_python_tag)


def load_env_yaml(run_dir) -> dict:
    with open(Path(run_dir) / "params" / "env.yaml") as f:
        return yaml.load(f, Loader=_Loader)


def load_agent_yaml(run_dir) -> dict:
    with open(Path(run_dir) / "params" / "agent.yaml") as f:
        return yaml.load(f, Loader=_Loader)


def find_runs(root: Path = WEEK5_LOGS) -> list:
    """โฟลเดอร์ run ทั้งหมดใต้ root (มี params/env.yaml) เรียงตามชื่อ (= เวลา)"""
    if not root.exists():
        return []
    return sorted(p for p in root.iterdir() if (p / "params" / "env.yaml").exists())
