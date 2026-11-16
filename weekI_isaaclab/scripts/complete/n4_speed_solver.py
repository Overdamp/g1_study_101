"""N4: ความเร็วของ Newton บน GPU + ผลของพารามิเตอร์ solver

    python n4_speed_solver.py               # A + B
    python n4_speed_solver.py --only A      # วัดความเร็วอย่างเดียว
    python n4_speed_solver.py --max-worlds 2048

A. env-step/s ตามจำนวน world (1 → 1024) แบบ CUDA graph และแบบ eager (เรียก kernel ทีละตัวจาก Python)
   → ทำไม RL ต้องรันหลายพัน env พร้อมกัน · CUDA graph ช่วยตรงไหน
B. หุ่นยืนด้วย PD ×8 (ท่ารูปปั้น ยืนได้จาก N2) 2 s แล้วเปลี่ยนค่าของ solver ทีละตัว
   ดู: solver ใช้กี่ iteration จริง, pelvis จมลง/ลอยเท่าไร, เร็วขึ้น/ช้าลงเท่าไร
   ค่าเริ่ม = ที่ task Isaac Lab ของ Unitree ใช้ (cone pyramidal, impratio 1, implicitfast, ls_iterations 15)
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import ilib  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--only", choices=["A", "B"], default=None)
ap.add_argument("--max-worlds", type=int, default=1024)
args = ap.parse_args()

ilib.quiet()
import numpy as np  # noqa: E402


def throughput(sim: ilib.G1Sim, n: int = 200) -> float:
    """physics step × world ต่อวินาที"""
    # >>>TODO(N4) อุ่นเครื่อง 2 step → wp.synchronize() → จับเวลา step(n) → synchronize → คืน n·W/เวลา
    sim.step(2)
    sim.wp.synchronize()
    t = time.perf_counter()
    sim.step(n)
    sim.wp.synchronize()             # GPU ทำงานแบบ async: ต้องรอให้เสร็จก่อนหยุดนาฬิกา
    return n * sim.W / (time.perf_counter() - t)
    # <<<TODO


# ================================================================ A
if args.only in (None, "A"):
    print("[A] physics step/s (× world) · dt 0.005 · หุ่นยืน PD ท่า default (ล้มระหว่างวัด = มี contact เยอะ)")
    rows = []
    proto = ilib.build_g1()
    W = 1
    while W <= args.max_worlds:
        t0 = time.time()
        g = ilib.G1Sim(worlds=W, proto=proto)
        build = time.time() - t0
        sps_g = throughput(g, 200)
        sps_e = None
        if W <= 64:
            e = ilib.G1Sim(worlds=W, proto=proto, use_graph=False)
            sps_e = throughput(e, 100)
            del e
        rows.append(dict(worlds=W, build_s=build, graph_sps=sps_g, eager_sps=sps_e,
                         graph_vs_eager=None if sps_e is None else sps_g / sps_e,
                         realtime_x=sps_g * g.dt))
        del g
        W *= 4 if W < 64 else 2
    ilib.print_table(rows, fmt={"build_s": "{:.1f}", "graph_sps": "{:,.0f}", "eager_sps": "{:,.0f}",
                                "graph_vs_eager": "×{:.1f}", "realtime_x": "×{:,.0f}"})
    print("    realtime_x = เร็วกว่าเวลาจริงกี่เท่า (รวมทุก world) · env step ของ RL = 4 physics step (decimation)")

# ================================================================ B
if args.only in (None, "B"):
    print("\n[B] พารามิเตอร์ solver · 16 world · PD ×8 ยืน 2 s")
    proto = ilib.build_g1(gain_scale=8.0)
    variants = [
        ("default (unitree_rl_lab)", {}, 0.005),
        ("cone elliptic", dict(cone="elliptic"), 0.005),
        ("elliptic + impratio 100", dict(cone="elliptic", impratio=100.0), 0.005),
        ("iterations 100→3", dict(iterations=3), 0.005),
        ("ls_iterations 15→2", dict(ls_iterations=2), 0.005),
        ("integrator euler", dict(integrator="euler"), 0.005),
        ("solver cg", dict(solver="cg"), 0.005),
        ("dt 0.002", {}, 0.002),
        ("dt 0.01", {}, 0.01),
    ]
    rows = []
    for name, kw, dt in variants:
        # >>>TODO(N4) สร้าง G1Sim(worlds=16, dt=dt, proto=proto, **kw) → เดิน 2 s → เก็บ z, tilt, iteration, ความเร็ว
        sim = ilib.G1Sim(worlds=16, dt=dt, proto=proto, **kw)
        n = int(round(2.0 / dt))
        n += n % 2
        t = time.perf_counter()
        sim.step(n)
        sim.wp.synchronize()
        el = time.perf_counter() - t
        z = sim.base_pos()[:, 2]
        it = sim.solver_iters()
        rows.append(dict(variant=name, dt=dt, z_end=float(z.mean()), tilt_deg=float(np.degrees(sim.tilt().max())),
                         iters_mean=float(it.mean()), iters_max=int(it.max()),
                         sim_s_per_wall_s=2.0 * 16 / el))
        # <<<TODO
        del sim
    ilib.print_table(rows, fmt={"dt": "{:.3f}", "z_end": "{:.4f}", "tilt_deg": "{:.2f}", "iters_mean": "{:.1f}",
                                "sim_s_per_wall_s": "{:,.0f}"})
    print("    sim_s_per_wall_s = วินาทีจำลอง (รวม 16 world) ต่อ 1 วินาทีจริง · รอบแรกช้ากว่าเพราะ compile kernel")
