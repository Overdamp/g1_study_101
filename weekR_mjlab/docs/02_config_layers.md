# 02: config 3 ชั้น, registry และ CLI override

## 1. config คือ dataclass ธรรมดา
```python
@dataclass(kw_only=True)
class ManagerBasedRlEnvCfg:             # mjlab/envs/manager_based_rl_env.py:47
  decimation: int
  scene: SceneCfg                       # หุ่น, พื้น, sensor, num_envs
  observations: dict[str, ObservationGroupCfg]
  actions: dict[str, ActionTermCfg]
  events: dict[str, EventTermCfg]
  sim: SimulationCfg                    # timestep, solver
  episode_length_s: float
  rewards / terminations / commands / curriculum / metrics: dict[str, ...]
  scale_rewards_by_dt: bool = True
```
ไม่มีเวทมนตร์: แก้ด้วย `cfg.rewards["pose"].weight = 2.0`, `del cfg.observations["actor"].terms["height_scan"]` ได้ตรงๆ **ก่อนสร้าง env** (หลังสร้างแล้ว manager deepcopy ไปแล้ว แก้ cfg จะไม่มีผล)

## 2. ชั้นของ config ของเรา
```
ชั้น 1  src/tasks/velocity/velocity_env_cfg.py   make_velocity_env_cfg()
        ทุกหุ่นใช้ร่วม: obs, reward 15 ตัว, event 6 ตัว, decimation 4, timestep 0.005, ROUGH terrain
        ช่องที่ต้องเติมตามหุ่นจะเว้นว่างไว้ เช่น body_names=()  # Set per-robot.
          │
ชั้น 2  src/tasks/velocity/config/g1_23dof/env_cfgs.py   unitree_g1_23dof_rough_env_cfg()
        เรียกชั้น 1 แล้ว: ใส่หุ่น G1 + DelayedActuator · sensor เท้า/ชนตัวเอง · ชื่อ body/site/geom
        action scale · DR เพิ่ม 7 ตัว (Phase 2–3) · std ของ pose · self_collisions
          │
ชั้น 3  ├─ unitree_g1_23dof_flat_env_cfg()          พื้นเรียบ · ลบ terrain_scan + height_scan · ลบ terrain_levels
        └─ unitree_g1_23dof_rough_blind_env_cfg()  rough แต่ลบ height_scan · บันไดสูงสุด 8 cm · track_linear w 2
        (+ play=True: ไม่มี noise, ไม่ผลัก, ไม่มี curriculum, episode ไม่จบ)
```
R1 `--base` แสดงสิ่งที่ชั้น 2 เพิ่ม · R1 `--diff Flat Blind` แสดงสิ่งที่ชั้น 3 ต่างกัน

ทำไม Blind ต้อง `del height_scan` (env_cfgs.py:314): P3b เทรนบน Flat ที่ actor = 80 ถ้าไม่ลบ actor ของ Rough = 80 + 187 = 267 → `mlp.0.weight` (512 × 80) โหลดไม่ได้ และหุ่นจริงก็ไม่มี height map (R5 `--rough`)

## 3. registry: ชื่อ task → config
```python
# src/tasks/velocity/config/g1_23dof/__init__.py
register_mjlab_task(
  task_id="Unitree-G1-23Dof-Flat",
  env_cfg=unitree_g1_23dof_flat_env_cfg(),            # สร้าง cfg ทันทีตอน import
  play_env_cfg=unitree_g1_23dof_flat_env_cfg(play=True),
  rl_cfg=unitree_g1_23dof_ppo_runner_cfg(),           # rl_cfg.py: MLP 512-256-128, PPO
  runner_cls=VelocityOnPolicyRunner,                  # save() export ONNX ด้วย
)
```
- `import src.tasks` = รันไฟล์ `__init__.py` ทุกชั้น → task ลงทะเบียนตัวเอง
- `load_env_cfg(task)` คืน **deepcopy** → แก้ได้โดยไม่กระทบตัวกลาง (`mjlab/tasks/registry.py:48`)
- `rlib.load_cfg()` ของเราทำแค่นี้ + เพิ่ม REPO ใน `sys.path` (train.py รันจาก cwd = REPO เลยไม่ต้องเพิ่ม)

## 4. CLI override (tyro) → เขียนทับ cfg ก่อนสร้าง env
```bash
python scripts/train.py Unitree-G1-23Dof-Flat \
  --env.scene.num-envs 4096 \
  --env.rewards.track-linear-velocity.weight 2.0 \
  --agent.max-iterations 500 --agent.resume True --agent.load-run p3b_seed
```
`train.py:24` นิยาม `TrainConfig(env: ManagerBasedRlEnvCfg, agent: RslRlBaseRunnerCfg, ...)` แล้วให้ tyro สร้าง CLI จาก dataclass:
- `--env.X.Y` = `cfg.env.X.Y` · ชื่อใน `--help` ใช้ขีด `-` แทน `_` (`rewards.foot-clearance`, `scene.num-envs`) ดูรายการทั้งหมดด้วย `python scripts/train.py <task> --help`
- ค่า default ของแต่ละ flag = ค่าจาก registry (ชั้น 3)
- หลัง parse: `dump_yaml(log_dir/params/env.yaml, asdict(cfg.env))` → **env.yaml = config ที่ใช้จริงหลัง override** (week5 `diff_configs.py` อ่านไฟล์นี้)

R8 `--weight term=w` ทำแบบเดียวกันด้วยมือ (`env_cfg.rewards[term].weight = w`)

## 5. ⚠️ กับดัก: func มาจากโมดูลไหน
ไฟล์ config import `mdp` คนละแบบ:
| ไฟล์ | import | ผล |
|---|---|---|
| `velocity_env_cfg.py:26,33` | `from mjlab.tasks.velocity import mdp` แล้วทับด้วย `import src.tasks.velocity.mdp as mdp` | term ส่วนใหญ่ใช้ของ **repo** |
| `velocity_env_cfg.py:27` | `from mjlab.tasks.velocity.mdp import UniformVelocityCommandCfg` | คำสั่งความเร็วใช้ของ **mjlab** |
| `env_cfgs.py:19` | `from mjlab.tasks.velocity import mdp` | `self_collision_cost` ใช้ของ **mjlab** |

ผล: แก้ `src/tasks/velocity/mdp/velocity_command.py` แล้ว**ไม่มีผลกับการเทรน** (บรรทัด 77 `*= norm > 0.1` ไม่ถูกใช้) · ตรวจเองได้ด้วย R1 `--where` หรือ
```python
type(env.command_manager.get_term("twist")).__module__   # 'mjlab.tasks.velocity.mdp.velocity_command'
```
บทเรียน: **อย่าเชื่อชื่อไฟล์ ให้ถาม object ว่ามาจากไหน** (`__module__`, `inspect.getsourcefile`)

## 6. ตำแหน่งที่ควรเปิดอ่าน
| อะไร | ไฟล์:บรรทัด |
|---|---|
| obs actor/critic | `velocity_env_cfg.py:58–136` |
| action scale 0.25 (แทนด้วยของ G1) | `velocity_env_cfg.py:152` → `env_cfgs.py:97–99` → `g1_23dof_constants.py:271–279` |
| คำสั่ง + curriculum คำสั่ง | `velocity_env_cfg.py:165–180, 377–386` |
| event พื้นฐาน | `velocity_env_cfg.py:186–255` |
| DR Phase 2–3 | `env_cfgs.py:114–188` |
| reward พื้นฐาน / std ของ pose | `velocity_env_cfg.py:261–354` / `env_cfgs.py:198–232` |
| decimation, timestep, episode | `velocity_env_cfg.py:420–430` |
| Flat / Blind | `env_cfgs.py:268–346` |
| PPO | `config/g1_23dof/rl_cfg.py` |

## คำถามเช็ค
1. แก้ `cfg.rewards["pose"].weight` หลัง `ManagerBasedRlEnv(cfg)` แล้ว reward เปลี่ยนไหม เพราะอะไร
2. อยากลอง `foot_clearance` target 0.12 m ผ่าน CLI ต้องพิมพ์ flag อะไร
3. ถ้าจะแก้สูตร `track_linear_velocity` ต้องแก้ไฟล์ไหน (repo หรือ mjlab) ตรวจยังไงให้แน่ใจ
