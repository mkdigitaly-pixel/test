#!/usr/bin/env python3
"""Проверка уникальности рерайта: нет цепочек 8+ слов из источника."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def normalize(text: str) -> list[str]:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return [w for w in text.split() if len(w) > 2]


def shingles(words: list[str], size: int = 8) -> set[tuple[str, ...]]:
    return {tuple(words[i : i + size]) for i in range(len(words) - size + 1)}


def load_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8")
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            return parts[2]
    return raw


def check(draft: Path, sources: list[Path], *, min_len: int = 8) -> int:
    draft_words = normalize(load_text(draft))
    draft_set = shingles(draft_words, min_len)
    hits: list[tuple[str, str]] = []
    for src in sources:
        src_set = shingles(normalize(load_text(src)), min_len)
        overlap = draft_set & src_set
        if overlap:
            sample = " ".join(next(iter(overlap)))
            hits.append((str(src), sample))
    if hits:
        print(f"⚠ Найдено совпадений цепочек {min_len}+ слов: {len(hits)}")
        for path, sample in hits[:10]:
            print(f"  {path}\n    «{sample}…»")
        return 1
    print(f"✓ Совпадений цепочек {min_len}+ слов нет")
    return 0


def main() -> None:
    p = argparse.ArgumentParser(description="Проверка уникальности рерайта")
    p.add_argument("draft", help="Черновик (статья/пост)")
    p.add_argument("sources", nargs="+", help="Файлы-источники или URL-тексты (.txt)")
    args = p.parse_args()
    draft = Path(args.draft)
    sources = [Path(s) for s in args.sources]
    sys.exit(check(draft, sources))


if __name__ == "__main__":
    main()
