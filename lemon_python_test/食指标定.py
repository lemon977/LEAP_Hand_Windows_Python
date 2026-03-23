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

class IndexFingerFinal:
    def __init__(self):
        self.motors = [1, 2, 3, 4]

        # ===== 连接 =====
        self.dxl = DynamixelClient(self.motors, 'COM3', 4000000)
        self.dxl.connect()

        print("✅ 已连接（食指最终版）")

        # ===== 位置模式 =====
        self.dxl.sync_write(self.motors, np.ones(4)*5, 11, 1)

        # ===== 控制参数 =====
        self.max_delta = 0.25
        self.max_error = 0.4

        # =====  你的真实标定数据 =====
        open_raw  = np.array([3.106, 1.239, 1.075, 4.633])
        close_raw = np.array([3.122, 3.761, 2.121, 5.501])

        # =====  安全余量（防红灯）=====
        margin = 0.1

        self.open_pos  = open_raw  + margin
        self.close_pos = close_raw - margin

        print("👉 open :", np.round(self.open_pos, 3))
        print("👉 close:", np.round(self.close_pos, 3))

        self.safe_init()

    # =========================
    def safe_init(self):
        print(" 安全初始化")
        self.dxl.set_torque_enabled(self.motors, False)
        time.sleep(0.3)

        pos = self.read_pos()
        self.dxl.write_desired_pos(self.motors, pos)
        time.sleep(0.2)

        self.dxl.set_torque_enabled(self.motors, True)
        print("✅ OK")

    # =========================
    def read_pos(self):
        pos = self.dxl.read_pos()
        print("📡 当前:", np.round(pos, 3))
        return pos

    # =========================
    # 核心控制
    # =========================
    def set_pos(self, target):
        raw = self.dxl.read_pos()

        # 防暴力（避免红灯）
        target = raw + np.clip(target - raw, -self.max_error, self.max_error)

        # 限速
        delta = target - raw
        delta = np.clip(delta, -self.max_delta, self.max_delta)

        final = raw + delta

        self.dxl.write_desired_pos(self.motors, final)

        print(" target:", np.round(target, 3))
        print(" raw   :", np.round(raw, 3))
        print(" cmd   :", np.round(final, 3))
        print("------")

    # =========================
    # 比例控制
    # =========================
    def move_ratio(self, ratio, steps=40):
        print(f"\n👉 ratio = {ratio}")

        for i in range(steps):
            alpha = (i + 1) / steps
            r = alpha * ratio

            target = self.open_pos + r * (self.close_pos - self.open_pos)
            self.set_pos(target)

            time.sleep(0.02)

    # =========================
    def open_hand(self):
        print("\n 张开")
        self.move_ratio(0.0)

    def close_hand(self):
        print("\n 握拳")
        self.move_ratio(1.0)

    # =========================
    def test_joint(self, jid):
        print(f"\n 单关节测试 {jid}")
        idx = jid - 1

        for _ in range(3):
            target = self.read_pos()
            target[idx] = self.close_pos[idx]
            self.set_pos(target)
            time.sleep(0.5)

            target[idx] = self.open_pos[idx]
            self.set_pos(target)
            time.sleep(0.5)

    # =========================
    def monitor(self):
        while True:
            self.read_pos()
            time.sleep(0.2)


# =========================
def main():
    tester = IndexFingerFinal()

    while True:
        print("\n==== 食指 FINAL ====")
        print("1 张开")
        print("2 握拳")
        print("3 单关节测试")
        print("4 实时监控")
        print("0 退出")

        cmd = input("输入: ")

        if cmd == "1":
            tester.open_hand()

        elif cmd == "2":
            tester.close_hand()

        elif cmd == "3":
            jid = int(input("输入关节ID (1-4): "))
            tester.test_joint(jid)

        elif cmd == "4":
            tester.monitor()

        elif cmd == "0":
            break


if __name__ == "__main__":
    main()