"""Regression tests for scoped link checking and workbench exclusion."""

import contextlib
import io
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import check_crossrefs as checker


class LinkTargetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, relative, text="正文"):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_exact_names_include_single_character_and_punctuation(self):
        self.write("世界/背景/业.md")
        self.write("故事/11.茶馆闲聊·火楼.md")
        source = self.write("故事/测试.md", "[[业]] [[11.茶馆闲聊·火楼]]\n[[11. 茶馆闲聊·火楼]]\n[[]]")
        errors = checker.check_link_targets(source, self.root, checker.collect_link_targets(self.root))
        self.assertEqual([(e["target"], e["line"], e["kind"]) for e in errors], [
            ("11. 茶馆闲聊·火楼", 2, "missing"), ("", 3, "missing"),
        ])

    def test_duplicate_stems_are_ambiguous(self):
        self.write("角色/同名.md")
        self.write("故事/同名.md")
        source = self.write("故事/引用.md", "[[同名]]")
        errors = checker.check_link_targets(source, self.root, checker.collect_link_targets(self.root))
        self.assertEqual(errors[0]["kind"], "ambiguous")

    def test_workbench_is_excluded_from_both_target_indexes_and_scan(self):
        self.write(".workbench/runs/隐藏草稿.md", "[[不存在]]")
        self.write("scripts/scene_runtime/PLAN.md", "[[不存在]]")
        self.write("世界/背景/正式.md", "正文")
        self.assertNotIn("隐藏草稿", checker.collect_link_targets(self.root))
        self.assertNotIn("隐藏草稿", checker.collect_targets(self.root, 1))
        self.assertNotIn("PLAN", checker.collect_link_targets(self.root))
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(checker.check_selected_links(self.root, ["."]), 0)
        self.assertIn("1 个文件", output.getvalue())

    def test_scoped_check_reports_missing_links_and_nonzero_status(self):
        self.write("世界/背景/正常.md")
        self.write("故事/选中.md", "[[正常]]\n[[失效]]")
        self.write("故事/未选.md", "[[另一个失效]]")
        with contextlib.redirect_stdout(io.StringIO()) as output:
            status = checker.check_selected_links(self.root, ["故事/选中.md"])
        self.assertEqual(status, 1)
        self.assertIn("选中.md:2", output.getvalue())
        self.assertNotIn("未选.md", output.getvalue())

    def test_outside_or_empty_selection_is_rejected(self):
        self.write("scripts/只读说明.md")
        for selected in ([".."], ["不存在.md"], ["scripts"]):
            with self.subTest(selected=selected), self.assertRaises(ValueError):
                checker.check_selected_links(self.root, selected)

    def test_workbench_alias_does_not_become_formal_content(self):
        target = self.write(".workbench/runs/隐藏草稿.md", "[[失效]]").parent
        alias = self.root / "public_alias"
        try:
            alias.symlink_to(target, target_is_directory=True)
            self.addCleanup(alias.unlink)
        except OSError:
            if os.name != "nt":
                self.skipTest("Directory links unavailable")
            env = dict(os.environ, SCENE_TEST_LINK=str(alias), SCENE_TEST_TARGET=str(target))
            result = subprocess.run([
                "powershell", "-NoProfile", "-NonInteractive", "-Command",
                "New-Item -ItemType Junction -Path $env:SCENE_TEST_LINK -Target $env:SCENE_TEST_TARGET -ErrorAction Stop | Out-Null",
            ], capture_output=True, env=env)
            if result.returncode:
                self.skipTest("Neither symlinks nor junctions available")
            self.addCleanup(alias.rmdir)
        self.assertFalse(checker.is_content_file(alias / "隐藏草稿.md", self.root))
        self.assertNotIn("隐藏草稿", checker.collect_link_targets(self.root))
        self.assertNotIn("隐藏草稿", checker.collect_targets(self.root, 1))
        with self.assertRaises(ValueError):
            checker.check_selected_links(self.root, ["public_alias"])


if __name__ == "__main__":
    unittest.main()
