"""Command line interface for TOKI's clock, alarms, and timer."""

from __future__ import annotations

import argparse
import math
import shlex
import shutil
import sys
import threading
import time
from datetime import datetime

from .keys import key_reader
from .models import Alarm
from .scheduler import Scheduler
from .service import create_alarm, delete_alarms_by_label, set_alarms_enabled_by_label
from .sound import play_alert, ring_alert
from .storage import AlarmStore, StorageError
from .timer import Countdown, format_duration, parse_duration
from .ui import draw_alert, draw_dashboard, draw_timer

ALERT_DURATION_SECONDS = 60.0
ALARM_POLL_SECONDS = 0.5
HELP_NOTICE_SECONDS = 12.0
NOTICE_SECONDS = 4.0

DASHBOARD_HELP = (
    'ALARM SET 07:30 --LABEL "GYM"\n'
    "  CREATE A ONE-TIME ALARM.\n"
    'ALARM SET 07:30 --LABEL "GYM" --DAILY\n'
    "  CREATE A DAILY ALARM.\n"
    "ALARM SET 07:30 --REPEAT DAILY\n"
    "  SET THE ALARM TO REPEAT EACH DAY.\n"
    "ALARM LIST\n"
    "  SHOW SAVED ALARMS AND THEIR STATUS.\n"
    'ALARM ENABLE "GYM"\n'
    "  TURN AN ALARM ON BY LABEL.\n"
    'ALARM DISABLE "GYM"\n'
    "  TURN AN ALARM OFF BY LABEL.\n"
    'ALARM DELETE "GYM"\n'
    "  REMOVE AN ALARM BY LABEL.\n\n"
    "TIMER 25M / 90S / 1H30M\n"
    "  START A COUNTDOWN USING SECONDS, MINUTES, OR HOURS.\n"
    "TIMER STOP / TIMER CANCEL\n"
    "  STOP THE RUNNING COUNTDOWN."
)


def _print_accent(text: str, *, error: bool = False) -> None:
    stream = sys.stderr if error else sys.stdout
    rendered = text.upper()
    if stream.isatty():
        rendered = f"\033[36m{rendered}\033[0m"
    print(rendered, file=stream, flush=True)


def _next_text(alarm: Alarm, now: datetime) -> str:
    occurrence = alarm.next_occurrence(now)
    if occurrence is None:
        return "missed"
    if occurrence.date() == now.date():
        return "today"
    return occurrence.strftime("%a %d %b")


def _dashboard_alarms(store: AlarmStore, now: datetime) -> list[str]:
    alarms = store.load()
    rows: list[str] = []
    for alarm in alarms:
        state = "●" if alarm.enabled else "○"
        when = _next_text(alarm, now)
        rows.append(f"  {state}  {alarm.time}  {alarm.label}  · {when}")
    return rows


def _alarm_table(store: AlarmStore, now: datetime) -> list[str]:
    alarms = store.load()
    if not alarms:
        return []
    rows: list[str] = []
    for alarm in alarms:
        state = "on" if alarm.enabled else "off"
        rows.append(
            f"{alarm.label}  [{state}]  {alarm.time}  "
            f"({alarm.repeat}, {_next_text(alarm, now)})"
        )
    return rows


def _notify(message: str) -> None:
    interactive = sys.stdin.isatty() and sys.stdout.isatty()
    if not interactive:
        audio = play_alert()
        _print_accent(f"\n{message}")
        if not audio:
            _print_accent("Audio unavailable.")
        return

    stop = threading.Event()
    sound_result: list[bool] = []
    sound_thread = threading.Thread(
        target=lambda: sound_result.append(ring_alert(stop, ALERT_DURATION_SECONDS)),
        daemon=True,
    )
    sound_thread.start()
    start = time.monotonic()
    last_displayed_second = None
    try:
        with key_reader() as pressed:
            while True:
                remaining = math.ceil(
                    max(0.0, ALERT_DURATION_SECONDS - (time.monotonic() - start))
                )
                if remaining != last_displayed_second:
                    draw_alert(message, remaining)
                    last_displayed_second = remaining
                if remaining == 0 or pressed(0.12) is not None:
                    break
    finally:
        stop.set()
        sound_thread.join(timeout=2.0)

    if sound_result and not sound_result[0]:
        _print_accent("\nAudio unavailable.")
    else:
        _print_accent("\nAlert silenced.")


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


def _handle_dashboard_command(
    text: str,
    store: AlarmStore,
    active_timer: Countdown | None,
) -> tuple[Countdown | None, str, bool]:
    """Run one command entered on the dashboard."""
    try:
        words = shlex.split(text)
        if not words:
            return active_timer, "", False

        command = words[0].lower()
        if command == "quit":
            return active_timer, "", True
        if command == "help":
            return active_timer, DASHBOARD_HELP, False
        if command == "timer":
            if len(words) == 2 and words[1].lower() in {"stop", "cancel"}:
                if active_timer is None:
                    return None, "", False
                return None, "Timer stopped.", False
            if len(words) != 2:
                raise ValueError("use timer DURATION, for example: timer 25m")
            if active_timer is not None:
                raise ValueError("a timer is already running; use timer stop first")
            seconds = parse_duration(words[1])
            timer = Countdown.start(seconds)
            return timer, f"Timer started: {format_duration(seconds)}", False

        if command != "alarm" or len(words) < 2:
            raise ValueError("enter alarm or timer commands here; type help for examples")
        action = words[1].lower()
        if action == "set":
            if len(words) < 3:
                raise ValueError(
                    'example: alarm set 07:30 --label "GYM" --daily; '
                    "omit --daily for a one-time alarm"
                )
            alarm_time = words[2]
            label = None
            repeat = "once"
            index = 3
            while index < len(words):
                option = words[index].lower()
                if option == "--daily":
                    repeat = "daily"
                    index += 1
                elif option == "--repeat" and index + 1 < len(words):
                    repeat = words[index + 1].lower()
                    index += 2
                elif option == "--label" and index + 1 < len(words):
                    label = words[index + 1]
                    index += 2
                else:
                    raise ValueError(f"unknown or incomplete alarm option: {option}")
            alarm = create_alarm(store, alarm_time, label, repeat)
            message = f"Alarm {alarm.label!r} set for {alarm.time} ({alarm.repeat})."
            return active_timer, message, False

        if action == "list":
            alarms = store.load()
            if not alarms:
                return active_timer, "", False
            summary = "\n".join(
                f"{item.label}  {'on' if item.enabled else 'off'}  {item.time}  "
                f"({item.repeat}, {_next_text(item, datetime.now())})"
                for item in alarms
            )
            return active_timer, summary, False

        if action in {"delete", "enable", "disable"} and len(words) >= 3:
            label = " ".join(words[2:])
            if action == "delete":
                deleted = delete_alarms_by_label(store, label)
                if not deleted:
                    raise ValueError(f"no alarm found with label {label!r}")
                if deleted == 1:
                    message = f"Deleted alarm {label!r}."
                else:
                    message = f"Deleted {deleted} alarms named {label!r}."
                return active_timer, message, False
            enabled = action == "enable"
            changed = set_alarms_enabled_by_label(store, label, enabled)
            if not changed:
                raise ValueError(f"no alarm found with label {label!r}")
            if changed == 1:
                message = f"Alarm {label!r} {'enabled' if enabled else 'disabled'}."
            else:
                state = "enabled" if enabled else "disabled"
                message = f"{changed} alarms named {label!r} {state}."
            return active_timer, message, False
        raise ValueError("use alarm set, list, enable, disable, or delete")
    except (StorageError, ValueError) as exc:
        return active_timer, str(exc), False


def run_dashboard(store: AlarmStore) -> int:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        _print_accent(
            "TOKI needs an interactive terminal. Run `toki` in your terminal.",
            error=True,
        )
        return 2

    scheduler = Scheduler()
    active_timer: Countdown | None = None
    command_buffer = ""
    command_cursor = 0
    notice = ""
    notice_until = 0.0
    last_alarm_poll = -1.0
    last_screen = None
    try:
        with key_reader() as read_key:
            while True:
                now = datetime.now()
                elapsed = time.monotonic()
                if elapsed - last_alarm_poll >= ALARM_POLL_SECONDS:
                    _fire_due(store, scheduler, now)
                    last_alarm_poll = elapsed

                if active_timer and active_timer.complete:
                    active_timer = None
                    _notify("Timer complete")
                    notice = ""
                    notice_until = 0.0

                key = read_key(0.1)
                if key in {"\r", "\n"}:
                    submitted = command_buffer
                    active_timer, result, should_quit = _handle_dashboard_command(
                        submitted, store, active_timer
                    )
                    command_buffer = ""
                    command_cursor = 0
                    notice = result
                    notice_seconds = (
                        HELP_NOTICE_SECONDS
                        if submitted.strip().lower() == "help"
                        else NOTICE_SECONDS
                    )
                    notice_until = time.monotonic() + notice_seconds
                    if should_quit:
                        break
                elif key in {"\x08", "\x7f"}:
                    if command_cursor:
                        command_buffer = (
                            command_buffer[: command_cursor - 1]
                            + command_buffer[command_cursor:]
                        )
                        command_cursor -= 1
                elif key == "LEFT":
                    command_cursor = max(0, command_cursor - 1)
                elif key == "RIGHT":
                    command_cursor = min(len(command_buffer), command_cursor + 1)
                elif key == "HOME" or key == "\x01":
                    command_cursor = 0
                elif key == "END" or key == "\x05":
                    command_cursor = len(command_buffer)
                elif key == "DELETE":
                    if command_cursor < len(command_buffer):
                        command_buffer = (
                            command_buffer[:command_cursor]
                            + command_buffer[command_cursor + 1 :]
                        )
                elif key == "\x15":
                    command_buffer = ""
                    command_cursor = 0
                elif key in {"UP", "DOWN"}:
                    # Vertical arrows are intentionally not command text.
                    pass
                elif key and key.isprintable():
                    command_buffer = (
                        command_buffer[:command_cursor]
                        + key
                        + command_buffer[command_cursor:]
                    )
                    command_cursor += len(key)

                if notice and time.monotonic() >= notice_until:
                    notice = ""

                now = datetime.now()
                alarms = _dashboard_alarms(store, now)
                remaining = format_duration(active_timer.remaining()) if active_timer else None
                size = shutil.get_terminal_size((80, 24))
                screen_state = (
                    now.strftime("%Y-%m-%d %H:%M"),
                    tuple(alarms),
                    remaining,
                    command_buffer,
                    command_cursor,
                    notice,
                    size.columns,
                    size.lines,
                )
                if screen_state != last_screen:
                    draw_dashboard(
                        now, alarms, remaining, command_buffer, notice, command_cursor
                    )
                    last_screen = screen_state
    except KeyboardInterrupt:
        return 0
    finally:
        if sys.stdout.isatty():
            print("\033[?25h\033[0m\n", end="")
    return 0


def run_timer(store: AlarmStore, seconds: int) -> int:
    countdown = Countdown.start(seconds)
    scheduler = Scheduler()
    interactive = sys.stdin.isatty() and sys.stdout.isatty()
    try:
        while not countdown.complete:
            _fire_due(store, scheduler, datetime.now())
            remaining = countdown.remaining()
            if interactive:
                draw_timer(remaining, seconds, elapsed=countdown.elapsed())
            else:
                _print_accent(f"Timer: {format_duration(remaining)}")
            time.sleep(min(1.0, max(0.01, countdown.remaining())))
        if interactive:
            draw_timer(0, seconds, elapsed=float(seconds))
        _notify("Timer complete")
        return 0
    except KeyboardInterrupt:
        if interactive:
            print("\033[0m\n", end="")
        _print_accent("Timer cancelled.")
        return 130


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="toki",
        description="A minimal clock, alarm, and timer for your terminal.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Run `toki` to open the dashboard. You can also use these commands directly\n"
            "in your shell, or enter them at the dashboard prompt without the `toki` prefix:\n"
            "  toki alarm set 07:30\n"
            '  toki alarm set 07:30 --label "GYM" --daily\n'
            "  toki alarm list | toki alarm enable LABEL | toki alarm disable LABEL\n"
            "  toki alarm delete LABEL\n"
            "  toki timer 25m\n"
            "Duration units: s, m, h (for example: toki timer 1h30m)."
        ),
    )
    parser.add_argument("-help", action="help", help="show this help message and exit")
    commands = parser.add_subparsers(dest="command")

    alarm = commands.add_parser("alarm", help="manage alarms")
    alarm_commands = alarm.add_subparsers(dest="alarm_command", required=True)
    set_command = alarm_commands.add_parser("set", help="create an alarm")
    set_command.add_argument("time", help="local time in 24-hour HH:MM format")
    set_command.add_argument("--label", help="short alarm label")
    set_command.add_argument("--repeat", choices=("once", "daily"), default="once")
    set_command.add_argument(
        "--daily", action="store_true", help="repeat every day (shorthand for --repeat daily)"
    )
    alarm_commands.add_parser("list", help="list alarms")
    for action in ("delete", "enable", "disable"):
        subcommand = alarm_commands.add_parser(action, help=f"{action} an alarm")
        subcommand.add_argument(
            "label",
            nargs="+",
            help="alarm label; quote labels containing spaces",
        )

    timer = commands.add_parser("timer", help="start a countdown (for example: 30m or 1h30m)")
    timer.add_argument("duration")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)
    store = AlarmStore()
    try:
        if args.command is None:
            return run_dashboard(store)
        if args.command == "timer":
            return run_timer(store, parse_duration(args.duration))
        if args.alarm_command == "set":
            repeat = "daily" if args.daily else args.repeat
            alarm = create_alarm(store, args.time, args.label, repeat)
            _print_accent(f"Alarm {alarm.label!r} set for {alarm.time} ({alarm.repeat}).")
            return 0
        if args.alarm_command == "list":
            rows = _alarm_table(store, datetime.now())
            if rows:
                _print_accent("\n".join(rows))
            return 0
        if args.alarm_command == "delete":
            label = " ".join(args.label)
            deleted = delete_alarms_by_label(store, label)
            if not deleted:
                _print_accent(f"No alarm found with label {label!r}.", error=True)
                return 1
            if deleted == 1:
                _print_accent(f"Deleted alarm {label!r}.")
            else:
                _print_accent(f"Deleted {deleted} alarms named {label!r}.")
            return 0
        if args.alarm_command in {"enable", "disable"}:
            label = " ".join(args.label)
            enabled = args.alarm_command == "enable"
            changed = set_alarms_enabled_by_label(store, label, enabled)
            if not changed:
                _print_accent(f"No alarm found with label {label!r}.", error=True)
                return 1
            if changed == 1:
                _print_accent(f"Alarm {label!r} {'enabled' if enabled else 'disabled'}.")
            else:
                state = "enabled" if enabled else "disabled"
                _print_accent(f"{changed} alarms named {label!r} {state}.")
            return 0
    except (StorageError, ValueError) as exc:
        _print_accent(f"toki: {exc}", error=True)
        return 2
    return 0
