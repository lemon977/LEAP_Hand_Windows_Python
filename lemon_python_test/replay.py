#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HDF5数据重播脚本 - 超慢速平滑回放，带多重速度保护
"""

import time
import sys
import os
import h5py
import numpy as np

script_dir = os.path.dirname(os.path.abspath(__file__))
sdk_python_dir = os.path.join(script_dir, "..", "python")
sys.path.append(os.path.abspath(sdk_python_dir))

from leap_hand_utils.dynamixel_client import *


class SafeReplayer:
    def __init__(self, port='COM3', baudrate=4000000):
        self.motors = list(range(1, 17))
        self.dxl = DynamixelClient(self.motors, port, baudrate)
        
        # 🔴 保守保护参数
        self.max_delta_per_step = 0.05      # 单步最大0.05 rad (~3度)
        self.min_step_time = 0.05           # 每步最少50ms
        self.default_step_duration = 0.2    # 默认每步200ms
        
        # 安全边界
        self.pos_low = np.array([2.5, 0.5, 0.5, 4.0, 2.5, -2.5, 3.5, 1.0, 
                                 2.5, 0.5, 1.5, 2.5, 4.0, 4.5, 2.0, 2.5])
        self.pos_high = np.array([3.8, 4.5, 3.5, 5.0, 3.8, 1.5, 6.0, 3.0, 
                                  3.8, 4.5, 5.0, 4.0, 5.5, 6.0, 4.5, 5.5])
        
    def connect(self):
        self.dxl.connect()
        print("✅ 已连接")
        
        # 设置电机内部平滑参数（更保守）
        self.dxl.sync_write(self.motors, np.ones(16) * 50, 112, 4)   # Profile Velocity: 50
        self.dxl.sync_write(self.motors, np.ones(16) * 20, 108, 4)   # Profile Acceleration: 20
        
        self.dxl.set_torque_enabled(self.motors, True)
        print("🔒 力矩开启")
        
        self.current_pos = self.dxl.read_pos()
        print(f"当前位置: {np.round(self.current_pos[[0,4,8,12]], 2)}")
        
    def disconnect(self):
        print("\n关闭力矩...")
        self.dxl.set_torque_enabled(self.motors, False)
        time.sleep(0.2)
        self.dxl.disconnect()
        
    def safe_move(self, target):
        """超保守移动：小步长，强制延时"""
        target = np.clip(target, self.pos_low, self.pos_high)
        
        start_pos = self.dxl.read_pos()
        total_delta = np.abs(target - start_pos)
        max_delta = np.max(total_delta)
        
        # 计算所需步数（每步最多0.05 rad）
        n_steps = max(int(max_delta / self.max_delta_per_step), 3)
        
        print(f"  移动距离: {max_delta:.3f} rad, 分{n_steps}步执行")
        
        for i in range(1, n_steps + 1):
            alpha = i / n_steps
            interp = start_pos + alpha * (target - start_pos)
            
            # 写入并强制等待
            self.dxl.write_desired_pos(self.motors, interp)
            time.sleep(self.min_step_time)
            
            # 每5步打印一次
            if i % 5 == 0 or i == n_steps:
                current = self.dxl.read_pos()
                error = np.max(np.abs(current - interp))
                print(f"    步{i}/{n_steps}, 跟踪误差: {error:.3f}")
        
        # 最终到达检查
        final_pos = self.dxl.read_pos()
        final_error = np.max(np.abs(final_pos - target))
        if final_error > 0.1:
            print(f"  ⚠️ 最终误差较大: {final_error:.3f}, 修正中...")
            self.dxl.write_desired_pos(self.motors, target)
            time.sleep(0.3)
        
        self.current_pos = target
        
    def replay_very_slow(self, hdf5_file, frame_interval=1.0):
        """
        超慢速重播：每帧之间固定间隔，忽略原始时间戳
        
        Parameters:
            frame_interval: 每帧之间的固定时间（秒），默认1秒
        """
        with h5py.File(hdf5_file, "r") as f:
            timestamps = f["timestamp"][:]
            joint_angles = f["joint_angles"][:]
        
        n_frames = len(joint_angles)
        print(f"\n📂 加载: {n_frames}帧")
        print(f"   预计用时: ~{n_frames * frame_interval / 60:.1f} 分钟")
        
        # 移动到起始位置（很慢）
        print(f"\n🐢 移动到起始位置（很慢，请等待）...")
        self.safe_move(joint_angles[0])
        input("\n准备就绪，按回车开始超慢速播放...")
        
        print(f"\n▶️ 开始播放，每帧间隔{frame_interval}秒")
        print("   按Ctrl+C随时暂停")
        
        try:
            for i in range(n_frames):
                target = joint_angles[i]
                
                # 检查合理性
                if np.any(target < self.pos_low - 0.5) or np.any(target > self.pos_high + 0.5):
                    print(f"   ⚠️ 帧{i} 数据异常，跳过")
                    continue
                
                print(f"\n帧 {i+1}/{n_frames} [{100*i/n_frames:.1f}%]")
                print(f"   目标: {np.round(target[[0,4,8,12]], 2)}")
                
                # 执行移动
                self.safe_move(target)
                
                # 帧间等待（额外延时）
                if i < n_frames - 1:
                    time.sleep(frame_interval)
                    
        except KeyboardInterrupt:
            print("\n⏸️ 用户暂停")
            input("按回车继续，或Ctrl+C退出...")
            
        print("\n✅ 播放完成")
        
    def step_by_step(self, hdf5_file):
        """单步模式：按回车执行下一帧"""
        with h5py.File(hdf5_file, "r") as f:
            joint_angles = f["joint_angles"][:]
        
        n_frames = len(joint_angles)
        print(f"\n🎬 单步模式: 共{n_frames}帧")
        print("   按回车执行下一帧，输入q退出")
        
        # 移动到起始位置
        self.safe_move(joint_angles[0])
        
        i = 0
        while i < n_frames:
            cmd = input(f"\n帧{i+1}/{n_frames} [{100*i/n_frames:.1f}%] 按回车继续: ").strip()
            if cmd.lower() == 'q':
                break
            
            self.safe_move(joint_angles[i])
            i += 1
        
        print("✅ 单步播放结束")


def main():
    import glob
    
    files = glob.glob("leaphand_*.h5")
    if not files:
        print("未找到HDF5文件")
        return
    
    files.sort()
    print("可用文件:")
    for i, f in enumerate(files):
        print(f"  {i}: {f}")
    
    choice = input(f"\n选择文件 (0-{len(files)-1}, 默认最新): ").strip()
    file_idx = int(choice) if choice.isdigit() else -1
    hdf5_file = files[file_idx]
    
    print("\n播放模式:")
    print("1. 超慢速连续播放（每帧1秒，推荐）")
    print("2. 单步模式（按回车执行）")
    print("3. 自定义间隔")
    
    mode = input("选择 (1/2/3): ").strip()
    
    replayer = SafeReplayer()
    
    try:
        replayer.connect()
        
        if mode == "1":
            replayer.replay_very_slow(hdf5_file, frame_interval=1.0)
        elif mode == "2":
            replayer.step_by_step(hdf5_file)
        elif mode == "3":
            interval = float(input("每帧间隔（秒，建议0.1-0.3）: ") or "1.0")
            replayer.replay_very_slow(hdf5_file, frame_interval=interval)
        else:
            print("无效选择")
            
    except KeyboardInterrupt:
        print("\n用户中断")
    finally:
        replayer.disconnect()


if __name__ == "__main__":
    main()