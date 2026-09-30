"""Local Windows UI for recovering and explicitly publishing a campus credential."""
import ipaddress
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import threading
import time
import tkinter as tk
from tkinter import filedialog, ttk
import urllib.error

import read_android_account as account

SECRET = 'CAMPUS_REFRESH_TOKEN'
DEFAULT_REPO = 'chihya72/gakumas-master-translation-pm'


class ToolError(Exception):
    """Only deliberately redacted, user-facing messages belong here."""


def endpoint(host, port):
    try:
        address = ipaddress.ip_address(host.strip().strip('[]'))
        number = int(port)
        if not 1 <= number <= 65535:
            raise ValueError
    except ValueError:
        raise ToolError('请输入有效的模拟器 IP 和 1–65535 范围内的 ADB 端口。') from None
    return f'[{address}]:{number}' if address.version == 6 else f'{address}:{number}'


def repository(value):
    value = value.strip()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+', value):
        raise ToolError('GitHub 仓库请填写 owner/repo，例如 ' + DEFAULT_REPO + '。')
    return value


def run_native(arguments, *, data=None, timeout=45, failure='本机命令执行失败。'):
    # Pipe credentials through stdin. Never use a shell, console, or exception
    # carrying command output; subprocess error text may contain private data.
    try:
        result = subprocess.run(arguments, input=data, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=timeout,
                                creationflags=subprocess.CREATE_NO_WINDOW)
    except subprocess.TimeoutExpired:
        raise ToolError(failure + ' 请求超时；请检查网络后重试。') from None
    except OSError:
        raise ToolError(failure + ' 请检查程序路径。') from None
    if result.returncode != 0:
        raise ToolError(failure) from None
    return result.stdout


def find_adb():
    candidates = [shutil.which('adb'),
                  str(Path(os.environ.get('ProgramFiles', r'C:\Program Files')) /
                      'Netease' / 'MuMu Player 12' / 'shell' / 'adb.exe'),
                  str(Path(os.environ.get('LOCALAPPDATA', '')) / 'Android' / 'Sdk' /
                      'platform-tools' / 'adb.exe')]
    return next((path for path in candidates if path and Path(path).is_file()), '')


def find_gh():
    path = shutil.which('gh')
    if not path:
        candidate = Path(os.environ.get('ProgramFiles', r'C:\Program Files')) / 'GitHub CLI' / 'gh.exe'
        path = str(candidate) if candidate.is_file() else None
    if not path:
        raise ToolError('未找到 GitHub CLI。请安装 gh，并在 pwsh 中执行 gh auth login。')
    return path


def connect_device(adb, device, progress):
    if not Path(adb).is_file() or Path(adb).suffix.lower() != '.exe':
        raise ToolError('未找到 adb.exe，请选择模拟器提供的 ADB 程序。')
    progress('正在连接模拟器…')
    run_native([adb, 'start-server'], failure='ADB 服务启动失败。')
    run_native([adb, 'connect', device], failure='ADB 连接失败，请检查 IP 和端口。')
    run_native([adb, '-s', device, 'get-state'], timeout=15,
               failure='设备不可用。请开启模拟器 ADB 调试，并确认该端口属于当前实例。')
    if account.device_command(device, '/system/bin/id -u').strip() != b'0':
        progress('正在请求 root ADB 权限…')
        run_native([adb, '-s', device, 'root'],
                   failure='无法开启 root ADB。请在模拟器设置中开启 root 权限。')
        # adb root restarts adbd only. Reconnect without touching the game.
        time.sleep(1)
        run_native([adb, 'connect', device], failure='root ADB 重连失败。')
        run_native([adb, '-s', device, 'wait-for-device'], timeout=20,
                   failure='等待 root ADB 超时。')
        if account.device_command(device, '/system/bin/id -u').strip() != b'0':
            raise ToolError('需要 root ADB 才能读取游戏私有账号文件；请在模拟器中开启 root。')


def recover(adb, device, progress=lambda _: None):
    try:
        connect_device(adb, device, progress)
        progress('正在读取账号并解密 Android Keystore…')
        names = account.auth_files(device)
        if len(names) != 1:
            raise ToolError('未找到唯一的游戏账号文件。请确认安装了学园偶像大师并已登录。')
        raw = account.read_account(device, names[0])
        if b'ENCRYPTED:' in raw:
            token = account.decrypt_on_device(device, names[0])
        else:
            token = account.extract_token(raw)
        progress('正在验证 Firebase 游戏凭据…')
        token = account.validate(token)
        if not isinstance(token, str) or not token or '\n' in token or '\r' in token:
            raise ToolError('服务器返回了不支持的凭据格式。')
        # Preserve the previous encrypted credential if any earlier step fails.
        cache = Path(__file__).parent / 'cache'
        cache.mkdir(exist_ok=True)
        encrypted = account.protect(token)
        pending = cache / 'firebase-refresh-token.dpapi.pending'
        pending.write_bytes(encrypted)
        pending.replace(cache / 'firebase-refresh-token.dpapi')
        return token
    except ToolError:
        raise
    except RuntimeError as error:
        if str(error).startswith('Firebase validation rejected; HTTP '):
            raise ToolError('Firebase 拒绝了账号凭据。请在游戏中重新登录，再读取；旧 Secret 尚未修改。') from None
        raise ToolError('读取或解密失败。请确认 root ADB、游戏已登录，并使用原登录模拟器。账号格式变化时需更新解密程序。') from None
    except (TimeoutError, ConnectionError, OSError, urllib.error.URLError):
        raise ToolError('连接或网络请求失败，请检查模拟器 ADB 和 Google 服务网络。') from None
    except Exception:
        raise ToolError('账号解析失败；响应内容已隐藏。请检查客户端版本和登录状态。') from None


def publish(token, repo, progress=lambda _: None):
    repo = repository(repo)
    gh = find_gh()
    progress('正在检查 GitHub 登录状态…')
    run_native([gh, 'auth', 'status', '--hostname', 'github.com'],
               failure='GitHub CLI 未登录或登录失效。请在 pwsh 中执行 gh auth login。')
    progress(f'正在更新 {repo} 的 Actions Secret…')
    # gh encrypts with the repository public key before upload. Noninteractive
    # stdin avoids --body (which exposes the credential in the process list).
    run_native([gh, 'secret', 'set', SECRET, '--app', 'actions', '--repo', repo],
               data=token.encode('utf-8'), timeout=60,
               failure='Secret 更新未获成功确认。请检查网络及仓库 Secrets 写入权限后重试。')
    return repo


class TokenWindow:
    def __init__(self, root):
        self.root = root
        self.token = None
        self.busy = False
        self.events = queue.Queue()
        root.title('Campus · 账号凭据更新')
        root.geometry('740x520')
        root.minsize(690, 490)
        style = ttk.Style(root)
        style.theme_use('vista' if 'vista' in style.theme_names() else 'clam')
        style.configure('TLabel', font=('Microsoft YaHei UI', 10))
        style.configure('TButton', font=('Microsoft YaHei UI', 10), padding=(12, 7))
        frame = ttk.Frame(root, padding=24)
        frame.pack(fill='both', expand=True)
        frame.columnconfigure(1, weight=1)
        ttk.Label(frame, text='重新获取游戏凭据', font=('Microsoft YaHei UI', 18, 'bold')).grid(
            row=0, column=0, columnspan=3, sticky='w', pady=(0, 8))
        ttk.Label(frame, text='先自行打开游戏并进入大厅，再读取。需要模拟器 root 和 ADB 调试。').grid(
            row=1, column=0, columnspan=3, sticky='w', pady=(0, 20))
        self.host = tk.StringVar(value='127.0.0.1')
        self.port = tk.StringVar(value='16448')
        self.adb = tk.StringVar(value=find_adb())
        self.repo = tk.StringVar(value=DEFAULT_REPO)
        self.inputs = []
        for row, label, variable in [(2, '模拟器 IP', self.host), (3, 'ADB 端口', self.port),
                                     (4, 'ADB 程序', self.adb), (5, 'GitHub 仓库', self.repo)]:
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky='w', padx=(0, 16), pady=7)
            entry = ttk.Entry(frame, textvariable=variable)
            entry.grid(row=row, column=1, columnspan=1 if row == 4 else 2, sticky='ew', pady=7)
            self.inputs.append(entry)
        self.browse = ttk.Button(frame, text='选择…', command=self.choose_adb)
        self.browse.grid(row=4, column=2, padx=(8, 0))
        ttk.Label(frame, text=f'更新目标：仓库级 Actions Secret · {SECRET}', foreground='#475569').grid(
            row=6, column=0, columnspan=3, sticky='w', pady=(8, 12))
        buttons = ttk.Frame(frame)
        buttons.grid(row=7, column=0, columnspan=3, sticky='w')
        self.read_button = ttk.Button(buttons, text='1  读取并验证', command=self.read)
        self.read_button.pack(side='left')
        self.upload_button = ttk.Button(buttons, text='2  上传 / 更新 Secret', command=self.upload, state='disabled')
        self.upload_button.pack(side='left', padx=(12, 0))
        self.status = tk.StringVar(value='等待读取。令牌不会显示在界面或日志中。')
        ttk.Label(frame, textvariable=self.status, wraplength=640, foreground='#164e63').grid(
            row=8, column=0, columnspan=3, sticky='w', pady=(20, 8))
        self.spinner = ttk.Progressbar(frame, mode='indeterminate')
        self.spinner.grid(row=9, column=0, columnspan=3, sticky='ew', pady=(0, 14))
        ttk.Label(frame, text='凭据仅在内存和当前 Windows 用户的加密缓存中保存。\n上传后，Actions 下次运行会使用新凭据；本工具不操作游戏。',
                  foreground='#64748b', wraplength=640).grid(row=10, column=0, columnspan=3, sticky='w')
        for variable in (self.host, self.port, self.adb, self.repo):
            variable.trace_add('write', self.invalidate)
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.report_callback_exception = lambda *_: self.status.set('界面操作失败；错误详情已隐藏，请重新打开工具。')
        root.after(100, self.poll)

    def choose_adb(self):
        path = filedialog.askopenfilename(title='选择模拟器的 adb.exe', filetypes=[('ADB', 'adb.exe')])
        if path:
            self.adb.set(path)

    def invalidate(self, *_):
        self.token = None
        self.upload_button.configure(state='disabled')
        if not self.busy:
            self.status.set('参数已修改，请重新读取并验证。')

    def set_busy(self, busy):
        self.busy = busy
        for control in self.inputs + [self.browse, self.read_button]:
            control.configure(state='disabled' if busy else 'normal')
        self.upload_button.configure(state='normal' if not busy and self.token else 'disabled')
        if busy:
            self.spinner.start(12)
        else:
            self.spinner.stop()

    def start(self, kind, action):
        self.set_busy(True)

        def work():
            try:
                result = action(lambda value: self.events.put(('progress', value)))
                self.events.put((kind, result))
            except ToolError as error:
                self.events.put(('error', str(error)))
            except Exception:
                self.events.put(('error', '操作失败；错误详情已隐藏。请检查连接与程序依赖。'))

        threading.Thread(target=work, daemon=True).start()

    def read(self):
        if self.busy:
            return
        self.invalidate()
        try:
            device = endpoint(self.host.get(), self.port.get())
            repository(self.repo.get())
        except ToolError as error:
            self.status.set(str(error))
            return
        adb = self.adb.get().strip()
        self.start('recovered', lambda progress: recover(adb, device, progress))

    def upload(self):
        if self.busy or not self.token:
            return
        token, repo = self.token, self.repo.get()
        self.start('published', lambda progress: publish(token, repo, progress))

    def poll(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == 'progress':
                    self.status.set(value)
                else:
                    if kind == 'recovered':
                        self.token = value
                        self.status.set('读取及 Firebase 验证成功。请核对仓库，再点击“上传 / 更新 Secret”。')
                    elif kind == 'published':
                        self.token = None
                        self.status.set(f'已更新 {value} 的 {SECRET}。Actions 下次运行将使用新凭据。')
                    else:
                        # Read failures have no token; upload failures may be retried.
                        self.status.set(value)
                    self.set_busy(False)
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    def close(self):
        if self.busy:
            self.status.set('正在处理，请等待本次操作完成后关闭窗口。设备临时程序会在读取结束时清理。')
            return
        self.token = None
        self.root.destroy()


def main():
    if os.name != 'nt':
        raise SystemExit('This credential tool requires Windows.')
    root = tk.Tk()
    TokenWindow(root)
    root.mainloop()


if __name__ == '__main__':
    main()
