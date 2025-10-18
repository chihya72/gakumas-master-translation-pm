# Special Mapping 使用说明

## 快速开始

### 运行改进版合并脚本
```bash
python scripts/incremental_merge.py
```

### 新的输出信息
- `📋 加载特殊映射:` - 显示加载的special mapping文件
- `🧠 智能解决冲突:` - 显示自动解决的翻译冲突
- `📊 翻译统计:` - 新增special统计

### 翻译优先级
```
special_mapping > todo/new > jp_cn > temp_key_cn(data)
```

## 文件结构

```
special_mapping/
├── README.md                    # 详细说明
├── ProduceItem/
│   └── pitem_01-2-096-0.json  # 复活琴音的棒冰特例
└── [其他数据类型]/
```

## 待gakumasu-diff更新时
1. 运行脚本观察智能冲突解决
2. 验证特例自动提取功能
3. 完善save_smart_resolved_exceptions逻辑

## 当前状态
✅ 框架搭建完成
✅ 测试验证通过
⏳ 等待真实数据验证
