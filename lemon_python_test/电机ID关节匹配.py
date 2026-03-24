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


class MotorMapper:
    def __init__(self):
        self.motors = list(range(1, 17))

        # 低刚度，防止暴力
        self.kP = 150
        self.kI = 0
        self.kD = 30
        self.curr_lim = 200

        # 连接
        try:
            self.dxl = DynamixelClient(self.motors, '/dev/ttyUSB0', 4000000)
            self.dxl.connect()
        except:
            try:
                self.dxl = DynamixelClient(self.motors, '/dev/ttyUSB1', 4000000)
                self.dxl.connect()
            except:
                self.dxl = DynamixelClient(self.motors, 'COM3', 4000000)
                self.dxl.connect()

        print("✅ 已连接")

        # 设置模式
        self.dxl.sync_write(self.motors, np.ones(16)*5, 11, 1)
        self.dxl.set_torque_enabled(self.motors, True)

        self.dxl.sync_write(self.motors, np.ones(16)*self.kP, 84, 2)
        self.dxl.sync_write(self.motors, np.ones(16)*self.kI, 82, 2)
        self.dxl.sync_write(self.motors, np.ones(16)*self.kD, 80, 2)
        self.dxl.sync_write(self.motors, np.ones(16)*self.curr_lim, 102, 2)

    def read_pos(self):
        return self.dxl.read_pos()

    def test_motor(self, motor_id):
        print(f"\n==============================")
        print(f"👉 正在测试：电机 ID = {motor_id}")
        print("👉 请盯着手，看看是哪个手指哪个关节在动！")
        print("==============================")

        pos = self.read_pos()
        base = pos.copy()

        for i in range(4):
            # 正方向
            pos[motor_id - 1] = base[motor_id - 1] + 0.25
            self.dxl.write_desired_pos(self.motors, pos)
            time.sleep(0.6)

            # 反方向
            pos[motor_id - 1] = base[motor_id - 1] - 0.25
            self.dxl.write_desired_pos(self.motors, pos)
            time.sleep(0.6)

        # 回到原位
        self.dxl.write_desired_pos(self.motors, base)

        print("✅ 这个电机测试完成")


def main():
    mapper = MotorMapper()

    print("\n📋 操作说明：")
    print("1️⃣ 每次输入一个 motor ID (1~16)")
    print("2️⃣ 观察哪个手指哪个关节在动")
    print("3️⃣ 记录下来！")
    print("0️⃣ 退出")

    while True:
        cmd = input("\n输入 motor ID: ")

        if cmd == "0":
            break

        try:
            mid = int(cmd)
            if 1 <= mid <= 16:
                mapper.test_motor(mid)
            else:
                print("❌ 输入范围 1~16")
        except:
            print("❌ 输入错误")


if __name__ == "__main__":
    main()