"""Stateless reading and quotation checks, using original temporary fixtures."""

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from novel_mining.cli import main
from novel_mining.extractor import validate_claims
from novel_mining.slicer import read_text


class MiningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / "original.txt"
        self.path.write_bytes("第一章 灯火\r\n😀石灯入夜发光。\r\n第二章 天明\r\n灯灭了。".encode("utf-8"))
        self.claim = {"target_name": "石灯", "category": "器物", "attribute": "用途",
                      "value": "入夜发光", "claim_type": "情节展示", "evidence_snippet": "石灯入夜发光"}

    def test_read_normalizes_without_writing(self):
        before = self.path.read_bytes()
        text = read_text(self.path)
        self.assertNotIn("\r", text)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual([p.name for p in self.root.iterdir()], ["original.txt"])

    def test_chapters_are_only_a_temporary_selection(self):
        selected = read_text(self.path, chapters="2")
        self.assertIn("灯灭了", selected)
        self.assertNotIn("入夜发光", selected)
        self.assertEqual(len(list(self.root.iterdir())), 1)

    def test_unavailable_or_invalid_range_fails(self):
        for value in ("0", "2-1", "1-99", "anything"):
            with self.assertRaises(ValueError):
                read_text(self.path, chapters=value)

    def test_bad_encoding_fails(self):
        self.path.write_bytes(b"\xff\xfa")
        with self.assertRaises(UnicodeDecodeError):
            read_text(self.path)

    def test_unique_quotation_needs_no_source_registration(self):
        self.assertEqual(validate_claims(read_text(self.path), [self.claim]), [])

    def test_invented_quotation_fails(self):
        self.claim['evidence_snippet'] = "原文没有写这一句"
        self.assertTrue(validate_claims(read_text(self.path), [self.claim]))

    def test_repeated_quotation_requires_precise_unicode_offsets(self):
        text = "😀石灯入夜发光，石灯入夜发光"
        self.assertTrue(validate_claims(text, [self.claim]))
        self.claim.update(evidence_start=1, evidence_end=7)
        self.assertEqual(validate_claims(text, [self.claim]), [])
        self.claim['evidence_start'] = True
        self.assertTrue(validate_claims(text, [self.claim]))

    def test_statement_requires_speaker(self):
        self.claim['claim_type'] = "人物说法"
        self.assertTrue(validate_claims(read_text(self.path), [self.claim]))
        self.claim['speaker'] = "村民"
        self.assertEqual(validate_claims(read_text(self.path), [self.claim]), [])

    def test_wrong_input_shape_fails(self):
        with self.assertRaises(ValueError):
            validate_claims("", {})
        self.assertTrue(validate_claims("", [None, {}]))

    def test_cli_does_not_create_files_or_change_input(self):
        claims = self.root / "claims.json"
        claims.write_text(json.dumps([self.claim], ensure_ascii=False), encoding="utf-8")
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        output = io.StringIO()
        with redirect_stdout(output):
            main(["check", str(self.path), "--claims", str(claims)])
        self.assertIn("Review meaning", output.getvalue())
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})


if __name__ == "__main__":
    unittest.main()
