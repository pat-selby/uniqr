"""Start UniQR at login on Linux, from the program itself.

    ./UniQR-linux-x86_64 --install-autostart
    ./UniQR-linux-x86_64 --install-autostart --hotkey '<ctrl>+<alt>+<shift>+q'
    ./UniQR-linux-x86_64 --uninstall-autostart

Most Linux desktops start whatever has a small "desktop entry" file in
~/.config/autostart/ when you log in. This writes that file, pointing at the copy
of UniQR that ran it. It lives in the program, not in a separate script, so
someone who only downloaded the one file needs nothing else.

The path is recorded, so if the file is moved or renamed, run the command again.

macOS has tools/install_mac_agent.py. On Windows, put a shortcut in shell:startup.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ENTRY_NAME = "uniqr.desktop"

# Characters that make an argument need quoting in an Exec line.
_RESERVED = set(" \t\n\"'\\><~|&;$*?#()`")


def _on_linux() -> bool:
    return sys.platform.startswith("linux")


def option(argv: list[str], name: str) -> str | None:
    """The value after `--name`, or from `--name=value`. None if absent."""
    for i, arg in enumerate(argv):
        if arg == name and i + 1 < len(argv):
            return argv[i + 1]
        if arg.startswith(name + "="):
            return arg.split("=", 1)[1]
    return None


def config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")


def entry_path(config: Path | None = None) -> Path:
    return (config or config_home()) / "autostart" / ENTRY_NAME


def program_command() -> list[str]:
    """How to start this same copy of UniQR again."""
    if getattr(sys, "frozen", False):
        # The packaged program is its own command. Absolute, so it still works
        # when it was started as ./UniQR-linux-x86_64 from some folder.
        return [str(Path(sys.executable).resolve())]
    return [sys.executable, str(Path(__file__).resolve().parent.parent / "app.py")]


def quote(arg: str) -> str:
    """One argument of an Exec line, quoted the way the Desktop Entry spec asks.

    A literal percent sign is written %%, because %f and friends are codes. An
    argument with spaces, angle brackets and the like goes in double quotes, with
    a backslash before any of " ` $ and \\ inside them.
    """
    arg = arg.replace("%", "%%")
    if not any(c in _RESERVED for c in arg):
        return arg
    return '"' + "".join("\\" + c if c in '"`$\\' else c for c in arg) + '"'


def desktop_entry(command: list[str], hotkey: str | None = None) -> str:
    """The text of the autostart file."""
    args = ["env", f"UNIQR_HOTKEY={hotkey}", *command] if hotkey else list(command)
    exec_line = " ".join(quote(a) for a in args)
    # The whole value is also a string with its own escapes, in which a
    # backslash must itself be doubled.
    exec_line = exec_line.replace("\\", "\\\\")
    return "\n".join(
        [
            "[Desktop Entry]",
            "Type=Application",
            "Name=UniQR",
            "Comment=Read QR codes on your screen with a hotkey",
            f"Exec={exec_line}",
            "Terminal=false",
            "X-GNOME-Autostart-enabled=true",
            "",
        ]
    )


def _hotkey_problem(hotkey: str) -> str | None:
    """Why this hotkey cannot work, or None. Skipped where pynput will not load.

    pynput refuses to import without an X server, which is also the case on a
    machine with no screen. There the answer is "unknown", and the file is written.
    """
    try:
        from pynput import keyboard

        keyboard.HotKey.parse(hotkey)
    except ValueError as exc:
        return str(exc)
    except Exception:  # noqa: BLE001 - cannot check here, so do not block
        return None
    return None


def install(hotkey: str | None = None, config: Path | None = None) -> int:
    if not _on_linux():
        print("This sets up start-at-login on Linux.", file=sys.stderr)
        print("On a Mac, run: python3 tools/install_mac_agent.py", file=sys.stderr)
        print("On Windows, put a shortcut to UniQR.exe in the folder that shell:startup opens.", file=sys.stderr)
        return 1
    if hotkey:
        problem = _hotkey_problem(hotkey)
        if problem:
            print(f"That hotkey will not work: {problem}", file=sys.stderr)
            print("Write it like '<ctrl>+<alt>+<shift>+q': modifiers in angle brackets, one letter or digit last.", file=sys.stderr)
            return 1

    command = program_command()
    path = entry_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(desktop_entry(command, hotkey), encoding="utf-8")
    path.chmod(0o644)

    print(f"Done. UniQR will start when you next log in.\n  {path}")
    print()
    print("To start it now, without logging out:")
    print("  " + " ".join(quote(a) for a in (["env", f"UNIQR_HOTKEY={hotkey}", *command] if hotkey else command)))
    print()
    print(f"It points at {command[0]}, so run this again if you move or rename that.")
    print("To undo it: run the same program with --uninstall-autostart")
    return 0


def uninstall(config: Path | None = None) -> int:
    path = entry_path(config)
    if not path.exists():
        print("UniQR was not set to start at login, so there is nothing to remove.")
        return 0
    path.unlink()
    print(f"Removed {path}. UniQR will no longer start when you log in.")
    print("A copy that is already running keeps running until you quit it.")
    return 0


def handle_command_line(argv: list[str]) -> int | None:
    """Act on --install-autostart / --uninstall-autostart. None means neither was given."""
    if "--install-autostart" in argv:
        return install(option(argv, "--hotkey"))
    if "--uninstall-autostart" in argv:
        return uninstall()
    return None
