"""Build the master descriptor from read-only copies of an installed Android APK."""

import json
from pathlib import Path
import re
import shutil
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import read_android_account as account
from decode_client_metadata import decode


def installed_apks(device):
    app_root = '/data/app'
    package_dir = re.compile(re.escape(account.PACKAGE) + r'-[\w=\-]+')
    parents = [app_root]
    folders = []
    for parent in parents:
        for name, _ in account.directory_entries(device, parent):
            if package_dir.fullmatch(name):
                folders.append(f'{parent}/{name}')
            elif parent == app_root and re.fullmatch(r'~~[\w=\-]+', name):
                parents.append(f'{parent}/{name}')
    if len(folders) != 1:
        raise ValueError('找不到唯一的已安装游戏 APK。请确认模拟器安装了当前版本。')
    folder = folders[0]
    names = [name for name, _ in account.directory_entries(device, folder)
             if re.fullmatch(r'[\w.\-]+\.apk', name)]
    names.sort(key=lambda name: (name != 'base.apk', 'arm64_v8a' not in name, name))
    return [f'{folder}/{name}' for name in names]


def extract_apk_inputs(apks, directory, pull):
    metadata = directory / 'global-metadata.dat'
    native = directory / 'libil2cpp.so'
    for remote in apks:
        local = directory / remote.rsplit('/', 1)[-1]
        pull(remote, local)
        with ZipFile(local) as apk:
            names = apk.namelist()
            if not metadata.exists():
                entry = next((name for name in names if name.endswith('/global-metadata.dat')), None)
                if entry:
                    metadata.write_bytes(apk.read(entry))
            if not native.exists():
                libraries = sorted(name for name in names if re.fullmatch(r'lib/[^/]+/libil2cpp\.so', name))
                if libraries:
                    entry = min(libraries, key=lambda name: not name.startswith('lib/arm64-v8a/'))
                    native.write_bytes(apk.read(entry))
        local.unlink()
        if metadata.exists() and native.exists():
            return metadata, native
    raise ValueError('已安装的 APK 缺少 IL2CPP 库或 metadata。请确认游戏安装完整。')


def find_dumper():
    cache = Path(__file__).parent / 'cache'
    on_path = shutil.which('Il2CppDumper.exe')
    candidates = [cache / 'schema-update' / 'il2cppdumper' / 'Il2CppDumper.exe',
                  cache / 'il2cppdumper' / 'Il2CppDumper.exe']
    if on_path:
        candidates.insert(0, Path(on_path))
    return next((path for path in candidates if path.is_file()), None)


def build_schema(adb, device, run_native, progress):
    try:
        from schema_from_dump import encode_descriptor, generate
    except ModuleNotFoundError as error:
        if error.name not in ('google', 'google.protobuf'):
            raise
        raise ValueError('缺少 Python protobuf，请在当前 Python 环境安装 protobuf。') from None
    dumper = find_dumper()
    if dumper is None:
        raise ValueError('找不到 Il2CppDumper.exe。请将 Windows 版放入 tools/campus/cache/il2cppdumper 或加入 PATH。')
    progress('正在从模拟器读取游戏 APK…')
    apks = installed_apks(device)

    def pull(remote, local):
        run_native([adb, '-s', device, 'pull', remote, str(local)], timeout=180,
                   failure='无法读取已安装的游戏 APK。请检查模拟器连接和 root 权限。')

    with TemporaryDirectory(prefix='campus-schema-') as folder:
        directory = Path(folder)
        metadata, native = extract_apk_inputs(apks, directory, pull)
        decoded = directory / 'global-metadata-dec.dat'
        decoded.write_bytes(decode(metadata, native))
        progress('正在生成并校验 Master Data Schema…')
        executable = directory / dumper.name
        shutil.copyfile(dumper, executable)
        (directory / 'config.json').write_text(json.dumps({
            'RequireAnyKey': False,
            'GenerateDummyDll': False,
            'GenerateStruct': False,
        }), encoding='utf-8')
        run_native([str(executable), str(native), str(decoded), str(directory)], timeout=240,
                   failure='Il2CppDumper 执行失败。请检查客户端版本和工具兼容性。')
        dump = directory / 'dump.cs'
        if not dump.is_file():
            raise ValueError('Il2CppDumper 未生成 dump.cs。请检查客户端版本和工具兼容性。')
        try:
            descriptor, _, _, _ = generate(dump.read_text(encoding='utf-8-sig'))
        except (ValueError, TypeError):
            raise ValueError('客户端的 Master Data Schema 无法通过校验。') from None
        return ('\n'.join(encode_descriptor(descriptor)) + '\n').encode('ascii')
