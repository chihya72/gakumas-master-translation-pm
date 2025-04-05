import os
import json
import shutil

def convert_files():
    # 定义源文件夹和目标文件夹
    jp_folder = 'temp_key_jp'
    cn_folder = 'temp_key_cn'
    output_folder = 'jp_cn'
    
    # 创建输出文件夹，如果已存在则先删除
    if os.path.exists(output_folder):
        shutil.rmtree(output_folder)
    os.makedirs(output_folder)
    
    # 获取日语文件夹中的所有JSON文件
    jp_files = [f for f in os.listdir(jp_folder) if f.endswith('.json')]
    
    # 处理每个文件
    for file_name in jp_files:
        # 检查中文文件夹中是否存在同名文件
        if not os.path.exists(os.path.join(cn_folder, file_name)):
            print(f"警告：未找到对应的中文文件 {file_name}，跳过")
            continue
        
        # 读取日语和中文文件
        with open(os.path.join(jp_folder, file_name), 'r', encoding='utf-8') as jp_file:
            jp_data = json.load(jp_file)
        
        with open(os.path.join(cn_folder, file_name), 'r', encoding='utf-8') as cn_file:
            cn_data = json.load(cn_file)
        
        # 创建新的映射：日语原文 -> 中文翻译
        new_data = {}
        for key in jp_data:
            if key in cn_data:
                new_data[jp_data[key]] = cn_data[key]
            else:
                print(f"警告：在 {file_name} 中未找到ID {key} 的中文翻译，跳过")
        
        # 保存新文件
        with open(os.path.join(output_folder, file_name), 'w', encoding='utf-8') as output_file:
            json.dump(new_data, output_file, ensure_ascii=False, indent=4)
        
        print(f"已处理文件: {file_name}")
    
    print(f"\n转换完成! 结果保存在 {output_folder} 文件夹中")

if __name__ == "__main__":
    convert_files()
