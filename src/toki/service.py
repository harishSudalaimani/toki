"""Alarm operations independent of CLI presentation."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from .models import Alarm
from .storage import AlarmStore


def parse_alarm_time(value: str) -> str:
    try:
        parsed = datetime.strptime(value, "%H:%M")
    except ValueError as exc:
        raise ValueError("time must use 24-hour HH:MM format (for example, 07:30)") from exc
    if parsed.strftime("%H:%M") != value:
        raise ValueError("time must use 24-hour HH:MM format (for example, 07:30)")
    return value


def create_alarm(store: AlarmStore, value: str, label: str = "Alarm", repeat: str = "once",
                 now: datetime | None = None) -> Alarm:
    value = parse_alarm_time(value)
    if repeat not in {"once", "daily"}:
        raise ValueError("repeat must be once or daily")
    now = now or datetime.now()
    alarm_time = datetime.strptime(value, "%H:%M").time()
    occurrence = datetime.combine(now.date(), alarm_time)
    if repeat == "once":
        if occurrence <= now:
            occurrence += timedelta(days=1)
        target_date = occurrence.date().isoformat()
    else:
        target_date = None
    alarm = Alarm(uuid4().hex[:8], value, label.strip() or "Alarm", repeat, True, target_date)
    alarms = store.load()
    alarms.append(alarm)
    store.save(alarms)
    return alarm


def delete_alarm(store: AlarmStore, alarm_id: str) -> bool:
    alarms = store.load()
    remaining = [alarm for alarm in alarms if alarm.id != alarm_id]
    if len(remaining) == len(alarms):
        return False
    store.save(remaining)
    return True


def set_alarm_enabled(store: AlarmStore, alarm_id: str, enabled: bool) -> bool:
    alarms = store.load()
    alarm = next((item for item in alarms if item.id == alarm_id), None)
    if alarm is None:
        return False
    alarm.enabled = enabled
    store.save(alarms)
    return True
