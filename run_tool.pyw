import os
import sys
import subprocess
import traceback
from pathlib import Path

import customtkinter as ctk
from tkinter import messagebox


ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

TOOLS = [
    {
        "title": "更新 JP-CN 映射文件",
        "desc": "更新日中映射数据，适合在控制台中查看执行日志。",
        "script": ROOT / "trans_tools" / "jp_cn.py",
        "console": True,
        "tag": "命令行",
    },
    {
        "title": "翻译填充工具",
        "desc": "打开图形界面，批量填充或处理翻译文本。",
        "script": ROOT / "trans_tools" / "full_trans_gui.py",
        "console": False,
        "tag": "GUI",
    },
    {
        "title": "JSON 文件对比工具",
        "desc": "对比 JSON 翻译文件，检查差异和缺漏内容。",
        "script": ROOT / "trans_tools" / "json_compare_gui.py",
        "console": False,
        "tag": "GUI",
    },
]


def get_python_executable(console: bool) -> str:
    exe = Path(sys.executable)

    if console and exe.name.lower() == "pythonw.exe":
        candidate = exe.with_name("python.exe")
        if candidate.exists():
            return str(candidate)

    if not console and exe.name.lower() == "python.exe":
        candidate = exe.with_name("pythonw.exe")
        if candidate.exists():
            return str(candidate)

    return str(exe)


def build_env() -> dict:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    return env


def run_console_script(script: Path):
    if not script.exists():
        messagebox.showerror("文件不存在", f"找不到脚本：\n{script}")
        return

    python_exe = get_python_executable(console=True)

    runner = ROOT / "_console_runner.py"
    runner.write_text(
        r'''
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
'''.lstrip(),
        encoding="utf-8",
    )

    try:
        subprocess.Popen(
            [python_exe, str(runner), str(script), str(ROOT)],
            cwd=str(ROOT),
            env=build_env(),
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
    except Exception:
        messagebox.showerror("启动失败", traceback.format_exc())


def run_gui_script(script: Path):
    if not script.exists():
        messagebox.showerror("文件不存在", f"找不到脚本：\n{script}")
        return

    python_exe = get_python_executable(console=False)
    log_file = LOG_DIR / f"{script.stem}.log"

    try:
        log = open(log_file, "a", encoding="utf-8")
        subprocess.Popen(
            [python_exe, str(script)],
            cwd=str(ROOT),
            env=build_env(),
            stdout=log,
            stderr=subprocess.STDOUT,
        )
    except Exception:
        messagebox.showerror("启动失败", traceback.format_exc())


def launch_tool(tool: dict):
    if tool["console"]:
        run_console_script(tool["script"])
    else:
        run_gui_script(tool["script"])


class ToolCard(ctk.CTkFrame):
    def __init__(self, master, tool: dict):
        super().__init__(
            master,
            fg_color="#ffffff",
            corner_radius=18,
            border_width=1,
            border_color="#e5e7eb",
        )

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)

        left = ctk.CTkFrame(self, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(22, 12), pady=18)

        top_line = ctk.CTkFrame(left, fg_color="transparent")
        top_line.pack(anchor="w", fill="x")

        title = ctk.CTkLabel(
            top_line,
            text=tool["title"],
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=18, weight="bold"),
            text_color="#111827",
        )
        title.pack(side="left")

        tag = ctk.CTkLabel(
            top_line,
            text=tool["tag"],
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=12, weight="bold"),
            text_color="#2563eb",
            fg_color="#eff6ff",
            corner_radius=999,
            padx=10,
            pady=4,
        )
        tag.pack(side="left", padx=(10, 0))

        desc = ctk.CTkLabel(
            left,
            text=tool["desc"],
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=13),
            text_color="#6b7280",
            anchor="w",
        )
        desc.pack(anchor="w", pady=(8, 0))

        path_label = ctk.CTkLabel(
            left,
            text=str(tool["script"].relative_to(ROOT)),
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color="#9ca3af",
            anchor="w",
        )
        path_label.pack(anchor="w", pady=(8, 0))

        button = ctk.CTkButton(
            self,
            text="启动",
            width=92,
            height=38,
            corner_radius=12,
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=14, weight="bold"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            command=lambda: launch_tool(tool),
        )
        button.grid(row=0, column=1, sticky="e", padx=(8, 22), pady=18)


class LauncherApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("翻译工具集合")
        self.geometry("760x560")
        self.minsize(720, 520)

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.configure(fg_color="#f3f4f6")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.create_header()
        self.create_body()
        self.create_footer()

    def create_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=34, pady=(30, 18))
        header.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            header,
            text="翻译工具集合",
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=30, weight="bold"),
            text_color="#111827",
        )
        title.grid(row=0, column=0, sticky="w")

        subtitle = ctk.CTkLabel(
            header,
            text="集中启动翻译相关工具。命令行工具会打开独立控制台窗口，GUI 工具会直接启动界面。",
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=14),
            text_color="#6b7280",
        )
        subtitle.grid(row=1, column=0, sticky="w", pady=(8, 0))

    def create_body(self):
        body = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color="#d1d5db",
            scrollbar_button_hover_color="#9ca3af",
        )
        body.grid(row=1, column=0, sticky="nsew", padx=28, pady=(0, 10))
        body.grid_columnconfigure(0, weight=1)

        for index, tool in enumerate(TOOLS):
            card = ToolCard(body, tool)
            card.grid(row=index, column=0, sticky="ew", padx=6, pady=8)

    def create_footer(self):
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=34, pady=(0, 24))
        footer.grid_columnconfigure(0, weight=1)

        root_label = ctk.CTkLabel(
            footer,
            text=f"工作目录：{ROOT}",
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=12),
            text_color="#9ca3af",
        )
        root_label.grid(row=0, column=0, sticky="w")

        quit_button = ctk.CTkButton(
            footer,
            text="退出",
            width=86,
            height=34,
            corner_radius=10,
            fg_color="#e5e7eb",
            hover_color="#d1d5db",
            text_color="#374151",
            command=self.destroy,
        )
        quit_button.grid(row=0, column=1, sticky="e")


if __name__ == "__main__":
    try:
        app = LauncherApp()
        app.mainloop()
    except Exception:
        log_file = LOG_DIR / "launcher_error.log"
        log_file.write_text(traceback.format_exc(), encoding="utf-8")
        messagebox.showerror("启动器错误", f"启动器发生错误，详情见：\n{log_file}")