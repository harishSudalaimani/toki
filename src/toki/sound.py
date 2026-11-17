"""Best-effort audible alerts with a terminal-bell fallback."""

from __future__ import annotations

import math
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import wave


def _run(command: list[str], timeout: float = 4.0) -> bool:
    try:
        result = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
            check=False,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _linux_sound() -> bool:
    canberra = shutil.which("canberra-gtk-play")
    if canberra and _run([canberra, "-i", "alarm-clock-elapsed"]):
        return True

    # Desktop Linux commonly has one of these players. Generate a short WAV so
    # TOKI does not depend on a particular distro's collection of sound files.
    players = [player for player in (shutil.which("paplay"), shutil.which("aplay")) if player]
    if not players:
        return False

    fd, name = tempfile.mkstemp(prefix="toki-alert-", suffix=".wav")
    os.close(fd)
    try:
        sample_rate = 22050
        frame_count = int(sample_rate * 0.8)
        frames = bytearray()
        for index in range(frame_count):
            position = index / sample_rate
            frequency = 880 if position < 0.4 else 1175
            fade = min(1.0, position / 0.025, (0.8 - position) / 0.04)
            sample = int(9000 * max(0.0, fade) * math.sin(2 * math.pi * frequency * position))
            frames.extend(struct.pack("<h", sample))
        with wave.open(name, "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(sample_rate)
            audio.writeframes(frames)
        return any(_run([player, name]) for player in players)
    finally:
        try:
            os.unlink(name)
        except OSError:
            pass


def play_alert() -> bool:
    """Play a short system sound, falling back to the terminal bell."""
    played = False
    if sys.platform == "win32":
        try:
            import winsound

            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            played = True
        except (ImportError, RuntimeError):
            pass
    elif sys.platform == "darwin":
        player = shutil.which("afplay")
        sound = "/System/Library/Sounds/Glass.aiff"
        if player and os.path.exists(sound):
            played = _run([player, sound])
    elif sys.platform.startswith("linux"):
        played = _linux_sound()

    if not played:
        print("\a", end="", flush=True)
    return played
