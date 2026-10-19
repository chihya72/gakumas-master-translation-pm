"""Compare values of shared JSON keys between Git commits (or a working file)."""

import argparse
import json
from pathlib import Path
import subprocess
import sys


DEFAULT_FILE = r"pretranslate_todo\localization\localization_full.json"


def git(root, *arguments):
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError("Git 执行失败：{}".format(detail))
    return result.stdout


def resolve_commit(root, revision):
    return git(
        root, "rev-parse", "--verify", "--end-of-options", revision + "^{commit}"
    ).decode("ascii").strip()


def load_object(content, label):
    try:
        data = json.loads(content.decode("utf-8-sig"))
    except (UnicodeError, ValueError) as error:
        raise ValueError("{} 不是有效的 UTF-8 JSON：{}".format(label, error))
    if not isinstance(data, dict):
        raise ValueError("{} 的 JSON 顶层必须是对象（键值表）".format(label))
    return data


def changed_values(old, new):
    """Object key order is irrelevant; JSON types and array order are preserved."""
    changes = []
    for key in sorted(old.keys() & new.keys()):
        before = json.dumps(old[key], ensure_ascii=False, sort_keys=True)
        after = json.dumps(new[key], ensure_ascii=False, sort_keys=True)
        if before != after:
            changes.append({"key": key, "old": old[key], "new": new[key]})
    return changes


def compare(root, file_name, base, target=None, working_tree=False):
    root = Path(git(root, "rev-parse", "--show-toplevel").decode("utf-8").strip())
    file_path = Path(file_name)
    if not file_path.is_absolute():
        file_path = root / file_path
    file_path = file_path.resolve()
    try:
        relative = file_path.relative_to(root.resolve())
    except ValueError:
        raise ValueError("文件必须位于仓库内：{}".format(file_path))
    # Git object names require forward slashes even on Windows.
    git_path = relative.as_posix()
    base_sha = resolve_commit(root, base)
    old = load_object(git(root, "show", base_sha + ":" + git_path), base)
    if working_tree:
        target_sha = None
        target_label = "working-tree"
        new = load_object(file_path.read_bytes(), str(file_path))
    else:
        target_label = target or "HEAD"
        target_sha = resolve_commit(root, target_label)
        new = load_object(
            git(root, "show", target_sha + ":" + git_path), target_label
        )
    changes = changed_values(old, new)
    return {
        "file": str(relative),
        "base": {"ref": base, "commit": base_sha},
        "target": {"ref": target_label, "commit": target_sha},
        "changed_count": len(changes),
        "changes": changes,
    }


def make_parser():
    parser = argparse.ArgumentParser(
        description="比较同一 JSON 文件在两个版本中，同键但不同值的条目。新增和删除的键不列出。"
    )
    parser.add_argument("commit", help="要比较的历史 commit、标签或分支")
    parser.add_argument("--file", default=DEFAULT_FILE, help="文件绝对路径或相对仓库路径")
    parser.add_argument(
        "--repo", type=Path, default=Path(__file__).resolve().parent.parent,
        help="仓库目录；默认使用工具所在仓库，与终端当前目录无关",
    )
    targets = parser.add_mutually_exclusive_group()
    targets.add_argument("--target", help="目标 commit，默认为本地 HEAD（不自动拉取远端）")
    targets.add_argument("--working-tree", action="store_true", help="改为比较当前磁盘文件，包含未提交修改")
    parser.add_argument("--output", type=Path, help="另存完整 JSON 报告；父目录必须已存在")
    return parser


def main(argv=None):
    args = make_parser().parse_args(argv)
    try:
        if args.output:
            source = Path(args.file)
            if not source.is_absolute():
                repo_root = Path(git(args.repo, "rev-parse", "--show-toplevel").decode("utf-8").strip())
                source = repo_root / source
            if args.output.resolve() == source.resolve():
                raise ValueError("报告路径不能覆盖被比较的 JSON 文件")
        report = compare(args.repo, args.file, args.commit, args.target, args.working_tree)
        if args.output:
            args.output.write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        print("文件：{}".format(report["file"]))
        print("旧版本：{} ({})".format(report["base"]["ref"], report["base"]["commit"]))
        print("新版本：{} ({})".format(
            report["target"]["ref"], report["target"]["commit"] or "当前磁盘文件"
        ))
        print("同键不同值：{} 条".format(report["changed_count"]))
        for entry in report["changes"]:
            print("\n[{}]".format(entry["key"]))
            print("  旧：{}".format(json.dumps(entry["old"], ensure_ascii=False)))
            print("  新：{}".format(json.dumps(entry["new"], ensure_ascii=False)))
        if args.output:
            print("\n报告已保存：{}".format(args.output.resolve()))
    except (OSError, ValueError) as error:
        print("比较失败：{}".format(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
