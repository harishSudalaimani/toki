"""Foreground alarm polling."""

from __future__ import annotations

from datetime import datetime

from .models import Alarm


class Scheduler:
    """Find alarms whose local HH:MM slot has arrived, once per date."""

    def __init__(self) -> None:
        self._fired: set[tuple[str, str]] = set()

    def due(self, alarms: list[Alarm], now: datetime | None = None) -> list[Alarm]:
        now = now or datetime.now()
        fired: list[Alarm] = []
        for alarm in alarms:
            if not alarm.enabled or alarm.time != now.strftime("%H:%M"):
                continue
            if alarm.repeat == "once" and alarm.date != now.date().isoformat():
                continue
            key = (alarm.id, now.date().isoformat())
            if key not in self._fired:
                self._fired.add(key)
                fired.append(alarm)
        return fired
