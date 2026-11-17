"""Non-blocking character input for TOKI's dashboard and alerts."""

from __future__ import annotations

import codecs
import os
import sys
import time
from contextlib import contextmanager
from typing import Callable, Iterator


@contextmanager
def key_reader() -> Iterator[Callable[[float], str | None]]:
    """Yield a non-blocking key reader while preserving terminal settings."""
    if not sys.stdin.isatty():
        yield lambda timeout: None
        return

    if os.name == "nt":
        import msvcrt

        special_keys = {
            "K": "LEFT",
            "M": "RIGHT",
            "H": "UP",
            "P": "DOWN",
            "G": "HOME",
            "O": "END",
            "S": "DELETE",
        }

        def read_key(timeout: float) -> str | None:
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if msvcrt.kbhit():
                    char = msvcrt.getwch()
                    if char in {"\x00", "\xe0"}:
                        scan_deadline = time.monotonic() + 0.1
                        while time.monotonic() < scan_deadline:
                            if msvcrt.kbhit():
                                return special_keys.get(msvcrt.getwch())
                            time.sleep(0.005)
                        return None
                    return char
                time.sleep(0.01)
            return None

        yield read_key
        return

    import select
    import termios

    fd = sys.stdin.fileno()
    previous = termios.tcgetattr(fd)
    current = termios.tcgetattr(fd)
    current[3] &= ~(termios.ICANON | termios.ECHO)
    current[6][termios.VMIN] = 0
    current[6][termios.VTIME] = 0
    decoder = codecs.getincrementaldecoder("utf-8")()
    try:
        termios.tcsetattr(fd, termios.TCSADRAIN, current)

        def read_char(timeout: float) -> str | None:
            ready, _, _ = select.select([fd], [], [], timeout)
            if not ready:
                return None
            return decoder.decode(os.read(fd, 1)) or None

        csi_keys = {
            "A": "UP",
            "B": "DOWN",
            "C": "RIGHT",
            "D": "LEFT",
            "H": "HOME",
            "F": "END",
        }

        def read_key(timeout: float) -> str | None:
            char = read_char(timeout)
            if char != "\x1b":
                return char

            # Terminal emulators may deliver an escape sequence in separate
            # reads, so allow a short gap between its bytes.
            first = read_char(0.1)
            if first == "[":
                sequence = ""
                for _ in range(8):
                    part = read_char(0.1)
                    if part is None:
                        break
                    sequence += part
                    if 0x40 <= ord(part[-1]) <= 0x7E:
                        break
                if sequence in {"1~", "7~"}:
                    return "HOME"
                if sequence in {"4~", "8~"}:
                    return "END"
                if sequence == "3~":
                    return "DELETE"
                return csi_keys.get(sequence[-1:])
            if first == "O":
                final = read_char(0.1)
                return {
                    "A": "UP",
                    "B": "DOWN",
                    "C": "RIGHT",
                    "D": "LEFT",
                    "H": "HOME",
                    "F": "END",
                }.get(final)
            # Standalone Escape is still a key, which lets it silence alerts.
            return "ESC"

        yield read_key
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, previous)
