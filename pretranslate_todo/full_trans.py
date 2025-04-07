import os
import json

def fill_translations():
    # 1. 读取主文件
    try:
        with open('ProduceExamEffect.json', 'r', encoding='utf-8') as file:
            main_data = json.load(file)
    except FileNotFoundError:
        print("错误：未找到 ProduceExamEffect.json 文件")
        return
    except json.JSONDecodeError:
        print("错误：ProduceExamEffect.json 文件格式不正确")
        return

    # 获取需要填充翻译的键（值为空的键）
    empty_keys = {k for k, v in main_data.items() if v == ""}
    if not empty_keys:
        print("主文件中没有需要填充的空值")
        return

    print(f"找到 {len(empty_keys)} 个需要填充翻译的键")

    # 2. 遍历 jp_cn 目录下的所有 JSON 文件
    translations_found = 0
    jp_cn_dir = os.path.join(os.path.dirname('ProduceExamEffect.json'), 'jp_cn')
    
    if not os.path.exists(jp_cn_dir):
        print(f"错误：未找到 jp_cn 目录，请确保它与 ProduceExamEffect.json 在同一目录下")
        return

    for filename in os.listdir(jp_cn_dir):
        if not filename.endswith('.json'):
            continue
            
        file_path = os.path.join(jp_cn_dir, filename)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                translation_data = json.load(file)
        except (json.JSONDecodeError, UnicodeDecodeError):
            print(f"警告：跳过文件 {filename}，无法解析")
            continue

        # 3. 查找匹配的键并填充翻译
        for key in list(empty_keys):  # 使用list创建副本以便在迭代时修改
            if key in translation_data and translation_data[key]:
                main_data[key] = translation_data[key]
                empty_keys.remove(key)
                translations_found += 1
                print(f"找到翻译：{key} -> {translation_data[key]}")
                
        # 如果所有空键都已填充，可以提前退出
        if not empty_keys:
            break

    # 4. 保存更新后的主文件
    with open('ProduceExamEffect.json', 'w', encoding='utf-8') as file:
        json.dump(main_data, file, ensure_ascii=False, indent=2)
    
    print(f"完成！已填充 {translations_found} 个翻译")
    if empty_keys:
        print(f"警告：还有 {len(empty_keys)} 个键未找到翻译")

if __name__ == "__main__":
    fill_translations()
