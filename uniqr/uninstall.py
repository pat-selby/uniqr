"""Remove UniQR from this computer: the tray menu's "Uninstall UniQR".

    UniQR.exe --uninstall        the same, without the tray

UniQR is one file (an app on a Mac) with no installer, so nothing in Windows
Settings or the Finder knows about what else it leaves: the start-at-login
entry, the settings, the log and the tray icon. Deleting the file alone leaves
a start-at-login entry pointing at nothing. This removes all of it, then the
program itself.

Only files UniQR is known to write are deleted, never a whole folder, and a
folder goes only once it is empty. The C++ version keeps its log in the same
Windows folder, so wiping the folder would take that too.

On Windows a running program and its open log cannot be deleted, so a small
script does that part once UniQR has quit. A Mac app goes to the Trash rather
than being deleted, so a mistake can be undone.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from uniqr import autostart, logbook, settings

BUNDLE_ID = "com.patselby.uniqr"
# Written by tools/install_mac_agent.py for people who run UniQR from source.
MAC_AGENTS = ("com.patselby.uniqr", "com.patselby.uniqr-update")


def our_files() -> list[Path]:
    """Every file UniQR writes, whether or not it exists here."""
    log = logbook.log_path()
    files = [
        settings.path(),
        log,
        log.with_suffix(".log.1"),
        log.with_name("uniqr.alive"),
    ]
    if sys.platform == "win32":
        files.append(Path(os.environ.get("LOCALAPPDATA", Path.home())) / "UniQR" / "tray.ico")
    if sys.platform == "darwin":
        agents = Path.home() / "Library" / "LaunchAgents"
        files += [agents / f"{label}.plist" for label in MAC_AGENTS]
    return files


def our_folders() -> list[Path]:
    """The folders UniQR made, removed only if empty. Named UniQR, or never touched."""
    folders = {settings.config_dir(), logbook.log_path().parent}
    return sorted(f for f in folders if f.name.lower() == "uniqr")


def program() -> Path | None:
    """The file to remove: UniQR.exe, the Linux file, or UniQR.app.

    None when running from source, where the folder is the person's own copy of
    the code and not something to delete for them.
    """
    if not getattr(sys, "frozen", False):
        return None
    exe = Path(sys.executable).resolve()
    if sys.platform == "darwin":
        return next((p for p in exe.parents if p.suffix == ".app"), None)
    return exe


def remove() -> list[str]:
    """Undo what UniQR set up. Returns what could not be removed.

    Call finish() as the very last thing before the process ends.
    """
    problems = []
    if autostart.supported() and autostart.is_enabled() and not autostart.set_enabled(False):
        problems.append("the start-at-login entry")
    if sys.platform == "win32":
        return problems  # the files go after exit; see finish()

    for path in our_files():
        try:
            path.unlink(missing_ok=True)
        except OSError:
            problems.append(str(path))
    for folder in our_folders():
        try:
            folder.rmdir()
        except OSError:
            pass  # not empty, or already gone
    target = program()
    if target is not None:
        try:
            if sys.platform == "darwin":
                _to_trash(target)
            else:
                target.unlink()
        except OSError:
            problems.append(str(target))
    if sys.platform == "darwin":
        # Its entries under Screen Recording and Accessibility. Best effort:
        # an entry left behind does nothing once the app is gone.
        subprocess.run(["tccutil", "reset", "All", BUNDLE_ID], capture_output=True, check=False)
    return problems


def finish() -> None:
    """The steps that have to wait until UniQR is about to exit."""
    if sys.platform == "win32":
        script = Path(tempfile.gettempdir()) / "uniqr-uninstall.cmd"
        script.write_text(windows_script(our_files(), our_folders(), program()), encoding="utf-8")
        subprocess.Popen(
            ["cmd", "/c", str(script)],
            # A hidden console, not none: chcp needs one.
            creationflags=subprocess.CREATE_NO_WINDOW,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
    elif sys.platform == "darwin":
        # Last, because launchd stops a job it is told to remove, and that may
        # be this very process.
        for label in MAC_AGENTS:
            subprocess.run(["launchctl", "remove", label], capture_output=True, check=False)


def windows_script(files: list[Path], folders: list[Path], exe: Path | None) -> str:
    """A batch file that waits for UniQR to quit, then deletes what it left.

    The exe stays locked until both of UniQR's processes have ended (the
    one-file build runs as two), so it retries for up to half a minute. ping is
    the sleep, since `timeout` refuses to run without a console.
    """
    # chcp: cmd reads the script in the console code page, and the file is UTF-8.
    lines = ["@echo off", "chcp 65001 >nul", "set tries=0"]
    if exe is not None:
        lines += [
            ":retry",
            f'del /f /q "{exe}" >nul 2>&1',
            f'if not exist "{exe}" goto files',
            "set /a tries+=1",
            "if %tries% geq 30 goto files",
            "ping -n 2 127.0.0.1 >nul",
            "goto retry",
            ":files",
        ]
    else:
        lines.append("ping -n 3 127.0.0.1 >nul")
    lines += [f'del /f /q "{path}" >nul 2>&1' for path in files]
    lines += [f'rmdir "{folder}" >nul 2>&1' for folder in folders]
    # Deletes itself. The (goto) first stops cmd from complaining it vanished.
    lines.append('(goto) 2>nul & del /f /q "%~f0"')
    return "\r\n".join(lines) + "\r\n"


def _to_trash(app: Path) -> None:
    trash = Path.home() / ".Trash"
    dest = trash / app.name
    n = 2
    while dest.exists():
        dest = trash / f"{app.stem} {n}{app.suffix}"
        n += 1
    shutil.move(str(app), str(dest))


def run_command_line() -> int:
    """UniQR --uninstall: the same as the tray item, for when there is no tray."""
    from uniqr import store

    if store.packaged():
        print("This UniQR came from the Microsoft Store. Remove it in Settings > Apps.")
        return 1
    problems = remove()
    finish()
    if problems:
        print("UniQR is removed, apart from: " + ", ".join(problems))
        return 1
    if program() is None:
        print("UniQR's settings, log and start-at-login entry are removed.")
        print("You ran it from source, so delete that folder yourself if you like.")
    else:
        print("UniQR is removed from this computer.")
    return 0
