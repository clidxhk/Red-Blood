"""
Novel mining package.
"""

from .schema import SourceRecord, ChapterRecord, MentionRecord, ClaimRecord, EntityRecord, CandidateRecord
from .db import MiningDatabase
from .slicer import NovelSlicer
from .extractor import ChapterExtractor
from .evaluator import CandidateEvaluator

__all__ = [
    "SourceRecord",
    "ChapterRecord",
    "MentionRecord",
    "ClaimRecord",
    "EntityRecord",
    "CandidateRecord",
    "MiningDatabase",
    "NovelSlicer",
    "ChapterExtractor",
    "CandidateEvaluator",
]
