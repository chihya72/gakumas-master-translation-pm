# 比较 JSON 在 Git 历史中的值变化

需要 Python 3.6+ 和 Git，无第三方依赖。默认文件为
`pretranslate_todo\localization\localization_full.json`，默认目标为本地仓库的 `HEAD`。
工具不自动 fetch、pull 或修改翻译文件。

## 图形界面

打开仓库根目录的 `run_tool.pyw`，点击 **JSON Git 历史对比 → 启动**。
默认选择 localization_full.json，可从历史列表选提交，也可直接输入 commit。
目标可选最新提交 HEAD、指定提交或当前文件（含未提交修改）。
点击“开始对比”后，表格显示键名、旧值、新值；选中一行可在下方查看和复制完整文本。
搜索框可按键名或两端内容筛选。“导出全部”支持 JSON 和 CSV，导出包含全部比较结果。
界面需要启动器已有的 customtkinter 和 tkinter 环境。

以下命令在 PowerShell 7 中运行。把 `dc25e37` 替换成需要比较的 commit：

```powershell
python -B D:\GIT\gakumas-master-translation-pm\scripts\compare_json_commits.py dc25e37
if ($LASTEXITCODE -ne 0) { throw 'JSON comparison failed' }
```

只列出两个版本中都存在、但值不同的顶层键，按键排序，每条显示旧值和新值。
新增、删除的键和相同值不列出；JSON 的缩进、顶层键顺序及等价转义不算值变化。
换行以 `\n` 显示。嵌套值按完整 JSON 值比较。

## 导出 JSON 报告

`--output` 的相对路径基于终端当前目录，父目录必须已经存在。

```powershell
python -B D:\GIT\gakumas-master-translation-pm\scripts\compare_json_commits.py dc25e37 --output D:\GIT\gakumas-master-translation-pm\logs\localization_changes.json
if ($LASTEXITCODE -ne 0) { throw 'JSON comparison failed' }
```

报告包含文件路径、两端 commit、变化数量以及 `changes` 数组；数组条目为
`{"key": "字段名", "old": "旧值", "new": "新值"}`。没有变化时数组为空。
发现差异和没有差异都返回 0；commit 无效、文件不存在、JSON 无效或写报告失败返回非零。

## 比较未提交的修改

默认比较已提交版本。要包含当前磁盘上的修改，使用：

```powershell
python -B D:\GIT\gakumas-master-translation-pm\scripts\compare_json_commits.py HEAD --working-tree
if ($LASTEXITCODE -ne 0) { throw 'JSON comparison failed' }
```

## 其他文件或目标版本

`--file` 接受绝对路径或相对仓库根目录的路径。
`--target` 可指定另一个 commit、标签或分支，与 `--working-tree` 互斥。
其他仓库可通过 `--repo` 指定。

```powershell
python -B D:\GIT\gakumas-master-translation-pm\scripts\compare_json_commits.py dc25e37 --target a213311 --file D:\GIT\gakumas-master-translation-pm\pretranslate_todo\localization\localization.json
if ($LASTEXITCODE -ne 0) { throw 'JSON comparison failed' }
```
