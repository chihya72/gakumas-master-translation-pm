#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
翻译填充工具 - 带图形界面版本
使用tkinter创建简单的GUI界面
"""

import json
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import os
from typing import Dict


class FullTransGUI:
    """翻译填充工具图形界面"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("翻译填充工具")
        self.root.geometry("900x700")
        
        # 结果存储
        self.translations_found = 0
        self.empty_keys_count = 0
        self.remaining_keys_count = 0
        
        self.setup_ui()
    
    def setup_ui(self):
        """设置用户界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 文件选择框架
        file_frame = ttk.LabelFrame(main_frame, text="选择文件和目录", padding="10")
        file_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 主文件选择
        ttk.Label(file_frame, text="主JSON文件:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.main_file_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.main_file_var, width=60).grid(row=0, column=1, padx=(5, 5), pady=2)
        ttk.Button(file_frame, text="浏览", command=self.select_main_file).grid(row=0, column=2, pady=2)
        
        # JP-CN目录选择
        ttk.Label(file_frame, text="JP-CN目录:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.jp_cn_dir_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.jp_cn_dir_var, width=60).grid(row=1, column=1, padx=(5, 5), pady=2)
        ttk.Button(file_frame, text="浏览", command=self.select_jp_cn_dir).grid(row=1, column=2, pady=2)
        
        # 操作按钮框架
        button_frame = ttk.Frame(file_frame)
        button_frame.grid(row=2, column=0, columnspan=3, pady=10)
        
        ttk.Button(button_frame, text="预览翻译", command=self.preview_translations).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(button_frame, text="开始填充", command=self.fill_translations).grid(row=0, column=1, padx=(0, 10))
        
        # 进度框架
        progress_frame = ttk.LabelFrame(main_frame, text="进度信息", padding="10")
        progress_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        # 状态标签
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(progress_frame, textvariable=self.status_var).grid(row=0, column=1)
        
        # 结果显示框架
        result_frame = ttk.LabelFrame(main_frame, text="操作日志", padding="10")
        result_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # 结果文本区域
        self.result_text = scrolledtext.ScrolledText(result_frame, width=90, height=25, wrap=tk.WORD)
        self.result_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 底部按钮框架
        bottom_button_frame = ttk.Frame(main_frame)
        bottom_button_frame.grid(row=3, column=0, columnspan=2, pady=(0, 10))
        
        ttk.Button(bottom_button_frame, text="保存日志", command=self.save_log).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(bottom_button_frame, text="清空日志", command=self.clear_log).grid(row=0, column=1, padx=(0, 10))
        ttk.Button(bottom_button_frame, text="退出", command=self.root.quit).grid(row=0, column=2)
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
        file_frame.columnconfigure(1, weight=1)
        progress_frame.columnconfigure(0, weight=1)
    
    def select_main_file(self):
        """选择主JSON文件"""
        filename = filedialog.askopenfilename(
            title="选择主JSON文件",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            self.main_file_var.set(filename)
            # 自动设置jp_cn目录为主文件所在目录下的jp_cn文件夹
            main_dir = os.path.dirname(filename)
            jp_cn_path = os.path.join(main_dir, 'jp_cn')
            if os.path.exists(jp_cn_path):
                self.jp_cn_dir_var.set(jp_cn_path)
    
    def select_jp_cn_dir(self):
        """选择JP-CN目录"""
        dirname = filedialog.askdirectory(
            title="选择JP-CN目录"
        )
        if dirname:
            self.jp_cn_dir_var.set(dirname)
    
    def load_json(self, file_path: str) -> Dict:
        """加载JSON文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.log_message(f"❌ 错误：未找到文件 '{file_path}'")
            return None
        except json.JSONDecodeError as e:
            self.log_message(f"❌ 错误：文件 '{file_path}' 不是有效的JSON格式: {e}")
            return None
        except Exception as e:
            self.log_message(f"❌ 错误：读取文件 '{file_path}' 时发生错误: {e}")
            return None
    
    def log_message(self, message: str):
        """在日志区域添加消息"""
        self.result_text.insert(tk.END, message + "\n")
        self.result_text.see(tk.END)
        self.root.update_idletasks()
    
    def preview_translations(self):
        """预览可以找到的翻译"""
        main_file_path = self.main_file_var.get()
        jp_cn_dir = self.jp_cn_dir_var.get()
        
        if not main_file_path or not jp_cn_dir:
            messagebox.showwarning("警告", "请选择主JSON文件和JP-CN目录")
            return
        
        self.clear_log()
        self.log_message("=" * 80)
        self.log_message("🔍 预览翻译填充")
        self.log_message("=" * 80)
        self.log_message("")
        
        # 加载主文件
        main_data = self.load_json(main_file_path)
        if main_data is None:
            return
        
        # 获取需要填充翻译的键
        empty_keys = {k for k, v in main_data.items() if v == ""}
        if not empty_keys:
            self.log_message("ℹ️ 主文件中没有需要填充的空值")
            return
        
        self.log_message(f"📊 主文件统计:")
        self.log_message(f"   总键数: {len(main_data)}")
        self.log_message(f"   空值键数: {len(empty_keys)}")
        self.log_message("")
        
        # 检查JP-CN目录
        if not os.path.exists(jp_cn_dir):
            self.log_message(f"❌ 错误：未找到JP-CN目录 '{jp_cn_dir}'")
            return
        
        # 预览可找到的翻译
        translations_found = 0
        translation_files = []
        
        for filename in os.listdir(jp_cn_dir):
            if not filename.endswith('.json'):
                continue
                
            file_path = os.path.join(jp_cn_dir, filename)
            translation_data = self.load_json(file_path)
            if translation_data is None:
                continue
            
            file_translations = 0
            for key in empty_keys:
                if key in translation_data and translation_data[key]:
                    file_translations += 1
            
            if file_translations > 0:
                translation_files.append((filename, file_translations))
                translations_found += file_translations
        
        self.log_message(f"📁 JP-CN目录分析:")
        self.log_message(f"   目录路径: {jp_cn_dir}")
        self.log_message(f"   JSON文件数: {len([f for f in os.listdir(jp_cn_dir) if f.endswith('.json')])}")
        self.log_message("")
        
        if translation_files:
            self.log_message(f"✅ 可找到翻译的文件:")
            for filename, count in translation_files:
                self.log_message(f"   📄 {filename}: {count} 个翻译")
            self.log_message("")
            
            self.log_message(f"📈 预览结果:")
            self.log_message(f"   可填充翻译数: {translations_found}")
            self.log_message(f"   剩余空值数: {len(empty_keys) - translations_found}")
            self.log_message(f"   填充率: {translations_found/len(empty_keys)*100:.1f}%")
        else:
            self.log_message("⚠️ 未找到任何可用的翻译")
        
        self.log_message("")
        self.log_message("💡 提示：点击'开始填充'按钮执行实际的翻译填充操作")
    
    def fill_translations(self):
        """执行翻译填充"""
        main_file_path = self.main_file_var.get()
        jp_cn_dir = self.jp_cn_dir_var.get()
        
        if not main_file_path or not jp_cn_dir:
            messagebox.showwarning("警告", "请选择主JSON文件和JP-CN目录")
            return
        
        # 确认操作
        result = messagebox.askyesno(
            "确认操作", 
            f"即将修改文件:\n{main_file_path}\n\n确定要继续吗？"
        )
        if not result:
            return
        
        self.clear_log()
        self.log_message("=" * 80)
        self.log_message("🚀 开始翻译填充")
        self.log_message("=" * 80)
        self.log_message("")
        
        self.status_var.set("正在处理...")
        self.progress_var.set(0)
        
        # 加载主文件
        main_data = self.load_json(main_file_path)
        if main_data is None:
            self.status_var.set("处理失败")
            return
        
        # 获取需要填充翻译的键
        empty_keys = {k for k, v in main_data.items() if v == ""}
        if not empty_keys:
            self.log_message("ℹ️ 主文件中没有需要填充的空值")
            self.status_var.set("无需处理")
            return
        
        self.log_message(f"📊 找到 {len(empty_keys)} 个需要填充翻译的键")
        self.log_message("")
        
        # 检查JP-CN目录
        if not os.path.exists(jp_cn_dir):
            self.log_message(f"❌ 错误：未找到JP-CN目录 '{jp_cn_dir}'")
            self.status_var.set("处理失败")
            return
        
        # 获取所有JSON文件
        json_files = [f for f in os.listdir(jp_cn_dir) if f.endswith('.json')]
        total_files = len(json_files)
        
        if total_files == 0:
            self.log_message("❌ 错误：JP-CN目录中没有JSON文件")
            self.status_var.set("处理失败")
            return
        
        # 处理翻译文件
        translations_found = 0
        processed_files = 0
        
        for filename in json_files:
            processed_files += 1
            progress = (processed_files / total_files) * 100
            self.progress_var.set(progress)
            self.status_var.set(f"处理文件 {processed_files}/{total_files}")
            
            file_path = os.path.join(jp_cn_dir, filename)
            translation_data = self.load_json(file_path)
            if translation_data is None:
                continue
            
            file_translations = 0
            
            # 查找匹配的键并填充翻译
            for key in list(empty_keys):  # 使用list创建副本以便在迭代时修改
                if key in translation_data and translation_data[key]:
                    main_data[key] = translation_data[key]
                    empty_keys.remove(key)
                    translations_found += 1
                    file_translations += 1
                    self.log_message(f"✅ 找到翻译: {key} -> {translation_data[key]}")
            
            if file_translations > 0:
                self.log_message(f"📄 文件 {filename}: 填充了 {file_translations} 个翻译")
                self.log_message("")
            
            # 如果所有空键都已填充，可以提前退出
            if not empty_keys:
                self.log_message("🎉 所有空值都已填充完成！")
                break
            
            self.root.update_idletasks()
        
        # 保存更新后的主文件
        try:
            with open(main_file_path, 'w', encoding='utf-8', newline='\n') as file:
                json.dump(main_data, file, ensure_ascii=False, indent=2)
            self.log_message("💾 主文件已保存")
        except Exception as e:
            self.log_message(f"❌ 保存文件时发生错误: {e}")
            self.status_var.set("保存失败")
            return
        
        # 显示最终结果
        self.log_message("")
        self.log_message("=" * 80)
        self.log_message("📈 最终统计")
        self.log_message("=" * 80)
        self.log_message(f"✅ 已填充翻译数: {translations_found}")
        if empty_keys:
            self.log_message(f"⚠️ 仍有空值数: {len(empty_keys)}")
        else:
            self.log_message("🎉 所有空值都已填充！")
        
        self.progress_var.set(100)
        self.status_var.set("处理完成")
        
        # 显示完成消息
        messagebox.showinfo(
            "完成", 
            f"翻译填充完成！\n\n已填充: {translations_found} 个翻译\n剩余空值: {len(empty_keys)} 个"
        )
    
    def save_log(self):
        """保存日志到文件"""
        if not self.result_text.get(1.0, tk.END).strip():
            messagebox.showwarning("警告", "没有日志可保存")
            return
        
        filename = filedialog.asksaveasfilename(
            title="保存操作日志",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8', newline='\n') as f:
                    f.write(self.result_text.get(1.0, tk.END))
                messagebox.showinfo("成功", f"日志已保存到: {filename}")
            except Exception as e:
                messagebox.showerror("错误", f"保存文件时发生错误:\n{e}")
    
    def clear_log(self):
        """清空日志"""
        self.result_text.delete(1.0, tk.END)
        self.progress_var.set(0)
        self.status_var.set("就绪")


def main():
    """主函数"""
    root = tk.Tk()
    app = FullTransGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
