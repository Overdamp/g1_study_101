import math 
import threading
import time 

from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_

LEFT_ELBOW = 18

class LowStateReader:
    def __init__(self):
        self.count = 0
        self.elbow_q = None
        self.lock = threading.Lock()

    def handler(self, msg: LowState_):
        with self.lock:
            self.count += 1

            self.elbow_q = msg.motor_state[LEFT_ELBOW].q

def main():
    ChannelFactoryInitialize (1, "lo")
    reader = LowStateReader()
    sub  = ChannelSubscriber("rt/lowstate", LowState_)
    sub.Init(reader.handler, 10)

    t_last = time.monotonic()
    while True:
        time.sleep(1)
        with reader.lock:
            n = reader.count
            reader.count = 0 
            q = reader.elbow_q

        now = time.monotonic()
        hz = n / (now - t_last)
        t_last = now

        if q is None:
            print(f"{hz:6.1f} Hz (no LowState yet)", flush= True)
        else:
            print(f"{hz:6.1f} Hz elbow_L = {math.degrees(q)} deg", flush= True)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    