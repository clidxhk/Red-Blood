"""Evidence, review, migration and source-isolation regression tests."""

import copy
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from novel_mining.db import MiningDatabase
from novel_mining.extractor import ChapterExtractor
from novel_mining.slicer import NovelSlicer
from novel_mining.evaluator import CandidateEvaluator
from novel_mining.cli import build_report


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = MiningDatabase(self.root / "mining.db")
        self.register("a")
        self.ext = ChapterExtractor(self.db)

    def register(self, source_id):
        raw = self.root / f"{source_id}.txt"
        raw.write_bytes("第一章 灯火\r\n😀石像在夜里发光。\r\n第二章 清晨\r\n天亮了。".encode("utf-8"))
        return NovelSlicer(self.db).register_and_slice(raw, source_id, "测试书", encoding="utf-8")

    def response(self, source_id="a"):
        chapter, body = self.ext.chapter_text(source_id, f"{source_id}_c0001")
        quote = "石像在夜里发光。"
        start = body.index(quote)
        return {"source_id": source_id, "chapter_id": chapter['chapter_id'],
                "chapter_sha256": chapter['sha256'], "checked_categories": ["器物"],
                "claims": [{"target_name": "镇村石像", "category": "器物", "attribute": "用途",
                            "value": "夜间发光", "claim_type": "情节展示", "conditions": "夜里",
                            "evidence_start": start, "evidence_end": start + len(quote),
                            "evidence_snippet": quote}]}

    def approve(self, source_id="a"):
        claim = self.db.get_claims(source_id)[0]
        self.ext.review_claim(source_id, claim['claim_id'], "测试复核者", "原文只支持夜间发光", True)

    def test_real_positions_are_not_semantic_approval(self):
        self.ext.import_response("a", self.response())
        self.assertEqual(self.db.get_claims("a")[0]['status'], "evidence_checked")
        self.assertEqual(CandidateEvaluator(self.db).evaluate_candidates("a"), [])
        self.assertEqual(self.ext.audit("a"), [])

    def test_wrong_quote_rolls_back_entire_response(self):
        response = self.response()
        bad = copy.deepcopy(response['claims'][0])
        bad['evidence_snippet'] = "假证据"
        response['claims'].append(bad)
        with self.assertRaises(ValueError):
            self.ext.import_response("a", response)
        self.assertEqual(self.db.get_claims("a"), [])
        self.assertEqual(self.db.get_chapters("a")[0]['status'], "pending")

    def test_wrong_hash_and_range_are_rejected(self):
        for field, value in (("evidence_start", -1), ("evidence_end", 9999), ("evidence_start", True)):
            response = self.response()
            response['claims'][0][field] = value
            with self.assertRaises(ValueError):
                self.ext.import_response("a", response)
        response = self.response()
        response['chapter_sha256'] = "0" * 64
        with self.assertRaises(ValueError):
            self.ext.import_response("a", response)

    def test_review_gate_and_idempotent_import(self):
        response = self.response()
        self.ext.import_response("a", response)
        self.approve()
        self.ext.import_response("a", response)
        self.assertEqual(len(self.db.get_claims("a")), 1)
        self.assertEqual(self.db.get_claims("a")[0]['status'], "verified")
        self.assertEqual(len(CandidateEvaluator(self.db).evaluate_candidates("a")), 1)

    def test_changed_summary_does_not_inherit_review(self):
        response = self.response()
        self.ext.import_response("a", response)
        self.approve()
        response['claims'][0]['value'] = "无限照亮世界"
        self.ext.import_response("a", response)
        self.assertEqual(len(self.db.get_claims("a")), 2)
        self.assertEqual(CandidateEvaluator(self.db).evaluate_candidates("a"), [])

    def test_review_rejects_blank_notes(self):
        self.ext.import_response("a", self.response())
        claim = self.db.get_claims("a")[0]
        with self.assertRaises(ValueError):
            self.ext.review_claim("a", claim['claim_id'], "", "", True)

    def test_same_name_in_two_books_is_not_merged(self):
        self.register("b")
        for source_id in ("a", "b"):
            self.ext.import_response(source_id, self.response(source_id))
            self.approve(source_id)
            CandidateEvaluator(self.db).evaluate_candidates(source_id)
        a = self.db.get_all_entities("a")[0]
        b = self.db.get_all_entities("b")[0]
        self.assertNotEqual(a['entity_id'], b['entity_id'])
        self.assertEqual(len(self.db.get_all_candidates("a")), 1)
        self.assertNotIn("b_c0001", build_report(self.db, "a"))

    def test_changed_source_blocks_approved_candidates(self):
        self.ext.import_response("a", self.response())
        self.approve()
        CandidateEvaluator(self.db).evaluate_candidates("a")
        path = self.root / "a_normalized.txt"
        path.write_text(path.read_text(encoding="utf-8") + "变动", encoding="utf-8")
        with self.assertRaises(ValueError):
            CandidateEvaluator(self.db).evaluate_candidates("a")
        self.assertEqual(len(self.ext.audit("a")), 1)
        self.assertNotIn("待创作准入）", build_report(self.db, "a"))

    def test_no_result_chapter_is_imported_not_verified(self):
        response = self.response()
        response['claims'] = []
        self.ext.import_response("a", response)
        self.assertEqual(self.db.get_chapters("a")[0]['status'], "imported")
        self.assertEqual(self.db.get_all_entities("a"), [])

    def test_source_version_cannot_be_overwritten(self):
        with self.assertRaises(ValueError):
            self.register("a")

    def test_invalid_encoding_is_not_silently_replaced(self):
        raw = self.root / "bad.txt"
        raw.write_bytes(b"\xff\xfe\xfa")
        with self.assertRaises(UnicodeDecodeError):
            NovelSlicer(self.db).register_and_slice(raw, "bad", encoding="utf-8")
        self.assertIsNone(self.db.get_source("bad"))

    def test_character_statement_requires_speaker(self):
        response = self.response()
        response['claims'][0]['claim_type'] = "人物说法"
        with self.assertRaises(ValueError):
            self.ext.import_response("a", response)

    def test_import_cannot_self_approve(self):
        response = self.response()
        response['claims'][0].update(status="verified", reviewer="伪造", review_note="自评通过")
        self.ext.import_response("a", response)
        claim = self.db.get_claims("a")[0]
        self.assertEqual(claim['status'], "evidence_checked")
        self.assertEqual(claim['reviewer'], "")

    def test_wrong_source_and_missing_coverage_are_rejected(self):
        response = self.response()
        response['source_id'] = "other"
        with self.assertRaises(ValueError):
            self.ext.import_response("a", response)
        response = self.response()
        response['checked_categories'] = []
        with self.assertRaises(ValueError):
            self.ext.import_response("a", response)

    def test_no_chapter_boundaries_requires_manual_review(self):
        raw = self.root / "unstructured.txt"
        raw.write_text("没有章回标题的正文", encoding="utf-8")
        with self.assertRaises(ValueError):
            NovelSlicer(self.db).register_and_slice(raw, "unstructured", encoding="utf-8")
        self.assertIsNone(self.db.get_source("unstructured"))

    def test_legacy_verified_records_are_quarantined(self):
        legacy = self.root / "legacy.db"
        with sqlite3.connect(legacy) as conn:
            conn.execute("CREATE TABLE entities (entity_id TEXT PRIMARY KEY, canonical_name TEXT, "
                         "category TEXT, aliases_json TEXT, claims_json TEXT, chapter_ids_json TEXT, status TEXT)")
            conn.execute("INSERT INTO entities VALUES ('old','石像','器物','[]','[]','[]','verified')")
        conn.close()
        migrated = MiningDatabase(legacy)
        self.assertEqual(migrated.get_all_entities()[0]['status'], "needs_review")
        self.assertEqual(migrated.get_all_entities("a"), [])


if __name__ == "__main__":
    unittest.main()
