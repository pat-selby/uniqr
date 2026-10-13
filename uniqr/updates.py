"""Telling a person that a newer UniQR exists. It tells; it never installs.

This is the only place UniQR talks to the internet, and only when the person
agreed to it or clicked "Check for updates now". It sends one HTTPS request to
GitHub, asking for the newest release of this project. GitHub can see the
sender's address and the name UniQR/<version>. Nothing about scans, screens or
the computer is sent.

What comes back is treated as untrusted. Only a version number is read from it,
and the page offered to the person is built from that number here, never taken
from the reply. Nothing is downloaded or run.
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from uniqr import settings

REPO = "pat-selby/uniqr"
API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASE_PAGE = f"https://github.com/{REPO}/releases/tag/v"
TIMEOUT_S = 6
MAX_BYTES = 200_000  # a release reply is a few thousand; refuse anything absurd
CHECK_EVERY_S = 24 * 60 * 60
MAX_IGNORED = 3  # the question is put at most this often without an answer

# ASCII digits only: \d would also accept digits from other scripts.
_VERSION = re.compile(r"[vV]?([0-9]+(?:\.[0-9]+){0,3})")


class UpdateError(Exception):
    """The check could not be completed. The message says why, in plain words."""


@dataclass(frozen=True)
class Release:
    version: str  # "0.1.8"
    url: str  # the release page, built here

    @property
    def parts(self) -> tuple[int, ...]:
        return parse_version(self.version) or ()


@dataclass(frozen=True)
class Outcome:
    status: str  # "newer", "current" or "error"
    release: Release | None = None
    detail: str = ""


def parse_version(text: str) -> tuple[int, ...] | None:
    """(0, 1, 8) for "v0.1.8" or "0.1.8". None for anything else, such as 0.1.8-rc1."""
    match = _VERSION.fullmatch(str(text).strip())
    if not match:
        return None
    return tuple(int(p) for p in match.group(1).split("."))


def is_newer(latest: str, current: str) -> bool:
    """Whether `latest` is a higher version than `current`. False if either is unreadable."""
    a, b = parse_version(latest), parse_version(current)
    if a is None or b is None:
        return False
    width = max(len(a), len(b))  # 0.2 and 0.2.0 are the same version
    return a + (0,) * (width - len(a)) > b + (0,) * (width - len(b))


def parse_release(payload: bytes | str) -> Release:
    """The newest release named in GitHub's reply. UpdateError if it makes no sense."""
    try:
        data: Any = json.loads(payload)
    except (ValueError, UnicodeDecodeError) as exc:
        raise UpdateError("The reply was not readable.") from exc
    tag = data.get("tag_name") if isinstance(data, dict) else None
    parts = parse_version(tag) if isinstance(tag, str) else None
    if parts is None:
        raise UpdateError("The reply did not name a version UniQR understands.")
    version = ".".join(str(p) for p in parts)
    return Release(version=version, url=RELEASE_PAGE + version)


def fetch_latest(
    current: str = "",
    opener: Callable[..., Any] = urllib.request.urlopen,
    url: str = API_URL,
    timeout: float = TIMEOUT_S,
) -> Release:
    """Ask GitHub for the newest release. UpdateError on any failure."""
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"UniQR/{current or 'unknown'}",
        },
    )
    try:
        with opener(request, timeout=timeout) as reply:
            final = str(reply.geturl())
            if not final.startswith("https://api.github.com/"):
                raise UpdateError("The reply came from somewhere unexpected.")
            body = reply.read(MAX_BYTES + 1)
    except UpdateError:
        raise
    except Exception as exc:  # noqa: BLE001 - offline, blocked, timed out, bad certificate...
        raise UpdateError(f"Could not reach GitHub ({type(exc).__name__}).") from exc
    if len(body) > MAX_BYTES:
        raise UpdateError("The reply was far larger than expected.")
    return parse_release(body)


def check(current: str, fetch: Callable[[str], Release] = fetch_latest) -> Outcome:
    """Compare this version with the newest release. Never raises."""
    try:
        release = fetch(current)
    except UpdateError as exc:
        return Outcome("error", detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        return Outcome("error", detail=f"Unexpected problem ({type(exc).__name__}).")
    if is_newer(release.version, current):
        return Outcome("newer", release)
    return Outcome("current", release)


# -- what is remembered ---------------------------------------------------------


def supported() -> bool:
    return sys.platform == "win32" or sys.platform.startswith("linux")


def enabled() -> bool:
    return bool(settings.get("update_check", False))


def set_enabled(on: bool) -> bool:
    return settings.set("update_check", bool(on))


def should_ask(quiet: bool = False, restarted: bool = False) -> bool:
    """Whether this start should ask about automatic checks.

    Only the packaged program asks, once, and never when it was started quietly
    or by its own watchdog. Yes and no are final; ignoring it three times ends it.
    """
    if quiet or restarted or not supported():
        return False
    if not getattr(sys, "frozen", False):
        return False
    if settings.get("update_asked") or enabled():
        return False
    return int(settings.get("update_ignored", 0)) < MAX_IGNORED


def record_answer(answered: bool | None, stopping: bool = False) -> None:
    """Remember what happened to the question. A card closed only because UniQR
    was quitting says nothing, so it is not counted."""
    if answered is not None:
        settings.set("update_asked", True)
    elif not stopping:
        settings.set("update_ignored", int(settings.get("update_ignored", 0)) + 1)


def next_check_at(now: float | None = None) -> float:
    """When the next automatic check is due: a day after the last one."""
    last = float(settings.get("update_last_check", 0) or 0)
    return last + CHECK_EVERY_S


def record_check(when: float | None = None) -> None:
    settings.set("update_last_check", time.time() if when is None else when)


def already_told(version: str) -> bool:
    return settings.get("update_notified") == version


def record_told(version: str) -> None:
    settings.set("update_notified", version)
