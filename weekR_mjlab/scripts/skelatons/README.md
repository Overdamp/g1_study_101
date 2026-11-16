# โมดูล R: โครงให้เติม (skeleton)

> เฉลยอยู่ที่ `../complete/` · docs อยู่ที่ `../../docs/` · ใช้ `conda activate unitree_rl_mjlab` · ต้องมี GPU ว่าง ~1 GB

## ลำดับ
1. อ่าน `docs/README.md` → `01_big_picture.md` → `02_config_layers.md` (R0)
2. เติม `rlib_skeleton.py` **ทีละส่วนตามงาน** แล้วรันเทสต์บ่อยๆ:
   ```bash
   conda activate unitree_rl_mjlab
   cd ~/g1_study/weekR_mjlab/scripts/skelatons
   python rlib_skeleton.py          # ตอนเริ่ม PASS 2/18 → ครบ 18/18
   ```
   | TODO | งาน | เทสต์ที่จะผ่าน |
   |---|---|---|
   | `cfg_summary`, `diff_cfg` | R1 | 6 ข้อ |
   | `term_slices` | R2 | 3 ข้อ |
   | `StepTracer._wrap`, `__exit__` | R3 | 4 ข้อ |
   | `fix_command`, `manual_reward` | R4 | 2 ข้อ |
   | `ActorMLP.__call__` | R7 | 1 ข้อ |
3. ทำ `r1_..._skeleton.py` → `r8_..._skeleton.py` ตามลำดับ แต่ละไฟล์มี **"ทายก่อนรัน"** ที่หัวไฟล์ และ TODO ของไฟล์นั้นเอง
   (R5 มี `my_terms_skeleton.py` ให้เติมด้วย)

ทุกไฟล์**รันได้ตั้งแต่ยังไม่เติม** (ผลจะว่าง/เป็นศูนย์ หรือพิมพ์ว่า TODO) เติมแล้วรันซ้ำเพื่อเทียบกับที่ทาย

## ส่วนที่ให้ไว้แล้ว (อ่านให้เข้าใจ ไม่ต้องเขียน)
`setup_path`, `load_cfg`, `make_env`, `ActorMLP.__init__`, `StepTracer.__enter__`, `compress`, `print_table`, เทสต์

## ถ้าติด
| อาการ | ดูที่ |
|---|---|
| `ModuleNotFoundError: mjlab` / `torch` | ยังไม่ได้ `conda activate unitree_rl_mjlab` (g1_sdk ไม่มี) |
| `ModuleNotFoundError: src` | ไม่ได้เรียก `rlib.setup_path()` / `load_cfg` ก่อน import `src.tasks...` |
| `CUDA out of memory` | session งานหลักเทรนอยู่ → `nvidia-smi` แล้วรอ หรือลด `num_envs` |
| แก้ cfg แล้วไม่มีผล | แก้หลัง `make_env` (manager deepcopy ไปแล้ว) → แก้ก่อนสร้าง env |
| `ValueError: heading_command=False but ranges.heading is set` (หรือกลับกัน) | `fix_command` ต้องตั้ง `ranges.heading = None` คู่กับ `heading_command = False` |
| obs term ต่อกันไม่ได้ (`torch.cat` shape) | term คืน (N,) แทน (N, 1) → ใช้ `x[:, 2:3]` |
| ตาราง `[INFO]` ยาวเต็มจอ | ห่อ `make_env` ด้วย `contextlib.redirect_stdout(io.StringIO())` (สคริปต์ทำให้แล้ว) |
| คำสั่งไม่คงที่ทั้งที่ตั้ง ranges | ลืมปิด heading / standing / curriculum `command_vel` (ดู docstring `fix_command`) |
