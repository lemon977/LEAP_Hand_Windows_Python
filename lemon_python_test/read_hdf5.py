#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HDF5数据读取脚本 - 用于读取LEAP Hand采集的数据
"""

import h5py
import numpy as np
import matplotlib.pyplot as plt


def read_hdf5(file_path):
    """
    读取HDF5文件，返回时间戳和关节角度
    
    Parameters:
        file_path: HDF5文件路径
    
    Returns:
        timestamps: 时间戳数组 (N,)
        joint_angles: 关节角度数组 (N, 16)
    """
    with h5py.File(file_path, "r") as f:
        timestamps = f["timestamp"][:]
        joint_angles = f["joint_angles"][:]
    
    print(f"✅ 读取成功: {file_path}")
    print(f"   总帧数: {len(timestamps)}")
    print(f"   持续时间: {timestamps[-1] - timestamps[0]:.2f} 秒")
    print(f"   实际频率: {len(timestamps) / (timestamps[-1] - timestamps[0]):.1f} Hz")
    print(f"   关节角度形状: {joint_angles.shape}")
    
    return timestamps, joint_angles


def print_info(timestamps, joint_angles):
    """打印数据基本信息"""
    print("\n" + "="*50)
    print("数据概览")
    print("="*50)
    
    # 时间信息
    duration = timestamps[-1] - timestamps[0]
    avg_interval = np.mean(np.diff(timestamps))
    std_interval = np.std(np.diff(timestamps))
    
    print(f"时间戳范围: {timestamps[0]:.3f} ~ {timestamps[-1]:.3f} s")
    print(f"总时长: {duration:.2f} s")
    print(f"平均间隔: {avg_interval*1000:.2f} ms (std: {std_interval*1000:.2f} ms)")
    print(f"实际采样率: {1/avg_interval:.1f} Hz")
    
    # 关节角度统计
    print(f"\n关节角度统计 (16个电机):")
    print(f"  最小值: {np.min(joint_angles, axis=0).round(3)}")
    print(f"  最大值: {np.max(joint_angles, axis=0).round(3)}")
    print(f"  均值:   {np.mean(joint_angles, axis=0).round(3)}")
    print(f"  标准差: {np.std(joint_angles, axis=0).round(3)}")


def plot_joints(timestamps, joint_angles, finger=None):
    """
    绘制关节角度曲线
    
    Parameters:
        timestamps: 时间戳
        joint_angles: 关节角度 (N, 16)
        finger: 指定手指名称 (index/middle/ring/thumb)，None则绘制全部
    """
    # 手指到电机索引的映射
    finger_map = {
        "index":  slice(0, 4),   # 食指: 0-3
        "middle": slice(4, 8),   # 中指: 4-7
        "ring":   slice(8, 12),  # 无名指: 8-11
        "thumb":  slice(12, 16), # 拇指: 12-15
    }
    
    if finger and finger in finger_map:
        idx = finger_map[finger]
        data = joint_angles[:, idx]
        motors = list(range(idx.start, idx.stop))
        title = f"{finger.capitalize()} Finger Joints"
        n_plots = 4
    else:
        data = joint_angles
        motors = list(range(16))
        title = "All Joints (16 Motors)"
        n_plots = 16
    
    # 创建子图
    n_rows = (n_plots + 3) // 4  # 每行4个
    fig, axes = plt.subplots(n_rows, 4, figsize=(16, 3*n_rows), sharex=True)
    axes = axes.flatten() if n_plots > 1 else [axes]
    
    # 相对时间（从0开始）
    t = timestamps - timestamps[0]
    
    for i, (ax, motor_id) in enumerate(zip(axes[:n_plots], motors)):
        ax.plot(t, data[:, i], linewidth=1)
        ax.set_ylabel(f"Motor {motor_id}")
        ax.set_ylim([joint_angles[:, motor_id].min() - 0.1, 
                     joint_angles[:, motor_id].max() + 0.1])
        ax.grid(True, alpha=0.3)
    
    # 隐藏多余的子图
    for ax in axes[n_plots:]:
        ax.axis('off')
    
    axes[-1].set_xlabel("Time (s)")
    fig.suptitle(title, fontsize=14)
    plt.tight_layout()
    plt.show()


def export_to_csv(timestamps, joint_angles, output_file):
    """导出为CSV格式"""
    # 创建表头
    header = ["timestamp"] + [f"motor_{i}" for i in range(16)]
    
    # 组合数据
    data = np.column_stack([timestamps, joint_angles])
    
    # 保存
    np.savetxt(output_file, data, delimiter=",", header=",".join(header), comments="")
    print(f"✅ 已导出CSV: {output_file}")


def main():
    import sys
    
    # 命令行参数或交互式输入
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        # 自动查找最新的hdf5文件
        import glob
        files = glob.glob("leaphand_data_*.h5")
        if not files:
            file_path = input("请输入HDF5文件路径: ")
        else:
            files.sort()
            file_path = files[-1]
            print(f"自动选择最新文件: {file_path}")
    
    # 读取数据
    timestamps, joint_angles = read_hdf5(file_path)
    
    # 打印信息
    print_info(timestamps, joint_angles)
    
    # 交互式菜单
    while True:
        print("\n" + "="*50)
        print("操作选项:")
        print("1. 绘制所有关节")
        print("2. 绘制食指 (index)")
        print("3. 绘制中指 (middle)")
        print("4. 绘制无名指 (ring)")
        print("5. 绘制拇指 (thumb)")
        print("6. 导出为CSV")
        print("0. 退出")
        
        choice = input("选择: ").strip()
        
        if choice == "1":
            plot_joints(timestamps, joint_angles)
        elif choice == "2":
            plot_joints(timestamps, joint_angles, "index")
        elif choice == "3":
            plot_joints(timestamps, joint_angles, "middle")
        elif choice == "4":
            plot_joints(timestamps, joint_angles, "ring")
        elif choice == "5":
            plot_joints(timestamps, joint_angles, "thumb")
        elif choice == "6":
            csv_file = file_path.replace(".h5", ".csv")
            export_to_csv(timestamps, joint_angles, csv_file)
        elif choice == "0":
            break
        else:
            print("无效选择")


if __name__ == "__main__":
    main()