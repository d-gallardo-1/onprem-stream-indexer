"""Runtime settings read from environment variables."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass

API_PREFIX = "/api/v1"


@dataclass(frozen=True)
class Settings:
    #: Pause between two documents of a progressive search, in seconds.
    stream_delay: float
    #: Pause between two stages of a simulated crawl, in seconds.
    crawl_stage_delay: float
    #: Most documents one progressive search may send.
    max_stream_events: int


def _number(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, default))
    except ValueError:
        return default
    # "inf" and "nan" parse as floats but are not usable settings.
    return value if math.isfinite(value) else default


def load_settings() -> Settings:
    """Read settings; invalid values fall back to the defaults.

    * ``LEXSTREAM_STREAM_DELAY_MS``       pause between streamed search results (120)
    * ``LEXSTREAM_CRAWL_STAGE_DELAY_MS``  pause between simulated crawl stages (700)
    * ``LEXSTREAM_MAX_STREAM_EVENTS``     documents one search stream may send (100)
    """
    return Settings(
        stream_delay=min(5000.0, max(0.0, _number("LEXSTREAM_STREAM_DELAY_MS", 120))) / 1000,
        crawl_stage_delay=min(10_000.0, max(0.0, _number("LEXSTREAM_CRAWL_STAGE_DELAY_MS", 700)))
        / 1000,
        max_stream_events=min(500, max(1, int(_number("LEXSTREAM_MAX_STREAM_EVENTS", 100)))),
    )
