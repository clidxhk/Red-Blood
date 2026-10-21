"""Read selected text in memory; do not register sources or save progress."""

from pathlib import Path
import re

CHAPTER_PATTERN = re.compile(r"^[ \t]*(第[0-9零一二三四五六七八九十百千万]+[章回节卷].*)$", re.MULTILINE)


def read_text(path, encoding="utf-8-sig", chapters=None):
    text = Path(path).read_bytes().decode(encoding, errors="strict")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if chapters is None:
        return text
    selection = re.fullmatch(r"([1-9]\d*)(?:-([1-9]\d*))?", chapters)
    if not selection:
        raise ValueError("chapters must be a positive index or inclusive range, e.g. 1-3")
    start = int(selection[1])
    end = int(selection[2] or selection[1])
    headings = list(CHAPTER_PATTERN.finditer(text))
    if not 1 <= start <= end <= len(headings):
        raise ValueError("Chapter range unavailable; read the original text and check its headings")
    stop = headings[end].start() if end < len(headings) else len(text)
    return text[headings[start - 1].start():stop]
