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
import math

# ===================== LEAP Hand 官方固定换算参数 =====================
# 舵机分辨率：0 ~ 4095
# 对应角度：0 ~ 360° = 0 ~ 2π 弧度
# ============================================================
 
def native_to_rad(native_value):
    """
    功能：把 Dynamixel Wizard 里的原生值(0~4095) → 脚本用的弧度
    输入：native_value → 你在Wizard里看到的数字（如 2048）
    输出：rad → 你脚本里直接能用的弧度
    """
    return (native_value / 4095.0) * 2 * math.pi

def rad_to_native(rad_value):
    """
    功能：把脚本里的弧度 → 转回Wizard原生值
    """
    return (rad_value / (2 * math.pi)) * 4095.0

# ===================== 使用示例 =====================
if __name__ == "__main__":
    print("="*60)
    print("      LEAP HAND 换算工具：原生值(0-4095) ↔ 弧度(rad)")
    print("="*60)

    while True:
        print("\n请选择功能：")
        print("1 → 原生值(Wizard) 转 弧度(脚本)")
        print("2 → 弧度(脚本) 转 原生值(Wizard)")
        print("0 → 退出")
        choice = input("\n输入选择：")

        if choice == "0":
            break

        elif choice == "1":
            val = input("\n输入 Wizard 原生值(0-4095)：")
            try:
                native = float(val)
                rad = native_to_rad(native)
                print(f"✅ 原生值 {native} → 弧度 = {rad:.4f}")
            except:
                print("❌ 输入错误")

        elif choice == "2":
            val = input("\n输入 弧度值：")
            try:
                rad = float(val)
                native = rad_to_native(rad)
                print(f"✅ 弧度 {rad} → 原生值 = {native:.0f}")
            except:
                print("❌ 输入错误")

    print("\n退出工具")