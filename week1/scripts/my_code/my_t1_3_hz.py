import threading
import time

from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_


class LowStateCounter:

    def __init__(self):
        self.count = 0 
        self.lock = threading.Lock()

    def handler(self, msg: LowState_):
        with self.lock:
            self.count += 1

    
def main():
    ChannelFactoryInitialize(1,"lo")
    counter = LowStateCounter()
    sub = ChannelSubscriber("rt/lowstate", LowState_)
    sub.Init(counter.handler, 10)

    t_last = time.monotonic()
    while True:
        time.sleep(1)

        with counter.lock:
            n = counter.count
            counter.count  = 0

            now = time.monotonic()
            dt= now - t_last
            t_last = now
            print (f"{n / dt:7.1f} Hz ({n} msg in {dt:.3f} s)", flush=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass