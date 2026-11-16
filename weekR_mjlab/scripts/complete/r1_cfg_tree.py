"""R1: อ่าน config ของ task โดยไม่สร้าง env (เร็ว ไม่ใช้ GPU) ฉบับสมบูรณ์

  python r1_cfg_tree.py                         # ต้นไม้ term ของ Flat
  python r1_cfg_tree.py --task Unitree-G1-23Dof-Rough-Blind
  python r1_cfg_tree.py --where                 # + ไฟล์:บรรทัด ของฟังก์ชันแต่ละ term (ไปเปิดอ่านต่อ)
  python r1_cfg_tree.py --diff Unitree-G1-23Dof-Flat Unitree-G1-23Dof-Rough-Blind
  python r1_cfg_tree.py --base                  # ค่าพื้นฐาน + ค่าที่ G1 ตั้งเพิ่ม (ดูว่าชั้นไหนตั้งอะไร)

สิ่งที่ควรเห็น
  - config = dataclass ธรรมดา (ManagerBasedRlEnvCfg) ข้างในเป็น dict ของ term → แก้/ลบได้เหมือน dict
  - term = func + params (+ weight / mode / time_out) · manager แค่วนเรียก func ทุกตัว
  - Flat vs Blind: obs ของ actor เหมือนกันทุกตัว (80) ต่างที่ terrain / curriculum / weight
"""
import argparse
import inspect

import rlib


def where(func) -> str:
    """ไฟล์:บรรทัด ของฟังก์ชัน (ย่อ path ให้อ่านง่าย)"""
    f = func if inspect.isfunction(func) or inspect.isclass(func) else type(func)
    try:
        path = inspect.getsourcefile(f) or "?"
        line = inspect.getsourcelines(f)[1]
    except (TypeError, OSError):
        return "?"
    path = path.replace(str(rlib.REPO) + "/", "repo/")
    if "site-packages/" in path:
        path = "site-packages/" + path.split("site-packages/")[1]
    return f"{path}:{line}"


def print_tree(cfg, show_where: bool) -> None:
    print(f"decimation {cfg.decimation} × timestep {cfg.sim.mujoco.timestep} s "
          f"= step_dt {cfg.decimation * cfg.sim.mujoco.timestep:g} s "
          f"({1 / (cfg.decimation * cfg.sim.mujoco.timestep):g} Hz) · episode {cfg.episode_length_s:g} s "
          f"· num_envs {cfg.scene.num_envs}")
    terrain = cfg.scene.terrain
    print(f"terrain: {terrain.terrain_type if terrain else None} · sensors: "
          f"{[s.name for s in (cfg.scene.sensors or ())]}")

    # หา func จริงของแต่ละ term เพื่อบอกตำแหน่งไฟล์ (ใช้กับ --where)
    funcs = {}
    for g, gc in cfg.observations.items():
        for n, t in gc.terms.items():
            funcs[(f"obs.{g}", n)] = t.func
    for mgr in rlib.TERM_DICTS:
        for n, t in getattr(cfg, mgr).items():
            if hasattr(t, "func"):
                funcs[(mgr, n)] = t.func
            else:
                funcs[(mgr, n)] = type(t)

    for mgr, terms in rlib.cfg_summary(cfg).items():
        print(f"\n[{mgr}] {len(terms)} term")
        for name, desc in terms.items():
            extra = f"   ← {where(funcs[(mgr, name)])}" if show_where and (mgr, name) in funcs else ""
            print(f"  {name:28s} {desc}{extra}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default=rlib.FLAT)
    ap.add_argument("--where", action="store_true")
    ap.add_argument("--diff", nargs=2, metavar=("A", "B"))
    ap.add_argument("--base", action="store_true", help="เทียบ make_velocity_env_cfg() กับ G1 Rough")
    args = ap.parse_args()

    if args.diff:
        a, b = (rlib.load_cfg(t) for t in args.diff)
        print(f"A = {args.diff[0]}\nB = {args.diff[1]}\n")
        rlib.print_table(rlib.diff_cfg(a, b), ["manager", "term", "A", "B"])
        return

    if args.base:
        # ชั้นที่ 1: factory กลาง (ทุกหุ่นใช้ร่วม) · ชั้นที่ 2: G1 ปรับ/เพิ่ม
        rlib.setup_path()
        import mjlab.tasks  # noqa: F401
        import src.tasks  # noqa: F401
        from src.tasks.velocity.velocity_env_cfg import make_velocity_env_cfg
        base = make_velocity_env_cfg()
        g1 = rlib.load_cfg(rlib.ROUGH)
        print("A = make_velocity_env_cfg() (velocity_env_cfg.py)\nB = Unitree-G1-23Dof-Rough (env_cfgs.py)\n")
        rlib.print_table(rlib.diff_cfg(base, g1), ["manager", "term", "A (base)", "B (G1)"])
        print("\n(ค่าใน params เช่น body_names / std ที่ G1 เติมทีหลังไม่แสดงในตารางนี้ → ดู env_cfgs.py:97–242)")
        return

    print_tree(rlib.load_cfg(args.task), args.where)


if __name__ == "__main__":
    main()
