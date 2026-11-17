"""JSON persistence with atomic writes and explicit corruption errors."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .models import Alarm


class StorageError(Exception):
    """Raised when stored alarm data cannot safely be read or written."""


def data_path() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys_platform() == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "toki" / "alarms.json"


def sys_platform() -> str:
    # Kept in a tiny function to make platform path selection easy to patch in tests.
    import sys

    return sys.platform


class AlarmStore:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path is not None else data_path()

    def load(self) -> list[Alarm]:
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, list):
                raise ValueError("top-level JSON value must be a list")
            return [Alarm.from_dict(item) for item in raw]
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise StorageError(
                f"Cannot read alarms in {self.path}: {exc}. "
                "The file was left untouched; fix or move it before continuing."
            ) from exc

    def save(self, alarms: list[Alarm]) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary_name = tempfile.mkstemp(
                prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent
            )
            temporary = Path(temporary_name)
            try:
                with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                    json.dump([alarm.to_dict() for alarm in alarms], stream, indent=2)
                    stream.write("\n")
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, self.path)
            finally:
                temporary.unlink(missing_ok=True)
        except OSError as exc:
            raise StorageError(f"Cannot save alarms to {self.path}: {exc}") from exc
