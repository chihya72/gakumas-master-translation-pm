import json
import re
from pathlib import Path
from collections import defaultdict


INPUT_JSON = "ProduceItem.json"          # 改成你的原始 json 文件名
OUTPUT_DIR = "filtered_by_first"   # 输出目录
TARGET_VALUE = "会"                # 要筛选的值


def safe_filename(name: str) -> str:
    """
    防止 Windows 文件名非法字符。
    你的 key 目前基本是安全的，但保留这个函数更稳。
    """
    return re.sub(r'[\\/:*?"<>|]', "_", name)


def main():
    input_path = Path(INPUT_JSON)
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise TypeError("输入 JSON 顶层必须是对象，也就是 { key: value } 结构")

    grouped = defaultdict(dict)

    for key, value in data.items():
        if value != TARGET_VALUE:
            continue

        # 取第一个字段：第一个 | 前面的内容
        first_field = key.split("|", 1)[0]

        # 把完整的原始键值对放进对应分组
        grouped[first_field][key] = value

    for first_field, items in grouped.items():
        filename = safe_filename(first_field) + ".json"
        output_path = output_dir / filename

        with output_path.open("w", encoding="utf-8", newline="\n") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)

        print(f"已输出：{output_path}，共 {len(items)} 条")

    print(f"\n完成，共生成 {len(grouped)} 个 json 文件。")


if __name__ == "__main__":
    main()