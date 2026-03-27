import time
import sys
import os
import h5py
import numpy as np
from datetime import datetime

script_dir = os.path.dirname(os.path.abspath(__file__))
sdk_python_dir = os.path.join(script_dir, "..", "python")
sys.path.append(os.path.abspath(sdk_python_dir))

from leap_hand_utils.dynamixel_client import *

# ===================== 配置 =====================
SERIAL_PORT = "COM3"
BAUDRATE = 4000000
MOTOR_IDS = list(range(1, 17))
SAMPLE_FREQUENCY = 10  # 10Hz稳定
BUFFER_SIZE = 10

SAVE_PATH = f"leaphand_teach_{datetime.now().strftime('%Y%m%d_%H%M%S')}.h5"

def init_hdf5(file_path):
    with h5py.File(file_path, "w") as f:
        f.create_dataset("timestamp", (0,), maxshape=(None,), dtype=np.float64, compression="gzip")
        f.create_dataset("joint_angles", (0, 16), maxshape=(None, 16), dtype=np.float32, compression="gzip")

def append_data_batch(file_path, timestamps, joint_angles):
    with h5py.File(file_path, "a") as f:
        f["timestamp"].resize((f["timestamp"].shape[0] + len(timestamps),))
        f["timestamp"][-len(timestamps):] = timestamps
        f["joint_angles"].resize((f["joint_angles"].shape[0] + len(joint_angles), 16))
        f["joint_angles"][-len(joint_angles):] = joint_angles

def main():
    hand = None
    
    try:
        print(f"连接 {SERIAL_PORT}...")
        hand = DynamixelClient(MOTOR_IDS, port=SERIAL_PORT, baudrate=BAUDRATE)
        hand.connect()
        print("连接成功")
        
        # 关键：关闭力矩，这样手可以自由移动
        hand.set_torque_enabled(MOTOR_IDS, False)
        print("    力矩已关闭 - 现在可以手动移动机械手")
        print("   （手会下垂，请用手托着或放在桌面上操作）")
        
        # 测试读取（确认能读编码器）
        test_pos = hand.read_pos()
        print(f"当前位置: {np.round(test_pos, 2)}")
        
    except Exception as e:
        print(f" 初始化失败: {e}")
        return

    init_hdf5(SAVE_PATH)
    ts_buffer = []
    angle_buffer = []
    total_count = 0

    print(f"\n 开始示教采集（{SAMPLE_FREQUENCY}Hz）")
    print("=" * 50)
    print("操作说明：")
    print("  - 用手直接掰动机械手到目标姿势")
    print("  - 保持姿势不动，系统会自动记录")
    print("  - 按 Ctrl+C 停止采集")
    print("=" * 50)

    try:
        while True:
            loop_start = time.time()
            
            # 只读位置（不写入任何控制指令）
            try:
                current_angles = hand.read_pos()
            except Exception as e:
                print(f"读取错误: {e}")
                time.sleep(0.1)
                continue

            current_ts = time.time()
            ts_buffer.append(current_ts)
            angle_buffer.append(current_angles)
            total_count += 1

            # 批量写入
            if len(ts_buffer) >= BUFFER_SIZE:
                append_data_batch(SAVE_PATH, ts_buffer, angle_buffer)
                print(f" 已记录: {total_count} 帧 | 当前角度: {np.round(current_angles[[0,4,8,12]], 2)}")  # 只显示4个根部关节
                ts_buffer.clear()
                angle_buffer.clear()

            # 频率控制
            elapsed = time.time() - loop_start
            sleep_time = max(0.001, 1.0/SAMPLE_FREQUENCY - elapsed)
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\n 停止采集")
    finally:
        # 保存剩余数据
        if ts_buffer:
            try:
                append_data_batch(SAVE_PATH, ts_buffer, angle_buffer)
            except:
                pass
        
        # 安全关闭（保持力矩关闭状态断开）
        print("断开连接...")
        try:
            hand.disconnect()
        except:
            pass
        
        duration = total_count / SAMPLE_FREQUENCY
        print(f"\n 示教完成！")
        print(f"   总帧数: {total_count}")
        print(f"   时长: {duration:.1f} 秒")
        print(f"   文件: {SAVE_PATH}")

if __name__ == "__main__":
    main()