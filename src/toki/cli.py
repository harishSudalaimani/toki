"""Command line interface and foreground dashboard."""

from __future__ import annotations

import argparse
import sys
import threading
import time
from datetime import datetime

from .rabbit import dance
from .scheduler import Scheduler
from .service import create_alarm, delete_alarm, set_alarm_enabled
from .sound import play_alert
from .stopwatch import Stopwatch, format_elapsed
from .storage import AlarmStore, StorageError
from .timer import Countdown, format_duration, parse_duration


def _next_text(alarm, now: datetime) -> str:
    occurrence = alarm.next_occurrence(now)
    if occurrence is None:
        return "missed"
    if occurrence.date() == now.date():
        return occurrence.strftime("today at %H:%M")
    return occurrence.strftime("%a %d %b at %H:%M")


def _alarm_table(store: AlarmStore, now: datetime) -> list[str]:
    alarms = store.load()
    if not alarms:
        return ["  No alarms set."]
    rows = []
    for alarm in alarms:
        status = "on " if alarm.enabled else "off"
        rows.append(
            f"  {alarm.id}  [{status}] {alarm.time}  {alarm.label} "
            f"({alarm.repeat}, {_next_text(alarm, now)})"
        )
    return rows


def _notify(message: str) -> None:
    sound_result: list[bool] = []
    sound_thread = threading.Thread(target=lambda: sound_result.append(play_alert()), daemon=True)
    sound_thread.start()
    dance()
    sound_thread.join()
    audio_played = sound_result[0] if sound_result else False
    print(f"\n  ⏰ {message}", flush=True)
    if not audio_played:
        print("  Audio unavailable. Check your system sound settings.", flush=True)


def _fire_due(store: AlarmStore, scheduler: Scheduler, now: datetime) -> None:
    alarms = store.load()
    due = scheduler.due(alarms, now)
    if not due:
        return
    _notify(", ".join(alarm.label for alarm in due))
    changed = False
    for alarm in due:
        if alarm.repeat == "once":
            alarm.enabled = False
            changed = True
    if changed:
        store.save(alarms)


def _paint(value: str, code: str, enabled: bool) -> str:
    return f"\033[{code}m{value}\033[0m" if enabled else value


def _draw_dashboard(store: AlarmStore, now: datetime, tick: int = 0) -> None:
    color = sys.stdout.isatty()
    if color:
        # ANSI clear/home works in current Windows Terminal, macOS Terminal and Unix TTYs.
        print("\033[2J\033[H", end="")
    spinner = ("|", "/", "-", "\\")[tick % 4]
    print(_paint(f"TOKI {spinner}", "1;36", color))
    print(_paint("─" * 58, "2", color))
    print("  " + _paint(f"{now:%H:%M:%S}", "1;32", color) + f"     {now:%A, %B %d, %Y}")
    print("\n  ALARMS")
    print("\n".join(_alarm_table(store, now)))
    print("\n  TIMERS")
    print("  No active timers.  Run: toki timer 25m")
    print("\n  Press Ctrl+C to exit TOKI.", flush=True)


def run_dashboard(store: AlarmStore) -> int:
    scheduler = Scheduler()
    try:
        tick = 0
        while True:
            now = datetime.now()
            _draw_dashboard(store, now, tick)
            _fire_due(store, scheduler, now)
            time.sleep(1)
            tick += 1
    except KeyboardInterrupt:
        print("\nTOKI closed.")
        return 0


def run_timer(store: AlarmStore, seconds: int) -> int:
    countdown = Countdown.start(seconds)
    scheduler = Scheduler()
    try:
        while not countdown.complete:
            now = datetime.now()
            _fire_due(store, scheduler, now)
            remaining = countdown.remaining()
            filled = int(24 * min(1.0, countdown.elapsed() / countdown.duration))
            bar = "█" * filled + "░" * (24 - filled)
            color = sys.stdout.isatty()
            level = "32" if remaining > 10 else "33" if remaining > 3 else "31"
            line = f"Timer: {format_duration(remaining)}  [{bar}]  Ctrl+C to cancel"
            if color:
                print("\r\033[2K" + _paint(line, level, True), end="", flush=True)
            else:
                print(line, flush=True)
            time.sleep(1)
        if sys.stdout.isatty():
            print()
        _notify("Timer complete")
        return 0
    except KeyboardInterrupt:
        print("\nTimer cancelled.")
        return 130


def run_stopwatch(store: AlarmStore) -> int:
    stopwatch = Stopwatch.start()
    scheduler = Scheduler()
    spinner = ("◴", "◷", "◶", "◵")
    tick = 0
    tty = sys.stdout.isatty()
    try:
        while True:
            _fire_due(store, scheduler, datetime.now())
            text = f"Stopwatch {spinner[tick % len(spinner)]}  {format_elapsed(stopwatch.elapsed())}  ·  Ctrl+C to stop"
            if tty:
                print("\r\033[2K" + _paint(text, "1;36", True), end="", flush=True)
            else:
                print(text, flush=True)
            time.sleep(0.1 if tty else 1)
            tick += 1
    except KeyboardInterrupt:
        if tty:
            print()
        print(f"Stopped at {format_elapsed(stopwatch.elapsed())}.")
        return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="toki", description="A minimal command-line time companion.")
    commands = parser.add_subparsers(dest="command")

    alarm = commands.add_parser("alarm", help="manage alarms")
    alarm_commands = alarm.add_subparsers(dest="alarm_command", required=True)
    set_command = alarm_commands.add_parser("set", help="create an alarm")
    set_command.add_argument("time", help="local time in 24-hour HH:MM format")
    set_command.add_argument("--label", default="Alarm", help="short alarm label")
    set_command.add_argument("--repeat", choices=("once", "daily"), default="once")
    set_command.add_argument("--daily", action="store_true", help="repeat every day (shorthand for --repeat daily)")
    alarm_commands.add_parser("list", help="list alarms")
    for action in ("delete", "enable", "disable"):
        sub = alarm_commands.add_parser(action, help=f"{action} an alarm")
        sub.add_argument("id", help="alarm ID")

    timer = commands.add_parser("timer", help="start a countdown (for example: 30m or 1h30m)")
    timer.add_argument("duration")
    commands.add_parser("stopwatch", help="measure elapsed time; press Ctrl+C to stop")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    store = AlarmStore()
    try:
        if args.command is None:
            return run_dashboard(store)
        if args.command == "timer":
            return run_timer(store, parse_duration(args.duration))
        if args.command == "stopwatch":
            return run_stopwatch(store)
        if args.alarm_command == "set":
            repeat = "daily" if args.daily else args.repeat
            alarm = create_alarm(store, args.time, args.label, repeat)
            print(f"Alarm {alarm.id} set for {alarm.time} ({alarm.repeat}).")
            return 0
        if args.alarm_command == "list":
            print("\n".join(_alarm_table(store, datetime.now())))
            return 0
        if args.alarm_command == "delete":
            if not delete_alarm(store, args.id):
                print(f"No alarm found with ID {args.id}.", file=sys.stderr)
                return 1
            print(f"Deleted alarm {args.id}.")
            return 0
        if args.alarm_command in {"enable", "disable"}:
            enabled = args.alarm_command == "enable"
            if not set_alarm_enabled(store, args.id, enabled):
                print(f"No alarm found with ID {args.id}.", file=sys.stderr)
                return 1
            print(f"Alarm {args.id} {'enabled' if enabled else 'disabled'}.")
            return 0
    except (StorageError, ValueError) as exc:
        print(f"toki: {exc}", file=sys.stderr)
        return 2
    return 0
