"""Copy remote Actions YAML into local orig, then run the existing JSON converter."""
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile


def remote_repository(root):
    result = subprocess.run(['git', 'remote', 'get-url', 'origin'], cwd=root,
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError('Cannot read this repository origin.')
    match = re.fullmatch(r'(?:https://github\.com/|git@github\.com:)([\w.-]+/[\w.-]+?)(?:\.git)?/?',
                         result.stdout.strip())
    if not match:
        raise RuntimeError('Origin must be a GitHub repository URL.')
    return match[1]


def copy_yaml_snapshot(archive_path, destination, staging):
    """Read the complete snapshot before replacing any local YAML files."""
    with zipfile.ZipFile(archive_path) as archive:
        members = archive.infolist()
        roots = {member.filename.split('/', 1)[0] for member in members}
        if len(roots) != 1:
            raise RuntimeError('Unexpected repository archive layout.')
        prefix = roots.pop() + '/gakumasu-diff/'
        tables = {}
        version = None
        for member in members:
            if member.is_dir() or not member.filename.startswith(prefix):
                continue
            relative = member.filename[len(prefix):]
            if relative == 'master-version.txt':
                version = archive.read(member)
            elif relative.startswith('orig/'):
                name = relative[len('orig/'):]
                if not name.endswith('.yaml'):
                    continue
                if '/' in name or '\\' in name or ':' in name or name in tables:
                    raise RuntimeError('Unexpected YAML file path in repository archive.')
                target = staging / name
                with archive.open(member) as source, target.open('wb') as output:
                    shutil.copyfileobj(source, output)
                tables[name] = target
        if not tables:
            raise RuntimeError('Remote main has no orig YAML. Push the submodule migration and new workflow first.')
    # Only game YAML and its version marker are copied. No application or
    # translation source files are checked out, merged, or overwritten.
    for name, source in tables.items():
        shutil.copyfile(source, destination / name)
    for old in destination.glob('*.yaml'):
        if old.name not in tables:
            old.unlink()
    if version is not None:
        (destination.parent / 'master-version.txt').write_bytes(version)
    print(f'Copied {len(tables)} YAML tables into {destination}.', flush=True)
    return len(tables)


def update(root):
    destination = root / 'gakumasu-diff' / 'orig'
    if not destination.is_dir():
        raise RuntimeError('Local gakumasu-diff\\orig directory is missing.')
    repository = remote_repository(root)
    cache = root / 'tools' / 'campus' / 'cache'
    cache.mkdir(parents=True, exist_ok=True)
    # codeload serves one commit snapshot, avoiding inconsistent per-file reads
    # if Actions pushes while this download is in progress.
    url = f'https://codeload.github.com/{repository}/zip/refs/heads/main'
    print(f'Downloading Actions YAML from {repository}@main...', flush=True)
    with tempfile.TemporaryDirectory(prefix='yaml-update-', dir=cache) as folder:
        staging = Path(folder)
        archive_path = staging / 'repository.zip'
        request = urllib.request.Request(url, headers={'User-Agent': 'gakumas-master-data-updater'})
        with urllib.request.urlopen(request, timeout=60) as response, archive_path.open('wb') as output:
            shutil.copyfileobj(response, output)
        copy_yaml_snapshot(archive_path, destination, staging)
    print('Running gakumasu_diff_to_json.py...', flush=True)
    result = subprocess.run([sys.executable, str(root / 'scripts' / 'gakumasu_diff_to_json.py'), '--strict'], cwd=root)
    if result.returncode != 0:
        raise RuntimeError('Local JSON conversion failed; review the converter output above.')


def main():
    try:
        update(Path(__file__).resolve().parent.parent)
    except (OSError, RuntimeError, urllib.error.URLError, zipfile.BadZipFile) as error:
        print(f'Master data update failed: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
