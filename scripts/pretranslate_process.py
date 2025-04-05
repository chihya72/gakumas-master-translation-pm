import os
import json
import shutil
import argparse

import import_db_json
import export_db_json


def values_to_keys():
    root_dir = input("export 文件夹: ") or "exports"
    output_dir = "./pretranslate_todo/full_out"

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for root, dirs, files in os.walk(root_dir):
        for name in files:
            if not name.endswith(".json"):
                continue

            data = {}
            with open(os.path.join(root, name), 'r', encoding='utf-8') as f:
                orig_data = json.load(f)

            for _, v in orig_data.items():
                data[v] = ""

            with open(os.path.join(output_dir, name), 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

            print("save file", name)


def pretranslated_to_kv_files(
        root_dir: str,
        translated_dir: str,
        save_dir="pretranslate_todo/translated_out"
):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    for root, dirs, files in os.walk(translated_dir):
        for name in files:
            if not name.endswith("_translated.json"):
                continue
            translated_file = os.path.join(root, name)
            orig_file = os.path.join(root_dir, name[:-16] + ".json")
            save_file = os.path.join(save_dir, name[:-16] + ".json")

            with open(translated_file, 'r', encoding='utf-8') as f:
                translated_data = json.load(f)  # 日文: 原文

            with open(orig_file, 'r', encoding='utf-8') as f:
                orig_data = json.load(f)  # key: 日文

            for k, orig_jp in orig_data.items():
                orig_data[k] = translated_data.get(orig_jp, orig_jp)

            with open(save_file, 'w', encoding='utf-8') as f:
                json.dump(orig_data, f, ensure_ascii=False, indent=4)

            print("合并文件", name)
    print("合并完成，接下来请执行 import_db_json 将翻译文件导回")


def gen_todo(new_files_dir: str):
    """
    生成未翻译过的 jp: "" 文件
    """
    old_files_dir = "./data"
    temp_key_cn_dir = "./pretranslate_todo/temp_key_cn"
    temp_key_jp_dir = "./pretranslate_todo/temp_key_jp"
    todo_out_dir = "./pretranslate_todo/todo"

    if not os.path.isdir(temp_key_cn_dir):
        os.makedirs(temp_key_cn_dir)
    if not os.path.isdir(temp_key_jp_dir):
        os.makedirs(temp_key_jp_dir)
    if not os.path.isdir(todo_out_dir):
        os.makedirs(todo_out_dir)

    # 旧已翻译插件 json 转 key: cn
    for root, dirs, files in os.walk(old_files_dir):
        for file in files:
            if file.endswith(".json"):
                input_path = os.path.join(root, file)
                output_path = os.path.join(temp_key_cn_dir, file)
                export_db_json.ex_main(input_path, output_path)

    # 新插件 json 转 key: jp
    for root, dirs, files in os.walk(new_files_dir):
        for file in files:
            if file.endswith(".json"):
                input_path = os.path.join(root, file)
                output_path = os.path.join(temp_key_jp_dir, file)
                export_db_json.ex_main(input_path, output_path)

    # 遍历新的 jp 文件
    for root, dirs, files in os.walk(temp_key_jp_dir):
        for file in files:
            jp_file = os.path.join(root, file)
            cn_file = os.path.join(temp_key_cn_dir, file)
            out_data = {}

            with open(jp_file, 'r', encoding='utf-8') as f:
                jp_data = json.load(f)

            if not os.path.exists(cn_file):
                for _, v in jp_data.items():
                    out_data[v] = ""
            else:
                with open(cn_file, 'r', encoding='utf-8') as f:
                    cn_data = json.load(f)
                for k, v in jp_data.items():
                    if k not in cn_data:
                        out_data[v] = ""

            if out_data:
                todo_file = os.path.join(todo_out_dir, file)
                with open(todo_file, 'w', encoding='utf-8') as f:
                    json.dump(out_data, f, ensure_ascii=False, indent=4)
                print("TODO File", todo_file)


def merge_todo():
    new_files_dir = "./pretranslate_todo/todo/new"  # 只有新的 jp: cn
    old_trans_dir = "./pretranslate_todo/temp_key_cn"  # 旧版 key: cn
    new_key_jp_dir = "./pretranslate_todo/temp_key_jp"  # 新版 key: jp
    output_dir = "./pretranslate_todo/merged"  # 新的 key: cn

    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    # 首先将新的 key: jp 复制到输出文件夹
    for root, dirs, files in os.walk(new_key_jp_dir):
        for file in files:
            if file.endswith(".json"):
                shutil.copyfile(os.path.join(root, file), os.path.join(output_dir, file))

    # 合并旧翻译
    for root, dirs, files in os.walk(old_trans_dir):
        for file in files:
            if file.endswith(".json"):
                old_key_cn_file = os.path.join(root, file)  # 旧版 key: cn
                new_key_jp_file = os.path.join(output_dir, file)  # 目前 output_dir 是新版 key: jp

                with open(old_key_cn_file, 'r', encoding='utf-8') as f:
                    old_key_cn_data: dict = json.load(f)
                if os.path.exists(new_key_jp_file):
                    with open(new_key_jp_file, 'r', encoding='utf-8') as f:
                        new_key_jp_data = json.load(f)
                else:
                    new_key_jp_data = {}

                for k, v in old_key_cn_data.items():
                    new_key_jp_data[k] = v

                with open(new_key_jp_file, 'w', encoding='utf-8') as f:
                    json.dump(new_key_jp_data, f, ensure_ascii=False, indent=4)

    pretranslated_to_kv_files(output_dir, new_files_dir, output_dir)

    if input("继续执行 import_db_json，请输入 1: ") == "1":
        import_db_json.main("./gakumasu-diff/json", output_dir, "data")
        print("文件已输出到 data")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--gen_todo', action='store_true')
    parser.add_argument('--merge', action='store_true')
    args = parser.parse_args()

    if (not args.gen_todo) and (not args.merge):
        do_idx = input("[1] 全部导出转为待翻译文件\n"
                       "[2] 对比更新病生成 todo 文件\n"
                       "[3] 翻译文件(jp: cn)转回 key-value json\n"
                       "[4] 将翻译后的 todo 文件合并回插件 json\n"
                       "请选择操作: ")
    elif args.gen_todo:
        gen_todo("gakumasu-diff/json")
        return
    elif args.merge:
        do_idx = "4"
    else:
        raise RuntimeError("Invalid Arguments.")

    if do_idx == "1":
        values_to_keys()

    elif do_idx == "2":
        gen_todo(input("新 gakumasu_diff_to_json 文件夹: ") or "gakumasu-diff/json")

    elif do_idx == "3":
        pretranslated_to_kv_files(
            root_dir=input("export 文件夹: ") or "exports",
            translated_dir=input("预翻译完成文件夹: ")
        )

    elif do_idx == "4":
        merge_todo()


if __name__ == '__main__':
    main()
