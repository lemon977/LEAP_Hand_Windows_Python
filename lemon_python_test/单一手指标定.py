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
import json
from pathlib import Path
from leap_hand_utils.dynamixel_client import *


class FingerCalibrator:
    def __init__(self, motors, name="finger"):
        self.motors = motors
        self.name = name

        # ===== 连接 =====
        self.dxl = DynamixelClient(self.motors, 'COM3', 4000000)
        self.dxl.connect()
        print(f"✅ 已连接 [{self.name}] -> {self.motors}")

        # ===== 位置模式 =====
        self.dxl.sync_write(self.motors, np.ones(len(motors)) * 5, 11, 1)

        # ===== 控制参数 =====
        self.max_delta = 0.25
        self.max_error = 0.4

        # ===== 标定文件 =====
        self.save_path = Path(f"{self.name}_calib.json")

        self.open_pos = None
        self.close_pos = None

        self.safe_init()

        # 自动加载
        if self.save_path.exists():
            self.load_calibration()

    # =========================
    def safe_init(self):
        print("🔒 安全初始化")
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
    def set_pos(self, target):
        raw = self.dxl.read_pos()

        # 防暴力
        target = raw + np.clip(target - raw, -self.max_error, self.max_error)

        # 限速
        delta = target - raw
        delta = np.clip(delta, -self.max_delta, self.max_delta)

        final = raw + delta

        self.dxl.write_desired_pos(self.motors, final)

        print(" target:", np.round(target, 3))
        print(" cmd   :", np.round(final, 3))
        print("------")

    def calibrate_all(self):
        print("\n===== 整手一键标定 =====")

        # ❗断电（关键）
        self.dxl.set_torque_enabled(self.motors, False)
        print("🔓 已解锁全部电机")

        # ===== 张开 =====
        input("\n👉 把整只手摆到【完全张开】，然后回车")
        open_all = self.read_pos()

        # ===== 闭合 =====
        input("\n👉 把整只手摆到【完全握拳】，然后回车")
        close_all = self.read_pos()

        # 上电
        self.dxl.set_torque_enabled(self.motors, True)
        print("🔒 已重新上电")

        # ===== 安全余量 =====
        margin_default = 0.1
        margin_thumb = 0.15

        for name, ids in FINGER_MAP.items():
            margin = margin_thumb if name == "thumb" else margin_default

            for i, mid in enumerate(ids):
                self.open_pos[mid-1] = open_all[mid-1] + margin
                self.close_pos[mid-1] = close_all[mid-1] - margin

        # 同时保存单指（很关键）
        self.save_finger(
            name,
            ids,
            open_all[[i-1 for i in ids]] + margin,
            close_all[[i-1 for i in ids]] - margin
        )

    print("\n✅ 整手标定完成（已自动拆分保存每个手指）")
    def calibrate(self):
        print("\n===== 开始标定 =====")

        # ❗ 关闭力矩（关键）
        self.dxl.set_torque_enabled(self.motors, False)
        print("🔓 已解锁电机（可以随便掰）")

        input("👉 手动摆【完全张开】，回车")
        open_raw = self.read_pos()

        input("👉 手动摆【完全闭合】，回车")
        close_raw = self.read_pos()

        # ❗ 重新上电（锁住当前位置）
        self.dxl.set_torque_enabled(self.motors, True)
        print("🔒 已重新上电")

        # ===== 安全余量 =====
        margin = 0.1
        self.open_pos = open_raw + margin
        self.close_pos = close_raw - margin

        print("\n✅ 标定完成")
        print("open :", np.round(self.open_pos, 3))
        print("close:", np.round(self.close_pos, 3))

        self.save_calibration()
    # =========================
    def save_calibration(self):
        data = {
            "motors": self.motors,
            "open": self.open_pos.tolist(),
            "close": self.close_pos.tolist()
        }

        with open(self.save_path, "w") as f:
            json.dump(data, f, indent=4)

        print(f"💾 已保存 -> {self.save_path}")

    # =========================
    def load_calibration(self):
        with open(self.save_path, "r") as f:
            data = json.load(f)

        self.open_pos = np.array(data["open"])
        self.close_pos = np.array(data["close"])

        print(f"📂 已加载标定 [{self.name}]")
        print("open :", np.round(self.open_pos, 3))
        print("close:", np.round(self.close_pos, 3))

    # =========================
    # 比例控制
    # =========================
    def move_ratio(self, ratio, steps=40):
        if self.open_pos is None:
            print("❌ 还没标定")
            return

        for i in range(steps):
            alpha = (i + 1) / steps
            r = alpha * ratio

            target = self.open_pos + r * (self.close_pos - self.open_pos)
            self.set_pos(target)
            time.sleep(0.02)

    def open_hand(self):
        self.move_ratio(0.0)

    def close_hand(self):
        self.move_ratio(1.0)


# =========================
def main():
    print("==== 通用手指标定工具 ====")

    motors = input("输入电机ID（空格分隔）: ")
    motors = [int(x) for x in motors.split()]

    name = input("输入手指名称（如 index/thumb）: ")

    finger = FingerCalibrator(motors, name)

    while True:
        print("\n==== MENU ====")
        print("1 标定")
        print("2 张开")
        print("3 闭合")
        print("4 读取位置")
        print("0 退出")

        cmd = input("输入: ")

        if cmd == "1":
            finger.calibrate()

        elif cmd == "2":
            finger.open_hand()

        elif cmd == "3":
            finger.close_hand()

        elif cmd == "4":
            finger.read_pos()

        elif cmd == "0":
            break


if __name__ == "__main__":
    main()