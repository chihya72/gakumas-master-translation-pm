#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按照参考JSON文件的键顺序排列脚本
根据参考JSON文件中的键顺序，对目标JSON文件进行重新排列
"""

import json
import argparse
import os
from collections import OrderedDict


def get_key_order_from_reference(reference_file):
    """
    从参考文件中获取键的顺序
    
    Args:
        reference_file: 参考JSON文件路径
    
    Returns:
        键的顺序列表
    """
    try:
        with open(reference_file, 'r', encoding='utf-8') as f:
            reference_data = json.load(f)
        
        if isinstance(reference_data, dict):
            return list(reference_data.keys())
        else:
            raise ValueError("参考文件必须是一个JSON对象（字典）")
    
    except Exception as e:
        raise Exception(f"读取参考文件失败: {e}")


def sort_by_reference_order(data, key_order):
    """
    按照参考顺序对数据进行排序
    
    Args:
        data: 要排序的JSON数据
        key_order: 参考的键顺序列表
    
    Returns:
        按参考顺序排列的数据
    """
    if isinstance(data, dict):
        # 创建键的优先级映射
        key_priority = {key: i for i, key in enumerate(key_order)}
        
        # 分离存在于参考顺序中的键和不存在的键
        existing_keys = []
        new_keys = []
        
        for key in data.keys():
            if key in key_priority:
                existing_keys.append(key)
            else:
                new_keys.append(key)
        
        # 对存在的键按参考顺序排序
        existing_keys.sort(key=lambda x: key_priority[x])
        
        # 对新键按字母顺序排序
        new_keys.sort()
        
        # 合并键列表
        sorted_keys = existing_keys + new_keys
        
        # 创建排序后的字典
        sorted_dict = OrderedDict()
        for key in sorted_keys:
            sorted_dict[key] = sort_by_reference_order(data[key], key_order)
        
        return sorted_dict
    
    elif isinstance(data, list):
        # 对列表中的每个元素递归处理
        return [sort_by_reference_order(item, key_order) for item in data]
    
    else:
        # 其他类型直接返回
        return data


def sort_json_by_reference(input_file, reference_file, output_file=None, indent=4):
    """
    按照参考文件的键顺序对JSON文件进行排序
    
    Args:
        input_file: 输入JSON文件路径
        reference_file: 参考JSON文件路径
        output_file: 输出文件路径（如果为None，则覆盖输入文件）
        indent: JSON格式化缩进
    """
    try:
        # 获取参考键顺序
        print(f"正在读取参考文件: {reference_file}")
        key_order = get_key_order_from_reference(reference_file)
        print(f"参考文件包含 {len(key_order)} 个键")
        
        # 读取要排序的JSON文件
        print(f"正在读取目标文件: {input_file}")
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 按参考顺序排序
        print("正在按参考顺序排列键...")
        sorted_data = sort_by_reference_order(data, key_order)
        
        # 确定输出文件路径
        if output_file is None:
            output_file = input_file
        
        # 写入排序后的数据
        print(f"正在写入文件: {output_file}")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(sorted_data, f, ensure_ascii=False, indent=indent, separators=(',', ': '))
        
        print(f"排序完成！文件已保存到: {output_file}")
        
        # 统计信息
        if isinstance(sorted_data, dict):
            total_keys = len(sorted_data)
            matched_keys = sum(1 for key in sorted_data.keys() if key in key_order)
            new_keys = total_keys - matched_keys
            
            print(f"统计信息:")
            print(f"  总键数: {total_keys}")
            print(f"  匹配参考顺序的键: {matched_keys}")
            print(f"  新键（按字母排序）: {new_keys}")
        
    except FileNotFoundError as e:
        print(f"错误：找不到文件 - {e}")
    except json.JSONDecodeError as e:
        print(f"错误：JSON格式无效 - {e}")
    except Exception as e:
        print(f"错误：{e}")


def main():
    parser = argparse.ArgumentParser(description='按照参考JSON文件的键顺序对目标文件进行排序')
    parser.add_argument('input_file', help='要排序的JSON文件路径')
    parser.add_argument('reference_file', help='参考JSON文件路径（提供键的顺序）')
    parser.add_argument('-o', '--output', help='输出文件路径（可选，默认覆盖输入文件）')
    parser.add_argument('-i', '--indent', type=int, default=4, help='JSON缩进空格数（默认4）')
    parser.add_argument('--backup', action='store_true', help='创建原文件的备份')
    
    args = parser.parse_args()
    
    # 检查文件是否存在
    if not os.path.exists(args.input_file):
        print(f"错误：输入文件 {args.input_file} 不存在")
        return
    
    if not os.path.exists(args.reference_file):
        print(f"错误：参考文件 {args.reference_file} 不存在")
        return
    
    # 创建备份（如果需要）
    if args.backup and args.output is None:
        backup_file = args.input_file + '.backup'
        print(f"正在创建备份: {backup_file}")
        with open(args.input_file, 'r', encoding='utf-8') as src:
            with open(backup_file, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
    
    # 执行排序
    sort_json_by_reference(args.input_file, args.reference_file, args.output, args.indent)


if __name__ == '__main__':
    main()