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

class FullHandController:
    def __init__(self):
        # ===== 16个电机 =====
        self.motors = list(range(1, 17))

        self.dxl = DynamixelClient(self.motors, 'COM3', 4000000)
        self.dxl.connect()

        print("已连接（整手控制）")

        # ===== 位置模式 =====
        self.dxl.sync_write(self.motors, np.ones(16) * 5, 11, 1)

        # ===== 控制参数 =====
        self.max_delta = 0.2   # 每步最大增量（平滑插值可调整）
        self.max_error = 0.35  # 可保留，但平滑插值主要靠steps

        # ===== 标定数据 =====
        margin = 0.1
        open_all = np.array([
            3.136991, 1.237922, 1.067651, 4.741534,
            3.213690, 4.362642, 4.338098, 1.751806,
            3.141593, 1.211845, 2.702874, 3.089437,
            4.623418, 5.152642, 2.724350, 3.101709
        ])
        close_all = np.array([
            3.193748, 3.767457, 2.601632, 4.623418,
            3.190680, 6.933594, 5.483981, 1.774816,
            3.175340, 3.782796, 4.097263, 3.078699,
            4.922544, 4.887263, 3.572641, 4.845845
        ])

        self.open_pos = open_all + margin
        self.close_pos = close_all - margin

        print("open :", np.round(self.open_pos, 3))
        print("close:", np.round(self.close_pos, 3))

        self.safe_init()


    def safe_init(self):
        print("安全初始化")
        self.dxl.set_torque_enabled(self.motors, False)
        time.sleep(0.3)

        pos = self.read_pos()
        self.dxl.write_desired_pos(self.motors, pos)
        time.sleep(0.2)

        self.dxl.set_torque_enabled(self.motors, True)
        print("初始化完成")


    def read_pos(self):
        pos = self.dxl.read_pos()
        print("当前:", np.round(pos, 3))
        return pos


    # 平滑插值控制核心

    def set_pos(self, target, steps=10, sleep_time=0.02):
        """
        平滑插值控制整手运动
        - target: 目标位置 (16,)
        - steps: 平滑分段
        - sleep_time: 每步延时
        """
        current = self.dxl.read_pos()

        # 分步插值
        for i in range(1, steps + 1):
            alpha = i / steps
            interp = current + alpha * (target - current)
            self.dxl.write_desired_pos(self.motors, interp)
            pos_now = self.dxl.read_pos()
            # 打印位置
            print("目标:", np.round(interp, 3), " 当前:", np.round(pos_now, 3))
            time.sleep(sleep_time)


    # 整手比例控制

    def move_ratio(self, ratio, steps=50):
        print(f"\n ratio = {ratio}")
        target = self.open_pos + ratio * (self.close_pos - self.open_pos)
        self.set_pos(target, steps=steps)


    def open_hand(self):
        print("\n张开整手")
        self.move_ratio(0.0)

    def close_hand(self):
        print("\n握拳整手")
        self.move_ratio(1.0)


    # 任意抓握程度

    def grasp(self, ratio):
        ratio = np.clip(ratio, 0.0, 1.0)
        self.move_ratio(ratio)


    # 单手指测试

    def test_finger(self, name):
        finger_map = {
            "index": slice(0, 4),
            "middle": slice(4, 8),
            "ring": slice(8, 12),
            "thumb": slice(12, 16),
        }

        if name not in finger_map:
            print("手指名称错误")
            return

        s = finger_map[name]

        for _ in range(3):
            target = self.read_pos()
            target[s] = self.close_pos[s]
            self.set_pos(target, steps=20)
            time.sleep(0.5)

            target[s] = self.open_pos[s]
            self.set_pos(target, steps=20)
            time.sleep(0.5)


# =========================
def main():
    hand = FullHandController()

    while True:
        print("\n==== 整手控制 ====")
        print("1 张开")
        print("2 握拳")
        print("3 抓握(输入比例)")
        print("4 单手指测试")
        print("0 退出")

        cmd = input("输入: ")

        if cmd == "1":
            hand.open_hand()
        elif cmd == "2":
            hand.close_hand()
        elif cmd == "3":
            try:
                r = float(input("输入 ratio (0~1): "))
                hand.grasp(r)
            except ValueError:
                print("输入无效")
        elif cmd == "4":
            name = input("index / middle / ring / thumb: ")
            hand.test_finger(name)
        elif cmd == "0":
            break
        else:
            print("未知命令")


if __name__ == "__main__":
    main()