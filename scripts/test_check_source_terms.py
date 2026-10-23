"""Regression tests for source-term residue scanning (check_source_terms)."""

import contextlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import check_source_terms as checker

REPO_ROOT = Path(__file__).resolve().parent.parent


class ParseRecordTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write_record(self, text):
        path = self.root / "素材/某书/取材记录.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_parses_section_and_ignores_other_sections(self):
        record = self.write_record(
            "# 记录\n\n## 批次索引\n\n- 霸体不该算入\n\n"
            "## 搬运禁词\n\n- 灵胎神藏\n- 霸体三丹功\n\n## 舍弃与废弃\n\n- 神魔真言\n"
        )
        self.assertEqual(checker.parse_record_terms(record), ["灵胎神藏", "霸体三丹功"])

    def test_non_list_lines_are_skipped_with_warning(self):
        record = self.write_record("## 搬运禁词\n\n- 霸体\n- 霸体\n| 灵胎神藏 |\n神魔真言\n")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertEqual(checker.parse_record_terms(record), ["霸体"])
        self.assertIn("逐行一词", stderr.getvalue())

    def test_collect_terms_rejects_missing_records(self):
        with self.assertRaises(ValueError):
            checker.collect_terms(self.root, [self.root / "素材/缺/取材记录.md"])

    def test_collect_terms_merges_records_in_order_and_dedupes(self):
        first = self.write_record("## 搬运禁词\n\n- 灵胎神藏\n")
        second = self.root / "素材/他书/取材记录.md"
        second.parent.mkdir(parents=True, exist_ok=True)
        second.write_text("## 搬运禁词\n\n- 霸体\n- 灵胎神藏\n", encoding="utf-8")
        self.assertEqual(
            checker.collect_terms(self.root, [first, second]),
            ["灵胎神藏", "霸体"],
        )


class ScanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_scan_file_reports_line_number_and_term(self):
        target = self.write("世界/背景/试文.md", "首行干净。\n他修的正是灵胎神藏之法。\n")
        hits = checker.scan_file(target, ["灵胎神藏"])
        self.assertEqual([(line, term) for line, term, _ in hits], [(2, "灵胎神藏")])

    def test_scan_targets_default_excludes_material_domain(self):
        self.write("世界/条目.md", "正文")
        self.write("素材/某书/取材记录.md", "## 搬运禁词\n\n- 霸体\n")
        targets = checker.scan_targets(self.root, None)
        self.assertEqual([t.name for t in targets], ["条目.md"])
        explicit = checker.scan_targets(self.root, ["素材/某书/取材记录.md"])
        self.assertEqual(explicit, [])

    def test_scan_targets_rejects_outside_paths(self):
        with self.assertRaises(ValueError):
            checker.scan_targets(self.root, ["../外部.md"])

    def test_scan_targets_skip_missing_directories(self):
        self.write("故事/回目.md", "正文")
        targets = checker.scan_targets(self.root, None)
        self.assertEqual([t.name for t in targets], ["回目.md"])


class CliSmokeTests(unittest.TestCase):
    def test_clean_scan_against_repo_returns_zero(self):
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "check_source_terms.py"),
             "--terms", "绝不存在的词xyzzy"],
            capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("命中 0 处", result.stdout)

    def test_outside_target_is_rejected_with_nonzero(self):
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "check_source_terms.py"),
             "--terms", "任意", "../外部"],
            capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(result.returncode, 2)

    def test_no_terms_warns_and_returns_zero(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        empty = Path(temp.name) / "空记录.md"
        empty.write_text("# 无禁词节\n", encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "check_source_terms.py"),
             "--records", str(empty)],
            capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("未收集到任何搬运禁词", result.stderr)


if __name__ == "__main__":
    unittest.main()
