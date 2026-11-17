"""Countdown parsing and monotonic timer state."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass

_TOKEN = re.compile(r"(\d+)([hms])")


def parse_duration(value: str) -> int:
    if not value:
        raise ValueError("duration is required, such as 25m or 1h30m")
    position = 0
    total = 0
    seen: set[str] = set()
    scale = {"h": 3600, "m": 60, "s": 1}
    for match in _TOKEN.finditer(value.lower()):
        if match.start() != position:
            raise ValueError("use a duration such as 90s, 30m, or 1h30m")
        amount, unit = int(match.group(1)), match.group(2)
        if unit in seen:
            raise ValueError(f"duration unit '{unit}' may only appear once")
        seen.add(unit)
        total += amount * scale[unit]
        position = match.end()
    if position != len(value) or total <= 0:
        raise ValueError("duration must be greater than zero; use 90s, 30m, or 1h30m")
    return total


@dataclass
class Countdown:
    duration: int
    started_at: float

    @classmethod
    def start(cls, duration: int) -> "Countdown":
        if duration <= 0:
            raise ValueError("duration must be greater than zero")
        return cls(duration, time.monotonic())

    def remaining(self, now: float | None = None) -> int:
        elapsed = (time.monotonic() if now is None else now) - self.started_at
        return max(0, self.duration - int(elapsed))

    @property
    def complete(self) -> bool:
        return self.remaining() == 0


def format_duration(seconds: int) -> str:
    hours, remainder = divmod(max(0, seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
