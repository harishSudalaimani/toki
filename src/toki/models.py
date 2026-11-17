"""Core data models for alarms."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta


@dataclass
class Alarm:
    id: str
    time: str
    label: str = "Alarm"
    repeat: str = "once"
    enabled: bool = True
    date: str | None = None

    def next_occurrence(self, now: datetime | None = None) -> datetime | None:
        """Return the next scheduled local occurrence, if one remains."""
        if not self.enabled:
            return None
        now = now or datetime.now()
        alarm_time = time.fromisoformat(self.time)
        if self.repeat == "once":
            if self.date is None:
                return None
            occurrence = datetime.combine(date.fromisoformat(self.date), alarm_time)
            return occurrence if occurrence >= now else None

        occurrence = datetime.combine(now.date(), alarm_time)
        return occurrence if occurrence >= now else occurrence + timedelta(days=1)

    @classmethod
    def from_dict(cls, data: dict) -> "Alarm":
        alarm = cls(**data)
        # Validate persisted values before they can reach scheduling or display.
        datetime.strptime(alarm.time, "%H:%M")
        if alarm.repeat not in {"once", "daily"}:
            raise ValueError("repeat must be 'once' or 'daily'")
        if alarm.repeat == "once" and alarm.date is not None:
            date.fromisoformat(alarm.date)
        if not alarm.id or not isinstance(alarm.enabled, bool):
            raise ValueError("invalid alarm id or enabled flag")
        return alarm

    def to_dict(self) -> dict:
        return asdict(self)
