"""Picks the sentence of a document that best shows why it matched."""

from __future__ import annotations

import re

from .tokenizer import tokenize

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
MAX_SNIPPET_CHARS = 240


def best_snippet(body: str, matched_terms: set[str]) -> str:
    """Return the sentence with most matched terms, or the first one."""
    sentences = [part for part in _SENTENCE_END.split(body.strip()) if part]
    if not sentences:
        return ""
    best = max(sentences, key=lambda sentence: len(matched_terms & set(tokenize(sentence))))
    if not matched_terms & set(tokenize(best)):
        best = sentences[0]
    if len(best) > MAX_SNIPPET_CHARS:
        best = best[: MAX_SNIPPET_CHARS - 1].rstrip() + "…"
    return best
