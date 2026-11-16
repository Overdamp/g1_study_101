# source ~/g1_study/weekI_isaaclab/env.sh   ← ใช้ "source" ไม่ใช่ bash (ต้องแก้ PATH ของ shell ปัจจุบัน)
# env ของ Isaac Lab 3.0 + Newton 1.2 ที่ session งานหลักทำ cross-sim ไว้ (Isaac Sim 6.0, torch 2.10)
# conda กับ uv venv ชนกัน (PATH / LD_LIBRARY_PATH) → ปิด conda ก่อนเสมอ
if [ -n "$CONDA_PREFIX" ]; then conda deactivate 2>/dev/null; conda deactivate 2>/dev/null; fi
source ~/nvidia/IsaacLab-unitree/env_isaaclab/bin/activate
export OMNI_KIT_ACCEPT_EULA=YES      # ไม่ตั้ง = Isaac ค้างรอถาม EULA
export PYTHONWARNINGS=ignore
cd ~/g1_study/weekI_isaaclab/scripts
echo "[weekI] python = $(which python)  ·  ทำงานใน $(pwd)"
