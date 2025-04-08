import json

def merge_localization_files():
    """合并日文和中文翻译文件"""
    try:
        # 读取原始文件
        with open('localization_orig.json', 'r', encoding='utf-8') as f:
            japanese_data = json.load(f)
        
        with open('localization.json', 'r', encoding='utf-8') as f:
            chinese_data = json.load(f)
        
        # 创建新的合并字典
        merged_data = {}
        
        # 获取所有唯一的键
        all_keys = set(japanese_data.keys()) | set(chinese_data.keys())
        
        # 为每个键创建新的结构
        for key in all_keys:
            merged_data[key] = {
                "japanese": japanese_data.get(key, ""),
                "chinese": chinese_data.get(key, "")
            }
        
        # 写入新文件
        with open('localization_dual.json', 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, ensure_ascii=False, indent=2)
        
        print("成功创建 localization_dual.json 文件")
    except Exception as e:
        print(f"合并文件时出错: {str(e)}")

def extract_chinese_translations():
    """从合并文件中提取中文翻译"""
    try:
        # 读取合并后的文件
        with open('localization_dual.json', 'r', encoding='utf-8') as f:
            dual_data = json.load(f)
        
        # 创建只包含中文翻译的字典
        chinese_data = {}
        
        # 提取每个键的中文翻译
        for key, translations in dual_data.items():
            chinese_data[key] = translations["chinese"]
        
        # 写入新文件
        with open('localization_cn.json', 'w', encoding='utf-8') as f:
            json.dump(chinese_data, f, ensure_ascii=False, indent=2)
        
        print("成功创建 localization_cn.json 文件")
    except Exception as e:
        print(f"提取中文翻译时出错: {str(e)}")

def main():
    while True:
        print("\n=== 本地化文件处理工具 ===")
        do_idx = input("[1] 合并日文和中文翻译文件\n"
                      "[2] 从合并文件中提取中文翻译\n"
                      "[3] 退出\n"
                      "请选择操作: ")
        
        if do_idx == "1":
            merge_localization_files()
        elif do_idx == "2":
            extract_chinese_translations()
        elif do_idx == "3":
            print("程序已退出")
            break
        else:
            print("无效的选择，请重新输入")

if __name__ == "__main__":
    main()
