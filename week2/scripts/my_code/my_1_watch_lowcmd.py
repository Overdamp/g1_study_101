
import argparse
import math
import threading
import time

from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowCmd_

DOMAIN = 1
IFACE = "lo"
PRINT_PERIOD = 1.0
NUM_MOTORS = 29

class LowCmdWatcher:
    def __init__(self):
        self.count = 0
        self.latest = None
        self.lock = threading.Lock()

    def handler (self, msg: LowCmd_):
        with self.lock:
            self.count += 1
            self.latest = msg

def summarize(msg: LowCmd_, hz: float, slot: int) -> str:
    m = msg.motor_cmd[slot]
    active = sum(1 for i in range(NUM_MOTORS)if msg.motor_cmd[i].kp > 0 )
    return (f"{hz:6.1f} Hz | mode_machine {msg.mode_machine} pr {msg.mode_pr} | "
            f"slot {slot}: mode {m.mode} q {m.q:+.3f} rad ({math.degrees(m.q):+6.1f}°) "
            f"kp {m.kp:5.1f} kd {m.kd:4.2f} tau {m.tau:+.2f} | kp>0: {active:2d} slot | crc {msg.crc:#010x}")

def main():
    parser = argparse.ArgumentParser(description= "ฟัง rt/lowcms (อ่านอย่างเดียว)")
    parser.add_argument("--slot", type=int, default=18, help="slot ที่จะแสดงรายละเอียด (18 = ศอกซ้าย)")
    args = parser.parse_args()

    ChannelFactoryInitialize(DOMAIN, IFACE)
    watcher = LowCmdWatcher()
    sub = ChannelSubscriber("rt/lowcmd", LowCmd_)
    sub.Init(watcher.handler, 10)

    t_last = time.monotonic()
    while True:
        time.sleep(PRINT_PERIOD)
        with watcher.lock:
            n = watcher.count 
            watcher.count = 0
            msg = watcher.latest
        now = time.monotonic()
        hz = n / (now - t_last)
        t_last = now

        if n == 0:
            print(f"{hz:6.1f} Hz | no lowcmd (ยังไม่มีโปรแกรมไหนส่ง)", flush=True)
        else:
            print(summarize(msg, hz, args.slot), flush=True)


if __name__== "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nหยุดฟังแล้ว")

