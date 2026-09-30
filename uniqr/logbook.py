"""Somewhere for UniQR to leave a record of itself.

Started from a shortcut, UniQR runs under pythonw.exe, which has no console.
Python sets sys.stdout to None there, and print() quietly does nothing. So a
crash during startup leaves no trace at all: the app simply is not running,
with no way to tell that from never having been started. This writes what the
app says, and anything that kills it, to a file instead.
"""

import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

# One old file is kept, so a crash is not scrolled away by later runs.
MAX_BYTES = 512 * 1024


def log_path() -> Path:
    """Where this platform expects a program to keep its log.

    Dropping a UniQR folder straight into the home directory, which is what
    the Windows-only version did everywhere else, is untidy on a Mac and wrong
    on Linux.
    """
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Logs" / "UniQR"
    elif sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "UniQR"
    else:
        state = os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state"
        base = Path(state) / "uniqr"
    base.mkdir(parents=True, exist_ok=True)
    return base / "uniqr.log"


class _Tee:
    """Writes to the log file, and to the console when there is one."""

    def __init__(self, stream, console) -> None:
        self.stream = stream
        self.console = console

    def write(self, text: str) -> int:
        # print() writes the text and its newline separately. Only the text
        # gets a line in the file; writing the lone newline too would double
        # space the whole log.
        if text.strip():
            stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.stream.write(f"{stamp}  {text.rstrip()}\n")
            self.stream.flush()
        if self.console is not None:
            try:
                self.console.write(text)
                self.console.flush()
            except (ValueError, OSError):
                pass
        return len(text)

    def flush(self) -> None:
        self.stream.flush()

    def isatty(self) -> bool:
        return False


def _rotate(path: Path) -> None:
    try:
        if path.exists() and path.stat().st_size > MAX_BYTES:
            path.replace(path.with_suffix(".log.1"))
    except OSError:
        pass  # a locked or unwritable file must not stop the app starting


def start(argv: list[str] | None = None) -> Path:
    """Send print() and crashes to the log file. Returns where it went."""
    path = log_path()
    _rotate(path)
    handle = path.open("a", encoding="utf-8", errors="replace")

    console_out, console_err = sys.stdout, sys.stderr
    sys.stdout = _Tee(handle, console_out)
    sys.stderr = _Tee(handle, console_err)

    def on_crash(kind, value, tb) -> None:
        if issubclass(kind, KeyboardInterrupt):
            sys.__excepthook__(kind, value, tb)
            return
        text = "".join(traceback.format_exception(kind, value, tb))
        print("UniQR stopped because of an error:\n" + text)

    sys.excepthook = on_crash

    print("-" * 60)
    print(f"UniQR starting. python {sys.version.split()[0]} on {sys.platform}")
    if argv:
        print("command: " + " ".join(argv))
    return path
