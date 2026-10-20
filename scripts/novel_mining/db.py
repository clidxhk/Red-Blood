"""
SQLite database storage for novel mining pipeline.
Location: .workbench/novel_mining/mining.db
"""

import json
import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Any

from .schema import (
    SourceRecord,
    ChapterRecord,
    MentionRecord,
    ClaimRecord,
    EntityRecord,
    CandidateRecord,
)

DEFAULT_DB_PATH = Path(".workbench/novel_mining/mining.db")


class MiningDatabase:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                source_id TEXT PRIMARY KEY,
                title TEXT,
                author TEXT,
                version_tag TEXT,
                file_path TEXT,
                sha256 TEXT,
                file_size INTEGER,
                encoding TEXT,
                normalized_sha256 TEXT,
                total_chars INTEGER,
                total_chapters INTEGER,
                created_at TEXT
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS chapters (
                chapter_id TEXT PRIMARY KEY,
                source_id TEXT,
                chapter_index INTEGER,
                raw_title TEXT,
                normalized_title TEXT,
                start_char INTEGER,
                end_char INTEGER,
                char_count INTEGER,
                sha256 TEXT,
                status TEXT,
                FOREIGN KEY (source_id) REFERENCES sources (source_id)
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS mentions (
                mention_id TEXT PRIMARY KEY,
                task_id TEXT,
                chapter_id TEXT,
                raw_name TEXT,
                alias TEXT,
                category TEXT,
                char_offset INTEGER,
                context_snippet TEXT,
                FOREIGN KEY (chapter_id) REFERENCES chapters (chapter_id)
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS claims (
                claim_id TEXT PRIMARY KEY,
                task_id TEXT,
                chapter_id TEXT,
                target_name TEXT,
                category TEXT,
                attribute TEXT,
                value TEXT,
                claim_type TEXT,
                conditions TEXT,
                speaker TEXT,
                evidence_snippet TEXT,
                FOREIGN KEY (chapter_id) REFERENCES chapters (chapter_id)
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                entity_id TEXT PRIMARY KEY,
                canonical_name TEXT,
                category TEXT,
                aliases_json TEXT,
                claims_json TEXT,
                chapter_ids_json TEXT,
                status TEXT
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS candidates (
                candidate_id TEXT PRIMARY KEY,
                entity_id TEXT,
                canonical_name TEXT,
                category TEXT,
                destination TEXT,
                reason TEXT,
                target_spec_path TEXT,
                proposed_adaptation_json TEXT,
                FOREIGN KEY (entity_id) REFERENCES entities (entity_id)
            )
            """)
            conn.commit()

    def save_source(self, s: SourceRecord):
        with self._get_connection() as conn:
            conn.execute("""
            INSERT OR REPLACE INTO sources (
                source_id, title, author, version_tag, file_path, sha256,
                file_size, encoding, normalized_sha256, total_chars, total_chapters, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                s.source_id, s.title, s.author, s.version_tag, s.file_path, s.sha256,
                s.file_size, s.encoding, s.normalized_sha256, s.total_chars, s.total_chapters, s.created_at
            ))

    def save_chapters(self, chapters: List[ChapterRecord]):
        with self._get_connection() as conn:
            conn.executemany("""
            INSERT OR REPLACE INTO chapters (
                chapter_id, source_id, chapter_index, raw_title, normalized_title,
                start_char, end_char, char_count, sha256, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                (
                    c.chapter_id, c.source_id, c.chapter_index, c.raw_title, c.normalized_title,
                    c.start_char, c.end_char, c.char_count, c.sha256, c.status
                )
                for c in chapters
            ])

    def save_mentions(self, mentions: List[MentionRecord]):
        with self._get_connection() as conn:
            conn.executemany("""
            INSERT OR REPLACE INTO mentions (
                mention_id, task_id, chapter_id, raw_name, alias, category,
                char_offset, context_snippet
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                (
                    m.mention_id, m.task_id, m.chapter_id, m.raw_name, m.alias, m.category,
                    m.char_offset, m.context_snippet
                )
                for m in mentions
            ])

    def save_claims(self, claims: List[ClaimRecord]):
        with self._get_connection() as conn:
            conn.executemany("""
            INSERT OR REPLACE INTO claims (
                claim_id, task_id, chapter_id, target_name, category, attribute,
                value, claim_type, conditions, speaker, evidence_snippet
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                (
                    c.claim_id, c.task_id, c.chapter_id, c.target_name, c.category, c.attribute,
                    c.value, c.claim_type, c.conditions, c.speaker, c.evidence_snippet
                )
                for c in claims
            ])

    def save_entities(self, entities: List[EntityRecord]):
        with self._get_connection() as conn:
            conn.executemany("""
            INSERT OR REPLACE INTO entities (
                entity_id, canonical_name, category, aliases_json, claims_json,
                chapter_ids_json, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [
                (
                    e.entity_id, e.canonical_name, e.category,
                    json.dumps(e.aliases, ensure_ascii=False),
                    json.dumps(e.claims, ensure_ascii=False),
                    json.dumps(e.chapter_ids, ensure_ascii=False),
                    e.status
                )
                for e in entities
            ])

    def save_candidates(self, candidates: List[CandidateRecord]):
        with self._get_connection() as conn:
            conn.executemany("""
            INSERT OR REPLACE INTO candidates (
                candidate_id, entity_id, canonical_name, category, destination,
                reason, target_spec_path, proposed_adaptation_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                (
                    cand.candidate_id, cand.entity_id, cand.canonical_name, cand.category,
                    cand.destination, cand.reason, cand.target_spec_path,
                    json.dumps(cand.proposed_adaptation, ensure_ascii=False)
                )
                for cand in candidates
            ])

    def get_chapters(self, source_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            query = "SELECT * FROM chapters WHERE source_id = ? ORDER BY chapter_index ASC"
            if limit:
                query += f" LIMIT {limit}"
            cur = conn.cursor()
            cur.execute(query, (source_id,))
            return [dict(r) for r in cur.fetchall()]

    def get_mentions_for_chapter(self, chapter_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM mentions WHERE chapter_id = ?", (chapter_id,))
            return [dict(r) for r in cur.fetchall()]

    def get_all_entities(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM entities ORDER BY category, canonical_name")
            rows = []
            for r in cur.fetchall():
                d = dict(r)
                d["aliases"] = json.loads(d["aliases_json"])
                d["claims"] = json.loads(d["claims_json"])
                d["chapter_ids"] = json.loads(d["chapter_ids_json"])
                rows.append(d)
            return rows

    def get_all_candidates(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM candidates ORDER BY destination, category")
            rows = []
            for r in cur.fetchall():
                d = dict(r)
                d["proposed_adaptation"] = json.loads(d["proposed_adaptation_json"])
                rows.append(d)
            return rows
