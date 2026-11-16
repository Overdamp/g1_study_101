"""m3_band.py: step loop + viewer + หนังยาง (งาน M3) โครงให้เติม

รัน:  python3 m3_band.py                        (หน้าต่าง: Space หยุด · 9 เปิด/ปิดหนังยาง · 7/↑ สั้นลง · 8/↓ ยาวขึ้น)
      python3 m3_band.py --headless --duration 5
ก่อนเริ่ม: เติม ElasticBand.force / apply ใน g1mj_skeleton.py (เทสต์ ElasticBand ต้องผ่าน)

ทายก่อนรัน: (1) pelvis (qpos[2]) นิ่งที่ความสูงเท่าไร  (มวล 34.14 kg, k = 200 N/m, จุดแขวน z = 3, length 0)
            (2) ศอกซ้ายห้อยค้างที่กี่องศา (งาน 1.4 วัดได้ +69.3°)
เฉลย: ../complete/m3_band.py
"""

import argparse

import numpy as np

from g1mj_skeleton import ElasticBand, G, load, motor_q, run

SLOT_ELBOW_L = 18


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--duration", type=float, default=None)
    ap.add_argument("--stiffness", type=float, default=200.0)
    args = ap.parse_args()
    if args.headless and args.duration is None:
        args.duration = 5.0

    m, d = load()
    band = ElasticBand(stiffness=args.stiffness)
    # TODO 1: คำนวณความสูงที่คาด: z = point_z − m·g / k   (m = m.body_subtreemass[0]) แล้วพิมพ์

    def step_fn(m, d):
        # TODO 2: band.apply(m, d)   (ไม่ต้องตั้ง ctrl: ctrl = 0 = มอเตอร์ไม่ออกแรง)
        pass

    def report(m, d):
        # TODO 3: พิมพ์ d.time, d.qpos[2], band.f[2], ศอกซ้ายเป็นองศา (motor_q(m, d)[SLOT_ELBOW_L])
        pass

    run(m, d, step_fn, duration=args.duration, headless=args.headless,
        key_callback=band.key, every=0.5, every_fn=report)
    # คำถาม: ทำไม pelvis นิ่งไม่ตรงกับที่ทายเป๊ะ (ใบ้: main.cc วัดระยะจากอะไร ออกแรงที่ body ไหน)
    # คำถาม: --stiffness 400 แล้ว z เปลี่ยนเท่าไร ตรงกับสูตรไหม


if __name__ == "__main__":
    main()
