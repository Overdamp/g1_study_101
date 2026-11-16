"""N5: ดูหุ่นใน viewer ของ Newton (หน้าต่าง OpenGL) + ลากหุ่นด้วยเมาส์

    python n5_viewer.py                       # 4 ตัว gain ×1, ×2, ×4, ×8 ยืนด้วย PD
    python n5_viewer.py --scales 8 --worlds 1 # ตัวเดียว gain ×8 (รูปปั้น) ลองลากให้ล้ม
    python n5_viewer.py --fixed               # pelvis ตรึง ดูแขนขาห้อยตามน้ำหนัก
    python n5_viewer.py --null --frames 50    # ไม่เปิดหน้าต่าง (ทดสอบว่าโค้ดรันได้)

ใน viewer: ลากเมาส์ซ้าย = หมุนกล้อง · คลิกขวาค้างที่ตัวหุ่นแล้วลาก = ดึง body นั้น (picking ผ่าน apply_forces)
          space = หยุด/เล่น · ESC = ปิด
ใช้โหมด eager (ไม่ใช้ CUDA graph) เพราะแรงจากเมาส์ต้องใส่ทุก step จาก Python
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import ilib  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--scales", default="1,2,4,8")
ap.add_argument("--fixed", action="store_true")
ap.add_argument("--null", action="store_true", help="ViewerNull: ไม่เปิดหน้าต่าง")
ap.add_argument("--frames", type=int, default=0, help="จำนวนเฟรมแล้วปิด (0 = ไม่จำกัด)")
args = ap.parse_args()
scales = [float(s) for s in args.scales.split(",")]

ilib.quiet()
import newton  # noqa: E402
import newton.viewer  # noqa: E402
import numpy as np  # noqa: E402

sim = ilib.G1Sim(worlds=len(scales), floating=not args.fixed, use_graph=False)
# gain ต่อ world (แบบเดียวกับ N2)
ke = sim.model.joint_target_ke.numpy().reshape(sim.W, sim.nd)
kd = sim.model.joint_target_kd.numpy().reshape(sim.W, sim.nd)
s = np.array(scales, dtype=np.float32)[:, None]
ke[:, sim.d_idx] = ilib.KP * s
kd[:, sim.d_idx] = ilib.KD * s
sim.model.joint_target_ke.assign(ke.ravel())
sim.model.joint_target_kd.assign(kd.ravel())
sim.solver.notify_model_changed(newton.solvers.SolverNotifyFlags.JOINT_DOF_PROPERTIES)

viewer = newton.viewer.ViewerNull() if args.null else newton.viewer.ViewerGL(width=1280, height=720)
viewer.set_model(sim.model)
print(f"world {sim.W} · gain scale {scales} · {'fixed' if args.fixed else 'floating'} · physics 4 step/เฟรม (50 fps จำลอง)")

t, frame = 0.0, 0
while viewer.is_running():
    if not viewer.is_paused():
        for _ in range(4):                       # 4 × 5 ms = 20 ms ต่อเฟรม (เท่า step_dt ของ RL)
            sim.state_0.clear_forces()
            viewer.apply_forces(sim.state_0)     # แรงจากการลากเมาส์ → body_f ของ state
            sim.solver.step(sim.state_0, sim.state_1, sim.control, None, sim.dt)
            sim.state_0, sim.state_1 = sim.state_1, sim.state_0
        t += 4 * sim.dt
    viewer.begin_frame(t)
    viewer.log_state(sim.state_0)
    viewer.end_frame()
    frame += 1
    if frame % 50 == 0 and not args.fixed:
        print(f"  t {t:5.1f} s · pelvis z {np.round(sim.base_pos()[:, 2], 3)} · "
              f"tilt° {np.round(np.degrees(sim.tilt()), 0)}")
    if args.frames and frame >= args.frames:
        break
viewer.close()
