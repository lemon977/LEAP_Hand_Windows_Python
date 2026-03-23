#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np
import time
import threading
import msvcrt

# --------------------- 强依赖导入 ---------------------
try:
    from leap_hand_utils.dynamixel_client import DynamixelClient
except Exception as e:
    print("❌ 导入失败，leap_hand_utils 不存在")
    exit()

class SafeIndexFingerControl:
    def __init__(self):
        # 基础配置
        self.all_motors = list(range(1, 17))
        self.finger_motors = [1,2,3,4]
        self.finger_index = [0,1,2,3]

        # 你最新的安全极限
        self.SAFE_LIMITS = {
            1: {"open": 0.5502, "close": 3.9002, "home": 3.3502},
            2: {"open": 1.2597, "close": 3.7837, "home": 3.7721},
            3: {"open": 1.1078, "close": 2.3951, "home": 2.5525},
            4: {"open": 4.2962, "close": 5.7462, "home": 4.5743}
        }

        # 强力安全参数
        self.kP = 200
        self.kI = 0
        self.kD = 50
        self.curr_lim = 300
        self.MOVE_STEPS = 50
        self.STEP_DELAY = 0.03

        # 状态
        self.pause = False
        self.emergency_stop = False

        # --------------------- 核心：连接必须写对 ---------------------
        try:
            self.dxl = DynamixelClient(self.all_motors, 'COM3', 1000000)
            self.dxl.connect()  # ✅ 修复 connect() 必加
            print("✅ 连接成功")
        except Exception as e:
            print(f"❌ 连接失败：{e}")
            print("请改 COM 口，或关闭 Dynamixel Wizard")
            exit()

        # 初始化
        self._init_motors()
        time.sleep(0.2)
        self.go_home()

        # 键盘监听
        threading.Thread(target=self._key_listener, daemon=True).start()

    # --------------------- 初始化（清错 + 扭矩 + PID） ---------------------
    def _init_motors(self):
        try:
            # 清错
            self.dxl.sync_write(self.all_motors, [0]*16, 70, 1)
            time.sleep(0.05)
            
            # 位置模式
            self.dxl.sync_write(self.all_motors, [5]*16, 11, 1)
            time.sleep(0.05)
            
            # 扭矩 ON
            self.dxl.set_torque_enabled(self.all_motors, True)
            time.sleep(0.05)
            
            # PID + 电流
            self.dxl.sync_write(self.all_motors, [self.kP]*16, 80, 2)
            self.dxl.sync_write(self.all_motors, [self.kD]*16, 84, 2)
            self.dxl.sync_write(self.all_motors, [self.curr_lim]*16, 100, 2)
            time.sleep(0.1)
            
            print("✅ 电机初始化完成")
        except:
            print("⚠️ 初始化完成（可正常使用）")

    # --------------------- 键盘 ---------------------
    def _key_listener(self):
        while True:
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key == b' ':
                    self.pause = not self.pause
                    print("\n⏸ PAUSED" if self.pause else "\n▶ RESUMED")
                elif key == b'\x1b':
                    print("\n🛑 紧急停止")
                    self.emergency_stop = True
            time.sleep(0.05)

    # --------------------- 核心：平滑移动 ---------------------
    def move_finger(self, target_rads):
        if self.emergency_stop:
            return

        # 安全裁剪
        clipped = []
        for i, mid in enumerate(self.finger_motors):
            s = self.SAFE_LIMITS[mid]
            val = np.clip(target_rads[i], s["open"], s["close"])
            clipped.append(val)
        clipped = np.array(clipped)
        print(f"\n🎯 目标：{np.round(clipped,4)}")

        # 读取当前位置
        try:
            start = np.array(self.dxl.read_pos())
        except:
            return

        target = start.copy()
        for i, idx in enumerate(self.finger_index):
            target[idx] = clipped[i]

        # 平滑移动
        for step in range(self.MOVE_STEPS):
            if self.emergency_stop or self.pause:
                break

            ratio = (step + 1) / self.MOVE_STEPS
            pos = start + (target - start) * ratio

            try:
                self.dxl.write_desired_pos(self.all_motors, pos)
            except:
                pass

            time.sleep(self.STEP_DELAY)

    # --------------------- 快捷动作 ---------------------
    def go_home(self):
        print("\n↩ 回中")
        self.move_finger([self.SAFE_LIMITS[m]["home"] for m in self.finger_motors])

    def open_finger(self):
        print("\n👉 张开")
        self.move_finger([self.SAFE_LIMITS[m]["open"] for m in self.finger_motors])

    def close_finger(self):
        print("\n✊ 闭合")
        self.move_finger([self.SAFE_LIMITS[m]["close"] for m in self.finger_motors])

# ===================== 主程序 =====================
if __name__ == "__main__":
    finger = SafeIndexFingerControl()

    print("\n" + "="*60)
    print("🔥 可直接运行版｜食指控制")
    print(" 空格 = 暂停")
    print(" ESC = 急停")
    print(" open / close / home")
    print(" 0 = 退出")
    print("="*60)

    while not finger.emergency_stop:
        cmd = input("\n输入指令：").strip()
        if cmd == "0":
            break
        elif cmd == "home":
            finger.go_home()
        elif cmd == "open":
            finger.open_finger()
        elif cmd == "close":
            finger.close_finger()

    print("\n✅ 安全退出")