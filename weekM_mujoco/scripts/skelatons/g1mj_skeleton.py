"""g1mj_skeleton.py: ไลบรารีกลางของโมดูล M (MuJoCo ล้วน ไม่มี DDS) โครงให้เติม

ไฟล์ m1–m7 ใน skelatons/ import จากไฟล์นี้ **เติม TODO ให้เทสต์ผ่านก่อน** (ทำไปพร้อมงาน M1–M6 ก็ได้)
รันตรงๆ = เทสต์ (ไม่เปิดหน้าต่าง):  python3 g1mj_skeleton.py
ส่วนที่ "ให้ไว้แล้ว": load, build_model, save_xml, load_deploy, run, view_static (อ่านให้เข้าใจ แต่ไม่ต้องเขียน)
อ้างอิง: weekM_mujoco/docs/python_api.md · เฉลย: ../complete/g1mj.py
ใช้ Python ระบบ (`python3`, มี mujoco 3.14 + onnxruntime) ไม่ใช่ conda g1_sdk

แนวคิดหลัก: unitree_mujoco (sim ที่เราใช้ทุกสัปดาห์) ก็คือโค้ดแบบในไฟล์นี้ เขียนด้วย C++
  - actuator index i  = slot i ของ LowState  (29 ตัว เรียงตาม SDK)
  - sensordata[i], [i+29], [i+58] = q, dq, tau ของ slot i  (unitree_sdk2_bridge.h:183–194)
  - ctrl[i] = tau + kp(q_des − q) + kd(dq_des − dq)          (bridge ทำทุก physics step)
  - ElasticBand = แรงสปริงดึง torso_link ขึ้นไปหาจุด (0, 0, 3)  (main.cc:53–85)
"""

import time
from pathlib import Path
from types import SimpleNamespace

import mujoco
import numpy as np
import yaml

G1_DIR = Path.home() / "nvidia/unitree/unitree_mujoco/unitree_robots/g1"
XML = G1_DIR / "scene_23dof.xml"                       # ไฟล์เดียวกับที่ ~/g1_study/sim/config.yaml ใช้
DEPLOY = (Path.home() / "nvidia/unitree/unitree_rl_mjlab/deploy/robots/g1_23dof/config/policy/velocity/v0"
          / "params/deploy.yaml")
MODELS = Path(__file__).resolve().parents[2] / "models"   # weekM_mujoco/models: ที่เก็บ XML ที่เราแก้เอง
UNUSED_SLOTS = (13, 14, 20, 21, 27, 28)                    # ข้อต่อหลอก (body ลอยอยู่ที่ z = 20 m)
G = 9.81

# GLFW key code ที่ใช้ใน key_callback ของ viewer (= ASCII ของตัวพิมพ์ใหญ่/ตัวเลข)
KEY_SPACE, KEY_7, KEY_8, KEY_9 = 32, 55, 56, 57
KEY_UP, KEY_DOWN = 265, 264


# ---------------------------------------------------------------------------
# โหลดโมเดล
# ---------------------------------------------------------------------------
def load(xml: Path = XML):
    """คืน (MjModel, MjData)  ·  MjModel = ค่าคงที่ (มวล, ลิมิต, timestep)  MjData = สถานะที่เปลี่ยนทุก step"""
    m = mujoco.MjModel.from_xml_path(str(xml))
    return m, mujoco.MjData(m)


def build_model(arm_frictionloss=None, frictionloss=None, armature=None, step_h=0.0, step_x=1.0,
                timestep=None, xml: Path = XML):
    """แก้โมเดลด้วยโค้ด (MjSpec) แทนการแก้ไฟล์ XML · คืน (spec, m, d)

    arm_frictionloss : frictionloss ของข้อต่อแขน (shoulder/elbow/wrist)
    frictionloss / armature : ของทุกข้อต่อ 23 ตัว (ไม่รวมข้อต่อหลอก)
    step_h : ใส่ขั้นบันได 1 ขั้น สูง step_h [m] เริ่มที่ x = step_x ยาว 3 m (0 = ไม่ใส่)
    """
    spec = mujoco.MjSpec.from_file(str(xml))
    for j in spec.joints:
        if j.type != mujoco.mjtJoint.mjJNT_HINGE or j.frictionloss == 0.0:   # ข้าม free joint + ข้อต่อหลอก
            continue
        if frictionloss is not None:
            j.frictionloss = frictionloss
        if armature is not None:
            j.armature = armature
        if arm_frictionloss is not None and any(k in j.name for k in ("shoulder", "elbow", "wrist")):
            j.frictionloss = arm_frictionloss
    if step_h > 0:
        spec.worldbody.add_geom(name="step", type=mujoco.mjtGeom.mjGEOM_BOX,
                                size=[1.5, 1.0, step_h / 2],                 # size = ครึ่งความยาว (half-size)
                                pos=[step_x + 1.5, 0.0, step_h / 2], rgba=[0.8, 0.5, 0.2, 1])
    if timestep is not None:
        spec.option.timestep = timestep
    m = spec.compile()
    return spec, m, mujoco.MjData(m)


def save_xml(spec, name: str) -> Path:
    """เขียน XML ของ spec ลง weekM_mujoco/models/<name>.xml (meshdir เป็น path เต็ม เปิดจากที่ไหนก็ได้)"""
    MODELS.mkdir(exist_ok=True)
    spec.meshdir = str(G1_DIR / "meshes") + "/"
    out = MODELS / f"{name}.xml"
    out.write_text(spec.to_xml())
    return out


# ---------------------------------------------------------------------------
# slot ของ SDK ↔ index ใน MuJoCo
# ---------------------------------------------------------------------------
def slot_table(m) -> SimpleNamespace:
    """ตารางของ actuator 29 ตัว (index = slot ของ LowState)

    joint_id[i] : joint ที่ actuator i ขับ   (ลำดับ joint ใน XML ≠ ลำดับ slot! ข้อต่อหลอกอยู่ท้าย XML)
    qadr[i]     : ตำแหน่งใน d.qpos   (เริ่มที่ 7 เพราะ free joint ใช้ 7 ช่อง)
    dadr[i]     : ตำแหน่งใน d.qvel   (เริ่มที่ 6 เพราะ free joint ใช้ 6 ช่อง)
    """
    # TODO [M1] jid = m.actuator_trnid[:, 0]  (คอลัมน์ 0 = id ของ joint ที่ actuator ขับ)
    # TODO [M1] qadr = m.jnt_qposadr[jid], dadr = m.jnt_dofadr[jid], names = [m.joint(j).name for j in jid]
    n = m.nu
    return SimpleNamespace(joint_id=np.zeros(n, int), qadr=np.zeros(n, int), dadr=np.zeros(n, int),
                           names=[""] * n, ctrlrange=m.actuator_ctrlrange.copy())


def motor_q(m, d) -> np.ndarray:
    """q ของ 29 slot อ่านจาก sensor แบบเดียวกับ bridge (= LowState.motor_state[i].q)"""
    # TODO [M1] sensordata ช่วงแรก m.nu ตัว (ใช้ .copy() เพราะ d.sensordata เป็น view ที่เปลี่ยนทุก step)
    return np.zeros(m.nu)


def motor_dq(m, d) -> np.ndarray:
    # TODO [M1] ช่วงที่สอง (ดู unitree_sdk2_bridge.h:193)
    return np.zeros(m.nu)


def motor_tau(m, d) -> np.ndarray:
    """jointactuatorfrc = แรงบิดที่ actuator ให้จริง (หลัง clamp ด้วย ctrlrange) = tau_est ใน sim"""
    # TODO [M1] ช่วงที่สาม
    return np.zeros(m.nu)


def load_deploy(path: Path = DEPLOY, nu: int = 29) -> SimpleNamespace:
    """kp, kd, ท่า default จาก deploy.yaml ของ policy v0 เรียงตาม slot (slot ที่ไม่ใช้ = 0)"""
    y = yaml.safe_load(open(path))
    out = SimpleNamespace(kp=np.zeros(nu), kd=np.zeros(nu), q_default=np.zeros(nu), ids=list(y["joint_ids_map"]))
    for i, s in enumerate(out.ids):
        out.kp[s] = y["stiffness"][i]
        out.kd[s] = y["damping"][i]
        out.q_default[s] = y["default_joint_pos"][i]
    return out


def set_pose(m, d, q_slot, base_z=None, base_quat=None) -> None:
    """ตั้งท่า (เขียน qpos ตรงๆ = "วาง" หุ่น ไม่ใช่สั่งมอเตอร์) แล้ว mj_forward ให้ตำแหน่ง/sensor อัพเดท"""
    # TODO [M2] เขียน q_slot ลง d.qpos ที่ตำแหน่ง slot_table(m).qadr
    # TODO [M2] ถ้ามี base_z → d.qpos[2] · ถ้ามี base_quat → d.qpos[3:7] (ลำดับ w, x, y, z)
    # TODO [M2] d.qvel[:] = 0 แล้ว mujoco.mj_forward(m, d)  (ไม่ forward = xpos / sensordata ยังเป็นค่าเก่า)
    pass


# ---------------------------------------------------------------------------
# ควบคุม
# ---------------------------------------------------------------------------
def pd_ctrl(m, d, q_des, kp, kd, dq_des=0.0, tau_ff=0.0) -> np.ndarray:
    """สูตรเดียวกับ unitree_sdk2_bridge.h:183  (MuJoCo จะ clamp ด้วย ctrlrange เอง ±25 Nm ที่ศอก)"""
    # TODO [M4] tau_ff + kp(q_des − q) + kd(dq_des − dq)  ใช้ motor_q / motor_dq
    return np.zeros(m.nu)


class ElasticBand:
    """แปลจาก unitree_mujoco/simulate/src/main.cc:53–85 · ปุ่มใน sim จริง: 9 เปิด/ปิด, 7 สั้นลง, 8 ยาวขึ้น"""

    def __init__(self, stiffness=200.0, damping=100.0, point=(0.0, 0.0, 3.0), length=0.0):
        self.stiffness, self.damping = stiffness, damping
        self.point = np.array(point, dtype=float)
        self.length = length
        self.enable = True
        self.f = np.zeros(3)

    def force(self, x, dx) -> np.ndarray:
        """x, dx = ตำแหน่ง/ความเร็วของฐาน (qpos[0:3], qvel[0:3]) · คืนแรง [N] ในกรอบโลก"""
        # TODO [M3] แปลจาก main.cc:57–75: delta = point − x, dist = |delta|, u = delta / dist
        # TODO [M3] v = dx · u   แรง = (stiffness·(dist − length) − damping·v) · u
        return np.zeros(3)

    def apply(self, m, d) -> None:
        """เขียนลง xfrc_applied ของ torso_link (6 ค่า: แรง 3 + โมเมนต์ 3 กรอบโลก)  ปิดอยู่ = แรง 0"""
        # TODO [M3] b = m.body("torso_link").id
        # TODO [M3] self.f = force(qpos[0:3], qvel[0:3]) ถ้า enable ไม่งั้น 0 → d.xfrc_applied[b, :3] = self.f
        pass

    def key(self, keycode) -> bool:
        """ปุ่มแบบเดียวกับ sim จริง · คืน True ถ้าเป็นปุ่มของหนังยาง"""
        if keycode == KEY_9:
            self.enable = not self.enable
        elif keycode in (KEY_7, KEY_UP):
            self.length -= 0.1
        elif keycode in (KEY_8, KEY_DOWN):
            self.length += 0.1
        else:
            return False
        print(f"[band] enable={self.enable} length={self.length:.1f} m", flush=True)
        return True


# ---------------------------------------------------------------------------
# อ่านค่า
# ---------------------------------------------------------------------------
def projected_gravity(quat) -> np.ndarray:
    """(w, x, y, z) → แรงโน้มถ่วงในกรอบลำตัว (สูตรเดียวกับ week4 obs.py)"""
    # TODO [M2] ลอกจาก week4 obs.py ได้ (หรือเขียนจาก docs/observations.md)
    return np.zeros(3)


def foot_forces(m, d):
    """แรงตั้งฉาก [N] ที่พื้น (geom ชื่อ floor หรือ step) ดันเท้าซ้าย/ขวา (body *_ankle_roll_link)"""
    # TODO [M6] ground = id ของ geom "floor" (และ "step" ถ้ามี: เช็คด้วย mj_name2id(...) >= 0)
    # TODO [M6] วน i in range(d.ncon): c = d.contact[i] · ถ้า geom หนึ่งเป็นพื้น ดูอีก geom ว่าอยู่ body เท้าไหน
    #           (m.geom_bodyid[geom] == m.body("left_ankle_roll_link").id ...)
    # TODO [M6] f6 = np.zeros(6); mujoco.mj_contactForce(m, d, i, f6); f6[0] = แรงตั้งฉาก → บวกเข้าเท้านั้น
    return 0.0, 0.0


def to_lowstate(m, d) -> SimpleNamespace:
    """แปลง MjData → object หน้าตาเหมือน LowState_ (field ที่ week4/obs.py ใช้) = สิ่งที่ bridge ทำก่อน publish"""
    # TODO [M7] motors = list ยาว 35 ของ SimpleNamespace(q=..., dq=..., tau_est=...)  (29 ตัวแรกจาก motor_q/dq/tau ที่เหลือ 0)
    # TODO [M7] imu = SimpleNamespace(quaternion=d.sensor("imu_quat").data.copy(), gyroscope=..."imu_gyro"...,
    #                                 accelerometer=..."imu_acc"...)
    motors = [SimpleNamespace(q=0.0, dq=0.0, tau_est=0.0) for _ in range(35)]
    imu = SimpleNamespace(quaternion=np.array([1.0, 0, 0, 0]), gyroscope=np.zeros(3), accelerometer=np.zeros(3))
    return SimpleNamespace(motor_state=motors, imu_state=imu, mode_machine=4)


# ---------------------------------------------------------------------------
# วน step (มี/ไม่มีหน้าต่าง)
# ---------------------------------------------------------------------------
def run(m, d, step_fn, duration=None, headless=False, key_callback=None, every=None, every_fn=None):
    """เรียก step_fn(m, d) ก่อน mj_step ทุกครั้ง

    headless=True : ไม่เปิดหน้าต่าง วิ่งเร็วสุด (ต้องมี duration)
    headless=False: viewer แบบ passive = เราเป็นคน step เอง viewer แค่วาด → ต้อง sync() และหน่วงเวลาให้ real-time เอง
                    Space = หยุด/เล่น (เราทำเอง เพราะ passive viewer ไม่ได้ step ให้)
    every, every_fn : เรียก every_fn(m, d) ทุก every วินาทีของ sim (ไว้พิมพ์ค่า)
    """
    next_print = 0.0

    def tick():
        nonlocal next_print
        step_fn(m, d)
        mujoco.mj_step(m, d)
        if every_fn is not None and d.time >= next_print:
            every_fn(m, d)
            next_print += every

    if headless:
        if duration is None:
            raise ValueError("headless ต้องกำหนด duration")
        while d.time < duration:
            tick()
        return

    # ⚠️ ห้ามเขียน `import mujoco.viewer` ในฟังก์ชันนี้: มันจะผูกชื่อ `mujoco` เป็นตัวแปร local ของ run()
    #    แล้ว tick() ที่เรียก mujoco.mj_step จะพัง (NameError/UnboundLocalError แบบเดียวกับคำถามสัปดาห์ 1)
    from mujoco import viewer as mjviewer
    state = {"paused": False}

    def on_key(k):
        if k == KEY_SPACE:
            state["paused"] = not state["paused"]
            print("[pause]" if state["paused"] else "[play]", flush=True)
        elif key_callback is not None:
            key_callback(k)

    with mjviewer.launch_passive(m, d, key_callback=on_key) as v:
        wall0, sim0 = time.monotonic(), d.time
        while v.is_running() and (duration is None or d.time < duration):
            if state["paused"]:
                v.sync()
                time.sleep(0.02)
                wall0, sim0 = time.monotonic(), d.time      # เริ่มนับเวลาใหม่หลังเล่นต่อ
                continue
            with v.lock():                                  # กัน viewer อ่าน d ระหว่างเราแก้
                tick()
            v.sync()
            lag = (d.time - sim0) - (time.monotonic() - wall0)
            if lag > 0:                                     # sim เร็วกว่านาฬิกา → รอ
                time.sleep(lag)
    time.sleep(0.5)     # รอ thread วาดภาพของ viewer ปิดให้เสร็จ (ถ้าออกทันที บางเครื่อง Segmentation fault ตอนจบ)


def view_static(m, d) -> None:
    """เปิดหน้าต่างดูท่าที่ตั้งไว้ โดยไม่ step ฟิสิกส์ (ปิดหน้าต่างเพื่อจบ)"""
    from mujoco import viewer as mjviewer
    with mjviewer.launch_passive(m, d) as v:
        while v.is_running():
            v.sync()
            time.sleep(0.05)
    time.sleep(0.5)     # เหมือนใน run(): กัน Segmentation fault ตอนจบ


# ---------------------------------------------------------------------------
# เทสต์
# ---------------------------------------------------------------------------
def run_tests():
    ok = True

    def check(name, cond_fn):
        nonlocal ok
        try:
            cond = bool(cond_fn())
        except Exception as e:
            cond = False
            name += f"  ({type(e).__name__}: {e})"
        ok &= cond
        print(f"  {'PASS' if cond else 'FAIL'}  {name}")

    m, d = load()
    print("ขนาดโมเดล")
    check("nq = 7 + 29 = 36, nv = 6 + 29 = 35, nu = 29", lambda: (m.nq, m.nv, m.nu) == (36, 35, 29))
    check("timestep 0.002 s (500 Hz)", lambda: abs(m.opt.timestep - 0.002) < 1e-12)

    print("slot_table")
    tab = slot_table(m)
    check("slot 18 = left_elbow_joint, qadr 23", lambda: tab.names[18] == "left_elbow_joint" and tab.qadr[18] == 23)
    check("slot 13 = waist_roll_joint (หลอก) qadr 30", lambda: tab.names[13] == "waist_roll_joint" and tab.qadr[13] == 30)
    check("dadr = qadr − 1 ทุกตัว (free joint: 7 qpos แต่ 6 qvel)", lambda: np.all(tab.dadr == tab.qadr - 1))

    print("set_pose + sensor")
    dep = load_deploy()
    set_pose(m, d, dep.q_default, base_z=1.0)
    check("motor_q อ่านจาก sensordata = ท่าที่ตั้ง", lambda: np.allclose(motor_q(m, d), dep.q_default))
    check("ข้อต่อหลอกอยู่สูง 20 m", lambda: d.body("waist_roll").xpos[2] == 20.0)
    th = np.radians(10)
    set_pose(m, d, dep.q_default, base_z=1.0, base_quat=[np.cos(th / 2), 0, np.sin(th / 2), 0])   # ก้ม 10°
    g_sensor = projected_gravity(d.sensor("imu_quat").data)
    g_mat = d.body("pelvis").xmat.reshape(3, 3).T @ np.array([0, 0, -1.0])    # Rᵀ g
    check("projected_gravity(imu_quat) = Rᵀ·(0,0,−1)", lambda: np.allclose(g_sensor, g_mat, atol=1e-6) and g_sensor[2] < -0.9)
    check("ก้ม 10° → gx = +sin10° ≈ +0.174", lambda: abs(g_sensor[0] - np.sin(th)) < 1e-6)

    print("pd_ctrl")
    m2, d2 = load()
    set_pose(m2, d2, np.zeros(m2.nu), base_z=1.0)
    q_des = np.zeros(m2.nu)
    q_des[18] = 0.1
    tau = pd_ctrl(m2, d2, q_des, np.full(m2.nu, 14.3), np.full(m2.nu, 0.9))
    check("ศอก: 14.3 × 0.1 = 1.43 Nm ตัวอื่น 0", lambda: abs(tau[18] - 1.43) < 1e-9 and np.allclose(np.delete(tau, 18), 0))

    print("foot_forces + to_lowstate")
    set_pose(m, d, dep.q_default, base_z=0.78, base_quat=[1, 0, 0, 0])   # ตั้งตรง จมพื้นนิดหน่อย → mj_forward คำนวณแรงสัมผัสให้
    fl, fr = foot_forces(m, d)
    check("กดเท้าลงพื้น: แรงทั้งสองเท้า > 50 N และซ้าย ≈ ขวา (±5%)", lambda: fl > 50 and fr > 50 and abs(fl - fr) < 0.05 * fl)
    ls = to_lowstate(m, d)
    check("to_lowstate: 35 motor, motor_state[18].q = q ศอกซ้าย", lambda:
          len(ls.motor_state) == 35 and abs(ls.motor_state[18].q - dep.q_default[18]) < 1e-9)
    check("to_lowstate: imu quaternion = imu_quat sensor", lambda: np.allclose(ls.imu_state.quaternion, d.sensor("imu_quat").data))

    print("ElasticBand")
    band = ElasticBand()
    f = band.force([0, 0, 1.0], [0, 0, 0])
    check("ห่างจุดแขวน 2 m → แรงขึ้น 400 N", lambda: np.allclose(f, [0, 0, 400.0]))
    f = band.force([0, 0, 1.0], [0, 0, 1.0])
    check("กำลังขึ้น 1 m/s → damping ลดแรง 100 N", lambda: np.allclose(f, [0, 0, 300.0]))

    print("build_model")
    _, mb, _ = build_model(arm_frictionloss=0.0, step_h=0.05)
    el = mb.joint("left_elbow_joint").dofadr[0]
    kn = mb.joint("left_knee_joint").dofadr[0]
    check("arm frictionloss 0 แต่เข่ายัง 0.2", lambda: mb.dof_frictionloss[el] == 0.0 and abs(mb.dof_frictionloss[kn] - 0.2) < 1e-12)
    check("มี geom 'step' สูง 5 cm", lambda: abs(mb.geom("step").size[2] - 0.025) < 1e-12)

    print("ผ่านทั้งหมด ✅" if ok else "ยังมี FAIL")
    return ok


if __name__ == "__main__":
    run_tests()
