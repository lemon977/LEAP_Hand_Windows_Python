#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import time
import threading
from leap_hand_utils.dynamixel_client import *

class SafeMotorMapper:
    def __init__(self):
        self.motors = list(range(1, 17))
        self.stop_flag = False  

        # 极致安全参数
        self.kP = 120
        self.kI = 0
        self.kD = 40
        self.curr_lim = 180
        self.CURRENT_THRESHOLD = 150
        self.step_size = 0.05    # 单步移动幅度
        self.step_delay = 0.3    # 步间延迟

        # 连接COM3
        try:
            self.dxl = DynamixelClient(self.motors, 'COM3', 4000000)
            self.dxl.connect()
        except:
            print("❌ 连接失败，请检查COM口/电源/Wizard是否关闭")
            exit()

        print("✅ 连接成功 | Windows 安全模式")
        self.clear_all_errors()
        
        # 初始化舵机
        self.dxl.sync_write(self.motors, np.ones(16)*5, 11, 1)
        self.dxl.set_torque_enabled(self.motors, True)
        self.dxl.sync_write(self.motors, np.ones(16)*self.kP, 84, 2)
        self.dxl.sync_write(self.motors, np.ones(16)*self.kI, 82, 2)
        self.dxl.sync_write(self.motors, np.ones(16)*self.kD, 80, 2)
        self.dxl.sync_write(self.motors, np.ones(16)*self.curr_lim, 102, 2)
        time.sleep(0.2)

    # 清除硬件错误
    def clear_all_errors(self):
        try:
            self.dxl.sync_write(self.motors, [0]*16, 70, 1)
            time.sleep(0.1)
            print("✅ 硬件错误已清除")
        except:
            pass

    # 读取电流/位置
    def read_current(self):
        try:
            return np.array(self.dxl.read_cur())
        except:
            return np.zeros(16)
    def read_pos(self):
        return np.array(self.dxl.read_pos())

    # 监听回车停止
    def wait_for_enter(self):
        input()
        self.stop_flag = True

    # ---------------------- 核心：平滑移动（单电机）----------------------
    def smooth_single_move(self, motor_id, direction, base_pos):
        index = motor_id - 1
        current_pos = base_pos.copy()
        self.stop_flag = False
        final_limit_pos = current_pos.copy()

        enter_thread = threading.Thread(target=self.wait_for_enter, daemon=True)
        enter_thread.start()

        while not self.stop_flag:
            current_pos[index] += direction
            send_pos = base_pos.copy()
            send_pos[index] = current_pos[index]

            try:
                self.dxl.write_desired_pos(self.motors, send_pos)
            except:
                break

            time.sleep(self.step_delay)
            final_limit_pos = current_pos.copy()

            # 堵转保护
            current = self.read_current()[index]
            if current > self.CURRENT_THRESHOLD:
                print(f"⚠️  堵转保护！电流={current:.1f}mA")
                break

        return final_limit_pos

    # ---------------------- 新增：平滑回归初始位置 ----------------------
    def smooth_return_home(self, motor_id, current_pos, home_pos):
        """平滑回到初始位置，无硬跳变"""
        index = motor_id - 1
        target_pos = current_pos.copy()
        print("↩️ 平滑回归初始位置...")

        # 分步插值移动
        steps = 30
        for i in range(steps):
            ratio = (i + 1) / steps
            target_pos[index] = current_pos[index] + (home_pos[index] - current_pos[index]) * ratio
            send_pos = home_pos.copy()
            send_pos[index] = target_pos[index]
            self.dxl.write_desired_pos(self.motors, send_pos)
            time.sleep(0.05)
        time.sleep(0.5)

    # ---------------------- 新增：保存数据到TXT文件 ----------------------
    def save_limit_data(self, motor_id, home_pos, flex_pos, extend_pos):
        filename = f"motor_{motor_id}_limit.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"=== 电机 ID {motor_id} 极限位置记录 ===\n")
            f.write(f"初始位置(弧度)：{np.round(home_pos, 4)}\n")
            f.write(f"弯曲极限位置(弧度)：{np.round(flex_pos, 4)}\n")
            f.write(f"张开极限位置(弧度)：{np.round(extend_pos, 4)}\n")
            f.write("\n使用说明：\n")
            f.write("1. 控制代码中目标位置必须在【张开极限 ~ 弯曲极限】之间\n")
            f.write("2. 严格遵守此范围，永远不会堵转、红灯、报错\n")
        print(f"✅ 数据已保存至：{filename}")

    # ---------------------- 主测试逻辑 ----------------------
    def test_motor_safe_limit(self, motor_id):
        print(f"\n========================================")
        print(f"🎯 测试电机 ID: {motor_id} | 平滑移动 + 数据记录")
        print(f"✅ 按回车开始 → 到极限按回车停止")
        print("========================================")

        # 1. 读取并打印初始位置
        home_pos = self.read_pos().copy()
        print(f"\n📌 初始位置：{np.round(home_pos, 4)}")

        # 2. 测试弯曲极限
        print("\n1/3 测试【弯曲方向】极限")
        input("按回车开始...")
        flex_limit_pos = self.smooth_single_move(motor_id, self.step_size, home_pos)
        print(f"📌 弯曲极限位置：{np.round(flex_limit_pos, 4)}")

        # 3. 平滑回初始位置
        self.smooth_return_home(motor_id, flex_limit_pos, home_pos)

        # 4. 测试张开极限
        print("\n2/3 测试【张开方向】极限")
        input("按回车开始...")
        extend_limit_pos = self.smooth_single_move(motor_id, -self.step_size, home_pos)
        print(f"📌 张开极限位置：{np.round(extend_limit_pos, 4)}")

        # 5. 最终平滑回中
        self.smooth_return_home(motor_id, extend_limit_pos, home_pos)

        # 6. 保存数据到文件
        self.save_limit_data(motor_id, home_pos, flex_limit_pos, extend_limit_pos)
        print(f"\n🎉 电机 {motor_id} 测试全部完成！")

# ===================== 主程序 =====================
def main():
    try:
        mapper = SafeMotorMapper()
    except Exception as e:
        print(f"初始化失败: {e}")
        return

    print("\n" + "="*60)
    print(" 🖥️  Windows 专用 - 电机极限测试(平滑回中+数据记录)")
    print(" 输入 1-16：测试电机 | 0：退出 | 移动中按回车=停止")
    print(" 自动生成TXT文件记录极限位置")
    print("="*60)

    while True:
        cmd = input("\n输入电机 ID: ").strip()
        if cmd == "0":
            print("\n👋 程序退出")
            break
        try:
            mid = int(cmd)
            if 1 <= mid <= 16:
                mapper.test_motor_safe_limit(mid)
            else:
                print("❌ 输入 1~16")
        except:
            print("❌ 输入错误")

if __name__ == "__main__":
    main()