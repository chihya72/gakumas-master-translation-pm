# Gakumas Master Translation 本地仓库改进总结

基于原版 [gakumas-master-translation](https://github.com/imas-tools/gakumas-master-translation) 的改进内容：

## 1. Special Mapping 特殊映射系统

**解决问题**：日文助词"を"在不同语境下需要不同翻译（大多数"会"，特定情况"向"）

**具体实现**：
- 新增 `special_mapping/` 目录结构，按数据类型分类管理特例
- 创建条目级精确控制文件，如 `ProduceItem/pitem_01-2-096-0.json`
- 修改 `incremental_merge.py` 新增最高优先级特殊映射处理
- 优先级从 `todo/new > jp_cn > data` 升级为 `special_mapping > todo/new > jp_cn > data`

## 2. 智能冲突解决机制

**解决问题**：翻译冲突需要人工逐个处理

**具体实现**：
- 检测 `jp_cn翻译 == data翻译 != todo/new翻译` 的情况
- 自动判断jp_cn/data是通用翻译，todo/new可能是特例
- 智能选择通用翻译，自动标记特例信息
- 实际测试中自动解决了26个冲突键

## 3. 备份和变化检测系统

**解决问题**：游戏更新时无法追踪已翻译内容对应原文的变化

**具体实现**：
- 新增 `make backup` 命令，备份 `temp_key_jp` 到 `temp_key_jp_old`
- 改进 `gen_todo()` 函数，从只检测新增键扩展到检测值变化键
- 检测逻辑：`k in jp_old_data and jp_old_data[k] != v and k in cn_data`
- 输出CSV格式变化文件到 `todo/changed/` 目录
- 生成详细变化日志 `jp_changes_log_YYYYMMDD_HHMMSS.txt`

## 4. Changed 翻译应用系统

**解决问题**：变化的翻译需要手动逐个更新

**具体实现**：
- 新增 `apply_changed_translations()` 函数
- 自动读取 `changed/` 目录中的CSV文件
- 解析格式：`旧值,新值,旧翻译,新翻译`
- 自动更新到 `temp_key_cn` 和 `jp_cn` 文件夹
- 支持批量处理多个文件

## 5. jp_cn 通用翻译映射目录

**解决问题**：缺乏统一的日中翻译映射管理

**具体实现**：
- 新增 `pretranslate_todo/jp_cn/` 目录
- 存储日文到中文的通用翻译映射
- 在优先级体系中作为第三级
- 为Special Mapping系统提供对比基准

## 6. 增强的脚本功能

**pretranslate_process.py 改进**：
- 代码从206行扩展到510行
- 新增2个命令行参数：`--backup`、`--apply_changed`
- 交互菜单从4个选项扩展到6个
- 新增智能警告系统和详细状态报告

**新增 incremental_merge.py 脚本**：
- 455行专业合并逻辑
- 实现特殊映射加载和智能冲突解决
- 详细的统计和冲突报告功能

## 7. Makefile 命令扩展

**新增命令**：
- `make backup` - 备份temp_key_jp用于变化检测

**改进现有命令**：
- `make gen-todo` - 支持变化检测
- `make merge` - 使用增强合并脚本含Special Mapping

## 8. 目录结构扩展

**新增目录**：
- `special_mapping/` - 特殊映射系统
- `pretranslate_todo/jp_cn/` - 通用翻译映射
- `pretranslate_todo/todo/changed/` - 变化记录CSV
- `pretranslate_todo/temp_key_jp_old/` - 备份目录
- `pretranslate_todo/conflicts/` - 冲突报告

**新增文件类型**：
- CSV变化文件
- 时间戳变化日志
- 特例映射JSON文件

---

## 翻译流程对比

### 原版流程（基础）
```
1. make update
   - 从 gakumasu-diff 仓库获取最新 diff 文件
   - 将 orig/ 转换为 json/

2. make gen-todo  
   - 对比 data/ 和 gakumasu-diff/json/
   - 生成 temp_key_cn/ 和 temp_key_jp/
   - 只检测新增内容，输出到 todo/

3. 人工翻译
   - 翻译 todo/ 中的文件
   - 移动到 todo/new/ 并重命名为 *_translated.json

4. make merge
   - 合并 _translated 文件和现有翻译
   - 输出到 data/
```

### 改进版流程（专业）
```
1. make backup (新增)
   - 备份当前 temp_key_jp/ 到 temp_key_jp_old/
   - 为变化检测提供基础

2. make update  
   - 从 gakumasu-diff 仓库获取最新 diff 文件
   - 将 orig/ 转换为 json/

3. make gen-todo (增强)
   - 对比 data/ 和 gakumasu-diff/json/
   - 生成 temp_key_cn/ 和 temp_key_jp/
   - 检测新增内容 → todo/
   - 检测变化内容 → todo/changed/ (CSV格式)
   - 生成变化日志

4. 人工翻译 (双重)
   - 翻译 todo/ 中的新增内容
   - 翻译 todo/changed/ 中的变化内容 (CSV第4列填入新翻译)
   - 移动到 todo/new/ 并重命名为 *_translated.json

5. python scripts/pretranslate_process.py --apply_changed (新增)
   - 自动应用 changed/ 中的翻译更新
   - 更新到 temp_key_cn/ 和 jp_cn/

6. make merge (增强)
   - 使用 incremental_merge.py 进行智能合并
   - 优先级：special_mapping > todo/new > jp_cn > data
   - 自动解决翻译冲突
   - 输出详细统计和冲突报告
```

### 推荐的新流程操作步骤

**第一次使用**：
```bash
# 1. 备份（如果不是第一次）
make backup

# 2. 获取最新数据
make update

# 3. 生成待翻译内容
make gen-todo

# 4. 检查输出
# - pretranslate_todo/todo/ 包含新增内容
# - pretranslate_todo/todo/changed/ 包含变化内容(如果有备份)
# - jp_changes_log_*.txt 包含详细变化记录

# 5. 人工翻译
# - 翻译 todo/ 中的 JSON 文件
# - 编辑 changed/ 中的 CSV 文件（第4列填入新翻译）
# - 完成后移动到 todo/new/ 并添加 _translated 后缀

# 6. 应用变化翻译（如果有 changed/ 文件）
python scripts/pretranslate_process.py --apply_changed

# 7. 最终合并
make merge

# 8. 检查结果
# - data/ 目录包含最终翻译文件
# - pretranslate_todo/conflicts/ 包含冲突报告
```

**日常更新流程**：
```bash
make backup → make update → make gen-todo → 翻译 → --apply_changed → make merge
```

### 关键改进点

1. **备份机制**：每次更新前先备份，支持变化检测
2. **双重检测**：不仅检测新增，还检测已有内容的变化
3. **智能合并**：自动解决冲突，支持特殊映射
4. **结构化处理**：CSV格式的变化管理，便于批量编辑
5. **详细报告**：完整的统计信息和冲突分析

**总结**：从基础翻译工具升级为专业翻译管理系统，主要解决了上下文翻译歧义、游戏更新追踪、冲突自动化处理等核心问题。