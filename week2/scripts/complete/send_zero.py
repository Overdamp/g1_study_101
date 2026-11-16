"""send_zero.py: ส่ง LowCmd ที่ kp = kd = tau = 0 ทุกข้อต่อ ทุก 2 ms (งาน 2.2)  ✅ ส่ง lowcmd (sim เท่านั้น)

ผลที่ควรเห็น: หุ่นใน sim ไม่เปลี่ยนเลย เพราะ tau = 0 + 0·(...) + 0·(...) = 0 เหมือนตอนยังไม่มีใครส่ง
แต่ watch_lowcmd.py จะเห็น ~500 Hz และ kp = 0 → พิสูจน์ว่าท่อส่งคำสั่งทำงาน ก่อนจะใส่ค่าที่มีผลจริง

รัน:  conda activate g1_sdk && python week2/scripts/complete/send_zero.py
"""

from common import NUM_MOTORS, Every, run_control_loop, set_header

report = Every(1.0)
ticks = 0


def build_cmd(cmd, state, t):
    global ticks
    set_header(cmd, state)
    for i in range(NUM_MOTORS):
        m = cmd.motor_cmd[i]
        m.mode = 1
        m.q = 0.0          # kp = 0 → q ไม่มีผล ใส่อะไรก็ได้
        m.dq = 0.0
        m.tau = 0.0
        m.kp = 0.0
        m.kd = 0.0

    ticks += 1
    if t >= 1.0 and report(t):         # เริ่มรายงานหลัง 1 s (ตอน t ≈ 0 ค่าเฉลี่ยยังไม่มีความหมาย)
        print(f"t={t:6.1f} s  ส่งไปแล้ว {ticks} ครั้ง (เฉลี่ย {ticks / max(t, 1e-6):.0f} Hz)", flush=True)


if __name__ == "__main__":
    print("send_zero: ส่งคำสั่งศูนย์ทุกข้อต่อ (Ctrl+C เพื่อหยุด)")
    try:
        run_control_loop(build_cmd)
    except KeyboardInterrupt:
        print("\nหยุดแล้ว: sim จะใช้คำสั่งสุดท้าย (ศูนย์) ต่อไป ซึ่งก็คือปล่อยอิสระเหมือนเดิม")
