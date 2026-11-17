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


def create_alarm(
    store: AlarmStore,
    value: str,
    label: str | None = None,
    repeat: str = "once",
    now: datetime | None = None,
) -> Alarm:
    value = parse_alarm_time(value)
    if repeat not in {"once", "daily"}:
        raise ValueError("repeat must be once or daily")
    alarms = store.load()
    used_labels = {alarm.label.casefold() for alarm in alarms}
    if label is None or not label.strip():
        label = "Alarm"
        suffix = 2
        while label.casefold() in used_labels:
            label = f"Alarm {suffix}"
            suffix += 1
    else:
        label = label.strip()
        if label.casefold() in used_labels:
            raise ValueError(f"an alarm already uses the label {label!r}; choose a unique label")
    now = now or datetime.now()
    alarm_time = datetime.strptime(value, "%H:%M").time()
    occurrence = datetime.combine(now.date(), alarm_time)
    if repeat == "once":
        if occurrence <= now:
            occurrence += timedelta(days=1)
        target_date = occurrence.date().isoformat()
    else:
        target_date = None
    alarm = Alarm(uuid4().hex[:8], value, label, repeat, True, target_date)
    alarms.append(alarm)
    store.save(alarms)
    return alarm


def delete_alarms_by_label(store: AlarmStore, label: str) -> int:
    """Delete every alarm with this label, matching case-insensitively."""
    alarms = store.load()
    remaining = [alarm for alarm in alarms if alarm.label.casefold() != label.casefold()]
    deleted = len(alarms) - len(remaining)
    if deleted:
        store.save(remaining)
    return deleted


def set_alarms_enabled_by_label(store: AlarmStore, label: str, enabled: bool) -> int:
    """Set enabled state on every alarm with this label, matching case-insensitively."""
    alarms = store.load()
    matches = [alarm for alarm in alarms if alarm.label.casefold() == label.casefold()]
    if matches:
        for alarm in matches:
            alarm.enabled = enabled
        store.save(alarms)
    return len(matches)


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
