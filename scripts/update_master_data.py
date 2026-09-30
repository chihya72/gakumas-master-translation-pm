"""Pull this repository's Actions YAML, then run the existing local converter."""
from pathlib import Path
import subprocess
import sys


def update(root):
    print('Pulling this repository, including gakumasu-diff\\orig...', flush=True)
    result = subprocess.run(['git', 'pull', '--ff-only'], cwd=root)
    if result.returncode != 0:
        raise RuntimeError('Git pull failed; JSON conversion was not started.')
    print('Running gakumasu_diff_to_json.py...', flush=True)
    result = subprocess.run(
        [sys.executable, str(root / 'scripts' / 'gakumasu_diff_to_json.py'), '--strict'],
        cwd=root,
    )
    if result.returncode != 0:
        raise RuntimeError('Local JSON conversion failed; review the converter output above.')


def main():
    try:
        update(Path(__file__).resolve().parent.parent)
    except (OSError, RuntimeError) as error:
        print(f'Master data update failed: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
