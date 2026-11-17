"""TOKI's attitude, kept separate from its timekeeping logic."""

import random

MESSAGES = (
    "Time is running. Unlike your productivity.",
    "Another alarm? Ambitious.",
    "Congratulations. You survived another minute.",
    "Your schedule called. It sounds concerned.",
    "Make today count. Or at least make it to lunch.",
    "The clock keeps ticking. It has no choice either.",
)


def quip() -> str:
    return random.choice(MESSAGES)
