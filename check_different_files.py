#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import yaml
import json
from pathlib import Path

def has_japanese_text(text):
    """检查文本是否包含日语字符"""
    # 日语字符范围：平假名、片假名、汉字
    japanese_pattern = re.compile(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]')
    return bool(japanese_pattern.search(text))

def check_file_for_japanese(file_path):
    """检查文件是否包含日语内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            return has_japanese_text(content)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False

def main():
    orig_dir = Path(r"d:\GIT\gakumas-master-translation-pm\gakumasu-diff\orig")
    json_dir = Path(r"d:\GIT\gakumas-master-translation-pm\gakumasu-diff\json")
    
    # 获取orig文件夹中的所有yaml文件（去除扩展名）
    orig_files = set()
    for file in orig_dir.glob("*.yaml"):
        orig_files.add(file.stem)  # 文件名不包含扩展名
    
    # 获取json文件夹中的所有json文件（去除扩展名）
    json_files = set()
    for file in json_dir.glob("*.json"):
        json_files.add(file.stem)  # 文件名不包含扩展名
    
    # 找出orig中有但json中没有的文件
    different_files = orig_files - json_files
    
    print(f"Found {len(different_files)} files in orig folder that don't exist in json folder:")
    print("=" * 60)
    
    japanese_files = []
    
    for filename in sorted(different_files):
        yaml_file = orig_dir / f"{filename}.yaml"
        if yaml_file.exists():
            has_japanese = check_file_for_japanese(yaml_file)
            status = "含有日语" if has_japanese else "不含日语"
            print(f"{filename}.yaml - {status}")
            
            if has_japanese:
                japanese_files.append(filename)
    
    print("\n" + "=" * 60)
    print(f"Summary: {len(japanese_files)} files contain Japanese text:")
    for filename in japanese_files:
        print(f"  - {filename}.yaml")

if __name__ == "__main__":
    main()