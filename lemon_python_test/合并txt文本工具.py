"""
Adapted from LEAP Hand (Shaw & Pathak, 2023, CC BY-NC 4.0)
Original repository: https://github.com/leap-hand/LEAP_Hand_Sim

Modifications by lemon977:
- Smooth interpolation motion
- Motor temperature protection
- Grasp ratio enhancements

⚠️ Non-commercial use only
"""
import argparse
import sys
 
def merge_files(input_files, output_file, delimiter='\n\n'):
    """
    按顺序合并多个文件到一个输出文件
    :param input_files: 输入文件路径列表（按合并顺序）
    :param output_file: 输出文件路径
    :param delimiter: 文件之间的分隔符（默认两个换行）
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as outfile:
            for i, file_path in enumerate(input_files):
                try:
                    with open(file_path, 'r', encoding='utf-8') as infile:
                        content = infile.read()
                        outfile.write(content)
                        
                        # 不在最后一个文件后加分隔符
                        if i < len(input_files) - 1:
                            outfile.write(delimiter)
                    
                    print(f"✅ 已读取: {file_path}")
                
                except FileNotFoundError:
                    print(f"❌ 错误: 文件未找到 - {file_path}", file=sys.stderr)
                    sys.exit(1)
                except PermissionError:
                    print(f"❌ 错误: 没有权限读取文件 - {file_path}", file=sys.stderr)
                    sys.exit(1)
                except Exception as e:
                    print(f"❌ 错误: 读取文件 {file_path} 时发生未知错误 - {str(e)}", file=sys.stderr)
                    sys.exit(1)
        
        print(f"\n🎉 合并完成！输出文件: {output_file}")
    
    except PermissionError:
        print(f"❌ 错误: 没有权限写入输出文件 - {output_file}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ 错误: 写入输出文件时发生未知错误 - {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    # 设置命令行参数
    parser = argparse.ArgumentParser(
        description='按指定顺序合并多个文本文件到一个文件中',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('input_files', nargs='+', help='要合并的文件路径（按合并顺序排列）')
    parser.add_argument('-o', '--output', default='merged.txt', help='输出文件路径（默认: merged.txt）')
    parser.add_argument('-d', '--delimiter', default='\n\n', help='文件之间的分隔符（默认: 两个换行符）')
    
    args = parser.parse_args()
    
    # 执行合并
    merge_files(args.input_files, args.output, args.delimiter)