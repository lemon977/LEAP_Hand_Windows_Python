"""
Adapted from LEAP Hand (Shaw & Pathak, 2023, CC BY-NC 4.0)
Original repository: https://github.com/leap-hand/LEAP_Hand_Sim

Modifications by lemon977:
- Smooth interpolation motion
- Motor temperature protection
- Grasp ratio enhancements

⚠️ Non-commercial use only
"""
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import time
from leap_hand_utils.dynamixel_client import *


class FourFingerCalibrator:
    def __init__(self):
        # ===== 16个电机 =====
        self.motors = list(range(1, 17))

        self.dxl = DynamixelClient(self.motors, 'COM3', 4000000)
        self.dxl.connect()

        print("✅ 已连接（四指标定）")

        # ⚠️ 标定阶段：直接关闭力矩（关键！）
        self.dxl.set_torque_enabled(self.motors, False)
        print("👉 已关闭力矩，可以手动掰动")

        # ===== 手指映射 ===== 
        self.fingers = {
            "index":  [1, 2, 3, 4],
            "middle": [5, 6, 7, 8],
            "ring":   [9, 10, 11, 12],
            "thumb":  [13, 14, 15, 16],
        }

        self.results = {}

    # =========================
    def read_pos(self):
        pos = self.dxl.read_pos()
        print("📡 当前:", np.round(pos, 3))
        return pos

    # =========================
    def calibrate_one_finger(self, name, ids):
        print(f"\n====================")
        print(f"👉 标定 {name}")
        print(f"电机ID: {ids}")
        print("====================")

        input("👉 手动摆【完全张开】，然后回车")
        open_pos = self.read_pos()[[i-1 for i in ids]]

        input("👉 手动摆【完全握拳】，然后回车")
        close_pos = self.read_pos()[[i-1 for i in ids]]

        self.results[name] = {
            "open": open_pos,
            "close": close_pos
        }

        print(f"✅ {name} 完成")
        print("open :", np.round(open_pos, 3))
        print("close:", np.round(close_pos, 3))

    # =========================
    def run(self):
        for name, ids in self.fingers.items():
            self.calibrate_one_finger(name, ids)

        self.save_to_txt()

    # =========================
    def save_to_txt(self):
        filename = "four_finger_calibration.txt"

        with open(filename, "w") as f:
            f.write("===== LEAP HAND CALIBRATION (4 FINGERS) =====\n\n")

            for name, data in self.results.items():
                f.write(f"[{name}]\n")
                f.write(f"open  = {np.round(data['open'], 6).tolist()}\n")
                f.write(f"close = {np.round(data['close'], 6).tolist()}\n\n")

        print(f"\n💾 已保存到 {filename}")


# =========================
def main():
    calibrator = FourFingerCalibrator()
    calibrator.run()


if __name__ == "__main__":
    main()