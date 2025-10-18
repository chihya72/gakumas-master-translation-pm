# Special Mapping 翻译冲突解决方案实施记录

## 项目背景

### 问题描述
在gakumas翻译项目中遇到了上下文相关的翻译歧义问题：
- 日文助词"を"在不同语境下需要不同的中文翻译
- 大多数情况下："を" → "会"
- 特定语境下："を" → "向"（如`pitem_01-2-096-0`中的"干扰卡を消除"应译为"干扰卡向消除"）

### 现有merge流程的问题
原有的增量合并优先级：`todo/new > jp_cn > temp_key_cn(data)`
- 基于简单键值对映射，无法处理上下文相关翻译
- jp_cn中的单一映射"を": "向"会影响所有包含"を"的文本
- 导致翻译不一致：某些地方需要"向"，某些地方需要"会"

## 解决方案设计

### 核心思路
1. **隔离特例**：将需要特殊处理的翻译条目完全独立管理
2. **保持现有流程**：jp_cn继续处理通用情况
3. **智能冲突解决**：当jp_cn和data一致而todo/new不同时，识别为特例情况
4. **自动特例提取**：从gakumasu-diff中提取完整的新增条目作为special mapping

### 新的优先级体系
```
special_mapping > todo/new > jp_cn > temp_key_cn(data)
```

### 智能冲突解决规则
当发现以下情况时，触发智能解决：
- `jp_cn翻译 == data翻译 != todo/new翻译`
- 判断：jp_cn/data是通用翻译，todo/new是特例
- 行动：使用jp_cn/data翻译，将todo/new标记为特例

## 实施进展

### 1. 创建Special Mapping结构

#### 目录结构
```
special_mapping/
├── README.md                       # 说明文档
├── ProduceItem/
│   ├── pitem_01-2-096-0.json      # 复活琴音的棒冰特例
│   └── [其他特例文件]
├── Character/
└── [其他数据类型]
```

#### 特例文件格式
```json
{
  "pitem_01-2-096-0|...|produceDescriptions[0].text": "集中",
  "pitem_01-2-096-0|...|produceDescriptions[1].text": "效果的技能卡获得时，视觉能力值在700以上的时候，随机",
  "pitem_01-2-096-0|...|produceDescriptions[2].text": "干扰卡",
  "pitem_01-2-096-0|...|produceDescriptions[3].text": "向",
  "pitem_01-2-096-0|...|produceDescriptions[4].text": "消除",
  "pitem_01-2-096-0|...|produceDescriptions[5].text": "\n视觉能力值上升+",
  "pitem_01-2-096-0|...|produceDescriptions[6].text": "30",
  "pitem_01-2-096-0|...|produceDescriptions[7].text": "\n（课程中1次）",
  "pitem_01-2-096-0|...|name": "复活琴音的棒冰"
}
```

### 2. 修改incremental_merge.py

#### 新增函数

##### load_special_mappings()
- 功能：加载special_mapping目录中的特殊映射
- 返回：(special_mappings字典, special_keys集合)
- 按文件加载，支持多个特例文件

##### is_special_key()
- 功能：检查键是否属于特殊映射
- 逻辑：前缀匹配，如pitem_01-2-096-0开头的键

##### save_smart_resolved_exceptions() [待完善]
- 功能：保存智能解决的特例到special_mapping
- 逻辑：按条目ID分组，提取完整条目信息

#### 修改的合并逻辑

##### 特殊映射优先处理
```python
# 首先检查是否为特殊映射键（最高优先级）
if is_special_key(key, special_keys) and key in special_mappings:
    used_translation = special_mappings[key]
    source = "special_mapping"
    special_count += 1
    final_key_cn_data[key] = used_translation
    # 特殊映射不参与冲突检测
    continue
```

##### 智能冲突解决
```python
# 智能冲突解决：如果jp_cn和data翻译一致，而todo/new不同，则优先使用jp_cn/data
if (len(available_translations) >= 2 and 
    "jp_cn" in available_translations and 
    "data" in available_translations and
    "todo/new" in available_translations):
    
    jp_cn_trans = available_translations["jp_cn"]
    data_trans = available_translations["data"]
    todo_new_trans = available_translations["todo/new"]
    
    if jp_cn_trans == data_trans and jp_cn_trans != todo_new_trans:
        # 使用通用翻译，收集特例信息
        used_translation = jp_cn_trans
        source = "jp_cn(智能解决)"
        smart_exceptions.append({...})
```

### 3. 测试验证

#### 测试方法
1. 创建测试用的`ProduceItem_translated.json`
2. 包含"を": "TEST-会"的映射
3. 验证pitem_01-2-096-0使用special mapping中的"向"
4. 验证其他键使用智能解决的"向"（来自jp_cn/data一致性）

#### 测试结果
- ✅ Special mapping正常工作：pitem_01-2-096-0相关键不出现在冲突报告中
- ✅ 智能解决正确识别：26个冲突键被识别为特例情况
- ✅ 优先级机制正确：special=9, jp_cn=8509, 其他正常分布

### 4. 当前文件状态

#### 已创建文件
- `special_mapping/README.md` - 完整的说明文档
- `special_mapping/ProduceItem/pitem_01-2-096-0.json` - 测试用特例文件
- `scripts/incremental_merge.py` - 已修改，包含完整逻辑

#### 已修改文件
- `pretranslate_todo/jp_cn/ProduceItem.json` - 移除了"を": "向"映射（后被用户撤销）

## 待完善功能

### 1. 完整的特例提取逻辑

当前save_smart_resolved_exceptions()函数需要完善为：

```python
def extract_complete_entry_from_diff(json_filename, entry_id):
    """从gakumasu-diff中提取完整条目"""
    diff_file = f"./gakumasu-diff/json/{json_filename}"
    data_file = f"./data/{json_filename}"
    
    # 对比diff和data，找出新增内容
    # 提取entry_id相关的所有字段
    # 返回完整的条目映射
```

### 2. 特例识别改进策略

正确的特例识别流程：
1. **发现冲突**：jp_cn和data一致，todo/new不同
2. **定位来源**：在gakumasu-diff中找到新增条目
3. **提取完整条目**：根据条目ID提取所有相关字段
4. **创建special mapping**：为整个条目创建完整映射

### 3. 自动化特例管理

```python
def analyze_diff_and_create_special_mapping():
    """
    自动分析diff文件，识别需要特殊处理的条目
    """
    # 1. 对比gakumasu-diff/json和data，找出新增条目
    # 2. 分析新增条目中的翻译模式
    # 3. 自动创建special mapping文件
    # 4. 更新jp_cn映射，移除冲突项
```

## 技术细节

### 键名结构分析
```
pitem_01-2-096-0|ProduceDescriptionType_ProduceExamEffectType|...|produceDescriptions[3].text
^^^^^^^^^^^^^^^^^^^^^  <- 条目ID，用于分组
                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^  <- 字段路径
```

### 特例文件命名规范
- 文件名：`{条目ID}.json`
- 位置：`special_mapping/{数据类型}/{条目ID}.json`
- 内容：该条目的所有相关字段的键值对

### 合并优先级详解
1. **special_mapping**：最高优先级，完全控制特定条目
2. **todo/new**：新翻译内容，通常来自人工翻译
3. **jp_cn**：通用日中映射，处理常见翻译模式
4. **data**：现有数据，作为后备

## 下次工作计划

### 1. 验证时机
等待gakumasu-diff有新的更新时，使用真实数据验证：
- 特例自动提取逻辑
- 完整条目special mapping创建
- 智能冲突解决效果

### 2. 功能完善
- 实现完整的diff分析逻辑
- 添加special mapping的版本管理
- 创建特例审核工具

### 3. 文档更新
- 更新README.md中的特例列表
- 添加使用说明和最佳实践
- 记录已知问题和解决方案

## 已知问题和注意事项

### 1. 测试数据清理
- 测试完成后需要删除`ProduceItem_translated.json`
- 确保jp_cn映射的正确性

### 2. 性能考虑
- special_mapping文件数量增长后的加载效率
- 大量冲突时的处理性能

### 3. 维护成本
- 需要建立clear的special mapping管理规范
- 定期审核特例的必要性

---

## 成果总结

今天成功实现了：
✅ Special mapping框架搭建
✅ 智能冲突解决机制
✅ 优先级体系重构
✅ 测试验证通过

待下次gakumasu-diff更新时继续完善特例自动提取功能。
