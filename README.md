# gakumas-master-translation


简体中文 | [English](README_EN.md)



# 使用脚本更新

 - `make update` 更新 MasterDB 的 `orig` 和 `json` 文件
 - `make gen-todo` 生成待翻译文件到 `pretranslate_todo/todo` 文件夹内
   - 需要手动将 `pretranslate_todo/todo` 内的文件复制到 `gakumas-generic-strings-translation/working/todo` 内，然后在 `gakumas-generic-strings-translation` 内运行 `make pretranslate`
   - 翻译完成后将 `gakumas-generic-strings-translation/working/new` 内的文件复制到 `pretranslate_todo/todo/new` 内。若 `new` 文件夹不存在，则手动创建
 - `make merge` 将 `pretranslate_todo/todo/new` 内的文件合并到 `data`
 - 全部处理完成后，请手动清空 `pretranslate_todo` 文件夹



# 手动运行

## 全新翻译流程

 - 首先执行 `gakumasu_diff_to_json.py` 将 gakumasu-diff 这个仓库的 yaml 转为插件能识别的 json，这时候 json 内容是日文原文
 - 然后执行 `export_db_json.py` 将第一步生成的 json 转为 `key: 日文原文` 形式
 - 运行 `pretranslate_process.py`，选 `1`，将 `key: 日文原文` 转为 `日文: ""` 用于 pretranslate
 - 然后自行 pretranslate，得到 `日文: 中文` 文件
 - 完成后再次运行 `pretranslate_process.py`，选 `3`，将 pretranslate 后的 `日文: 中文` 转为 `key: 中文` 文件
 - 最后运行 `import_db_json.py` 将 `key: 中文` 文件转为插件能识别的 json 文件

## 基于旧文件更新

1. 生成 todo 文件: 运行 `pretranslate_process.py` 选 2。旧的翻译数据在 `data` 内，新的文件使用 `gakumasu_diff_to_json` 生成
2. 预翻译完成后，将新文件放入 `todo/new` 内，运行 `pretranslate_process.py` 选 4

# pm修改部分

## localization.json翻译

在localization路径下执行`localization.py`。选 1：将 `localization.json` 和 `localization_orig.json` 进行合并，生成 `localization_dual.json`。选 2：将 `localization_dual.json` 中的中文提取出来生成 `localization_cn.json`，可以直接改名为 `localization.json` 进行使用。
