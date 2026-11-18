# TOKI (TIME)

**A quiet companion for your time.**

TOKI is a cross-platform terminal clock, alarm manager, and countdown timer for Python 3.11+. It has no third-party runtime dependencies. The PyPI package is `toki-time`; it installs the `toki` command.

## Install

With pipx:

```bash
pipx install toki-time
toki
```

Or with pip:

```bash
python -m pip install toki-time
toki
```

## Use

Run `toki` to open the live dashboard. Type `help` at the dashboard prompt for its command list, or run `toki --help` in your shell. Press Ctrl+C to close the dashboard.

Commands can be entered at the dashboard prompt without the `toki` prefix, or run directly from the shell with it.

### Alarms

Alarms use your local time in 24-hour `HH:MM` format. They are one-time by default; use `--daily` or `--repeat daily` for a daily alarm. Give alarms distinct labels to manage them individually, and quote labels containing spaces. If you omit a label, TOKI assigns one such as `Alarm` or `Alarm 2`.

At the dashboard prompt:

```text
alarm set 07:30
alarm set 07:30 --label "GYM"
alarm set 07:30 --daily
alarm list
alarm enable "GYM"
alarm disable "GYM"
alarm delete "GYM"
```

The same commands work from the shell:

```bash
toki alarm set 07:30 --label "GYM"
toki alarm list
toki alarm disable "GYM"
```

A one-time alarm set for a time that has already passed today is scheduled for tomorrow. Actions on a repeated label apply to every alarm with that label.

### Timer

Timer durations use `s` for seconds, `m` for minutes, and `h` for hours. Units can be combined once each.

At the dashboard prompt:

```text
timer 90s
timer 30m
timer 1h30m
timer stop
```

From the shell, start a standalone timer with:

```bash
toki timer 30m
```

Press Ctrl+C to cancel a standalone timer. `timer stop` is available at the dashboard prompt.

## Alerts and data

Keep TOKI running for alarms to alert. Alarm settings are saved between launches, but a shell command such as `toki alarm set ...` exits after saving; use the dashboard to keep the alarm scheduler running. Timers are not saved when TOKI closes. Interactive alerts play a synthesized duck sound for up to one minute; press any key to silence it. The dashboard adjusts to the terminal size without flashing. If the system has no supported sound player, TOKI reports that audio is unavailable.

Alarm data is stored in `alarms.json` under the platform's user configuration directory:

- Windows: `%APPDATA%/toki`
- macOS: `~/Library/Application Support/toki`
- Linux and other Unix systems: `$XDG_CONFIG_HOME/toki`, or `~/.config/toki` by default

The JSON file is written atomically. If it is malformed or cannot be read, TOKI reports its path and leaves it untouched.

## Development

Install an editable copy and run the test suite from the repository root:

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

TOKI is distributed under the MIT License; see [LICENSE](LICENSE).
