#!/usr/bin/env python3
"""Scripted joint motions on the gantry for actuator identification (G1 23-DoF).

Replaces g1_ctrl (never run both): publishes rt/lowcmd itself, moves to the
stand pose, then moves one joint at a time with
  step   +A, 0, -A, 0 (1.5 s each, 100 ms smooth edges)
  chirp  A * sin, 0.3 -> 2.5 Hz over 12 s (1 s fade in/out)
around that pose, with the training gains (deploy.yaml, default) or Unitree's
FixStand gains. Because the motion comes from the commands, pd_check.py
--replay can compare the real response with MuJoCo (armature, friction,
delay), which pushing by hand cannot.

Record with lowstate_monitor.py / lowcmd_monitor.py --log as usual; --segments
writes when each test ran (time.monotonic, same clock as the monitor logs).

Safety (robot hung on the gantry only):
  * the whole plan is checked against the MJCF limits (0.1 rad margin) and a
    target speed limit before anything is sent; --dry-run prints it only
  * damping (kp 0, Passive kd) on: remote L2 + B, Ctrl-C, LowState older than
    50 ms, a joint more than 0.5 rad from its target, motor > 70 C, a motor
    offline (vol 0 or motorstate != 0, real robot only); also at the end
  * refuses to start while rt/lowcmd is published (g1_ctrl) or, on the real
    robot, while the built-in controller runs (motion_mode.py check / release)

  python deploy/robots/g1_23dof/scripts/sysid_motion.py --dry-run
  python deploy/robots/g1_23dof/scripts/sysid_motion.py --iface lo --domain 1 --yes   # unitree_mujoco
  python deploy/robots/g1_23dof/scripts/sysid_motion.py --groups armL,armR,waist --segments ~/sysid_seg.csv
"""

import argparse  # อ่าน argument จาก command line
import csv  # เขียนไฟล์ segments (.csv)
import sys  # sys.path และ sys.exit
import time  # time.monotonic / perf_counter สำหรับจับเวลาและคุมจังหวะ loop
from dataclasses import dataclass  # ใช้สร้าง class Segment แบบสั้นๆ
from pathlib import Path  # จัดการ path ของไฟล์

import numpy as np  # คำนวณ array ของ q, kp, kd ทั้ง 29 slot
import yaml  # อ่าน config.yaml และ deploy.yaml

# เพิ่มโฟลเดอร์ scripts/ เข้า sys.path เพื่อ import สคริปต์ข้างเคียงได้
sys.path.insert(0, str(Path(__file__).resolve().parent))
# CONFIG_YAML    = path ของ config.yaml (gain ของ FSM: Passive / FixStand)
# DEFAULT_DEPLOY = path ของ deploy.yaml ของ policy velocity (gain ตอนเทรน + ท่ายืน)
from lowcmd_monitor import CONFIG_YAML, DEFAULT_DEPLOY  # noqa: E402
# DEFAULT_MJCF      = ไฟล์ MJCF ของหุ่น (ใช้อ่าน joint limit)
# G1_23DOF_JOINTS   = dict {slot: ชื่อข้อต่อ} เฉพาะ 23 slot ที่ใช้จริง
# NUM_SLOTS         = 29 (จำนวน slot มอเตอร์ทั้งหมดใน LowCmd ของ G1)
# load_joint_limits = ฟังก์ชันอ่าน {ชื่อข้อต่อ: (lo, hi)} จาก MJCF
from lowstate_monitor import DEFAULT_MJCF, G1_23DOF_JOINTS, NUM_SLOTS, load_joint_limits  # noqa: E402

# ---------------------------------------------------------------------------
# ค่าคงที่ด้านเวลา (หน่วยวินาที)
# ---------------------------------------------------------------------------
CONTROL_DT = 0.002  # คาบของ control loop = 2 ms (500 Hz)
RAMP_S = 3.0  # เวลาค่อยๆ เคลื่อนจากท่าปัจจุบันเข้าท่ายืน
HOLD_S = 2.0  # เวลานิ่งในท่ายืนก่อนเริ่ม test แรก
REST_S = 1.0  # เวลาพักระหว่าง test แต่ละอัน
STEP_HOLD_S = 1.5  # เวลาค้างแต่ละระดับของ step (+A, 0, -A, 0)
STEP_EDGE_S = 0.1  # เวลาของขอบ step (เปลี่ยนระดับแบบนุ่มด้วย raised cosine)
CHIRP_S = 12.0  # ความยาวของ chirp
CHIRP_F0, CHIRP_F1 = 0.3, 2.5  # ความถี่เริ่มต้น / ปลายของ chirp (Hz)
FADE_S = 1.0  # เวลา fade in / fade out ของแอมพลิจูด chirp
END_HOLD_S = 1.0  # เวลานิ่งในท่ายืนหลัง test สุดท้าย
DAMP_EXIT_S = 1.0  # เวลาส่งคำสั่ง damping ก่อนออกจากโปรแกรม

# ---------------------------------------------------------------------------
# ค่าคงที่ด้านความปลอดภัย
# ---------------------------------------------------------------------------
LIMIT_MARGIN = 0.1  # rad from the MJCF range  -- ระยะห่างขั้นต่ำจากขอบ joint limit
MAX_TARGET_SPEED = 6.0  # rad/s, planned q_des speed  -- ความเร็วสูงสุดของ q_des ในแผน
STALE_S = 0.05  # ถ้าไม่ได้ LowState ใหม่เกิน 50 ms ถือว่าขาดการติดต่อ -> damping
MAX_TRACK_ERR = 0.5  # rad, after the ramp  -- ถ้าข้อต่อห่างจาก q_des เกินนี้ -> damping
MAX_TEMP_C = 70  # อุณหภูมิมอเตอร์สูงสุด (°C) -> เกินแล้ว damping
LOWCMD_LISTEN_S = 0.5  # เวลาฟัง rt/lowcmd ก่อนเริ่ม เพื่อเช็คว่า g1_ctrl ไม่ได้รันอยู่
STATUS_S = 0.5  # พิมพ์สถานะบนหน้าจอทุกกี่วินาที

# Remote buttons in LowState.wireless_remote (unitree_joystick.hpp BtnUnion).
# (byte index, bit mask) ของปุ่มบนรีโมท ใช้กด L2 + B พร้อมกันเพื่อหยุดฉุกเฉิน
L2_BYTE, L2_MASK = 2, 0x20
B_BYTE, B_MASK = 3, 0x02

# Joint name suffix -> (step amplitude, chirp amplitude), rad.
# แอมพลิจูดของการขยับ แยกตามชนิดข้อต่อ (จับคู่ด้วยท้ายชื่อข้อต่อ)
AMPLITUDE = {
  "hip_pitch": (0.15, 0.10),
  "hip_roll": (0.10, 0.08),
  "hip_yaw": (0.10, 0.08),
  "knee": (0.15, 0.10),
  "ankle_pitch": (0.10, 0.08),
  "ankle_roll": (0.08, 0.05),
  "waist_yaw": (0.15, 0.10),
  "shoulder_pitch": (0.20, 0.15),
  "shoulder_roll": (0.12, 0.08),
  "shoulder_yaw": (0.20, 0.15),
  "elbow": (0.20, 0.15),
  "wrist_roll": (0.30, 0.20),
}
# กลุ่มข้อต่อ -> รายการ slot มอเตอร์ (เลือกด้วย --groups)
GROUPS = {
  "armL": [15, 16, 17, 18, 19],  # แขนซ้าย: shoulder pitch/roll/yaw, elbow, wrist roll
  "armR": [22, 23, 24, 25, 26],  # แขนขวา
  "waist": [12],  # waist yaw
  "legL": [0, 1, 2, 3, 4, 5],  # ขาซ้าย: hip pitch/roll/yaw, knee, ankle pitch/roll
  "legR": [6, 7, 8, 9, 10, 11],  # ขาขวา
}


# ---------------------------------------------------------------------------
# ส่วนที่ 1: โครงสร้างของแผนการทดสอบ
# ---------------------------------------------------------------------------
@dataclass
class Segment:
  """ช่วงเวลาหนึ่งในแผน (ramp, hold หรือ test ของข้อต่อหนึ่ง)."""

  name: str  # ชื่อที่แสดง เช่น "left_elbow" หรือ "hold"
  slot: int  # -1 = all joints (ramp, hold)  -- slot มอเตอร์ที่ขยับใน segment นี้
  kind: str  # ชนิด: "ramp", "hold", "step" หรือ "chirp"
  t0: float  # เวลาเริ่ม (วินาที นับจากเริ่มแผน)
  t1: float  # เวลาจบ (วินาที นับจากเริ่มแผน)
  amp: float = 0.0  # แอมพลิจูด (rad) ใช้กับ step / chirp เท่านั้น


def amplitudes(slot: int) -> tuple[float, float]:
  """คืน (แอมพลิจูด step, แอมพลิจูด chirp) ของ slot นี้ จากตาราง AMPLITUDE."""
  name = G1_23DOF_JOINTS[slot].removesuffix("_joint")  # เช่น "left_hip_pitch"
  for key, amp in AMPLITUDE.items():
    if name.endswith(key):  # จับคู่ด้วยท้ายชื่อ ใช้ได้ทั้งซ้ายและขวา
      return amp
  raise KeyError(name)  # ข้อต่อที่ไม่มีในตาราง -> error


# ---------------------------------------------------------------------------
# ส่วนที่ 2: สร้างสัญญาณ (offset จากท่ายืน)
# ---------------------------------------------------------------------------
def smooth(x: np.ndarray | float) -> np.ndarray | float:
  """0 -> 1 raised cosine on x in [0, 1].

  เปลี่ยนจาก 0 ไป 1 แบบนุ่มนวล ความเร็วเป็น 0 ที่ปลายทั้งสองข้าง (x < 0 ได้ 0, x > 1 ได้ 1)
  """
  x = np.clip(x, 0.0, 1.0)
  return 0.5 - 0.5 * np.cos(np.pi * x)


def step_offset(t: float, amp: float) -> float:
  """Offset ของ step test ที่เวลา t (นับจากต้น segment): +A, 0, -A, 0 ระดับละ STEP_HOLD_S."""
  levels = [amp, 0.0, -amp, 0.0]  # ระดับเป้าหมายทั้ง 4 ช่วง
  k = min(int(t // STEP_HOLD_S), 3)  # ตอนนี้อยู่ช่วงที่ k (0..3)
  prev = 0.0 if k == 0 else levels[k - 1]  # ระดับของช่วงก่อนหน้า (จุดเริ่มของขอบ)
  # เลื่อนจาก prev ไป levels[k] ภายใน STEP_EDGE_S แรกของช่วง แล้วค้างไว้
  return prev + (levels[k] - prev) * smooth((t - k * STEP_HOLD_S) / STEP_EDGE_S)


def chirp_offset(t: float, amp: float) -> float:
  """Offset ของ chirp test ที่เวลา t: sine ความถี่เพิ่มเชิงเส้นจาก CHIRP_F0 ถึง CHIRP_F1."""
  # phase = 2π ∫ f(t) dt โดย f(t) = f0 + (f1 - f0) t / T
  phase = 2 * np.pi * (CHIRP_F0 * t + (CHIRP_F1 - CHIRP_F0) * t * t / (2 * CHIRP_S))
  # ค่อยๆ เพิ่มแอมพลิจูดตอนต้น และลดตอนท้าย (FADE_S) จะได้ไม่กระชาก
  fade = smooth(t / FADE_S) * smooth((CHIRP_S - t) / FADE_S)
  return amp * fade * np.sin(phase)


# ---------------------------------------------------------------------------
# ส่วนที่ 3: วางแผนและตรวจแผน
# ---------------------------------------------------------------------------
def build_plan(slots: list[int], kinds: list[str]) -> list[Segment]:
  """สร้างลำดับ segment ทั้งหมด: ramp -> hold -> (test ทีละข้อต่อ ทีละชนิด) -> hold."""
  plan = [Segment("ramp to stand pose", -1, "ramp", 0.0, RAMP_S), Segment("hold", -1, "hold", RAMP_S, RAMP_S + HOLD_S)]
  t = RAMP_S + HOLD_S  # เวลาเริ่มของ test ถัดไป
  for slot in slots:
    a_step, a_chirp = amplitudes(slot)
    for kind in kinds:
      dur = 4 * STEP_HOLD_S if kind == "step" else CHIRP_S  # ความยาวของ test นี้
      amp = a_step if kind == "step" else a_chirp
      plan.append(Segment(G1_23DOF_JOINTS[slot].removesuffix("_joint"), slot, kind, t, t + dur, amp))
      t += dur + REST_S  # เว้นช่วงพักก่อน test ถัดไป
  plan.append(Segment("hold", -1, "hold", t, t + END_HOLD_S))
  return plan


def offsets(plan: list[Segment], t: float) -> np.ndarray:
  """Offset (rad) ของทั้ง 29 slot ที่เวลา t; ช่วงที่ไม่มี test เป็น 0 ทั้งหมด."""
  off = np.zeros(NUM_SLOTS)
  for seg in plan:
    if seg.slot >= 0 and seg.t0 <= t < seg.t1:  # เฉพาะ segment ที่เป็น test และกำลังรันอยู่
      tau = t - seg.t0  # เวลานับจากต้น segment (ไม่ใช่แรงบิด)
      off[seg.slot] = step_offset(tau, seg.amp) if seg.kind == "step" else chirp_offset(tau, seg.amp)
  return off


def check_plan(plan: list[Segment], base: np.ndarray, limits: dict) -> list[str]:
  """จำลอง q_des ทั้งแผน (หลังช่วง ramp) แล้วคืนรายการปัญหา; list ว่าง = ผ่าน."""
  problems = []
  ts = np.arange(plan[1].t1, plan[-1].t1, CONTROL_DT)  # ทุก tick ตั้งแต่จบ hold แรกจนจบแผน
  q = np.array([base + offsets(plan, t) for t in ts])  # q_des ทุก tick, shape (N, 29)
  speed = np.abs(np.diff(q, axis=0)) / CONTROL_DT  # ความเร็วของ q_des (rad/s)
  for slot, name in G1_23DOF_JOINTS.items():
    lo, hi = limits[name]  # joint limit จาก MJCF
    if q[:, slot].min() < lo + LIMIT_MARGIN or q[:, slot].max() > hi - LIMIT_MARGIN:
      problems.append(f"{name}: target {q[:, slot].min():+.3f}..{q[:, slot].max():+.3f} outside [{lo:+.3f}, {hi:+.3f}] - margin")
    if speed[:, slot].max() > MAX_TARGET_SPEED:
      problems.append(f"{name}: target speed {speed[:, slot].max():.1f} rad/s > {MAX_TARGET_SPEED}")
  return problems


def load_gains(which: str, deploy: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
  """29-slot kp, kd, stand pose and Passive kd (used slots only, others 0).

  which = "train"   -> kp/kd จาก deploy.yaml (ค่าเดียวกับตอนเทรน)
  which = "unitree" -> kp/kd ของ FixStand จาก config.yaml
  """
  dep = yaml.safe_load(open(deploy))  # เนื้อหา deploy.yaml
  fsm = yaml.safe_load(open(CONFIG_YAML))["FSM"]  # ส่วน FSM ของ config.yaml
  ids = dep["joint_ids_map"]  # ลำดับข้อต่อของ policy -> slot มอเตอร์
  kp, kd, base = np.zeros(NUM_SLOTS), np.zeros(NUM_SLOTS), np.zeros(NUM_SLOTS)
  base[ids] = dep["default_joint_pos"]  # ท่ายืน (q อ้างอิงที่ test ขยับรอบๆ)
  if which == "train":
    kp[ids], kd[ids] = dep["stiffness"], dep["damping"]
  else:
    kp[ids] = np.array(fsm["FixStand"]["kp"], float)[ids]
    kd[ids] = np.array(fsm["FixStand"]["kd"], float)[ids]
  passive_kd = np.zeros(NUM_SLOTS)  # kd ตอน damping (kp = 0)
  passive_kd[ids] = np.array(fsm["Passive"]["kd"], float)[ids]
  return kp, kd, base, passive_kd


def print_plan(plan: list[Segment], kp: np.ndarray, kd: np.ndarray, base: np.ndarray) -> None:
  """พิมพ์ตารางแผน: เวลาเริ่ม, ความยาว, ชื่อ test, ชนิด, แอมพลิจูด, ท่ายืน, kp, kd และเวลารวม."""
  print(f"{'t start':>8} {'dur':>5}  {'test':<20} {'kind':<6} {'amp':>5} {'base':>6} {'kp':>6} {'kd':>4}")
  for seg in plan:
    if seg.slot < 0:  # ramp / hold: ไม่มีข้อต่อเฉพาะ
      print(f"{seg.t0:8.1f} {seg.t1 - seg.t0:5.1f}  {seg.name:<20} {seg.kind:<6}")
    else:
      s = seg.slot
      print(f"{seg.t0:8.1f} {seg.t1 - seg.t0:5.1f}  {seg.name:<20} {seg.kind:<6} {seg.amp:5.2f} {base[s]:+6.2f} {kp[s]:6.1f} {kd[s]:4.1f}")
  print(f"total {plan[-1].t1:.0f} s ({plan[-1].t1 / 60:.1f} min)")


# ---------------------------------------------------------------------------
# ส่วนที่ 4: ติดต่อกับหุ่น (DDS)
# ---------------------------------------------------------------------------
class Robot:
  """Latest LowState plus the rt/lowcmd publisher."""

  def __init__(self) -> None:
    # import SDK เฉพาะตอนสร้าง Robot (ตอนต่อหุ่นจริง / sim)
    from unitree_sdk2py.core.channel import ChannelPublisher, ChannelSubscriber
    from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowCmd_
    from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowCmd_, LowState_
    from unitree_sdk2py.utils.crc import CRC

    self.state = None  # LowState ล่าสุดที่ได้รับ (None = ยังไม่เคยได้)
    self.t_state = 0.0  # เวลา (time.monotonic) ที่ได้ LowState ล่าสุด ใช้เช็ค stale
    self.sub = ChannelSubscriber("rt/lowstate", LowState_)  # รับสถานะมอเตอร์ / IMU / รีโมท
    self.sub.Init(self._on_state, 10)  # callback ทุก message, queue 10
    self.pub = ChannelPublisher("rt/lowcmd", LowCmd_)  # ส่งคำสั่งมอเตอร์
    self.pub.Init()
    self.cmd = unitree_hg_msg_dds__LowCmd_()  # message LowCmd ที่ใช้ซ้ำทุก tick
    self.crc = CRC()  # ตัวคำนวณ CRC (หุ่นไม่รับคำสั่งที่ CRC ผิด)

  def _on_state(self, msg) -> None:
    """Callback จาก DDS thread: เก็บ LowState ล่าสุดและเวลาที่ได้รับ."""
    self.state = msg
    self.t_state = time.monotonic()

  def q(self) -> np.ndarray:
    """ตำแหน่งข้อต่อปัจจุบันของทั้ง 29 slot (rad) จาก LowState ล่าสุด."""
    return np.array([self.state.motor_state[i].q for i in range(NUM_SLOTS)])

  def send(self, q: np.ndarray, kp: np.ndarray, kd: np.ndarray) -> None:
    """ส่งคำสั่ง PD: tau = kp (q - q_จริง) + kd (0 - dq_จริง), ไม่มี feed-forward."""
    self.cmd.mode_pr = 0  # โหมดข้อเท้า PR (pitch/roll)
    self.cmd.mode_machine = self.state.mode_machine  # ต้องตรงกับที่หุ่นรายงาน
    for i in range(NUM_SLOTS):
      m = self.cmd.motor_cmd[i]
      # mode 1 = เปิดมอเตอร์, q = ตำแหน่งเป้าหมาย, dq = 0, tau = 0
      m.mode, m.q, m.dq, m.tau, m.kp, m.kd = 1, float(q[i]), 0.0, 0.0, float(kp[i]), float(kd[i])
    self.cmd.crc = self.crc.Crc(self.cmd)
    self.pub.Write(self.cmd)


def lowcmd_traffic(listen_s: float) -> int:
  """ฟัง rt/lowcmd เป็นเวลา listen_s แล้วคืนจำนวน message (> 0 = มีโปรแกรมอื่นสั่งหุ่นอยู่)."""
  from unitree_sdk2py.core.channel import ChannelSubscriber
  from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowCmd_

  count = [0]  # ใช้ list เพื่อให้ lambda แก้ค่าได้
  sub = ChannelSubscriber("rt/lowcmd", LowCmd_)
  sub.Init(lambda _: count.__setitem__(0, count[0] + 1), 10)
  time.sleep(listen_s)
  sub.Close()
  return count[0]


# ---------------------------------------------------------------------------
# ส่วนที่ 5: ความปลอดภัยและบันทึกผล
# ---------------------------------------------------------------------------
def fault(robot: Robot, q_des: np.ndarray, check_err: bool, real: bool) -> str | None:
  """Reason to switch to damping, or None.

  check_err = เช็ค tracking error ด้วยหรือไม่ (ปิดช่วง ramp เพราะตอนนั้นห่างจากเป้าเป็นปกติ)
  real      = True เมื่อรันกับหุ่นจริง (เช็คมอเตอร์ offline เพิ่ม)
  """
  if time.monotonic() - robot.t_state > STALE_S:
    return f"LowState older than {STALE_S * 1e3:.0f} ms"
  st = robot.state
  rc = st.wireless_remote  # bytes ของรีโมท
  if rc[L2_BYTE] & L2_MASK and rc[B_BYTE] & B_MASK:
    return "remote L2 + B"
  for slot, name in G1_23DOF_JOINTS.items():
    ms = st.motor_state[slot]  # สถานะของมอเตอร์ตัวนี้
    if check_err and abs(ms.q - q_des[slot]) > MAX_TRACK_ERR:
      return f"{name} {abs(ms.q - q_des[slot]):.2f} rad from target"
    if ms.temperature[0] > MAX_TEMP_C:
      return f"{name} {ms.temperature[0]} C"
    if real and (ms.vol == 0 or ms.motorstate != 0):  # ไม่มีไฟ หรือมี error code
      return f"{name} offline (vol {ms.vol}, motorstate {ms.motorstate:#x})"
  return None


def write_segments(path: Path, plan: list[Segment], t_start: float, t_stop: float) -> None:
  """เขียน CSV เวลาเริ่ม / จบของแต่ละ segment (clock time.monotonic เดียวกับ log ของ monitor).

  t_start = เวลาที่เริ่มแผนจริง, t_stop = เวลาที่หยุด (จบแผนหรือ fault)
  เขียนเฉพาะ segment ที่เริ่มไปแล้ว; completed = 1 ถ้ารันจนจบ, 0 ถ้าถูกตัดกลางทาง
  """
  with open(path, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["test", "slot", "kind", "amp", "t0", "t1", "completed"])
    for seg in plan:
      if seg.t0 + t_start < t_stop:
        w.writerow([seg.name, seg.slot, seg.kind, seg.amp, f"{t_start + seg.t0:.4f}",
                    f"{t_start + min(seg.t1, t_stop - t_start):.4f}", int(seg.t1 + t_start <= t_stop)])
  print(f"segments written to {path}")


# ---------------------------------------------------------------------------
# ส่วนที่ 6: main
# ---------------------------------------------------------------------------
def main() -> int:
  """เลือกข้อต่อ -> วางแผนและตรวจ -> เช็คความพร้อม -> control loop -> damping -> บันทึก.

  exit code: 0 = จบตามแผน, 1 = ไม่เริ่ม (แผนผิด / หุ่นไม่พร้อม / ไม่ยืนยัน), 2 = หยุดเพราะ fault หรือ Ctrl-C
  """
  parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument("--iface", default="enp43s0", help="enp43s0 for the robot, lo for unitree_mujoco")
  parser.add_argument("--domain", type=int, default=0)  # DDS domain (หุ่นจริง 0, unitree_mujoco มักเป็น 1)
  parser.add_argument("--gains", choices=("train", "unitree"), default="train")
  parser.add_argument("--deploy", type=Path, default=DEFAULT_DEPLOY, help="deploy.yaml for train gains and the pose")
  parser.add_argument("--groups", default="armL,armR,waist,legL,legR", help=f"comma list of {','.join(GROUPS)}")
  parser.add_argument("--joints", default="", help="only joints whose name contains one of these (comma list)")
  parser.add_argument("--kinds", default="step,chirp")  # ชนิด test ที่จะรัน
  parser.add_argument("--segments", type=Path, default=None, help="CSV with the start/end time of each test")
  parser.add_argument("--dry-run", action="store_true", help="print and check the plan, send nothing")
  parser.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
  args = parser.parse_args()

  # --- เลือกข้อต่อที่จะทดสอบ ---
  slots = [s for g in args.groups.split(",") for s in GROUPS[g]]  # slot จากกลุ่มที่เลือก
  if args.joints:  # กรองต่อด้วยชื่อ เช่น --joints elbow,knee
    keys = args.joints.split(",")
    slots = [s for s in slots if any(k in G1_23DOF_JOINTS[s] for k in keys)]
  kinds = args.kinds.split(",")  # เช่น ["step", "chirp"]
  if not slots or any(k not in ("step", "chirp") for k in kinds):
    parser.error("no joints selected or unknown kind")

  # --- วางแผนและตรวจแผน (ยังไม่ติดต่อหุ่น) ---
  kp, kd, base, passive_kd = load_gains(args.gains, args.deploy)
  plan = build_plan(slots, kinds)
  print(f"gains: {args.gains} ({args.deploy.parent.parent.name if args.gains == 'train' else 'config.yaml FixStand'})")
  print_plan(plan, kp, kd, base)
  problems = check_plan(plan, base, load_joint_limits(DEFAULT_MJCF))
  for p in problems:
    print(f"PLAN ERROR: {p}")
  if problems:
    return 1
  print("plan OK: inside MJCF limits with margin, target speed limited")
  if args.dry_run:
    return 0

  # --- เช็คว่าหุ่นพร้อม ---
  from unitree_sdk2py.core.channel import ChannelFactoryInitialize

  real = args.iface != "lo"  # lo = sim (unitree_mujoco), อย่างอื่น = หุ่นจริง
  ChannelFactoryInitialize(args.domain, args.iface)  # เริ่ม DDS บน interface ที่เลือก
  n_cmd = lowcmd_traffic(LOWCMD_LISTEN_S)  # มีโปรแกรมอื่นส่ง lowcmd อยู่ไหม
  if n_cmd:
    print(f"refusing: {n_cmd} rt/lowcmd messages in {LOWCMD_LISTEN_S} s (stop g1_ctrl first)")
    return 1
  if real:  # หุ่นจริง: controller ในตัวของ Unitree ต้องถูก release แล้ว
    from unitree_sdk2py.comm.motion_switcher.motion_switcher_client import MotionSwitcherClient

    msc = MotionSwitcherClient()  # client ของบริการสลับโหมด motion
    msc.SetTimeout(5.0)
    msc.Init()
    code, data = msc.CheckMode()  # data["name"] ว่าง = ไม่มี controller ในตัวรันอยู่
    if code != 0 or (data or {}).get("name"):
      print(f"refusing: built-in controller not released (code {code}, mode {data}); run motion_mode.py release")
      return 1

  robot = Robot()
  t_wait = time.monotonic()
  while robot.state is None and time.monotonic() - t_wait < 2.0:  # รอ LowState แรกไม่เกิน 2 s
    time.sleep(0.01)
  if robot.state is None:
    print("no rt/lowstate: wrong interface/domain, robot off, or lo multicast off")
    return 1
  if not args.yes:
    print("The robot will move to the stand pose and then move each joint. Is it hung on the gantry, area clear?")
    if input("Type 'yes' to start: ").strip().lower() != "yes":
      return 1

  # --- control loop 500 Hz ---
  q_start = robot.q()  # ท่าตอนเริ่ม (จุดเริ่มของ ramp)
  t_start = time.monotonic()  # เวลา 0 ของแผน
  # reason      = เหตุผลที่หยุด loop
  # next_status = เวลาที่จะพิมพ์สถานะครั้งถัดไป (นับจาก t_start)
  # next_tick   = เวลา perf_counter ของ tick ถัดไป (คุมจังหวะ 2 ms ไม่ให้ drift)
  reason, next_status, next_tick = None, 0.0, time.perf_counter()
  seg_i = 0  # index ของ segment ปัจจุบัน (ใช้แสดงผลเท่านั้น)
  try:
    while True:
      t = time.monotonic() - t_start  # เวลานับจากเริ่มแผน
      if t >= plan[-1].t1:
        reason = "plan finished"
        break
      a = smooth(t / RAMP_S)  # สัดส่วน ramp: 0 -> 1 ใน RAMP_S แล้วค้างที่ 1
      q_des = q_start + (base - q_start) * a + offsets(plan, t)  # ตำแหน่งเป้าหมายของ tick นี้
      q_des[[s for s in range(NUM_SLOTS) if s not in G1_23DOF_JOINTS]] = 0.0  # slot ที่ไม่ใช้ = 0
      reason = fault(robot, q_des, t > RAMP_S, real)
      if reason:
        break
      robot.send(q_des, kp, kd)
      while seg_i + 1 < len(plan) and t >= plan[seg_i + 1].t0:  # เลื่อนไป segment ที่กำลังรัน
        seg_i += 1
      if t >= next_status:
        seg = plan[seg_i]
        print(f"\r{t:6.1f}/{plan[-1].t1:.0f} s  {seg.name:<20} {seg.kind:<6}", end="", flush=True)
        next_status = t + STATUS_S
      next_tick += CONTROL_DT
      time.sleep(max(0.0, next_tick - time.perf_counter()))  # รอจนถึง tick ถัดไป
  except KeyboardInterrupt:
    reason = "Ctrl-C"
  t_stop = time.monotonic()  # เวลาที่หยุด (ใช้ใน write_segments)
  print(f"\n-> damping ({reason})")

  # --- damping ก่อนออก ---
  # Damping until the end: the last command the motors keep is kp 0.
  zeros = np.zeros(NUM_SLOTS)  # kp = 0 ทุก slot
  t_damp = time.monotonic()  # เวลาเริ่ม damping
  try:
    while time.monotonic() - t_damp < DAMP_EXIT_S:
      if robot.state is not None:
        robot.send(robot.q(), zeros, passive_kd)  # q ไม่มีผลเพราะ kp = 0
      time.sleep(CONTROL_DT)
  except KeyboardInterrupt:
    pass
  if args.segments:
    write_segments(args.segments, plan, t_start, t_stop)
  return 0 if reason == "plan finished" else 2


if __name__ == "__main__":
  sys.exit(main())
