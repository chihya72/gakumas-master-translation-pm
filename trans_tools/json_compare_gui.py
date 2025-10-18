#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON文件对比工具 - 带图形界面版本
使用tkinter创建简单的GUI界面
"""

import json
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import os
from typing import Dict


class JSONComparerGUI:
    """JSON文件对比器图形界面"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("JSON文件对比工具")
        self.root.geometry("800x600")
        
        # 结果存储
        self.only_in_first = {}
        self.only_in_second = {}
        self.value_different = {}
        
        self.setup_ui()
    
    def format_value_as_text(self, value):
        """将值格式化为文本，保留所有转义字符不进行转义"""
        if isinstance(value, str):
            # 使用repr()来显示原始字符串，包括所有转义字符
            return repr(value)[1:-1]  # 去掉首尾的引号
        else:
            return str(value)
    
    def setup_ui(self):
        """设置用户界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 文件选择框架
        file_frame = ttk.LabelFrame(main_frame, text="选择要对比的JSON文件", padding="10")
        file_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 文件1选择
        ttk.Label(file_frame, text="文件1:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.file1_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file1_var, width=50).grid(row=0, column=1, padx=(5, 5), pady=2)
        ttk.Button(file_frame, text="浏览", command=self.select_file1).grid(row=0, column=2, pady=2)
        
        # 文件2选择
        ttk.Label(file_frame, text="文件2:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.file2_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file2_var, width=50).grid(row=1, column=1, padx=(5, 5), pady=2)
        ttk.Button(file_frame, text="浏览", command=self.select_file2).grid(row=1, column=2, pady=2)
        
        # 对比按钮
        ttk.Button(file_frame, text="开始对比", command=self.compare_files).grid(row=2, column=1, pady=10)
        
        # 结果显示框架
        result_frame = ttk.LabelFrame(main_frame, text="对比结果", padding="10")
        result_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # 结果文本区域
        self.result_text = scrolledtext.ScrolledText(result_frame, width=80, height=25, wrap=tk.WORD)
        self.result_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=(0, 10))
        
        ttk.Button(button_frame, text="保存结果", command=self.save_results).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(button_frame, text="清空结果", command=self.clear_results).grid(row=0, column=1, padx=(0, 10))
        ttk.Button(button_frame, text="退出", command=self.root.quit).grid(row=0, column=2)
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
        file_frame.columnconfigure(1, weight=1)
    
    def select_file1(self):
        """选择第一个文件"""
        filename = filedialog.askopenfilename(
            title="选择第一个JSON文件",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            self.file1_var.set(filename)
    
    def select_file2(self):
        """选择第二个文件"""
        filename = filedialog.askopenfilename(
            title="选择第二个JSON文件",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            self.file2_var.set(filename)
    
    def load_json(self, file_path: str) -> Dict:
        """加载JSON文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            messagebox.showerror("错误", f"文件 '{file_path}' 未找到")
            return None
        except json.JSONDecodeError as e:
            messagebox.showerror("错误", f"文件 '{file_path}' 不是有效的JSON格式:\n{e}")
            return None
        except Exception as e:
            messagebox.showerror("错误", f"读取文件 '{file_path}' 时发生错误:\n{e}")
            return None
    
    def compare_json(self, json1: Dict, json2: Dict):
        """对比两个JSON字典"""
        # 清空之前的结果
        self.only_in_first.clear()
        self.only_in_second.clear()
        self.value_different.clear()
        
        # 获取所有键的并集
        all_keys = set(json1.keys()) | set(json2.keys())
        
        for key in all_keys:
            if key in json1 and key in json2:
                # 键在两个文件中都存在，检查值是否相同
                if json1[key] != json2[key]:
                    self.value_different[key] = {
                        'file1_value': json1[key],
                        'file2_value': json2[key]
                    }
            elif key in json1:
                # 键只在第一个文件中存在
                self.only_in_first[key] = json1[key]
            else:
                # 键只在第二个文件中存在
                self.only_in_second[key] = json2[key]
    
    def compare_files(self):
        """执行文件对比"""
        file1_path = self.file1_var.get()
        file2_path = self.file2_var.get()
        
        if not file1_path or not file2_path:
            messagebox.showwarning("警告", "请选择两个要对比的JSON文件")
            return
        
        # 加载JSON文件
        json1 = self.load_json(file1_path)
        json2 = self.load_json(file2_path)
        
        if json1 is None or json2 is None:
            return
        
        # 执行对比
        self.compare_json(json1, json2)
        
        # 显示结果
        self.display_results(file1_path, file2_path, len(json1), len(json2))
    
    def display_results(self, file1_path: str, file2_path: str, len1: int, len2: int):
        """显示对比结果"""
        self.result_text.delete(1.0, tk.END)
        
        result = []
        result.append("=" * 80)
        result.append("JSON文件对比结果")
        result.append(f"文件1: {os.path.basename(file1_path)} ({len1} 个键)")
        result.append(f"文件2: {os.path.basename(file2_path)} ({len2} 个键)")
        result.append("=" * 80)
        result.append("")
        
        # 只在文件1中存在的键
        if self.only_in_first:
            result.append(f"🔍 只在文件1中存在的键 ({len(self.only_in_first)}个):")
            result.append("-" * 50)
            for key, value in self.only_in_first.items():
                result.append(f"键: {key}")
                result.append(f"值: {self.format_value_as_text(value)}")
                result.append("")
        
        # 只在文件2中存在的键
        if self.only_in_second:
            result.append(f"🔍 只在文件2中存在的键 ({len(self.only_in_second)}个):")
            result.append("-" * 50)
            for key, value in self.only_in_second.items():
                result.append(f"键: {key}")
                result.append(f"值: {self.format_value_as_text(value)}")
                result.append("")
        
        # 键相同但值不同
        if self.value_different:
            result.append(f"⚠️  键相同但值不同的项 ({len(self.value_different)}个):")
            result.append("-" * 50)
            for key, values in self.value_different.items():
                result.append(f"键: {key}")
                result.append(f"文件1值: {self.format_value_as_text(values['file1_value'])}")
                result.append(f"文件2值: {self.format_value_as_text(values['file2_value'])}")
                result.append("")
        
        # 统计信息
        result.append("📊 统计信息:")
        result.append("-" * 50)
        result.append(f"只在文件1中的键数量: {len(self.only_in_first)}")
        result.append(f"只在文件2中的键数量: {len(self.only_in_second)}")
        result.append(f"值不同的键数量: {len(self.value_different)}")
        
        total_differences = len(self.only_in_first) + len(self.only_in_second) + len(self.value_different)
        result.append(f"总差异数量: {total_differences}")
        
        if total_differences == 0:
            result.append("")
            result.append("✅ 两个JSON文件完全相同！")
        
        # 显示结果
        self.result_text.insert(tk.END, "\n".join(result))
        
        # 显示完成消息
        messagebox.showinfo("完成", f"对比完成！发现 {total_differences} 个差异。")
    
    def save_results(self):
        """保存结果到文件"""
        if not self.result_text.get(1.0, tk.END).strip():
            messagebox.showwarning("警告", "没有结果可保存")
            return
        
        filename = filedialog.asksaveasfilename(
            title="保存对比结果",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.result_text.get(1.0, tk.END))
                messagebox.showinfo("成功", f"结果已保存到: {filename}")
            except Exception as e:
                messagebox.showerror("错误", f"保存文件时发生错误:\n{e}")
    
    def clear_results(self):
        """清空结果"""
        self.result_text.delete(1.0, tk.END)


def main():
    """主函数"""
    root = tk.Tk()
    app = JSONComparerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()