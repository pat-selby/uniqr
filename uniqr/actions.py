"""What to do with a decoded payload."""

import ipaddress
import os
import shutil
import subprocess
import sys
import tempfile
import webbrowser
from dataclasses import dataclass
from urllib.parse import urlsplit

from uniqr import backends

SAFE_SCHEMES = ("http://", "https://")


@dataclass(frozen=True)
class LinkView:
    """A web link split up so the real destination is easy to see."""

    host: str  # where the link actually goes, port included if unusual
    rest: str  # path, query and fragment: shown dimmed, since it's less telling
    full: str  # the whole link, for the hover pop-up
    warnings: tuple[str, ...]


def describe_link(text: str) -> LinkView | None:
    """Break a web link into what a person needs to judge it.

    The host is the part that decides where a link goes, and it's the part
    attackers hide. `https://paypal.com@evil.example/login` reads like PayPal
    but goes to evil.example, because everything before an @ is treated as a
    user name. urlsplit applies the same rules a browser does, so the host it
    returns is the real one. Returns None for anything that is not an openable
    web link.
    """
    if not can_open(text):
        return None
    full = text.strip()
    try:
        parts = urlsplit(full)
        host = parts.hostname or ""
        port = parts.port
    except ValueError:
        return None
    if not host:
        return None

    warnings = []
    if parts.scheme.lower() != "https":
        warnings.append("Not secure: this link uses http, not https.")
    if parts.username is not None:
        warnings.append(f"Text before the @ is ignored. This really goes to {host}.")
    if any(label.startswith("xn--") for label in host.split(".")):
        warnings.append(
            "Uses international characters, a common lookalike trick. "
            "Check the address carefully."
        )
    try:
        ipaddress.ip_address(host)
        warnings.append("Goes to a raw IP address, not a website name.")
    except ValueError:
        pass

    rest = parts.path
    if parts.query:
        rest += "?" + parts.query
    if parts.fragment:
        rest += "#" + parts.fragment
    shown_host = f"{host}:{port}" if port else host
    return LinkView(host=shown_host, rest=rest, full=full, warnings=tuple(warnings))


def copy(text: str) -> None:
    """Put text on the system clipboard."""
    backends.copy_text(text)


def can_open(text: str) -> bool:
    """Only ordinary web links get an Open action.

    A QR code is untrusted input from the screen - it could hold a file:// or
    a custom app scheme aimed at something unpleasant. Handing an arbitrary
    string to ShellExecute is how you launch things you did not mean to, so
    everything except plain http(s) is copy-only.
    """
    return text.strip().lower().startswith(SAFE_SCHEMES)


# What a Linux desktop offers for "open this link in the user's browser", best
# first. xdg-open follows the browser the user chose in their desktop settings.
_LINUX_LAUNCHERS = (
    ["xdg-open"],
    ["gio", "open"],
    ["sensible-browser"],
    ["x-www-browser"],
)
# A launcher that fails does so at once. One still running after this long has
# handed the link to the browser (or is the browser, starting up).
_LAUNCH_WAIT_S = 0.8


def _linux() -> bool:
    return sys.platform.startswith("linux")


def _browser_env() -> dict[str, str]:
    """The environment a browser should start with.

    A packaged (one-file) UniQR puts its own unpacked folder first in
    LD_LIBRARY_PATH, so its bundled copies of system libraries are found first.
    A browser started from it inherits that, loads the wrong libraries and may
    fail to start at all, with nothing on screen. PyInstaller keeps the user's
    original value in LD_LIBRARY_PATH_ORIG.
    """
    env = dict(os.environ)
    if _linux() and getattr(sys, "frozen", False):
        original = env.pop("LD_LIBRARY_PATH_ORIG", None)
        if original is None:
            env.pop("LD_LIBRARY_PATH", None)
        else:
            env["LD_LIBRARY_PATH"] = original
    return env


def _launch(command: list[str], url: str, env: dict[str, str]) -> bool:
    """Run one launcher. True if it started and did not fail straight away."""
    program = shutil.which(command[0], path=env.get("PATH"))
    if program is None:
        return False
    with tempfile.TemporaryFile() as errors:
        try:
            proc = subprocess.Popen(
                [program, *command[1:], url],
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=errors,
                start_new_session=True,
            )
        except OSError as exc:
            print(f"{command[0]} could not be started: {exc}")
            return False
        try:
            code = proc.wait(timeout=_LAUNCH_WAIT_S)
        except subprocess.TimeoutExpired:
            return True
        if code == 0:
            return True
        errors.seek(0)
        detail = errors.read(300).decode(errors="replace").strip()
        print(f"{command[0]} could not open the link (exit {code}): {detail}")
        return False


def _open_on_linux(url: str) -> bool:
    env = _browser_env()
    if any(_launch(command, url, env) for command in _LINUX_LAUNCHERS):
        return True
    # Last resort, with the same clean environment.
    saved = os.environ.copy()
    try:
        os.environ.clear()
        os.environ.update(env)
        return bool(webbrowser.open(url))
    finally:
        os.environ.clear()
        os.environ.update(saved)


def open_url(text: str) -> bool:
    """Open a web link in the default browser. False if not allowed or not opened."""
    if not can_open(text):
        return False
    url = text.strip()
    if _linux():
        opened = _open_on_linux(url)
        if not opened:
            print("no way to open a browser worked; the link stays on the clipboard")
        return opened
    return bool(webbrowser.open(url))


def summarize(text: str, limit: int = 120) -> str:
    """A one-line version of a payload, for notifications."""
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"
