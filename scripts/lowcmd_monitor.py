from collections.abc import ByteString
from numpy import ndarray
from numpy.core import numerictypes
from openpyxl import compat
import  argparse
import csv
import sys
import threading
import time 
from pathlib import Path 
import numpy as np
import yaml
sys.pth .insert(0,str(Path(__file).resolve().parent))
from lowstate_monitor import G1_23DOF_JOINTS, NUM_SLOTS, UNUSED_SLOTS

REPO_ROOT = Path(__file__).resolve().parents[4]
CONFIG_YAML = REPO_ROOT / "deploy/robots/g1_23dof/config/config.yaml"
DEFAULT_DEPLOY = REPO_ROOT / "deploy/robots/g1_23dof/config/policy/velocity/v0/params/deploy.yaml"

GAIN_TOL =0.06

def expected_gains(config_yaml: Path,deploy_yaml: Path) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    fsm = yaml.safe_load(open(config_yaml))["FSM"]
    dep = yaml.safe_load(open(deploy_yaml))
    vel_kp = np.zeros(NUM_SLOTS)
    vel_kd = np.zeros(NUM_SLOTS)
    vel_kp[dep["joint_ids_map"]] = dep["stiffness"]
    vel_kd[dep["joint_ids_map"]] = dep["damping"]
    return {
    "Passive": (np.zeros(NUM_SLOTS), np.array(fsm["Passive"]["kd"], float)),
    "FixStand": (np.array(fsm["FixStand"]["kp"], float), np.array(fsm["FixStand"]["kd"], float)),
    "Velocity": (vel_kp, vel_kd),
  }

def gains_match(a: np.ndarray , b: np.ndarray ) -> np.ndarray:
    return np.abs(a - b) <= np.maximum(GAIN_TOL * np.abs(b), 1e-3)

def classify (kp: np.ndarray, kd: np.ndarray, expected: dict) -> tuple[str, list[int]]:
    best,best_bad = "unknown", list (range(NUM_SLOTS))
    