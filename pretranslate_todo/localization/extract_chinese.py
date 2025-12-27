#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从translated_dual1.json中提取中文翻译，生成仅包含中文的localization1.json文件
"""

import json
import os


def extract_chinese_from_dual(input_file, output_file):
    """
    从双语JSON文件中提取中文翻译
    
    Args:
        input_file (str): 输入的双语JSON文件路径
        output_file (str): 输出的纯中文JSON文件路径
    """
    try:
        # 读取输入文件
        with open(input_file, 'r', encoding='utf-8') as f:
            dual_data = json.load(f)
        
        # 提取中文翻译
        chinese_data = {}
        processed_count = 0
        skipped_count = 0
        
        for key, value in dual_data.items():
            if isinstance(value, dict) and 'chinese' in value:
                chinese_data[key] = value['chinese']
                processed_count += 1
            else:
                print(f"警告: 跳过无效条目 '{key}': {value}")
                skipped_count += 1
        
        # 写入输出文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(chinese_data, f, ensure_ascii=False, indent=4)
        
        print(f"处理完成!")
        print(f"- 成功处理: {processed_count} 条翻译")
        print(f"- 跳过条目: {skipped_count} 条")
        print(f"- 输出文件: {output_file}")
        
        return True
        
    except FileNotFoundError:
        print(f"错误: 找不到输入文件 '{input_file}'")
        return False
    except json.JSONDecodeError as e:
        print(f"错误: JSON解析失败 - {e}")
        return False
    except Exception as e:
        print(f"错误: {e}")
        return False


def main():
    """主函数"""
    # 设置文件路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(script_dir, 'translated_dual.json')
    output_file = os.path.join(script_dir, 'localization1.json')
    
    print("=== 中文翻译提取工具 ===")
    print(f"输入文件: {input_file}")
    print(f"输出文件: {output_file}")
    print("-" * 50)
    
    # 检查输入文件是否存在
    if not os.path.exists(input_file):
        print(f"错误: 输入文件不存在 - {input_file}")
        return
    
    # 如果输出文件已存在，询问是否覆盖
    if os.path.exists(output_file):
        response = input(f"输出文件 '{output_file}' 已存在，是否覆盖? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("操作已取消")
            return
    
    # 执行替换
    success = extract_chinese_from_dual(input_file, output_file)
    
    if success:
        print("-" * 50)
        print("替换成功完成!")
    else:
        print("-" * 50)
        print("替换失败!")


if __name__ == "__main__":
    main()