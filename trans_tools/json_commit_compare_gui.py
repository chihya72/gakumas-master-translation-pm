"""Visual Git comparison for shared keys in a JSON translation file."""

import csv
import json
from pathlib import Path
from queue import Empty, Queue
import sys
from threading import Thread
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.compare_json_commits import DEFAULT_FILE, compare, git


def value_text(value):
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)


def file_history(file_name):
    path = Path(file_name)
    if not path.is_absolute():
        path = ROOT / path
    try:
        relative = path.resolve().relative_to(ROOT)
    except ValueError:
        raise ValueError("请选择本仓库内的 JSON 文件")
    content = git(
        ROOT, "log", "-60", "--format=%h%x09%s", "HEAD", "--", relative.as_posix()
    ).decode("utf-8", errors="replace")
    return [line.replace("\t", "  ", 1) for line in content.splitlines() if line]


def export_report(report, destination):
    path = Path(destination)
    if path.suffix.lower() == ".csv":
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["key", "old", "new"])
            for entry in report["changes"]:
                writer.writerow([entry["key"], value_text(entry["old"]), value_text(entry["new"])])
    else:
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class JsonCommitCompareApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("JSON Git 历史对比")
        self.geometry("1180x860")
        self.minsize(1000, 760)
        self.configure(fg_color="#f3f4f6")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=2, minsize=160)
        self.grid_rowconfigure(4, weight=1, minsize=160)

        self.file_var = tk.StringVar(value=str(ROOT / DEFAULT_FILE))
        self.base_var = tk.StringVar()
        self.target_var = tk.StringVar(value="HEAD")
        self.mode_var = tk.StringVar(value="最新提交 HEAD")
        self.search_var = tk.StringVar()
        self.messages = Queue()
        self.revision = 0
        self.history_revision = 0
        self.history_values = []
        self.report = None
        self.source_path = None
        self.busy = False
        self.closed = False
        self._build_ui()
        for variable in (self.file_var, self.base_var, self.target_var, self.mode_var):
            variable.trace_add("write", self._invalidate)
        self.search_var.trace_add("write", lambda *_: self.render_rows())
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.after(100, self._poll)
        self.refresh_history()

    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 12))
        ctk.CTkLabel(header, text="JSON Git 历史对比", font=("Microsoft YaHei UI", 26, "bold"),
                     text_color="#111827").pack(anchor="w")
        ctk.CTkLabel(header, text="查看同键不同值的条目 · 新增和删除的键不列出 · 默认比较本地最新提交",
                     text_color="#6b7280", font=("Microsoft YaHei UI", 13)).pack(anchor="w", pady=(4, 0))

        settings = ctk.CTkFrame(self, fg_color="white", corner_radius=14)
        settings.grid(row=1, column=0, sticky="ew", padx=24)
        settings.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(settings, text="JSON 文件").grid(row=0, column=0, padx=16, pady=(14, 8), sticky="w")
        self.file_entry = ctk.CTkEntry(settings, textvariable=self.file_var, height=34)
        self.file_entry.grid(row=0, column=1, sticky="ew", pady=(14, 8))
        self.file_entry.bind("<FocusOut>", self._file_focus_out)
        self.file_entry.bind("<Return>", lambda _: self.refresh_history())
        ctk.CTkButton(settings, text="选择文件", width=100, command=self.choose_file).grid(
            row=0, column=2, padx=16, pady=(14, 8))
        ctk.CTkLabel(settings, text="历史提交").grid(row=1, column=0, padx=16, pady=6, sticky="w")
        self.base_combo = ctk.CTkComboBox(settings, variable=self.base_var, values=[], height=34)
        self.base_combo.grid(row=1, column=1, sticky="ew", pady=6)
        ctk.CTkButton(settings, text="刷新历史", width=100, command=self.refresh_history).grid(
            row=1, column=2, padx=16, pady=6)
        ctk.CTkLabel(settings, text="目标版本").grid(row=2, column=0, padx=16, pady=6, sticky="w")
        targets = ctk.CTkFrame(settings, fg_color="transparent")
        targets.grid(row=2, column=1, sticky="ew", pady=6)
        targets.grid_columnconfigure(1, weight=1)
        ctk.CTkOptionMenu(targets, variable=self.mode_var, width=180,
                          values=["最新提交 HEAD", "指定提交", "当前文件（含未提交）"],
                          command=self._mode_changed).grid(row=0, column=0, padx=(0, 12))
        self.target_entry = ctk.CTkEntry(targets, textvariable=self.target_var,
                                        placeholder_text="输入目标 commit / 分支", state="disabled", height=34)
        self.target_entry.grid(row=0, column=1, sticky="ew")
        self.compare_button = ctk.CTkButton(settings, text="开始对比", width=100, command=self.start_compare)
        self.compare_button.grid(row=2, column=2, padx=16, pady=6)
        ctk.CTkLabel(settings, text="历史列表显示该文件最近 60 次提交；也可直接输入 commit、标签或分支。",
                     text_color="#6b7280", anchor="w").grid(
            row=3, column=1, columnspan=2, sticky="ew", pady=(0, 10))

        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.grid(row=2, column=0, sticky="ew", padx=24, pady=12)
        toolbar.grid_columnconfigure(0, weight=1)
        self.summary_label = ctk.CTkLabel(toolbar, text="选择历史提交后开始对比", anchor="w",
                                          text_color="#374151")
        self.summary_label.grid(row=0, column=0, sticky="ew")
        ctk.CTkEntry(toolbar, textvariable=self.search_var, width=280, height=34,
                     placeholder_text="搜索键名 / 旧值 / 新值").grid(row=0, column=1, padx=12)
        self.export_button = ctk.CTkButton(toolbar, text="导出全部", width=100, state="disabled", command=self.export)
        self.export_button.grid(row=0, column=2)

        table = ctk.CTkFrame(self, fg_color="white", corner_radius=0)
        table.grid(row=3, column=0, sticky="nsew", padx=24)
        table.grid_columnconfigure(0, weight=1)
        table.grid_rowconfigure(0, weight=1)
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Diff.Treeview", font=("Microsoft YaHei UI", 11), rowheight=32,
                        background="white", fieldbackground="white", foreground="#1f2937", borderwidth=0)
        style.configure("Diff.Treeview.Heading", font=("Microsoft YaHei UI", 11, "bold"),
                        background="#eaf0f8", foreground="#374151", padding=8)
        style.map("Diff.Treeview", background=[("selected", "#dbeafe")], foreground=[("selected", "#1e3a8a")])
        self.tree = ttk.Treeview(table, columns=("key", "old", "new"), show="headings",
                                  selectmode="browse", style="Diff.Treeview", height=6)
        for column, label, width in (("key", "键名", 390), ("old", "旧值", 330), ("new", "新值", 330)):
            self.tree.heading(column, text=label, anchor="w")
            self.tree.column(column, width=width, minwidth=180, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")
        vertical = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal = ttk.Scrollbar(table, orient="horizontal", command=self.tree.xview)
        horizontal.grid(row=1, column=0, sticky="ew")
        self.tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.tree.bind("<<TreeviewSelect>>", self.show_detail)

        detail = ctk.CTkFrame(self, fg_color="white", corner_radius=14)
        detail.grid(row=4, column=0, sticky="nsew", padx=24, pady=(12, 0))
        detail.grid_columnconfigure((0, 1), weight=1, uniform="detail")
        detail.grid_rowconfigure(1, weight=1)
        self.detail_key = ctk.CTkLabel(detail, text="选择一行查看完整内容", anchor="w", text_color="#374151")
        self.detail_key.grid(row=0, column=0, columnspan=2, sticky="ew", padx=14, pady=(8, 0))
        self.detail_boxes = {}
        self.copy_buttons = []
        for column, field, label, color in ((0, "old", "旧值", "#fff4f2"), (1, "new", "新值", "#eefbf4")):
            panel = ctk.CTkFrame(detail, fg_color="transparent")
            panel.grid(row=1, column=column, sticky="nsew", padx=12, pady=(0, 12))
            panel.grid_columnconfigure(0, weight=1)
            panel.grid_rowconfigure(1, weight=1)
            ctk.CTkLabel(panel, text=label, anchor="w").grid(row=0, column=0, sticky="w")
            button = ctk.CTkButton(panel, text="复制" + label, width=85, height=26, state="disabled",
                                    command=lambda name=field: self.copy_value(name))
            button.grid(row=0, column=1, pady=4)
            self.copy_buttons.append(button)
            box = ctk.CTkTextbox(panel, wrap="word", height=100, fg_color=color,
                                 text_color="#111827", font=("Microsoft YaHei UI", 13))
            box.grid(row=1, column=0, columnspan=2, sticky="nsew")
            box.configure(state="disabled")
            self.detail_boxes[field] = box

        self.status = ctk.CTkLabel(self, text="正在读取历史提交…", anchor="w", text_color="#6b7280",
                                    wraplength=1100, justify="left")
        self.status.grid(row=5, column=0, sticky="ew", padx=24, pady=(8, 12))

    def _invalidate(self, *_):
        self.revision += 1
        self.report = None
        self.source_path = None
        self.export_button.configure(state="disabled")
        self.render_rows()
        self.summary_label.configure(text="参数已变更，请开始对比")
        self.status.configure(text="只读取本地版本；最新提交指 HEAD，不自动拉取远端。")

    def _mode_changed(self, _=None):
        mode = self.mode_var.get()
        self.target_entry.configure(state="normal" if mode == "指定提交" else "disabled")
        if mode == "最新提交 HEAD":
            self.target_var.set("HEAD")
        elif mode == "当前文件（含未提交）":
            self.target_var.set("当前磁盘文件")
        elif self.target_var.get() == "当前磁盘文件":
            self.target_var.set("HEAD")

    def _file_focus_out(self, _):
        if self.file_var.get().strip() != getattr(self, "history_file", None):
            self.refresh_history()

    def choose_file(self):
        filename = filedialog.askopenfilename(parent=self, initialdir=str(ROOT / "pretranslate_todo" / "localization"),
                                               title="选择仓库内的 JSON 文件", filetypes=[("JSON 文件", "*.json")])
        if filename:
            self.file_var.set(filename)
            self.refresh_history()

    def _run_task(self, kind, token, action):
        def worker():
            try:
                self.messages.put((kind, token, action(), None))
            except Exception as error:
                self.messages.put((kind, token, None, str(error)))
        Thread(target=worker, daemon=True).start()

    def refresh_history(self):
        self.history_revision += 1
        filename = self.file_var.get().strip()
        if filename != getattr(self, "history_file", None):
            self.base_var.set("")
        self.history_file = filename
        self.history_values = []
        self.base_combo.configure(values=[])
        self.status.configure(text="正在读取该文件的历史提交…")
        self._run_task("history", self.history_revision, lambda: file_history(filename))

    def _base_ref(self):
        value = self.base_var.get().strip()
        return value.split("  ", 1)[0] if value in self.history_values else value

    def start_compare(self):
        if self.busy:
            return
        base = self._base_ref()
        filename = self.file_var.get().strip()
        working_tree = self.mode_var.get() == "当前文件（含未提交）"
        target = self.target_var.get().strip() if self.mode_var.get() == "指定提交" else "HEAD"
        if not base or not filename or (not working_tree and not target):
            messagebox.showwarning("参数未填写", "请选择文件并填写需要比较的提交。", parent=self)
            return
        # Hide any earlier result while the requested comparison is running.
        self._invalidate()
        self.busy = True
        self.compare_button.configure(state="disabled", text="对比中…")
        self.status.configure(text="正在读取版本并对比…")
        self._run_task("compare", self.revision,
                       lambda: compare(ROOT, filename, base, target, working_tree))

    def _poll(self):
        if self.closed:
            return
        try:
            while True:
                kind, token, result, error = self.messages.get_nowait()
                if kind == "history":
                    if token != self.history_revision or self.file_var.get().strip() != self.history_file:
                        continue
                    if error:
                        self.status.configure(text="读取历史失败：" + error)
                        continue
                    self.history_values = result
                    self.base_combo.configure(values=result)
                    if not self.base_var.get().strip() and result:
                        self.base_var.set(result[min(1, len(result) - 1)])
                    if not self.busy and self.report is None:
                        self.status.configure(text="已载入 {} 次提交，可选择或直接输入历史版本。".format(len(result)))
                else:
                    self.busy = False
                    self.compare_button.configure(state="normal", text="开始对比")
                    if token != self.revision:
                        self.status.configure(text="参数已变更，请重新开始对比。")
                        continue
                    if error:
                        self.status.configure(text="对比失败，请检查文件和提交。")
                        messagebox.showerror("对比失败", error, parent=self)
                        continue
                    self.report = result
                    self.source_path = (ROOT / result["file"]).resolve()
                    self.export_button.configure(state="normal")
                    self.render_rows()
                    old = result["base"]["commit"][:12]
                    new = result["target"]["commit"]
                    self.status.configure(text="{}  →  {}    ·    {}".format(
                        old, new[:12] if new else "当前磁盘文件（含未提交修改）", result["file"]))
        except Empty:
            pass
        self.after(100, self._poll)

    def render_rows(self):
        children = self.tree.get_children()
        if children:
            self.tree.delete(*children)
        self._clear_detail()
        if self.report is None:
            return
        query = self.search_var.get().strip().casefold()
        visible = []
        for index, entry in enumerate(self.report["changes"]):
            values = (entry["key"], value_text(entry["old"]), value_text(entry["new"]))
            if query and not any(query in value.casefold() for value in values):
                continue
            iid = str(index)
            self.tree.insert("", "end", iid=iid, values=tuple(value.replace("\n", r"\n").replace("\r", r"\r") for value in values))
            visible.append(iid)
        self.summary_label.configure(text="共 {} 条变化 · 当前显示 {} 条".format(self.report["changed_count"], len(visible)))
        if visible:
            self.tree.selection_set(visible[0])
            self.show_detail()

    def _clear_detail(self):
        self.detail_key.configure(text="选择一行查看完整内容")
        for box in self.detail_boxes.values():
            box.configure(state="normal")
            box.delete("1.0", "end")
            box.configure(state="disabled")
        for button in self.copy_buttons:
            button.configure(state="disabled")

    def selected_entry(self):
        selected = self.tree.selection()
        return self.report["changes"][int(selected[0])] if self.report and selected else None

    def show_detail(self, _=None):
        entry = self.selected_entry()
        if entry is None:
            return
        self.detail_key.configure(text=entry["key"])
        for field, box in self.detail_boxes.items():
            box.configure(state="normal")
            box.delete("1.0", "end")
            box.insert("1.0", value_text(entry[field]))
            box.configure(state="disabled")
        for button in self.copy_buttons:
            button.configure(state="normal")

    def copy_value(self, field):
        entry = self.selected_entry()
        if entry is not None:
            self.clipboard_clear()
            self.clipboard_append(value_text(entry[field]))

    def export(self):
        if self.report is None:
            return
        destination = filedialog.asksaveasfilename(
            parent=self, title="导出全部变化", initialdir=str(ROOT / "logs"),
            initialfile="localization_changes.json", defaultextension=".json",
            filetypes=[("JSON 报告", "*.json"), ("CSV 表格", "*.csv")],
        )
        if not destination:
            return
        try:
            if Path(destination).resolve() == self.source_path:
                raise ValueError("报告路径不能覆盖被比较的 JSON 文件")
            export_report(self.report, destination)
            self.status.configure(text="已导出全部 {} 条变化：{}".format(self.report["changed_count"], destination))
        except (OSError, ValueError) as error:
            messagebox.showerror("导出失败", str(error), parent=self)

    def close(self):
        self.closed = True
        self.destroy()


if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    JsonCommitCompareApp().mainloop()
