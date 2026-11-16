from common import NUM_MOTORS, Every, run_control_loop, set_header

report = Every(1.0)
ticks = 0

def build_cmd(cmd, state, t):
    global ticks
    set_header(cmd, state)
    for i in range (NUM_MOTORS):
        m = cmd.motor_cmd[i]
        m.mode = 1 
        m.q = 0.0
        m.dq = 0.0
        m.tau = 0.0
        m.kp = 0.0
        m.kd = 0.0

    ticks += 1
    if t >= 1.0 and report(t):
        print(f"t={t:6.1f} s ส่งไปแล้ว {ticks} ครั้ง (เฉลี่ย {ticks / max (t, 1e-6):.0f} Hz)", flush=True)


if __name__ == "__main__":
    print("send_zero: สส่งคำสั่งศูนย์ทุกข้อต่อ (Ctrl+C เพื่อหยุด") 
    try:
        run_control_loop(build_cmd)
    except KeyboardInterrupt:
        print("\nหยุดแล้ว: sim จะใช้คำสั่งสุดท้าย (ศูนย์) ต่อไป ซึ่งก็คือปล่อยอิสระเหมือนเดิม")
