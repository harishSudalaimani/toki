"""Terminal layouts for TOKI's clock, timer, and alerts."""

from __future__ import annotations

import shutil
import sys
import unicodedata
from datetime import datetime

_DIGITS = {
    "0": ("███", "█ █", "█ █", "█ █", "███"),
    "1": (" ██", "  █", "  █", "  █", "███"),
    "2": ("███", "  █", "███", "█  ", "███"),
    "3": ("███", "  █", "███", "  █", "███"),
    "4": ("█ █", "█ █", "███", "  █", "  █"),
    "5": ("███", "█  ", "███", "  █", "███"),
    "6": ("███", "█  ", "███", "█ █", "███"),
    "7": ("███", "  █", "  █", "  █", "  █"),
    "8": ("███", "█ █", "███", "█ █", "███"),
    "9": ("███", "█ █", "███", "  █", "███"),
    ":": ("   ", " █ ", "   ", " █ ", "   "),
}
_ACCENT = "36"
_CLOCK = "97"
_DATE = "94"
_TIMER = "95"
_TIMER_DESCRIPTION = "93"
_ALARM = "93"
_ALARM_COMMAND = "94"
_ALARM_ITEM = "92"
_ALARM_DESCRIPTION = "92"
_MORE = "95"
_HELP = "96"
_INPUT = "96"
_MUTED = "90"


def _color(text: str, code: str, enabled: bool) -> str:
    return f"\033[{code}m{text}\033[0m" if enabled else text


def _char_width(char: str) -> int:
    if unicodedata.combining(char) or unicodedata.category(char) in {"Cf", "Mn", "Me"}:
        return 0
    return 2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1


def _cell_width(text: str) -> int:
    return sum(_char_width(char) for char in text)


def _fit(text: str, width: int) -> str:
    result = []
    used = 0
    for char in text:
        char_width = _char_width(char)
        if used + char_width > width:
            break
        result.append(char)
        used += char_width
    return "".join(result)


def _wrap_words(text: str, width: int) -> list[str]:
    """Wrap notice text so dashboard help stays readable in narrow terminals."""
    if width <= 0:
        return [text]
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if _cell_width(candidate) <= width:
            current = candidate
            continue
        if current:
            lines.append(current)
            current = ""
        if _cell_width(word) <= width:
            current = word
            continue
        piece = ""
        for char in word:
            if piece and _cell_width(piece + char) > width:
                lines.append(piece)
                piece = ""
            piece += char
        current = piece
    if current or not lines:
        lines.append(current)
    return lines


def _center(text: str, width: int) -> str:
    text = _fit(text, width)
    padding = max(0, width - _cell_width(text))
    left = padding // 2
    return " " * left + text + " " * (padding - left)


def _clock_art(value: str, scale: int) -> list[str]:
    glyphs = [_DIGITS[char] for char in value]
    rows = []
    for row_index in range(5):
        # Scale each glyph and its single-cell gap together; double-scaling the gap
        # pushed large digits past the card edge.
        line = " ".join(glyph[row_index] for glyph in glyphs)
        expanded = "".join(char * scale for char in line)
        rows.extend([expanded] * scale)
    return rows


def _terminal() -> tuple[int, int]:
    size = shutil.get_terminal_size((80, 24))
    return max(1, size.columns), max(1, size.lines)


def _card_line(text: str, inner: int, style: str | None = None, *, centered: bool = True) -> str:
    text = text.upper()
    if centered:
        padded = _center(text, inner)
    else:
        text = _fit(text, inner)
        padded = text + " " * max(0, inner - _cell_width(text))
    rendered = _color(padded, style, sys.stdout.isatty()) if style else padded
    return "│" + rendered + "│"


def _card(content: list[tuple[str, str | None, bool]], inner: int) -> list[str]:
    lines = [_color("╭" + "─" * inner + "╮", _ACCENT, sys.stdout.isatty())]
    lines.extend(
        _card_line(text, inner, style, centered=centered)
        for text, style, centered in content
    )
    lines.append(_color("╰" + "─" * inner + "╯", _ACCENT, sys.stdout.isatty()))
    return lines


def _paint(
    lines: list[str],
    columns: int,
    rows: int,
    card_width: int,
    cursor: tuple[int, int] | None = None,
) -> None:
    """Place a card in the terminal and refresh it without clearing the screen."""
    left = max(0, (columns - card_width) // 2)
    lines = [(" " * left) + line for line in lines]
    if not sys.stdout.isatty():
        sys.stdout.write("\n".join(lines) + "\n")
        sys.stdout.flush()
        return

    visible = lines[-rows:]
    dropped = len(lines) - len(visible)
    top = max(0, (rows - len(visible)) // 2)
    page = [""] * top + visible
    page.extend([""] * (rows - len(page)))
    output = "\033[H" + "\r\n".join(line + "\033[K" for line in page)
    if cursor is not None:
        line_index, cursor_offset = cursor
        cursor_row = max(1, min(rows, top + line_index - dropped + 1))
        cursor_column = max(1, min(columns, left + 2 + cursor_offset))
        output += f"\033[?25h\033[{cursor_row};{cursor_column}H"
    sys.stdout.write(output)
    sys.stdout.flush()


def _dimensions(columns: int) -> tuple[int, int]:
    width = min(100, max(3, columns - 2))
    return width, width - 2


def _timer_value(remaining: int, width: int) -> str:
    hours, remainder = divmod(remaining, 3600)
    minutes, seconds = divmod(remainder, 60)
    if width >= 8:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    if width >= 5:
        return f"{hours}h{minutes:02d}" if hours else f"{minutes:02d}:{seconds:02d}"
    return f"{remaining}s"


def draw_dashboard(
    now: datetime,
    alarms: list[str],
    timer_text: str | None = None,
    command: str = "",
    notice: str = "",
    command_cursor: int | None = None,
) -> None:
    columns, rows = _terminal()
    width, inner = _dimensions(columns)
    notice = notice.upper()
    clock_value = now.strftime("%H:%M") if inner >= 5 else now.strftime("%H%M")
    if notice:
        hint_lines: list[tuple[str, str]] = []
        help_group = ""
        for line in notice.splitlines():
            is_explanation = line.startswith("  ")
            text = line.strip()
            if text.startswith("ALARM "):
                help_group = "alarm"
                style = _ALARM_COMMAND
            elif text.startswith("TIMER "):
                help_group = "timer"
                style = _TIMER
            elif is_explanation and help_group == "alarm":
                style = _ALARM_DESCRIPTION
            elif is_explanation and help_group == "timer":
                style = _TIMER_DESCRIPTION
            elif text.startswith("ALARM"):
                style = _ALARM_COMMAND
            elif text.startswith("TIMER"):
                style = _TIMER
            else:
                style = _ACCENT
            wrapped = _wrap_words(line.strip(), max(1, inner - 2))
            hint_lines.extend(
                (f"  {part}" if inner > 2 else part, style) for part in wrapped
            )
    else:
        hint_lines = [(" " * max(0, inner - 4) + "HELP", _HELP)]
    compact = inner < 19 or rows < 17
    alarm_limit = 1 if compact or len(hint_lines) > 1 else 2
    shown_alarms = alarms[:alarm_limit]
    more_count = max(0, len(alarms) - len(shown_alarms))
    has_details = timer_text is not None or bool(alarms)

    if compact:
        content: list[tuple[str, str | None, bool]] = [
            ("TOKI", _ACCENT, True),
            (clock_value, _CLOCK, True),
            (now.strftime("%a, %d %b %Y"), _DATE, True),
        ]
        if timer_text is not None:
            content.append((f"TIMER  {timer_text}", _TIMER, True))
        if alarms:
            content.append(("ALARMS", _ALARM, True))
            content.extend((line, _ALARM_ITEM, False) for line in shown_alarms)
            if more_count:
                content.append((f"+ {more_count} MORE", _MORE, False))
    else:
        detail_lines = int(has_details) + int(timer_text is not None) + int(bool(alarms))
        detail_lines += len(shown_alarms) + int(bool(more_count))
        fixed_lines = 6 + detail_lines + len(hint_lines)
        scale = max(1, min(3, inner // 19, max(1, (rows - fixed_lines) // 5)))
        content = [
            ("TOKI", _ACCENT, True),
            ("", None, True),
            *((line, _CLOCK, True) for line in _clock_art(clock_value, scale)),
            (now.strftime("%A, %d %B %Y"), _DATE, True),
        ]
        if has_details:
            content.append(("─" * inner, _MUTED, True))
        if timer_text is not None:
            content.append((f"TIMER  {timer_text}", _TIMER, True))
        if alarms:
            content.append(("ALARMS", _ALARM, True))
            content.extend((line, _ALARM_ITEM, False) for line in shown_alarms)
            if more_count:
                content.append((f"+ {more_count} MORE", _MORE, False))
    cursor_index = (
        len(command)
        if command_cursor is None
        else max(0, min(command_cursor, len(command)))
    )
    # Keep one cell after the input for the terminal's visible cursor.
    input_width = max(0, inner - 3)
    if len(command) <= input_width:
        start = 0
    else:
        start = max(0, min(cursor_index - input_width + 1, len(command) - input_width))
    visible_command = command[start : start + input_width]
    command_line = _fit("> ", inner) + visible_command.upper()
    cursor_offset = 2 + _cell_width(command[start:cursor_index])
    cursor = (len(content) + 1, min(inner, cursor_offset))
    content.append((command_line, _INPUT, False))
    content.extend((line, style, False) for line, style in hint_lines)
    _paint(_card(content, inner), columns, rows, width, cursor)


def draw_timer(
    remaining: int,
    duration: int,
    elapsed: float | None = None,
) -> None:
    columns, rows = _terminal()
    width, inner = _dimensions(columns)
    value = _timer_value(remaining, inner)
    elapsed = duration - remaining if elapsed is None else elapsed
    progress = min(1.0, max(0.0, elapsed / duration))
    bar_width = max(1, min(60, inner - 8))
    filled = int(bar_width * progress)
    bar = "█" * filled + "─" * (bar_width - filled)
    compact = inner < 31 or rows < 14
    content: list[tuple[str, str | None, bool]] = [
        ("TOKI", _ACCENT, True),
        ("TIMER", _ACCENT, True),
    ]
    if compact:
        content.extend([
            (value, _ACCENT, True),
            (bar, _ACCENT, True),
            (f"{int(progress * 100)}%", _ACCENT, True),
        ])
    else:
        content.append(("", None, True))
        scale = max(1, min(3, inner // 31, max(1, (rows - 8) // 5)))
        content.extend((line, _ACCENT, True) for line in _clock_art(value, scale))
        content.extend([
            ("", None, True),
            (bar, _ACCENT, True),
            (f"{int(progress * 100)}%", _ACCENT, True),
        ])
    _paint(_card(content, inner), columns, rows, width)


def draw_alert(message: str, seconds_left: int) -> None:
    columns, rows = _terminal()
    width, inner = _dimensions(columns)
    is_timer = message.casefold() == "timer complete"
    heading = "TIMER COMPLETE" if is_timer else "ALARM"
    content: list[tuple[str, str | None, bool]] = [
        ("TOKI", _ACCENT, True),
        ("", None, True),
        (heading, _ACCENT, True),
    ]
    if not is_timer:
        content.append((message, _ACCENT, True))
    content.append(("─" * min(inner, 30), _ACCENT, True))
    content.extend([
        ("Any key to silence", _ACCENT, True),
        (f"Quacking for {seconds_left}s", _ACCENT, True),
    ])
    if len(content) + 2 > rows:
        content = [("TOKI", _ACCENT, True), (heading, _ACCENT, True)]
        if not is_timer:
            content.append((message, _ACCENT, True))
        content.append((f"Any key · {seconds_left}s", _ACCENT, True))
    _paint(_card(content, inner), columns, rows, width)
