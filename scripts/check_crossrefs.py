#!/usr/bin/env python3
"""
Cross-reference checker for the Red-Blood worldbuilding repository.

Scans all content .md files and checks: for every existing .md filename (sans extension),
when it appears as plain text inside another .md file's body, is it wrapped in [[ ]]?
Reports bare mentions — i.e. filenames that appear in text but aren't cross-referenced.

Usage:
    python scripts/check_crossrefs.py                    # check all content files
    python scripts/check_crossrefs.py --verbose          # show per-file breakdown
    python scripts/check_crossrefs.py --min-length 3     # only flag names >= 3 chars
    python scripts/check_crossrefs.py --output report.csv
    python scripts/check_crossrefs.py --skip-self        # don't flag self-mentions
"""

import sys
import io

# Fix Windows console encoding for Chinese output
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import argparse
import csv
import os
import re
from collections import defaultdict
from pathlib import Path


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent

# Directories to exclude from scanning entirely
SKIP_DIRS = {
    ".claude", ".codex", ".gemini", ".memory", ".obsidian",
    "scripts", "__pycache__", ".git",
}

# Filenames (exact) to exclude from the target-name set
SKIP_FILES = {
    "AGENTS.md", "CLAUDE.md", "MEMORY.md", "README.md",
}

# Filename prefixes to exclude from the target-name set
SKIP_PREFIXES = ("feedback_",)

# Subagent config filenames to skip
SKIP_SUBAGENTS = {
    "character-actor.md", "character-reviewer.md", "crosslink-checker.md",
    "research-agent.md", "style-writer.md", "teahouse-chronicler.md",
    "tone-checker.md", "worldbuilding-consistency.md",
}

# Minimum character length for a filename stem to be checked (avoids noise
# from very short names that match common Chinese bigrams).
DEFAULT_MIN_LENGTH = 2

# Regex to find all [[...]] wrapped references
CROSSREF_RE = re.compile(r"\[\[(.+?)\]\]")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def escape_regex(name: str) -> str:
    """Escape regex-special characters in a filename stem."""
    return re.escape(name)


def should_skip_dir(parts: tuple[str, ...]) -> bool:
    """Return True if any part of the path is a skip directory."""
    return bool(set(parts) & SKIP_DIRS)


def should_skip_target(name: str) -> bool:
    """Return True if this filename should not be a cross-reference target."""
    if name in SKIP_FILES or name in SKIP_SUBAGENTS:
        return True
    if name.startswith(SKIP_PREFIXES):
        return True
    return False


def collect_targets(root: Path, min_length: int) -> dict[str, Path]:
    """
    Walk the repo and return {stem: full_path} for every content .md file.

    The stem is the filename without the .md extension.
    """
    targets: dict[str, Path] = {}
    for md_path in root.rglob("*.md"):
        rel = md_path.relative_to(root)
        parts = rel.parts
        if should_skip_dir(parts):
            continue
        name = md_path.name
        if should_skip_target(name):
            continue
        stem = md_path.stem  # filename without .md
        if len(stem) < min_length:
            continue
        # If two files share the same stem (name collision across dirs),
        # keep the first one; warn about duplicates.
        if stem in targets:
            print(f"[WARN] Duplicate stem '{stem}': {targets[stem]} vs {md_path}", file=sys.stderr)
            continue
        targets[stem] = md_path
    return targets


def find_bare_mentions(
    text: str,
    stem: str,
    escaped_stem: str,
) -> list[int]:
    """
    Return list of start positions where `stem` appears in `text` OUTSIDE
    any [[...]] block.

    Strategy: replace every [[...]] span with spaces of equal length,
    then search for the stem in the sanitized text.
    """
    sanitized = list(text)
    for m in CROSSREF_RE.finditer(text):
        start, end = m.start(), m.end()
        for i in range(start, end):
            sanitized[i] = " "

    sanitized_text = "".join(sanitized)
    positions = []
    for m in re.finditer(escaped_stem, sanitized_text):
        positions.append(m.start())
    return positions


def check_file(
    md_path: Path,
    targets: dict[str, Path],
    min_length: int,
    skip_self: bool,
) -> list[dict]:
    """
    Scan one .md file for bare mentions of target stems.

    Returns a list of dicts: {file, stem, target_file, positions, count}
    """
    try:
        text = md_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"[WARN] Cannot read {md_path}: {exc}", file=sys.stderr)
        return []

    own_stem = md_path.stem
    results = []

    for stem, target_path in targets.items():
        if skip_self and stem == own_stem:
            continue
        escaped = escape_regex(stem)
        positions = find_bare_mentions(text, stem, escaped)
        if positions:
            results.append({
                "file": str(md_path.relative_to(ROOT)),
                "stem": stem,
                "target_file": str(target_path.relative_to(ROOT)),
                "count": len(positions),
                "positions": positions,
            })

    return results


def extract_context(text: str, pos: int, stem_len: int, width: int = 40) -> str:
    """Extract surrounding text context around a match position."""
    start = max(0, pos - width)
    end = min(len(text), pos + stem_len + width)
    before = text[start:pos]
    match = text[pos:pos + stem_len]
    after = text[pos + stem_len:end]
    return f"...{before}>>>{match}<<<{after}..."



def fix_file(
    md_path: Path,
    targets: dict[str, Path],
    min_length: int,
    skip_self: bool,
) -> int:
    """
    Modify a file in-place: wrap every bare mention of a target stem with [[ ]].

    Stems are processed longest-first so that longer filenames are wrapped
    before shorter substring matches.  After each wrap the new [[...]] block
    is automatically masked by subsequent find_bare_mentions calls.

    Returns the total number of replacements made.
    """
    try:
        text = md_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"[WARN] Cannot read {md_path}: {exc}", file=sys.stderr)
        return 0

    own_stem = md_path.stem
    relevant = [
        stem for stem in targets
        if not (skip_self and stem == own_stem)
    ]
    # Longest first, then alphabetical for determinism
    relevant.sort(key=lambda s: (-len(s), s))

    total_replacements = 0
    working_text = text

    for stem in relevant:
        escaped = escape_regex(stem)
        positions = find_bare_mentions(working_text, stem, escaped)
        if not positions:
            continue
        # Replace right-to-left so earlier positions stay valid
        for pos in reversed(positions):
            end_pos = pos + len(stem)
            working_text = (
                working_text[:pos] + f"[[{stem}]]" + working_text[end_pos:]
            )
            total_replacements += 1

    if total_replacements > 0:
        md_path.write_text(working_text, encoding="utf-8")

    return total_replacements


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Check that every .md filename used in text is wrapped in [[ ]] cross-references."
    )
    parser.add_argument(
        "--min-length", type=int, default=DEFAULT_MIN_LENGTH,
        help=f"Minimum stem length to check (default: {DEFAULT_MIN_LENGTH})",
    )
    parser.add_argument(
        "--skip-self", action="store_true",
        help="Don't flag a file mentioning its own name",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show per-file breakdown including context snippets",
    )
    parser.add_argument(
        "--output", "-o", type=str, default=None,
        help="Write CSV report to this file",
    )
    parser.add_argument(
        "--limit", type=int, default=0,
        help="Limit to first N files scanned (for quick sampling)",
    )
    parser.add_argument(
        "--show-context", type=int, default=0,
        help="Show up to N context snippets per bare mention",
    )
    parser.add_argument(
        "--fix", action="store_true",
        help="Automatically wrap bare mentions with [[...]] in-place",
    )
    parser.add_argument(
        "--yes", "-y", action="store_true",
        help="Skip confirmation prompt when using --fix",
    )
    args = parser.parse_args()

    # Phase 1: collect all target stems
    targets = collect_targets(ROOT, args.min_length)
    print(f"[INFO] Collected {len(targets)} target stems (min_length={args.min_length})", file=sys.stderr)

    # Phase 2: find all content .md files to scan
    scan_files = []
    for md_path in ROOT.rglob("*.md"):
        rel = md_path.relative_to(ROOT)
        if should_skip_dir(rel.parts):
            continue
        name = md_path.name
        if name in SKIP_FILES or name in SKIP_SUBAGENTS:
            continue
        if name.startswith(SKIP_PREFIXES):
            continue
        scan_files.append(md_path)

    print(f"[INFO] Scanning {len(scan_files)} content files", file=sys.stderr)

    if args.limit > 0:
        scan_files = scan_files[: args.limit]

    # Phase 3: scan each file
    all_results: list[dict] = []
    file_bare_counts: dict[str, list[dict]] = defaultdict(list)

    for i, md_path in enumerate(scan_files):
        results = check_file(md_path, targets, args.min_length, args.skip_self)
        all_results.extend(results)
        if results:
            for r in results:
                file_bare_counts[str(md_path.relative_to(ROOT))].append(r)
        if (i + 1) % 50 == 0:
            print(f"[INFO] Scanned {i+1}/{len(scan_files)} files...", file=sys.stderr)

    # Phase 4: report
    print(f"\n{'='*70}")
    print(f"RESULTS: {len(all_results)} bare mentions found across {len(file_bare_counts)} files")
    print(f"{'='*70}\n")

    if not all_results:
        print("All cross-references appear to be properly wrapped. ✓")
        return

    # Sort by file, then by stem
    all_results.sort(key=lambda r: (r["file"], r["stem"]))

    # Print summary table
    header = f"{'SOURCE FILE':<50} {'BARE STEM':<30} {'TARGET FILE':<50} {'#':>4}"
    print(header)
    print("-" * len(header))
    for r in all_results:
        print(f"{r['file']:<50} {r['stem']:<30} {r['target_file']:<50} {r['count']:>4}")

    # Verbose: show context
    if args.show_context > 0:
        print(f"\n{'='*70}")
        print("CONTEXT SNIPPETS")
        print(f"{'='*70}")
        for r in all_results:
            md_path = ROOT / r["file"]
            try:
                text = md_path.read_text(encoding="utf-8")
            except Exception:
                continue
            stem = r["stem"]
            shown = 0
            for pos in r["positions"]:
                if shown >= args.show_context:
                    break
                ctx = extract_context(text, pos, len(stem))
                print(f"\n  [{r['file']}] bare '{stem}':")
                print(f"  {ctx}")
                shown += 1

    # CSV output
    if args.output:
        with open(args.output, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["file", "stem", "target_file", "count", "first_position"])
            writer.writeheader()
            for r in all_results:
                r_copy = dict(r)
                r_copy["first_position"] = r["positions"][0] if r["positions"] else -1
                del r_copy["positions"]
                writer.writerow(r_copy)
        print(f"\n[INFO] CSV report written to {args.output}", file=sys.stderr)

    # Summary stats
    total_bare = sum(r["count"] for r in all_results)
    unique_stems = len(set(r["stem"] for r in all_results))
    print(f"\n[STATS] Total bare mentions: {total_bare} | Unique stems: {unique_stems} | Affected files: {len(file_bare_counts)}", file=sys.stderr)

    # ------------------------------------------------------------------
    # Phase 5: auto-fix (only when --fix is passed)
    # ------------------------------------------------------------------
    if args.fix and all_results:
        if not args.yes:
            print(
                f"\n[FIX] About to modify {len(file_bare_counts)} files in-place "
                f"({total_bare} replacements).",
                file=sys.stderr,
            )
            try:
                answer = input("Proceed? [y/N]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                answer = "n"
            if answer not in ("y", "yes"):
                print("[FIX] Aborted.", file=sys.stderr)
                return

        fixed_count = 0
        total_fixed = 0
        for rel_path in file_bare_counts:
            md_path = ROOT / rel_path
            n = fix_file(md_path, targets, args.min_length, args.skip_self)
            if n > 0:
                fixed_count += 1
                total_fixed += n
                print(f"  FIXED [{rel_path}]: {n} wrap(s)", file=sys.stderr)

        print(
            f"\n[FIX] Done: {fixed_count} file(s) modified, {total_fixed} total wrap(s) applied.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
