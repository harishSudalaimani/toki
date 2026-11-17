"""Synthesized duck quacks for TOKI alarms and timers."""

from __future__ import annotations

import math
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import wave
from threading import Event


def _make_quack() -> str:
    """Create a short, two-syllable duck-like quack as a temporary WAV."""
    fd, name = tempfile.mkstemp(prefix="toki-quack-", suffix=".wav")
    os.close(fd)
    sample_rate = 22050
    syllables = ((0.035, 0.24, 610.0, 270.0), (0.335, 0.29, 510.0, 230.0))
    sample_count = int(sample_rate * 0.72)
    samples = bytearray()
    for index in range(sample_count):
        seconds = index / sample_rate
        signal = 0.0
        for start, length, high_pitch, low_pitch in syllables:
            local = seconds - start
            if not 0.0 <= local < length:
                continue
            phase = 2 * math.pi * (
                high_pitch * local
                + (low_pitch - high_pitch) * local * local / (2 * length)
            )
            envelope = min(1.0, local / 0.012, (length - local) / 0.045)
            nasal = math.sin(phase) + 0.55 * math.sin(2 * phase) + 0.22 * math.sin(3 * phase)
            signal += max(0.0, envelope) * nasal
        sample = int(10500 * max(-1.0, min(1.0, signal)))
        samples.extend(struct.pack("<h", sample))

    with wave.open(name, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(sample_rate)
        audio.writeframes(samples)
    return name


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


def _ring_process(command: list[str], stop: Event, deadline: float) -> bool:
    """Repeat one audio player until stopped or the deadline is reached."""
    while not stop.is_set() and time.monotonic() < deadline:
        try:
            player = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            return False
        while player.poll() is None:
            if stop.wait(0.05) or time.monotonic() >= deadline:
                player.terminate()
                try:
                    player.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    player.kill()
                return True
        if player.returncode != 0:
            return False
    return True


def ring_alert(stop: Event, max_seconds: float = 60.0) -> bool:
    """Repeat the duck quack until silenced or the duration expires."""
    deadline = time.monotonic() + max_seconds
    if sys.platform == "win32":
        try:
            import winsound

            sound = _make_quack()
            try:
                flags = winsound.SND_FILENAME | winsound.SND_LOOP | winsound.SND_ASYNC
                winsound.PlaySound(sound, flags)
                stop.wait(max(0.0, deadline - time.monotonic()))
                winsound.PlaySound(None, 0)
                return True
            finally:
                try:
                    os.unlink(sound)
                except OSError:
                    pass
        except (ImportError, RuntimeError):
            return False

    commands: list[list[str]] = []
    if sys.platform == "darwin":
        player = shutil.which("afplay")
        if player:
            commands.append([player])
    elif sys.platform.startswith("linux"):
        commands.extend(
            [player]
            for player in (shutil.which("paplay"), shutil.which("aplay"))
            if player
        )
    if not commands:
        return False

    sound = _make_quack()
    try:
        for command in commands:
            if _ring_process([*command, sound], stop, deadline):
                return True
        return False
    finally:
        try:
            os.unlink(sound)
        except OSError:
            pass


def play_alert() -> bool:
    """Play one duck quack for a non-interactive alert."""
    if sys.platform == "win32":
        try:
            import winsound

            sound = _make_quack()
            try:
                winsound.PlaySound(sound, winsound.SND_FILENAME)
                return True
            finally:
                try:
                    os.unlink(sound)
                except OSError:
                    pass
        except (ImportError, RuntimeError):
            return False

    if sys.platform == "darwin":
        player = shutil.which("afplay")
        commands = [[player]] if player else []
    elif sys.platform.startswith("linux"):
        commands = [
            [player]
            for player in (shutil.which("paplay"), shutil.which("aplay"))
            if player
        ]
    else:
        commands = []
    if not commands:
        return False

    sound = _make_quack()
    try:
        return any(_run([*command, sound]) for command in commands)
    finally:
        try:
            os.unlink(sound)
        except OSError:
            pass
