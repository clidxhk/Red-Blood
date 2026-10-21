"""Import source-backed claims; never synthesize facts or approve semantics."""

import hashlib
import json

from .schema import EntityRecord


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class ChapterExtractor:
    def __init__(self, db):
        self.db = db

    def chapter_text(self, source_id, chapter_id):
        source = self.db.get_source(source_id)
        if not source:
            raise ValueError("Unknown source")
        chapters = {c["chapter_id"]: c for c in self.db.get_chapters(source_id)}
        if chapter_id not in chapters:
            raise ValueError("Chapter does not belong to source")
        path = self.db.db_path.parent / f"{source_id}_normalized.txt"
        text = path.read_text(encoding="utf-8")
        if digest(text) != source["normalized_sha256"]:
            raise ValueError("Normalized source hash mismatch; register a new source version")
        chapter = chapters[chapter_id]
        body = text[chapter["start_char"]:chapter["end_char"]]
        if digest(body) != chapter["sha256"]:
            raise ValueError("Chapter hash mismatch")
        return chapter, body

    def check_evidence(self, source_id, claim):
        chapter, body = self.chapter_text(source_id, claim["chapter_id"])
        start, end = claim.get("evidence_start"), claim.get("evidence_end")
        if type(start) is not int or type(end) is not int or not (0 <= start < end <= len(body)):
            raise ValueError("Invalid chapter-local evidence range")
        if claim.get("chapter_sha256") != chapter["sha256"]:
            raise ValueError("Evidence chapter hash mismatch")
        snippet = claim.get("evidence_snippet")
        if not isinstance(snippet, str) or not snippet.strip() or body[start:end] != snippet:
            raise ValueError("Evidence snippet does not match source range")

    def import_response(self, source_id, response):
        """Validate the complete chapter response before an atomic write.

        Evidence uses chapter-local Unicode code points, [start, end).
        Imports are append-only; exact re-imports retain review decisions.
        """
        if response.get("source_id") != source_id:
            raise ValueError("Response source mismatch")
        chapter_id = response["chapter_id"]
        chapter, _ = self.chapter_text(source_id, chapter_id)
        if response.get("chapter_sha256") != chapter["sha256"]:
            raise ValueError("Response chapter hash mismatch")
        categories = response.get("checked_categories")
        if not isinstance(categories, list) or not categories or any(
            not isinstance(c, str) or not c.strip() for c in categories
        ):
            raise ValueError("checked_categories must explicitly list inspected categories")
        claims = response.get("claims")
        if not isinstance(claims, list):
            raise ValueError("claims must be a list (empty is allowed)")
        prepared = []
        for cl in claims:
            for key in ("target_name", "category", "attribute", "value", "claim_type"):
                if not isinstance(cl.get(key), str) or not cl[key].strip():
                    raise ValueError(f"Missing claim field: {key}")
            if cl["category"] not in categories:
                raise ValueError("Claim category missing from checked_categories")
            if cl["claim_type"] not in ("旁白说明", "情节展示", "人物说法", "传闻", "否定/假设"):
                raise ValueError("Unknown claim type")
            if cl["claim_type"] in ("人物说法", "传闻") and not cl.get("speaker"):
                raise ValueError("Character statements and hearsay require speaker attribution")
            record = dict(cl, chapter_id=chapter_id, chapter_sha256=response["chapter_sha256"])
            self.check_evidence(source_id, record)
            # Identity includes source version and all semantic fields, so a
            # changed summary cannot inherit an earlier approval.
            identity = {k: record.get(k) for k in (
                "target_name", "category", "attribute", "value", "claim_type", "conditions",
                "speaker", "chapter_id", "chapter_sha256", "evidence_start", "evidence_end", "evidence_snippet")}
            claim_id = "clm_" + digest(json.dumps(identity, ensure_ascii=False, sort_keys=True))
            prepared.append((claim_id, record))
        with self.db._get_connection() as conn:
            for claim_id, cl in prepared:
                conn.execute(
                    "INSERT OR IGNORE INTO claims (claim_id,task_id,chapter_id,target_name,category,"
                    "attribute,value,claim_type,conditions,speaker,evidence_snippet,evidence_start,"
                    "evidence_end,chapter_sha256,status,reviewer,review_note) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'','')",
                    (claim_id, "import_" + chapter_id, chapter_id, cl["target_name"], cl["category"],
                     cl["attribute"], cl["value"], cl["claim_type"], cl.get("conditions", ""),
                     cl.get("speaker"), cl["evidence_snippet"], cl["evidence_start"],
                     cl["evidence_end"], cl["chapter_sha256"], "evidence_checked"))
            conn.execute("UPDATE chapters SET status='imported' WHERE chapter_id=?", (chapter_id,))
            # Persist coverage separately, including explicit no-result imports.
            conn.execute("CREATE TABLE IF NOT EXISTS imports (chapter_id TEXT PRIMARY KEY, "
                         "checked_categories TEXT, response_sha256 TEXT)")
            conn.execute("INSERT OR REPLACE INTO imports VALUES (?,?,?)", (
                chapter_id, json.dumps(categories, ensure_ascii=False),
                digest(json.dumps(response, ensure_ascii=False, sort_keys=True))))
        self.rebuild_entities(source_id)
        return len(prepared)

    def rebuild_entities(self, source_id):
        grouped = {}
        for cl in self.db.get_claims(source_id):
            # Legacy placeholder data stays visible in audits, not in entities
            # eligible for conversion.
            if cl["evidence_start"] is None:
                continue
            key = (cl["target_name"], cl["category"])
            grouped.setdefault(key, []).append(cl)
        entities = []
        for (name, category), claims in grouped.items():
            entities.append(EntityRecord(
                entity_id="ent_" + digest(json.dumps([source_id, name, category], ensure_ascii=False)),
                canonical_name=name, category=category, claims=claims,
                chapter_ids=sorted({c["chapter_id"] for c in claims}),
                status="verified" if all(c["status"] == "verified" for c in claims) else "needs_review",
                source_id=source_id))
        self.db.save_entities(entities)

    def review_claim(self, source_id, claim_id, reviewer, note, approve):
        if not reviewer.strip() or not note.strip():
            raise ValueError("A reviewer and source-based review note are required")
        claims = {c["claim_id"]: c for c in self.db.get_claims(source_id)}
        if claim_id not in claims:
            raise ValueError("Unknown claim for this source")
        self.check_evidence(source_id, claims[claim_id])
        with self.db._get_connection() as conn:
            conn.execute("UPDATE claims SET status=?,reviewer=?,review_note=? WHERE claim_id=?", (
                "verified" if approve else "rejected", reviewer, note, claim_id))
        self.rebuild_entities(source_id)

    def audit(self, source_id):
        issues = []
        for claim in self.db.get_claims(source_id):
            try:
                self.check_evidence(source_id, claim)
            except (ValueError, OSError) as exc:
                issues.append({"claim_id": claim["claim_id"], "target_name": claim["target_name"],
                               "issue": str(exc)})
        return issues

    def extract_chapters_1_to_10(self, source_id="mushenji_v1"):
        raise ValueError("Hardcoded extraction is disabled. Export a chapter and import evidence-backed JSON.")
