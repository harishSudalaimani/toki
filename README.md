# TOKI (TIME)

**A quiet companion for your time.**

TOKI is a minimal, cross-platform command-line clock, alarm manager, and countdown timer for Python 3.11+. It uses only the Python standard library at runtime.

## Install

From PyPI:

```bash
python -m pip install toki-time
```

Or use pipx for an isolated install:

```bash
pipx install toki-time
```

From a checkout:

```bash
python -m pip install .
```

The PyPI distribution is `toki-time` and installs the `toki` command. TOKI (TIME) is the product name shown in the interface and documentation.

## Use

Launch the live dashboard and press Ctrl+C to exit:

```bash
toki
```

Use alarm and timer commands at the dashboard's `>` prompt, or run them directly in your shell by adding the `toki` prefix. The dashboard shows a `HELP` hint while idle; type `help` to see each command and what it does. Use unique alarm labels to enable, disable, or delete alarms. Labels with spaces need quotes. Unnamed alarms get labels such as `Alarm` and `Alarm 2`. A one-time alarm set for a time that has passed today is scheduled for tomorrow.

```text
alarm set 07:30
alarm set 07:30 --label "Gym"
alarm set 07:30 --daily
alarm list
alarm disable "Gym"
alarm enable "Gym"
alarm delete "Gym"
```

Start or stop a countdown from the same prompt. Units can be combined once each:

```text
timer 30m
timer 3h
timer 90s
timer 1h30m
timer stop
```

The same commands work directly in the shell, for example:

```bash
toki alarm set 07:30 --label "Gym"
toki alarm list
toki alarm disable "Gym"
toki timer 30m
```

The standalone timer can be cancelled with Ctrl+C. Inside the dashboard, use `timer stop`.

Alarm data is stored as JSON in the platform's user configuration directory: `%APPDATA%/toki` on Windows, `~/Library/Application Support/toki` on macOS, or `$XDG_CONFIG_HOME/toki` (default `~/.config/toki`) on Linux and other Unix systems. Set `XDG_CONFIG_HOME` to choose a different Unix config root.

## How it works

The dashboard keeps the clock, active timer, and upcoming alarms visible together. Alarm and timer alerts use a simple text card and play TOKI's synthesized duck quack; interactive alerts repeat it for up to one minute and stop when any key is pressed. Screens resize to fit the terminal without flashing effects. If no native sound player is available, TOKI reports that audio is unavailable instead of triggering the terminal's visual bell. Alarms and timers require TOKI to remain running; countdowns are not saved after exit. TOKI supports one-time and daily alarms.

Alarm JSON is written atomically. If it is malformed or cannot be read, TOKI reports the file path and leaves it untouched rather than replacing it with an empty alarm list.

## Development

Install the project in editable mode, then run the standard-library test suite from the repository root:

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

TOKI is distributed under the MIT License; see [LICENSE](LICENSE).
