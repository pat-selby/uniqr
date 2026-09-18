"""What to do with a decoded payload."""

import ipaddress
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
