"""`UniQR --scan`: ask the UniQR already running to scan, from anywhere.

Wayland does not deliver global hotkeys to apps, so the hotkey UniQR listens
for never arrives there. Every Linux desktop can instead run a command from a
keyboard shortcut of the person's choosing, set in its own settings. That
command is `UniQR --scan`, and this module carries it to the running app.

  Linux, macOS  a Unix socket in the person's private runtime folder,
                readable only by them. The running app listens; --scan says
                "scan" and gets "ok" back.
  Windows       the running app's hidden window is sent the same message the
                tray's Scan now sends.

If no UniQR is running, `--scan` starts one, and it scans as soon as it is up.
"""

import os
import socket
import sys
import tempfile
import threading
from collections.abc import Callable
from pathlib import Path

REQUEST = b"scan\n"
ANSWER = b"ok\n"
WINDOW_CLASS = "UniQRHiddenWindow"  # see uniqr/shell.py
WM_COMMAND = 0x0111
IDM_SCAN = 1001
# Unix sockets: Linux and macOS. Looked up by name, since some Windows Pythons lack it.
_AF_UNIX: int = getattr(socket, "AF_UNIX", -1)


def socket_path() -> Path:
    """$XDG_RUNTIME_DIR is private to the person and cleared at logout."""
    base = os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir()
    uid = os.getuid() if hasattr(os, "getuid") else 0
    return Path(base) / f"uniqr-{uid}.sock"


def request_scan(path: Path | None = None) -> bool:
    """Ask the running UniQR to scan. False when none is running."""
    if sys.platform == "win32":
        return _request_scan_windows()
    target = path or socket_path()
    try:
        with socket.socket(_AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(3)
            client.connect(str(target))
            client.sendall(REQUEST)
            return client.recv(16) == ANSWER
    except OSError:
        return False


def _request_scan_windows() -> bool:
    if sys.platform != "win32":  # also tells the type checker windll exists below
        return False
    import ctypes

    user32 = ctypes.windll.user32
    hwnd = user32.FindWindowW(WINDOW_CLASS, None)
    return bool(hwnd) and bool(user32.PostMessageW(hwnd, WM_COMMAND, IDM_SCAN, 0))


class Server:
    """Listens for --scan on the Unix socket and calls `on_scan` for each one.

    `on_scan` runs on this listener's thread, so it must only hand the work
    to the thread that draws: the portable shell puts "scan" on its queue.
    """

    def __init__(self, on_scan: Callable[[], None], path: Path | None = None) -> None:
        self.on_scan = on_scan
        self.path = path or socket_path()
        self._sock: socket.socket | None = None

    def start(self) -> bool:
        """False if it cannot listen, such as when another UniQR already is."""
        if sys.platform == "win32":
            return False
        if self.path.exists():
            if request_ping(self.path):
                return False  # another UniQR answers here
            try:
                self.path.unlink()  # left by a UniQR that did not exit cleanly
            except OSError:
                return False
        try:
            sock = socket.socket(_AF_UNIX, socket.SOCK_STREAM)
            old_mask = os.umask(0o177)  # created readable and writable by the owner only
            try:
                sock.bind(str(self.path))
            finally:
                os.umask(old_mask)
            sock.listen(4)
        except OSError as exc:
            print(f"--scan will not work: could not listen at {self.path}: {exc}")
            return False
        self._sock = sock
        threading.Thread(target=self._serve, name="uniqr-remote", daemon=True).start()
        return True

    def _serve(self) -> None:
        sock = self._sock
        while sock is not None:
            try:
                client, _ = sock.accept()
            except OSError:
                return  # closed by stop()
            with client:
                client.settimeout(2)
                try:
                    data = client.recv(16)
                except OSError:
                    continue
                if data == REQUEST:
                    self.on_scan()
                    try:
                        client.sendall(ANSWER)
                    except OSError:
                        pass
                elif data == PING:
                    try:
                        client.sendall(ANSWER)
                    except OSError:
                        pass

    def stop(self) -> None:
        sock, self._sock = self._sock, None
        if sock is not None:
            sock.close()
            try:
                self.path.unlink()
            except OSError:
                pass


PING = b"ping\n"


def request_ping(path: Path) -> bool:
    """Whether a UniQR answers at `path`, without asking it to scan."""
    try:
        with socket.socket(_AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(1)
            client.connect(str(path))
            client.sendall(PING)
            return client.recv(16) == ANSWER
    except OSError:
        return False
