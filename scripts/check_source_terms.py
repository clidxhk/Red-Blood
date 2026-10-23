#!/usr/bin/env python3
"""
Source-term residue checker for the Red-Blood worldbuilding repository.

取材裁定为「原书自设、须拆译或舍弃」的专名，不得原样残留于正式内容。
本脚本从各取材记录的「## 搬运禁词」节收集词条，逐行扫描指定范围的
Markdown 文件，报告逐字命中。命中只代表疑似残留，须人工复核；
脚本只读，不修改任何文件。

Usage:
    python scripts/check_source_terms.py                # 扫描 世界/ 角色/ 故事/
    python scripts/check_source_terms.py 世界/器物      # 只扫指定文件或目录
    python scripts/check_source_terms.py --records 素材/牧神记/取材记录.md
    python scripts/check_source_terms.py --terms 霸体,灵胎神藏
"""

import sys
import io

# Fix Windows console encoding for Chinese output
if sys.platform == "win32" and __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Default formal-content scan roots; 素材/ 与 场景/ 不进默认范围
DEFAULT_SCAN_DIRS = ("世界", "角色", "故事")

# 取材记录中承载禁词清单的节标题（## 之后的部分）
SECTION_HEADING = "搬运禁词"

LIST_MARKER_RE = re.compile(r"^[-*+]\s+|^\d+[.、)]\s*")


def parse_record_terms(path: Path) -> list[str]:
    """从一份取材记录的「## 搬运禁词」节收集词条，保持出现顺序并去重。"""
    terms: list[str] = []
    in_section = False
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if line.startswith("## "):
            in_section = line[3:].strip() == SECTION_HEADING
            continue
        if not in_section or not line:
            continue
        if not LIST_MARKER_RE.match(line):
            print(f"[WARN] {path}: 搬运禁词节须逐行一词（列表项），忽略：{line}", file=sys.stderr)
            continue
        terms.append(LIST_MARKER_RE.sub("", line).strip())
    return list(dict.fromkeys(terms))


def default_records(root: Path) -> list[Path]:
    return sorted(root.glob("素材/*/取材记录.md"))


def collect_terms(root: Path, records: list[Path]) -> list[str]:
    """汇总各取材记录的禁词；记录缺失时按错误处理。禁词是数据，不限定在库内。"""
    terms: list[str] = []
    for record in records:
        if not record.is_file():
            raise ValueError(f"取材记录不存在：{record}")
        terms.extend(parse_record_terms(record))
    return list(dict.fromkeys(terms))


def scan_targets(root: Path, requested: list[str] | None) -> list[Path]:
    """收集待扫描的 Markdown 文件；取材域自身不进扫描范围。"""
    chosen: list[Path] = []
    if requested:
        for name in requested:
            path = (root / name).resolve()
            if not path.is_relative_to(root.resolve()) or not path.exists():
                raise ValueError(f"检查路径不存在或越出项目：{name}")
            chosen.extend(sorted(path.rglob("*.md")) if path.is_dir() else [path])
    else:
        for dirname in DEFAULT_SCAN_DIRS:
            directory = root / dirname
            if directory.is_dir():
                chosen.extend(sorted(directory.rglob("*.md")))

    result: list[Path] = []
    for path in chosen:
        if not path.is_file():
            continue
        try:
            rel = path.resolve().relative_to(root.resolve())
        except ValueError:
            continue
        if rel.parts and rel.parts[0] == "素材":
            continue
        result.append(path)
    return result


def scan_file(path: Path, terms: list[str]) -> list[tuple[int, str, str]]:
    """逐字子串匹配，返回 (行号, 词条, 行内容)；命中须人工复核。"""
    hits: list[tuple[int, str, str]] = []
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"[WARN] 无法读取 {path}：{exc}", file=sys.stderr)
        return hits
    for lineno, line in enumerate(text.splitlines(), 1):
        for term in terms:
            if term in line:
                hits.append((lineno, term, line.strip()))
    return hits


def main():
    parser = argparse.ArgumentParser(
        description="扫描正式内容中残留的取材源书自设专名（搬运禁词）。",
    )
    parser.add_argument(
        "targets", nargs="*", metavar="PATH",
        help="待扫描的文件或目录，默认扫描 世界/ 角色/ 故事/",
    )
    parser.add_argument(
        "--records", nargs="*", metavar="PATH",
        help="取材记录路径，默认取 素材/*/取材记录.md",
    )
    parser.add_argument(
        "--terms", default="",
        help="追加禁词（逗号分隔），与取材记录禁词合并使用",
    )
    args = parser.parse_args()

    try:
        records = [ROOT / name for name in args.records] if args.records else default_records(ROOT)
        terms = collect_terms(ROOT, records)
        if args.terms:
            terms = list(dict.fromkeys(
                terms + [t.strip() for t in args.terms.split(",") if t.strip()]
            ))
        targets = scan_targets(ROOT, args.targets)
    except (OSError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2

    if not targets:
        print("[ERROR] 所选范围没有可扫描的 Markdown 文件", file=sys.stderr)
        return 2
    if not terms:
        print(
            "[WARN] 未收集到任何搬运禁词；请在取材记录的「## 搬运禁词」节逐行登记，或用 --terms 指定。",
            file=sys.stderr,
        )
        return 0

    total = 0
    hit_files = 0
    for path in targets:
        hits = scan_file(path, terms)
        if not hits:
            continue
        hit_files += 1
        total += len(hits)
        rel = path.resolve().relative_to(ROOT.resolve())
        for lineno, term, line in hits:
            shown = line if len(line) <= 60 else line[:57] + "……"
            print(f"{rel.as_posix()}:{lineno} [{term}] {shown}")

    print(
        f"已扫描 {len(targets)} 个文件；禁词 {len(terms)} 条"
        f"（来自 {len(records)} 份取材记录）；命中 {total} 处，涉及 {hit_files} 个文件。"
    )
    if total:
        print("命中仅为疑似残留，请人工复核后裁定改写或豁免。")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
