"""What to do with a decoded payload."""

import webbrowser

from uniqr import backends

SAFE_SCHEMES = ("http://", "https://")


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


def open_url(text: str) -> bool:
    """Open a web link in the default browser. Returns False if not allowed."""
    if not can_open(text):
        return False
    webbrowser.open(text.strip())
    return True


def summarize(text: str, limit: int = 120) -> str:
    """A one-line version of a payload, for notifications."""
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"
