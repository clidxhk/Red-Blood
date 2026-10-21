"""Stateless text reading and evidence checks for worldbuilding research."""

from .extractor import validate_claims
from .slicer import read_text

__all__ = ["read_text", "validate_claims"]
