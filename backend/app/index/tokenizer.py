"""Text normalisation shared by indexing and querying."""

from __future__ import annotations

import re
import unicodedata

from ..models import Ruling

_WORD = re.compile(r"[a-z0-9]+")
STOPWORDS = frozenset(
    "a an and are as at be by for from in is it its of on or that the this to was were with".split()
)
#: A query is cut to this many terms; longer input adds cost, not precision.
MAX_QUERY_TERMS = 12


def tokenize(text: str) -> list[str]:
    """Lower-case words without accents or punctuation, stop words removed."""
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return [word for word in _WORD.findall(folded.lower()) if word not in STOPWORDS]


def ruling_tokens(ruling: Ruling) -> list[str]:
    """Tokens of every searchable field. The title counts twice, so it ranks higher."""
    fields = [
        ruling.title,
        ruling.title,
        ruling.summary_excerpt,
        ruling.authority,
        ruling.judge_or_inspector,
        ruling.docket_id,
        *ruling.cited_articles,
    ]
    return tokenize(" ".join(fields))
