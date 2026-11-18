"""Inverted index with BM25 ranking for the documents of one tenant."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

from ..models import Ruling
from .filters import SearchFilters
from .snippets import best_snippet
from .tokenizer import MAX_QUERY_TERMS, ruling_tokens, tokenize

BM25_K1 = 1.2
BM25_B = 0.75
#: The last query word also matches as a prefix from this length, for type-ahead.
MIN_PREFIX_CHARS = 3


@dataclass(frozen=True)
class SearchHit:
    ruling: Ruling
    score: float
    matched_terms: tuple[str, ...]
    snippet: str


class TenantIndex:
    def __init__(self) -> None:
        self._documents: dict[str, Ruling] = {}
        self._postings: dict[str, dict[str, int]] = {}
        self._lengths: dict[str, int] = {}
        self._total_length = 0
        self._posting_count = 0

    def __len__(self) -> int:
        return len(self._documents)

    def __contains__(self, doc_id: object) -> bool:
        return doc_id in self._documents

    @property
    def term_count(self) -> int:
        return len(self._postings)

    @property
    def posting_count(self) -> int:
        return self._posting_count

    def rulings(self) -> list[Ruling]:
        return list(self._documents.values())

    def add(self, ruling: Ruling) -> None:
        if ruling.docket_id in self._documents:
            raise ValueError(f"Ruling {ruling.docket_id} is already indexed.")
        tokens = ruling_tokens(ruling)
        self._documents[ruling.docket_id] = ruling
        self._lengths[ruling.docket_id] = len(tokens)
        self._total_length += len(tokens)
        for term, frequency in Counter(tokens).items():
            self._postings.setdefault(term, {})[ruling.docket_id] = frequency
            self._posting_count += 1

    def _expand(self, terms: list[str]) -> list[list[str]]:
        """Index terms each query word may match: itself, or a prefix for the last word."""
        groups: list[list[str]] = []
        for position, term in enumerate(terms):
            is_last = position == len(terms) - 1
            if is_last and len(term) >= MIN_PREFIX_CHARS:
                groups.append([known for known in self._postings if known.startswith(term)])
            else:
                groups.append([term] if term in self._postings else [])
        return groups

    def _score(self, doc_id: str, terms: set[str]) -> float:
        average = self._total_length / len(self._documents)
        length_norm = BM25_K1 * (1 - BM25_B + BM25_B * self._lengths[doc_id] / average)
        score = 0.0
        for term in terms:
            holders = self._postings[term]
            frequency = holders.get(doc_id)
            if not frequency:
                continue
            idf = math.log(1 + (len(self._documents) - len(holders) + 0.5) / (len(holders) + 0.5))
            score += idf * frequency * (BM25_K1 + 1) / (frequency + length_norm)
        return score

    def _match(self, query: str) -> dict[str, set[str]] | None:
        """Map each matching document to the index terms it matched; ``None`` = no text query."""
        terms = list(dict.fromkeys(tokenize(query)))[:MAX_QUERY_TERMS]
        if not terms:
            return None
        matched: dict[str, set[str]] | None = None
        for group in self._expand(terms):
            holders: dict[str, set[str]] = {}
            for term in group:
                for doc_id in self._postings[term]:
                    holders.setdefault(doc_id, set()).add(term)
            if matched is None:
                matched = holders
            else:  # every query word must match (AND)
                matched = {
                    doc_id: found | holders[doc_id]
                    for doc_id, found in matched.items()
                    if doc_id in holders
                }
            if not matched:
                return {}
        return matched or {}

    def search(self, query: str, filters: SearchFilters) -> list[SearchHit]:
        """Every matching ruling, best first. The caller decides how many to send."""
        matched = self._match(query)
        if matched is None:
            candidates = [(ruling, 0.0, ()) for ruling in self._documents.values()]
        else:
            candidates = [
                (self._documents[doc_id], self._score(doc_id, terms), tuple(sorted(terms)))
                for doc_id, terms in matched.items()
            ]
        kept = [item for item in candidates if filters.accepts(item[0])]
        # Best score first; newer decisions and then the docket keep the order stable.
        kept.sort(key=lambda item: item[0].docket_id)
        kept.sort(key=lambda item: item[0].decision_date, reverse=True)
        kept.sort(key=lambda item: item[1], reverse=True)
        return [
            SearchHit(ruling, round(score, 4), terms, best_snippet(ruling.summary_excerpt, set(terms)))
            for ruling, score, terms in kept
        ]
