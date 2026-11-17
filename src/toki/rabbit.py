"""A terminal-sized rabbit dance for completed alarms and timers."""

from __future__ import annotations

import sys
import time

_FRAMES = tuple(
    tuple(frame.splitlines())
    for frame in (
        r"""       /\       /\
      /  \_____/  \
     /   [=.=]   \
    |      ^      |
    |    \___/    |
     \           /
     /|  _____  |\
    /_|_/     \_|_\
      /_/     \_
""",
        r"""       /\       /\
      /  \_____/  \
     /   [=.=]   \
    |      ^      |
    |    \___/    |
     \           /
  ___/|  _____  |\___
     /_|_/   \_|_\
       /_/   \_
""",
        r"""       /\       /\
      /  \_____/  \
     /   [=.=]   \
    |      ^      |
    |    \___/    |
     \           /
  ___/|  _____  |\___
   __/_|_/   \_|_\__
      /_/     \_
""",
    )
)


def dance(duration: float = 2.1, frame_delay: float = 0.15) -> None:
    """Animate the rabbit in place without clearing the rest of the screen."""
    output = sys.stdout
    interactive = output.isatty()
    frame_count = max(1, round(duration / frame_delay))
    if interactive:
        output.write("\033[?25l")
    try:
        for index in range(frame_count):
            if interactive and index:
                output.write(f"\033[{len(_FRAMES[0])}A")
            frame = _FRAMES[index % len(_FRAMES)]
            for line in frame:
                output.write(("\033[2K" if interactive else "") + line + "\n")
            output.flush()
            if index + 1 < frame_count:
                time.sleep(frame_delay)
    finally:
        if interactive:
            output.write("\033[?25h")
            output.flush()
