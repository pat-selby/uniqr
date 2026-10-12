"""Start UniQR at login, from the program itself, on Linux and Windows.

    ./UniQR-linux-x86_64 --install-autostart
    ./UniQR-linux-x86_64 --install-autostart --hotkey '<ctrl>+<alt>+<shift>+q'
    UniQR.exe --install-autostart
    --uninstall-autostart undoes either

Linux: most desktops start whatever has a small "desktop entry" file in
~/.config/autostart/ when you log in. This writes that file.

Windows: the standard per-user list of programs to start at login is a "Run"
entry in the registry. This adds one, which needs no administrator rights and
appears under Settings, Apps, Startup.

Either way it points at the copy of UniQR that ran it, so someone who only
downloaded the one file needs nothing else. The path is recorded, so if the file
is moved or renamed, run the command again.

macOS has tools/install_mac_agent.py.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from uniqr import settings

ENTRY_NAME = "uniqr.desktop"

# The name of the entry in Windows' list of programs to start at login.
RUN_VALUE = "UniQR"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

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
    python = Path(sys.executable)
    if sys.platform == "win32" and python.name.lower() == "python.exe":
        # A login should not open a black console window that stays up for as
        # long as UniQR runs.
        windowless = python.with_name("pythonw.exe")
        if windowless.exists():
            python = windowless
    return [str(python), str(Path(__file__).resolve().parent.parent / "app.py")]


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
        print("This sets up start-at-login on Linux and Windows.", file=sys.stderr)
        print("On a Mac, run: python3 tools/install_mac_agent.py", file=sys.stderr)
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


class _Registry:
    """The real per-user Run list. Windows only, and tests swap it for a fake."""

    def write(self, name: str, value: str) -> None:
        if sys.platform == "win32":
            import winreg

            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
        else:
            raise OSError("the Windows registry is not available here")

    def read(self, name: str) -> str | None:
        if sys.platform == "win32":
            import winreg

            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
                    return str(winreg.QueryValueEx(key, name)[0])
            except FileNotFoundError:
                return None
        return None

    def delete(self, name: str) -> bool:
        if sys.platform == "win32":
            import winreg

            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.DeleteValue(key, name)
                return True
            except FileNotFoundError:
                return False
        return False


def _tell(message: str, ok: bool = True, quiet: bool = False) -> None:
    """Say how it went. The packaged Windows program has no console to print to,
    so there it also shows a small message box, unless told to be quiet."""
    print(message, file=sys.stdout if ok else sys.stderr)
    if sys.platform == "win32" and getattr(sys, "frozen", False) and not quiet:
        import ctypes

        ctypes.windll.user32.MessageBoxW(0, message, "UniQR", 0x40 if ok else 0x10)


def run_command(command: list[str]) -> str:
    """The command line stored in the Run list, quoted the way Windows reads it."""
    return subprocess.list2cmdline(command)


def install_windows(
    hotkey: str | None = None,
    quiet: bool = False,
    store: _Registry | None = None,
    name: str = RUN_VALUE,
    command: list[str] | None = None,
) -> int:
    store = store or _Registry()
    line = run_command(command or program_command())
    try:
        store.write(name, line)
    except OSError as exc:
        _tell(f"UniQR could not be set to start at login: {exc}", ok=False, quiet=quiet)
        return 1
    note = ""
    if hotkey:
        note = "\n\nThe hotkey option is ignored on Windows, which uses Win+Shift+Q, then Ctrl+Alt+Q."
    _tell(
        "Done. UniQR will start the next time you log in to Windows.\n\n"
        f"It starts: {line}\n\n"
        "If you move or rename that file, run this again. "
        "To see or switch it off: Settings, Apps, Startup. "
        "To remove it: run UniQR with --uninstall-autostart." + note,
        quiet=quiet,
    )
    return 0


def uninstall_windows(
    quiet: bool = False, store: _Registry | None = None, name: str = RUN_VALUE
) -> int:
    store = store or _Registry()
    if not store.delete(name):
        _tell("UniQR was not set to start at login, so there is nothing to remove.", quiet=quiet)
        return 0
    _tell(
        "Removed. UniQR will no longer start when you log in to Windows.\n"
        "A copy that is already running keeps running until you quit it.",
        quiet=quiet,
    )
    return 0


def handle_command_line(argv: list[str]) -> int | None:
    """Act on --install-autostart / --uninstall-autostart. None means neither was given."""
    quiet = "--quiet" in argv
    if "--install-autostart" in argv:
        if sys.platform == "win32":
            return install_windows(option(argv, "--hotkey"), quiet=quiet)
        return install(option(argv, "--hotkey"))
    if "--uninstall-autostart" in argv:
        if sys.platform == "win32":
            return uninstall_windows(quiet=quiet)
        return uninstall()
    return None


# -- asking, and the on/off switch used by the card and the tray menu -----------

# The question is put at most this many times without an answer. Someone who
# ignores it three times has answered, in effect, and asking again is nagging.
MAX_IGNORED = 3


def supported() -> bool:
    """Whether UniQR can set up start-at-login by itself here (not on a Mac)."""
    return sys.platform == "win32" or _on_linux()


def is_enabled(store: _Registry | None = None, config: Path | None = None) -> bool:
    if sys.platform == "win32":
        return (store or _Registry()).read(RUN_VALUE) is not None
    if _on_linux():
        return entry_path(config).exists()
    return False


def set_enabled(on: bool, store: _Registry | None = None, config: Path | None = None) -> bool:
    """Turn start-at-login on or off. True if it now matches what was asked."""
    if sys.platform == "win32":
        if on:
            return install_windows(quiet=True, store=store) == 0
        return uninstall_windows(quiet=True, store=store) == 0
    if _on_linux():
        if on:
            # Keep a hotkey chosen for this run, so a login copy uses it too.
            return install(os.environ.get("UNIQR_HOTKEY") or None, config) == 0
        return uninstall(config) == 0
    return False


def should_ask(quiet: bool = False, restarted: bool = False) -> bool:
    """Whether this start should put the start-at-login question.

    Only the packaged program asks: someone running from the source has the
    command-line options and the install guide, and a developer starting it
    fifty times a day does not want a question. It never asks when it is
    already set up, when it was started quietly or by its own watchdog, or once
    it has an answer.
    """
    if quiet or restarted or not supported():
        return False
    if not getattr(sys, "frozen", False):
        return False
    if settings.get("autostart_asked"):
        return False
    if int(settings.get("autostart_ignored", 0)) >= MAX_IGNORED:
        return False
    return not is_enabled()


def record_answer(answered: bool | None, stopping: bool = False) -> None:
    """Remember what happened to the question.

    Yes and no are final. No answer counts toward MAX_IGNORED, except when the
    card was closed because UniQR itself was quitting: that says nothing.
    """
    if answered is not None:
        settings.set("autostart_asked", True)
    elif not stopping:
        settings.set("autostart_ignored", int(settings.get("autostart_ignored", 0)) + 1)
