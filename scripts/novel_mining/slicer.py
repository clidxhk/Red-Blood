"""
Chapter slicing and source registration module.
Extracts chapters with stable character offsets into normalized text.
"""

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

from .schema import SourceRecord, ChapterRecord
from .db import MiningDatabase

CHAPTER_PATTERN = re.compile(r"^\s*(第[0-9零一二三四五六七八九十百千万]+[章回节卷].*)$", re.MULTILINE)


class NovelSlicer:
    def __init__(self, db: MiningDatabase, workdir: Path = Path(".workbench/novel_mining")):
        self.db = db
        self.workdir = workdir
        self.workdir.mkdir(parents=True, exist_ok=True)

    def register_and_slice(
        self,
        raw_path: Path,
        source_id: str = "mushenji_v1",
        title: str = "牧神记",
        author: str = "宅猪",
        version_tag: str = "校对版全本",
        encoding: str = "gb18030",
    ) -> Tuple[SourceRecord, List[ChapterRecord]]:
        # 1. Read raw bytes and calculate sha256
        with open(raw_path, "rb") as f:
            raw_bytes = f.read()

        raw_sha256 = hashlib.sha256(raw_bytes).hexdigest()
        file_size = len(raw_bytes)

        # 2. Decode text
        raw_text = raw_bytes.decode(encoding, errors="replace")

        # 3. Normalize newlines to \n
        normalized_text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
        normalized_bytes = normalized_text.encode("utf-8")
        normalized_sha256 = hashlib.sha256(normalized_bytes).hexdigest()

        # Save normalized text to workdir
        normalized_file_path = self.workdir / f"{source_id}_normalized.txt"
        with open(normalized_file_path, "w", encoding="utf-8") as f:
            f.write(normalized_text)

        # 4. Find all chapter boundaries
        matches = list(CHAPTER_PATTERN.finditer(normalized_text))
        total_chapters = len(matches)

        chapters: List[ChapterRecord] = []
        for i, match in enumerate(matches):
            chapter_index = i + 1
            raw_title = match.group(1).strip()
            start_char = match.start()
            end_char = matches[i + 1].start() if i + 1 < len(matches) else len(normalized_text)

            chapter_text = normalized_text[start_char:end_char]
            char_count = len(chapter_text)
            chapter_sha256 = hashlib.sha256(chapter_text.encode("utf-8")).hexdigest()

            # Clean chapter title
            clean_title = re.sub(r"^第[0-9零一二三四五六七八九十百千万]+[章回节卷]\s*", "", raw_title)

            chapter_id = f"{source_id}_c{chapter_index:04d}"
            chapters.append(
                ChapterRecord(
                    chapter_id=chapter_id,
                    source_id=source_id,
                    chapter_index=chapter_index,
                    raw_title=raw_title,
                    normalized_title=clean_title,
                    start_char=start_char,
                    end_char=end_char,
                    char_count=char_count,
                    sha256=chapter_sha256,
                    status="pending",
                )
            )

        now_str = datetime.now(timezone.utc).isoformat()
        source = SourceRecord(
            source_id=source_id,
            title=title,
            author=author,
            version_tag=version_tag,
            file_path=str(raw_path.resolve()),
            sha256=raw_sha256,
            file_size=file_size,
            encoding=encoding,
            normalized_sha256=normalized_sha256,
            total_chars=len(normalized_text),
            total_chapters=total_chapters,
            created_at=now_str,
        )

        # Persist to database
        self.db.save_source(source)
        self.db.save_chapters(chapters)

        return source, chapters
