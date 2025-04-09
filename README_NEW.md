

# Gakumasu 翻译工具集

这个工具集用于处理 Gakumasu 游戏的本地化翻译工作，提供了一套完整的流程从原始游戏数据提取待翻译文本，管理翻译过程，并将翻译内容合并回游戏数据结构。

## 功能概述

- 从原始 YAML 文件生成结构化 JSON 文件
- 对比新旧版本，生成待翻译内容
- 导出/导入翻译数据，支持增量翻译
- 合并翻译内容回原始文件结构
- 自动化工作流程，简化翻译管理

## 目录结构

```
.
├── gakumasu-diff/       # 原始和处理后的游戏数据
│   ├── orig/            # 从 git 拉取的原始 YAML 文件
│   └── json/            # 转换后的 JSON 文件
├── data/                # 完成翻译的插件 JSON 文件(最终结果)
├── exports/             # 导出的待翻译文件（key:value格式）
├── pretranslate_todo/   # 翻译处理临时文件
│   ├── todo/            # 待翻译的文件（日文:空白）
│   │   └── new/         # 新翻译内容（日文:中文）
│   ├── full_out/        # 导出的所有内容（用于全量翻译）
│   ├── translated_out/  # 翻译后的输出
│   ├── temp_key_cn/     # 临时键值对(key:中文)
│   ├── temp_key_jp/     # 临时键值对(key:日文)
│   └── merged/          # 合并后的翻译文件
├── scripts/             # 脚本文件
│   ├── gakumasu_diff_to_json.py  # YAML到JSON转换
│   ├── pretranslate_process.py   # 翻译流程处理
│   ├── import_db_json.py         # 导入JSON到插件格式
│   └── export_db_json.py         # 导出插件格式到JSON
└── Makefile             # 简化命令
```

## 安装与准备

1. 确保已安装Python 3.6+
2. 安装所需依赖:
   ```bash
   pip install pyyaml
   ```
3. 克隆或下载项目代码
4. 创建必要的目录结构:
   ```bash
   mkdir -p gakumasu-diff/orig gakumasu-diff/json data exports pretranslate_todo/{todo/new,full_out,translated_out,temp_key_cn,temp_key_jp,merged}
   ```

## 完整翻译流程

### 1. 获取原始数据

首先获取游戏的原始数据并转换为JSON格式:

```bash
make update
```

这一步会:
- 从git仓库更新`gakumasu-diff/orig`目录中的YAML文件
- 运行`gakumasu_diff_to_json.py`将YAML文件转换为结构化JSON
- 输出结果到`gakumasu-diff/json`目录

**注意:** 确保`gakumasu-diff/orig`已正确设置为git仓库，能够访问到原始YAML文件。

### 2. 生成待翻译文件

有两种生成待翻译文件的方式:

#### 方式A: 增量更新(推荐日常使用)

生成只包含新增内容的待翻译文件:

```bash
make gen-todo
```

或直接运行脚本:

```bash
python scripts/pretranslate_process.py --gen_todo
```

这一步会:
- 读取`data`目录中现有的翻译
- 分析`gakumasu-diff/json`中的新内容
- 输出只包含新增或修改内容的待翻译文件到`pretranslate_todo/todo`
- 格式为`{"日文": ""}`(等待填入翻译)

#### 方式B: 全量导出(首次翻译)

导出所有需要翻译的内容:

```bash
python scripts/pretranslate_process.py
# 选择选项1: 全部导出转为待翻译文件
```

这会将所有文本提取为待翻译格式，输出到`pretranslate_todo/full_out`目录。

### 3. 导出现有结构为Key-Value格式(可选)

如果需要查看或编辑现有翻译:

```bash
python scripts/export_db_json.py
```

这会将`gakumasu-diff/json`目录中的文件导出为key-value格式到`exports`目录。

### 4. 翻译文件

手动翻译步骤:

1. 打开`pretranslate_todo/todo`目录中的JSON文件
2. 为每个日文文本添加对应的翻译，将格式从`{"日文": ""}`改为`{"日文": "中文"}`
3. 保存翻译好的文件到`pretranslate_todo/todo/new`目录

也可以使用辅助工具或机器翻译批量处理，然后人工审校。

### 5. 将翻译文件转换为Key-Value格式(可选)

如果需要将日文:中文格式的翻译文件转换为key:value格式:

```bash
python scripts/pretranslate_process.py
# 选择选项3: 翻译文件(jp: cn)转回key-value json
```

这会将`pretranslate_todo/todo/new`目录中的翻译转换为`pretranslate_todo/translated_out`目录中的key-value格式。

### 6. 合并翻译到最终文件

将完成的翻译合并回游戏数据结构:

```bash
make merge
```

或直接运行脚本:

```bash
python scripts/pretranslate_process.py --merge
```

这一步会:
1. 将新翻译与现有翻译合并
2. 生成最终的翻译文件
3. 将结果保存到`data`目录，即可用的游戏本地化文件

### 7. 手动处理特定文件(可选)

如果需要单独处理某些文件:

```bash
# 导入单个文件的翻译
python scripts/import_db_json.py
# 按提示输入源JSON路径和翻译JSON路径

# 导出单个文件用于翻译
python scripts/export_db_json.py
# 按提示输入原JSON文件夹路径
```

## 文件格式说明

### YAML源文件

原始游戏数据，格式复杂，包含各种游戏相关信息。

### 转换后的JSON结构

```json
{
  "rules": {
    "primaryKeys": ["id", "name", "..."]
  },
  "data": [
    {
      "id": "123",
      "name": "示例名称",
      "description": "示例描述"
    }
  ]
}
```

### 待翻译格式

```json
{
  "日文文本1": "",
  "日文文本2": ""
}
```

### 翻译完成格式

```json
{
  "日文文本1": "中文翻译1",
  "日文文本2": "中文翻译2"
}
```

### Key-Value导出格式

```json
{
  "唯一标识1|字段路径": "文本内容",
  "唯一标识2|字段路径": "文本内容"
}
```

## 高级使用技巧

### 自定义翻译流程

可以修改`primary_key_rules`字典(在`gakumasu_diff_to_json.py`中)来控制哪些字段需要翻译。

### 批量处理

对于大量文件，推荐使用脚本批量操作:

```bash
# 例如，一次性处理所有文件
python scripts/pretranslate_process.py --gen_todo
# 翻译完成后
python scripts/pretranslate_process.py --merge
```

### 测试模式

在`gakumasu_diff_to_json.py`中有`TestMode`变量，设置为`True`时会在非主键文本后添加"TEST"标记，用于测试翻译流程。

## 注意事项和常见问题

1. **备份重要文件**
    - 在进行大规模操作前，建议备份`data`目录中的翻译文件

2. **路径问题**
    - 确保所有相对路径正确，脚本依赖于特定的目录结构

3. **YAML解析错误**
    - 如果遇到YAML解析错误，可能是由于特殊字符，检查`CustomLoader`类的设置

4. **合并冲突**
    - 多人协作时可能出现翻译冲突，建议采用版本控制系统管理翻译文件

5. **大文件处理**
    - 对于非常大的文件，可能需要增加处理超时时间或分批处理

6. **列表字段处理**
    - 列表类型的字段使用特殊标记`[LA_F]`和`[LA_N_F]`来表示，合并时会正确还原

## 项目文件说明

### gakumasu_diff_to_json.py

负责将YAML文件转换为结构化JSON，根据`primary_key_rules`定义的规则提取需要翻译的字段。

### pretranslate_process.py

管理整个翻译流程，提供四个主要功能:
1. 全部导出为待翻译文件
2. 生成增量待翻译文件
3. 翻译文件格式转换
4. 合并翻译回插件JSON

### import_db_json.py

将key-value格式的翻译内容导入到插件使用的JSON结构中。处理复杂的嵌套字段和列表字段。

### export_db_json.py

将插件格式的JSON文件导出为key-value格式，用于翻译。处理主键提取和路径规范化。



ProduceExamGimmickEffectGroup.json文件额外修改部分：温存 でない場合→未处于温存 的时候；好调 状態でない場合→未处于好调状态 的时候。对某几个“温存”、“好调”关键词做额外修改