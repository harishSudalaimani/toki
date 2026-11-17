# TOKI

**A quiet companion for your time.**

TOKI is a minimal, cross-platform command-line clock, alarm manager, countdown timer, and stopwatch for Python 3.11+. It uses only the Python standard library at runtime.

## Install

From a checkout:

```bash
python -m pip install .
```

Or install an isolated copy with pipx:

```bash
pipx install toki-time-companion
```

The project is packaged as `toki-time-companion` and installs the `toki` command. The PyPI name has not been checked or published as part of this build.

## Use

Launch the live dashboard and press Ctrl+C to exit:

```bash
toki
```

Set a one-time alarm (if the time has passed today, it is scheduled for tomorrow), or a daily alarm:

```bash
toki alarm set 07:30
toki alarm set 07:30 --label "Gym"
toki alarm set 07:30 --label "Medication" --repeat daily
toki alarm set 07:30 --daily
toki alarm list
toki alarm disable <id>
toki alarm enable <id>
toki alarm delete <id>
```

Run a countdown. Units can be combined once each:

```bash
toki timer 30m
toki timer 3h
toki timer 90s
toki timer 1h30m
```

The countdown animates a progress bar in an interactive terminal. To measure elapsed time instead, run the stopwatch and press Ctrl+C to stop it:

```bash
toki stopwatch
```

Alarm data is stored as JSON in the platform's user configuration directory: `%APPDATA%/toki` on Windows, `~/Library/Application Support/toki` on macOS, or `$XDG_CONFIG_HOME/toki` (default `~/.config/toki`) on Linux and other Unix systems. Set `XDG_CONFIG_HOME` to choose a different Unix config root.

## How it works

The dashboard and `toki timer` keep the process in the foreground and poll alarms while they run. When an alarm or timer completes, a large rabbit dances in the terminal alongside an alert sound. Alerts try the platform's system sound (or an available Linux sound player) and fall back to the terminal bell, followed by a visible terminal message. A terminal may suppress its bell; in that case, install/configure a system audio player. Timers use `time.monotonic()` for elapsed-time accuracy. TOKI has no background service: alarms only trigger while a TOKI process is running, and countdowns are not saved across process exits. The current MVP supports one-time and daily alarms; weekday recurrence and snoozing are not included.

Alarm JSON is written atomically. If it is malformed or cannot be read, TOKI reports the file path and leaves it untouched rather than replacing it with an empty alarm list.

## Development

Install the project in editable mode, then run the standard-library test suite from the repository root:

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

TOKI is distributed under the MIT License; see [LICENSE](LICENSE).
