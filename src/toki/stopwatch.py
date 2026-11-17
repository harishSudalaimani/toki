"""Monotonic elapsed-time tracking for the stopwatch command."""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class Stopwatch:
    started_at: float

    @classmethod
    def start(cls) -> "Stopwatch":
        return cls(time.monotonic())

    def elapsed(self, now: float | None = None) -> float:
        return max(0.0, (time.monotonic() if now is None else now) - self.started_at)


def format_elapsed(seconds: float) -> str:
    total_tenths = max(0, int(seconds * 10))
    hours, rest = divmod(total_tenths, 36000)
    minutes, rest = divmod(rest, 600)
    whole_seconds, tenths = divmod(rest, 10)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d}.{tenths}"
