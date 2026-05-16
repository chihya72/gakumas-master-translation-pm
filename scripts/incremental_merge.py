#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import shutil
import sys
import csv
from datetime import datetime

# 添加 scripts 目录到路径，以便导入其他模块
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))

import import_db_json
import export_db_json


def get_todo_new_files():
    """获取 todo/new 中的文件列表"""
    new_files_dir = "./pretranslate_todo/todo/new"
    todo_files = []
    
    if os.path.exists(new_files_dir):
        for root, dirs, files in os.walk(new_files_dir):
            for file in files:
                if file.endswith("_translated.json"):
                    json_name = file[:-16] + ".json"
                    todo_files.append(json_name)
    
    return todo_files


def pretranslated_to_kv_files_single(root_dir: str, translated_file: str, json_filename: str):
    """将单个翻译文件转换为 key-value 格式"""
    temp_output = {}
    
    with open(translated_file, 'r', encoding='utf-8') as f:
        translated_data = json.load(f)  # 日文: 中文

    orig_file = os.path.join(root_dir, json_filename)
    if os.path.exists(orig_file):
        with open(orig_file, 'r', encoding='utf-8') as f:
            orig_data = json.load(f)  # key: 日文

        for k, orig_jp in orig_data.items():
            temp_output[k] = translated_data.get(orig_jp, orig_jp)
    
    return temp_output


def load_special_mappings(json_filename):
    """加载special_mapping目录中的特殊映射"""
    special_mapping_dir = "./special_mapping"
    file_base_name = json_filename[:-5]  # 移除.json扩展名
    
    special_mappings = {}
    special_keys = set()  # 用于快速检查是否为特例键
    
    # 查找对应的special_mapping子目录
    category_dir = os.path.join(special_mapping_dir, file_base_name)
    if os.path.exists(category_dir):
        for special_file in os.listdir(category_dir):
            if special_file.endswith('.json'):
                special_file_path = os.path.join(category_dir, special_file)
                try:
                    with open(special_file_path, 'r', encoding='utf-8') as f:
                        special_data = json.load(f)
                        special_mappings.update(special_data)
                        # 记录特例键前缀（如pitem_01-2-096-0）
                        special_prefix = special_file[:-5]  # 移除.json
                        special_keys.add(special_prefix)
                        print(f"    📋 加载特殊映射: {special_file} ({len(special_data)} 条)")
                except Exception as e:
                    print(f"    ⚠️  加载特殊映射失败 {special_file}: {e}")
    
    return special_mappings, special_keys


def extract_complete_item_from_source(json_filename, item_id, source_dir="./gakumasu-diff/json"):
    """从源文件中提取完整的条目信息"""
    source_file = os.path.join(source_dir, json_filename)
    if not os.path.exists(source_file):
        print(f"    ⚠️  找不到源文件: {source_file}")
        return {}
    
    try:
        with open(source_file, 'r', encoding='utf-8') as f:
            source_data = json.load(f)
        
        # 提取该item_id的所有相关键值对
        item_mappings = {}
        for key, value in source_data.items():
            if key.startswith(item_id + "|"):
                item_mappings[key] = value
        
        return item_mappings
    except Exception as e:
        print(f"    ⚠️  读取源文件失败 {source_file}: {e}")
        return {}


def save_smart_resolved_exceptions(json_filename, smart_exceptions):
    """
    保存智能解决的特例到special_mapping
    
    TODO: 当gakumasu-diff有更新时，需要完善以下逻辑：
    1. 从gakumasu-diff/json中提取完整的新增条目
    2. 对比data和diff，确定哪些是真正的新增内容
    3. 为每个条目创建完整的special mapping文件
    
    当前版本：仅基于冲突键创建映射，待真实数据验证后完善
    """
    if not smart_exceptions:
        return
        
    special_mapping_dir = "./special_mapping"
    file_base_name = json_filename[:-5]  # 移除.json扩展名
    category_dir = os.path.join(special_mapping_dir, file_base_name)
    
    # 按条目ID分组
    exceptions_by_item = {}
    for exception in smart_exceptions:
        key = exception["key"]
        # 提取条目ID（例如从pitem_tower_001-exam_review-1-stage_022-1|...中提取pitem_tower_001-exam_review-1-stage_022-1）
        item_id = key.split("|")[0]
        if item_id not in exceptions_by_item:
            exceptions_by_item[item_id] = []
        exceptions_by_item[item_id].append(exception)
    
    # 为每个条目创建完整的special mapping
    for item_id, exceptions in exceptions_by_item.items():
        print(f"    🔍 处理特例条目: {item_id}")
        
        # 从gakumasu-diff中提取完整的条目
        complete_mappings = extract_complete_item_from_source(json_filename, item_id)
        
        if not complete_mappings:
            print(f"    ⚠️  无法找到条目 {item_id} 的完整信息")
            continue
        
        # 应用todo/new的特例翻译到完整映射中
        for exception in exceptions:
            key = exception["key"]
            if key in complete_mappings:
                complete_mappings[key] = exception["todo_new_translation"]
        
        # 创建目录
        if not os.path.exists(category_dir):
            os.makedirs(category_dir)
            
        # 保存special mapping文件
        special_file = os.path.join(category_dir, f"{item_id}.json")
        with open(special_file, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(complete_mappings, f, ensure_ascii=False, indent=2)
        
        print(f"    💾 已创建特例映射: {item_id}.json ({len(complete_mappings)} 条完整映射)")


def is_special_key(key, special_keys):
    """检查键是否属于特殊映射"""
    for special_prefix in special_keys:
        if key.startswith(special_prefix + "|"):
            return True
    return False


def incremental_merge():
    """
    增量合并流程：
    1. 只处理 todo/new 中存在的文件
    2. 对这些文件进行优先级合并：todo/new > jp_cn > temp_key_cn(data)
    3. 生成冲突报告CSV
    4. 只更新对应的 data 文件
    """
    new_files_dir = "./pretranslate_todo/todo/new"
    old_trans_dir = "./pretranslate_todo/temp_key_cn"
    new_key_jp_dir = "./pretranslate_todo/temp_key_jp"
    jp_cn_dir = "./pretranslate_todo/jp_cn"
    output_dir = "./pretranslate_todo/merged"
    conflicts_dir = "./pretranslate_todo/conflicts"
    data_dir = "./data"
    gakumasu_json_dir = "./gakumasu-diff/json"

    # 创建必要的目录
    for dir_path in [output_dir, conflicts_dir]:
        if not os.path.isdir(dir_path):
            os.makedirs(dir_path)

    print("🔄 开始增量合并流程...")
    
    # 1. 获取需要处理的文件列表
    todo_files = get_todo_new_files()
    if not todo_files:
        print("❌ todo/new 目录中没有找到翻译文件，无需合并")
        return
    
    print(f"📋 发现需要处理的文件 ({len(todo_files)} 个):")
    for file in todo_files:
        print(f"  - {file}")
    
    print(f"\n📋 翻译优先级：special_mapping > todo/new > jp_cn > temp_key_cn(data)")
    
    # 2. 处理每个文件
    all_conflicts = {}
    processed_files = []
    
    for json_filename in todo_files:
        print(f"\n📝 处理文件: {json_filename}")
        
        # 文件路径
        todo_translated_file = os.path.join(new_files_dir, json_filename[:-5] + "_translated.json")
        old_key_cn_file = os.path.join(old_trans_dir, json_filename)
        new_key_jp_file = os.path.join(new_key_jp_dir, json_filename)
        jp_cn_file = os.path.join(jp_cn_dir, json_filename)
        output_file = os.path.join(output_dir, json_filename)
        
        # 检查必要文件是否存在
        if not os.path.exists(todo_translated_file):
            print(f"  ⚠️  跳过 {json_filename}：找不到对应的翻译文件")
            continue
        
        if not os.path.exists(new_key_jp_file):
            print(f"  ⚠️  跳过 {json_filename}：找不到对应的 key-jp 映射文件")
            continue
        
        # 加载 todo/new 翻译（转换为 key-value 格式）
        print(f"  📥 加载 todo/new 翻译...")
        todo_new_kv = pretranslated_to_kv_files_single(new_key_jp_dir, todo_translated_file, json_filename)
        print(f"    ✅ 加载了 {len(todo_new_kv)} 条翻译")
        
        # 加载special_mapping（新增）
        print(f"  📥 加载特殊映射...")
        special_mappings, special_keys = load_special_mappings(json_filename)
        if special_mappings:
            print(f"    ✅ 加载了 {len(special_mappings)} 条特殊映射")
        else:
            print(f"    ℹ️  未找到特殊映射")
        
        # 加载其他数据源
        with open(new_key_jp_file, 'r', encoding='utf-8') as f:
            new_key_jp_data = json.load(f)  # key: jp 映射
        
        # 加载旧翻译 (来自data)
        old_key_cn_data = {}
        if os.path.exists(old_key_cn_file):
            with open(old_key_cn_file, 'r', encoding='utf-8') as f:
                old_key_cn_data = json.load(f)
        
        # 加载 jp_cn 翻译映射
        jp_cn_data = {}
        if os.path.exists(jp_cn_file):
            with open(jp_cn_file, 'r', encoding='utf-8') as f:
                jp_cn_data = json.load(f)
        
        # 合并翻译并记录冲突
        final_key_cn_data = {}
        conflicts = []
        smart_exceptions = []  # 收集智能解决的特例
        
        todo_new_count = 0
        jp_cn_count = 0
        old_count = 0
        untranslated_count = 0
        conflict_count = 0
        special_count = 0  # 新增：特殊映射计数
        
        for key, jp_value in new_key_jp_data.items():
            used_translation = None
            source = None
            
            # 首先检查是否为特殊映射键（最高优先级）
            if is_special_key(key, special_keys) and key in special_mappings:
                used_translation = special_mappings[key]
                source = "special_mapping"
                special_count += 1
                final_key_cn_data[key] = used_translation
                # 特殊映射不参与冲突检测
                continue
            
            # 检查所有可用的翻译来源
            available_translations = {}
            
            # todo/new 翻译
            if key in todo_new_kv and todo_new_kv[key] != jp_value:  # 确保不是未翻译的日文
                available_translations["todo/new"] = todo_new_kv[key]
            
            # jp_cn 翻译
            if jp_value in jp_cn_data:
                available_translations["jp_cn"] = jp_cn_data[jp_value]
            
            # data 翻译
            if key in old_key_cn_data and old_key_cn_data[key] != jp_value:  # 确保不是未翻译的日文
                available_translations["data"] = old_key_cn_data[key]
            
            # 智能冲突解决：如果jp_cn和data翻译一致，而todo/new不同，则优先使用jp_cn/data
            # 这种情况说明jp_cn/data是通用翻译，而todo/new可能是特例
            smart_resolution = False
            if (len(available_translations) >= 2 and 
                "jp_cn" in available_translations and 
                "data" in available_translations and
                "todo/new" in available_translations):
                
                jp_cn_trans = available_translations["jp_cn"]
                data_trans = available_translations["data"]
                todo_new_trans = available_translations["todo/new"]
                
                if jp_cn_trans == data_trans and jp_cn_trans != todo_new_trans:
                    # jp_cn和data一致，todo/new不同：使用jp_cn/data的翻译
                    used_translation = jp_cn_trans
                    source = "jp_cn(智能解决)"
                    jp_cn_count += 1
                    smart_resolution = True
                    
                    # 收集特例信息
                    smart_exceptions.append({
                        "key": key,
                        "jp_value": jp_value,
                        "todo_new_translation": todo_new_trans,
                        "used_translation": jp_cn_trans
                    })
                    
                    print(f"    🧠 智能解决冲突: {key[:50]}... 使用通用翻译 '{jp_cn_trans}' 而非特例 '{todo_new_trans}'")
            
            # 如果没有智能解决，按原有优先级选择翻译
            if not smart_resolution:
                if "todo/new" in available_translations:
                    used_translation = available_translations["todo/new"]
                    source = "todo/new"
                    todo_new_count += 1
                elif "jp_cn" in available_translations:
                    used_translation = available_translations["jp_cn"]
                    source = "jp_cn"
                    jp_cn_count += 1
                elif "data" in available_translations:
                    used_translation = available_translations["data"]
                    source = "data"
                    old_count += 1
                else:
                    used_translation = jp_value
                    source = "原文"
                    untranslated_count += 1
            
            final_key_cn_data[key] = used_translation
            
            # 记录冲突（多个来源有不同翻译）
            if len(available_translations) > 1:
                unique_translations = set(available_translations.values())
                if len(unique_translations) > 1:  # 确实有不同的翻译
                    conflict_record = {
                        "键名": key,
                        "日文原文": jp_value,
                        "当前使用": used_translation,
                        "使用来源": source
                    }
                    
                    for src, trans in available_translations.items():
                        conflict_record[f"{src}_翻译"] = trans
                    
                    conflicts.append(conflict_record)
                    conflict_count += 1
        
        # 保存合并后的文件
        with open(output_file, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(final_key_cn_data, f, ensure_ascii=False, indent=4)
        
        print(f"    📊 翻译统计: special={special_count}, todo/new={todo_new_count}, jp_cn={jp_cn_count}, data={old_count}, 未翻译={untranslated_count}")
        if conflict_count > 0:
            print(f"    ⚠️  发现冲突: {conflict_count} 个")
        
        # 保存智能解决的特例
        if smart_exceptions:
            print(f"    🧠 智能解决了 {len(smart_exceptions)} 个特例")
            save_smart_resolved_exceptions(json_filename, smart_exceptions)
        
        # 记录冲突和处理的文件
        if conflicts:
            all_conflicts[json_filename] = conflicts
        
        processed_files.append(json_filename)
        print(f"    ✅ 文件处理完成: {json_filename}")
    
    # 3. 生成冲突报告CSV
    if all_conflicts:
        print(f"\n📋 生成冲突报告...")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        conflicts_csv = os.path.join(conflicts_dir, f"incremental_conflicts_{timestamp}.csv")
        
        with open(conflicts_csv, 'w', encoding='utf-8-sig', newline='\n') as csvfile:
            fieldnames = ["文件名", "键名", "日文原文", "当前使用", "使用来源", "todo/new_翻译", "jp_cn_翻译", "data_翻译"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            total_conflicts = 0
            for file_name, conflicts in all_conflicts.items():
                for conflict in conflicts:
                    row = {
                        "文件名": file_name,
                        "键名": conflict.get("键名", ""),
                        "日文原文": conflict.get("日文原文", ""),
                        "当前使用": conflict.get("当前使用", ""),
                        "使用来源": conflict.get("使用来源", ""),
                        "todo/new_翻译": conflict.get("todo/new_翻译", ""),
                        "jp_cn_翻译": conflict.get("jp_cn_翻译", ""),
                        "data_翻译": conflict.get("data_翻译", "")
                    }
                    writer.writerow(row)
                    total_conflicts += 1
        
        print(f"  ✅ 冲突报告已生成: {conflicts_csv}")
        print(f"  📊 共发现 {total_conflicts} 个翻译冲突")
        print(f"  💡 请审核 CSV 文件中的冲突，并决定使用哪个翻译版本")
    else:
        print(f"\n🎉 未发现翻译冲突！")
    
    if not processed_files:
        print("\n❌ 没有文件被处理，合并操作结束")
        return
    
    print(f"\n✅ 增量合并完成！")
    print(f"📁 处理的文件: {len(processed_files)} 个")
    print(f"📁 合并结果保存在: {output_dir}")
    
    # 4. 询问是否继续执行增量导入
    user_input = input("\n🚀 是否继续执行增量导入，将翻译更新到 data 文件夹？(y/N): ").lower().strip()
    if user_input in ['y', 'yes']:
        print("📤 开始增量导入翻译到 data 文件夹...")
        
        # 只导入处理过的文件
        for json_filename in processed_files:
            base_file = os.path.join(gakumasu_json_dir, json_filename)
            translated_file = os.path.join(output_dir, json_filename)
            output_file = os.path.join(data_dir, json_filename)
            
            if os.path.exists(base_file) and os.path.exists(translated_file):
                import_db_json.import_main(base_file, translated_file, output_file)
                print(f"  ✅ 更新: {json_filename}")
            else:
                print(f"  ⚠️  跳过 {json_filename}：缺少必要文件")
        
        print("✅ 增量导入完成！")
    else:
        print("⏸️  跳过导入步骤")
        print(f"💡 如需手动导入特定文件，请运行：")
        print(f"   python scripts/import_db_json.py")
    
    # 5. 显示摘要
    print(f"\n📋 操作摘要:")
    print(f"   - 处理文件数: {len(processed_files)}")
    print(f"   - 冲突文件数: {len(all_conflicts)}")
    print(f"   - 处理的文件: {', '.join(processed_files[:5])}" + ("..." if len(processed_files) > 5 else ""))


if __name__ == '__main__':
    incremental_merge()
