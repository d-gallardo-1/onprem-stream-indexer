"""Structured filters applied on top of the text match."""

from __future__ import annotations

from dataclasses import dataclass

from ..models import Outcome, Ruling


@dataclass(frozen=True)
class SearchFilters:
    authority: str | None = None
    outcome: Outcome | None = None

    def accepts(self, ruling: Ruling) -> bool:
        if self.authority is not None and ruling.authority != self.authority:
            return False
        if self.outcome is not None and ruling.outcome != self.outcome:
            return False
        return True
