import json
import os
import re

# 定义文件路径
input_file_path = r"D:\GIT\gakumas-master-translation-pm\pretranslate_todo\todo\ProduceExamEffect.json"
output_dir = os.path.dirname(input_file_path)
output_file_path = os.path.join(output_dir, "ProduceExamEffect_number.json")

# 读取JSON文件
with open(input_file_path, 'r', encoding='utf-8') as file:
    data = json.load(file)

# 处理JSON数据
for key in data:
    # 检查键是否为纯数字或带符号的数字
    if key.isdigit() or re.match(r'^[+-]?\d+\.?\d*$', key):
        # 将符合条件的键复制到对应的值
        data[key] = key

# 将处理后的数据写入新文件
with open(output_file_path, 'w', encoding='utf-8') as file:
    json.dump(data, file, ensure_ascii=False, indent=4)

print(f"处理完成，新文件已保存为: {output_file_path}")
