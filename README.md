# Gakumas Master Translation Enhanced

> 基于 [gakumas-master-translation](https://github.com/imas-tools/gakumas-master-translation) 的增强版翻译工具集

**主要改进**：
- ✅ Special Mapping 特殊映射系统
- ✅ 智能冲突解决机制  
- ✅ 游戏更新变化检测
- ✅ 自动化翻译应用系统
- ✅ 增强的工作流程管理

简体中文 | [改进详情](IMPROVEMENTS_SUMMARY.md)

---

## 🚀 快速开始

### 必备环境
- Python 3.6+
- Git
- Make (Windows用户可使用 `winget install GnuWin32.Make`)

### 推荐工作流程
```bash
# 1. 备份当前状态（非首次使用）
make backup

# 2. 获取最新游戏数据
make update

# 3. 生成待翻译内容
make gen-todo

# 4. 翻译内容（详见下方说明）

# 5. 智能合并到最终文件
make merge
```

---

## 📁 目录结构

```
gakumas-master-translation-pm/
├── data/                          # 🎯 最终翻译文件（插件使用）
├── gakumasu-diff/                 # 📦 原始游戏数据
├── special_mapping/               # ⭐ 特殊映射系统
│   ├── README.md                  #    详细说明文档
│   ├── ProduceItem/               #    按数据类型分类
│   │   └── pitem_01-2-096-0.json #    具体特例文件
│   └── [其他数据类型]/
├── pretranslate_todo/             # 🔄 翻译工作区
│   ├── todo/                      #    待翻译文件
│   │   ├── [JSON文件]             #    新增内容
│   │   └── changed/               #    变化内容(CSV格式)
│   ├── temp_key_cn/               #    中文键值对缓存
│   ├── temp_key_jp/               #    日文键值对缓存  
│   ├── temp_key_jp_old/           #    备份目录
│   ├── jp_cn/                     #    通用日中映射
│   ├── conflicts/                 #    冲突报告
│   ├── merged/                    #    合并结果
│   └── jp_changes_log_*.txt       #    变化检测日志
└── scripts/                       # 🛠️ 工具脚本
```

---

## 🔧 命令详解

### make backup
**功能**：备份当前翻译状态  
**说明**：将 `temp_key_jp/` 备份到 `temp_key_jp_old/`，为变化检测提供基础
```bash
make backup
```

### make update  
**功能**：获取最新游戏数据  
**说明**：从 [gakumasu-diff](https://github.com/vertesan/gakumasu-diff) 拉取最新数据并转换为JSON格式
```bash
make update
```
⚠️ **注意**：如遇到第32万行括号错误，删除"text: 	（"中括号前的异常全角空格

### make gen-todo
**功能**：生成待翻译文件（增强版）  
**说明**：检测新增内容和变化内容，输出到不同目录
```bash
make gen-todo
```
**输出**：
- `todo/` - 新增内容（JSON格式）
- `todo/changed/` - 变化内容（CSV格式）
- 变化检测日志文件

### make merge
**功能**：智能合并翻译（增强版）  
**说明**：使用四级优先级体系和智能冲突解决进行合并
```bash
make merge
```
**优先级**：`special_mapping > todo/new > jp_cn > data`

---

## 📝 翻译流程详解

### 1. 新增内容翻译
编辑 `pretranslate_todo/todo/` 中的JSON文件：
```json
{
  "日文原文1": "中文翻译1",
  "日文原文2": "中文翻译2"
}
```
完成后移动到 `todo/new/` 并重命名为 `文件名_translated.json`

### 2. 变化内容翻译
编辑 `pretranslate_todo/todo/changed/` 中的CSV文件：
```csv
旧值,新值,旧翻译,新翻译
トラブルカードカードを除去,トラブルカードカードカードを削除,干扰卡会除去,干扰卡会删除
```
在第4列（新翻译）填入更新后的翻译

---

## ⭐ 特殊映射系统

### 使用场景
解决上下文相关的翻译歧义问题，如：
- 日文助词"を"：大多数情况翻译为"会"，特定语境翻译为"向"

### 创建特例
1. 在 `special_mapping/数据类型/` 目录下创建 `条目ID.json`
2. 文件格式：
```json
{
  "pitem_01-2-096-0|...|produceDescriptions[3].text": "向",
  "pitem_01-2-096-0|...|name": "复活琴音的棒冰"
}
```

### 特例优先级
特殊映射享有**最高优先级**，不参与冲突检测，确保特定条目的翻译完全按照特例执行。

---

## 🔍 高级功能

### 智能冲突解决
系统自动检测翻译冲突模式：
- 当 `jp_cn翻译 == data翻译 != todo/new翻译` 时
- 自动判断jp_cn/data为通用翻译，todo/new为特例
- 智能选择合适的翻译策略

### 变化检测系统
- **新增检测**：识别完全新的游戏内容
- **变化检测**：识别已有内容的原文变化
- **结构化记录**：CSV格式便于批量处理

### 冲突报告
合并完成后查看 `pretranslate_todo/conflicts/` 目录：
- 详细的冲突分析
- 翻译来源统计
- 处理建议

---

## 📊 脚本工具

### pretranslate_process.py（增强版）
```bash
python scripts/pretranslate_process.py [选项]

选项：
  --backup       备份当前temp_key_jp
  --gen_todo     生成待翻译文件
  --merge        合并翻译

交互模式：
  1. 全部导出转为待翻译文件
  2. 对比更新并生成todo文件  
  3. 翻译文件(jp: cn)转回key-value json
  4. 将翻译后的todo文件合并回插件json
  5. 备份当前temp_key_jp
  6. 应用changed文件夹中的新翻译
```

### incremental_merge.py（新增）
```bash
python scripts/incremental_merge.py

功能：
- 特殊映射系统处理
- 智能冲突解决
- 详细统计报告
- 冲突分析和建议
```

---

## 🔧 故障排除

### 常见问题

**Q: make update报错括号问题**  
A: 在错误提示的第32万行附近找到"text: 	（"，删除括号前的异常全角空格

**Q: 变化检测功能无法使用**  
A: 确保先执行 `make backup` 创建备份目录

**Q: 翻译冲突如何处理**  
A: 查看 `conflicts/` 目录的报告，系统已自动智能解决大部分冲突

**Q: 特殊映射不生效**  
A: 检查文件路径和JSON格式，确保条目ID匹配正确

### 获取帮助
- 查看详细日志文件了解处理过程
- 检查 `conflicts/` 目录获取冲突分析
- 参考相关文档获取更多信息

---

## 🏆 项目特点

### 相比原版的优势
- **专业化**：从基础工具升级为专业翻译管理系统
- **智能化**：自动冲突解决和变化检测
- **结构化**：完整的版本管理和状态跟踪
- **可扩展**：支持特殊映射和自定义翻译策略

### 适用场景
- 游戏本地化翻译项目
- 多人协作翻译工作
- 需要版本跟踪的翻译项目
- 有特殊翻译需求的内容管理

---

*基于 [gakumas-master-translation](https://github.com/imas-tools/gakumas-master-translation) 开发*  
*Enhanced by: chihya72*  
*Last Updated: 2025年10月11日*
