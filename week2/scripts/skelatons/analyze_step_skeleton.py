"""analyze_step_skeleton.py: วิเคราะห์ CSV จาก step_elbow (งาน 2.6–2.7)  ❌ ไม่ต่อ DDS

1. rise time (10% → 90%), overshoot, steady-state error  ของแต่ละไฟล์
2. คำนวณ tau = kp·(q_des − q) + kd·(0 − dq) เอง แล้วเทียบกับ tau_est ที่ sim รายงาน
3. (ถ้ามี matplotlib) พล็อต q(t) ทุกไฟล์บนรูปเดียว

รัน:  python week2/scripts/skelatons/analyze_step_skeleton.py step_kp5.csv step_kp14.csv step_kp40.csv step_kd0.csv
      พล็อต: ใช้ env unitree_rl_mjlab (g1_sdk ไม่มี matplotlib)
"""

# TODO [2.6] imports: sys, csv หรือ numpy  (matplotlib ให้ import ในฟังก์ชันพล็อต เพื่อให้ไฟล์ยังรันได้แม้ไม่มี)

SETTLE_S = 2.0           # ต้องตรงกับ step_elbow
HOLD_S = 3.0


def load(path):
    """คืน dict ของคอลัมน์ {'t': [...], 'q_des': [...], ...}"""
    # TODO [2.6] อ่าน CSV (np.loadtxt(..., skiprows=1) หรือ csv.DictReader)
    return None


def step_window(d):
    """ตัดเฉพาะช่วงที่เป้าเป็น q0 + amp  (SETTLE_S ≤ t < SETTLE_S + HOLD_S)"""
    # TODO [2.6]
    return None


def step_metrics(d):
    """คืน (rise_time_s, overshoot_pct, steady_error_deg) จากช่วง step"""
    # TODO [2.6] q0 = q ก่อน step,  q_final = เป้า,  ระยะ = q_final − q0
    # TODO [2.6] rise: เวลาแรกที่ q ข้าม 10% ของระยะ → เวลาแรกที่ข้าม 90%
    # TODO [2.6] overshoot: (max(q) − q_final) / ระยะ × 100  (ระวังถ้าระยะติดลบ)
    # TODO [2.6] steady error: q_final − ค่าเฉลี่ยของ q ใน 0.5 s สุดท้ายของช่วง  (เป็นองศา)
    # คำถาม: ทำไม steady error ไม่เป็น 0 แม้ kp สูง  (pd_control.md)
    return None


def torque_check(d):
    """คืน (rms_diff_Nm, corr) ระหว่าง tau ที่คำนวณเอง กับ tau_est"""
    # TODO [2.7] tau_calc = kp·(q_des − q) + kd·(0 − dq)
    # TODO [2.7] เทียบกับ tau_est: rms ของผลต่าง + correlation
    # คำถาม: sim คำนวณ ctrl ด้วยสูตรเดียวกัน (unitree_sdk2_bridge.h) ทำไมยังต่างกันนิดหน่อย?
    #   ใบ้: q ที่เราบันทึกกับ q ที่ sim ใช้ตอนคำนวณ เป็นของจังหวะเดียวกันไหม / ctrlrange ±25 Nm
    return None


def plot(datasets):
    """พล็อต q(t) ทุกไฟล์บนรูปเดียว (ข้ามถ้าไม่มี matplotlib)"""
    # TODO [2.6] try: import matplotlib.pyplot as plt  except ImportError: print แล้ว return
    # TODO [2.6] แกน x = t − SETTLE_S, แกน y = q − q0 (องศา), ใส่ legend เป็นชื่อไฟล์, เส้นเป้าหมาย
    pass


def main():
    # TODO [2.6] วนทุกไฟล์ใน sys.argv[1:]: load → step_metrics → torque_check
    # TODO [2.6] พิมพ์ตาราง: ไฟล์ | kp | kd | rise (ms) | overshoot (%) | ss error (°) | tau rms | corr
    # TODO [2.6] plot(...)
    # ทายก่อนรัน: kp 40 เทียบ kp 5 rise time ต่างกันกี่เท่า  (บันทึกลงตารางทายใน week2/docs/README.md)
    print("analyze_step: ยังไม่ได้เติม [2.6]")


if __name__ == "__main__":
    main()
