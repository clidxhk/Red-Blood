"""
Data models and schemas for novel mining pipeline.
Conforms to scripts/novel_mining/PLAN.md specifications.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class SourceRecord:
    source_id: str
    title: str
    author: str
    version_tag: str
    file_path: str
    sha256: str
    file_size: int
    encoding: str
    normalized_sha256: str
    total_chars: int
    total_chapters: int
    created_at: str


@dataclass
class ChapterRecord:
    chapter_id: str
    source_id: str
    chapter_index: int
    raw_title: str
    normalized_title: str
    start_char: int
    end_char: int
    char_count: int
    sha256: str
    status: str = "pending"


@dataclass
class MentionRecord:
    mention_id: str
    task_id: str
    chapter_id: str
    raw_name: str
    alias: Optional[str]
    category: str  # 草木, 丹药, 术法, 器物, 异类材料, 日用百艺
    char_offset: int
    context_snippet: str


@dataclass
class ClaimRecord:
    claim_id: str
    task_id: str
    chapter_id: str
    target_name: str
    category: str
    attribute: str  # 用途, 起势行法, 代价副作用, 水土环境, 境界限制, 配方材质, 生态机制
    value: str
    claim_type: str  # 旁白说明, 情节展示, 人物说法, 传闻
    conditions: str
    speaker: Optional[str]
    evidence_snippet: str
    evidence_start: Optional[int] = None
    evidence_end: Optional[int] = None
    chapter_sha256: str = ""
    status: str = "needs_review"
    reviewer: str = ""
    review_note: str = ""


@dataclass
class EntityRecord:
    entity_id: str
    canonical_name: str
    category: str
    aliases: List[str] = field(default_factory=list)
    claims: List[Dict[str, Any]] = field(default_factory=list)
    chapter_ids: List[str] = field(default_factory=list)
    status: str = "needs_review"
    source_id: str = ""


@dataclass
class CandidateRecord:
    candidate_id: str
    entity_id: str
    canonical_name: str
    category: str
    destination: str  # 优先转化, 专项评估, 暂缓采用, 仅留场景素材
    reason: str
    target_spec_path: str
    proposed_adaptation: Dict[str, Any] = field(default_factory=dict)
