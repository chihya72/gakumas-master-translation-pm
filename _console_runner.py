import os
import sys
import runpy
import traceback
from pathlib import Path

script = Path(sys.argv[1])
root = Path(sys.argv[2])

os.chdir(root)
sys.argv = [str(script)]

print("=" * 70)
print(f"正在执行：{script.name}")
print(f"工作目录：{root}")
print("=" * 70)
print()

try:
    runpy.run_path(str(script), run_name="__main__")
except SystemExit as e:
    code = e.code
    if code not in (0, None):
        print()
        print(f"程序退出码：{code}")
except Exception:
    print()
    print("程序执行时发生异常：")
    traceback.print_exc()
finally:
    print()
    input("按回车键关闭窗口...")
