from asyncio import exceptions
import time 

from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_    # G1 = ชุด hg (ใช้ go จะเงียบไม่มี error)

def on_lowstate(msg: LowState_):
    print ("ได้รับข้อความแล้ว")

def main():
    ChannelFactoryInitialize(1,"lo")
    sub = ChannelSubscriber("rt/lowstate", LowState_)
    while True:
        time.sleep(1)
    
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
