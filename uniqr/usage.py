"""Anonymous usage counts, sent once a day, only for people who said yes.

UniQR reads people's screens, so this sends as little as can still answer
"is it working for people?": how many scans, how many found something, how
long they took in rough bands, and which kinds of code turned up. Never a
screenshot, a link, any scanned text, a name, an address or an ID that follows
a person from day to day.

    off by default   nothing is counted or sent until the person says yes
    asked once       on a start where no other question is waiting
    one summary/day  the counts for a finished day, then they are cleared
    see it           `python app.py --show-usage` prints exactly what is sent
    turn it off      the tray menu, which also deletes what was counted

Nothing is asked or sent until APP_KEY holds an Aptabase app key. Aptabase
(aptabase.com) is a privacy-first analytics service for desktop apps: it keeps
counts, not people. An app key is public by design, like an address to post to.

The counts live in usage.json beside settings.json, where anyone can read them.
"""

from __future__ import annotations

import json
import os
import platform
import re
import secrets
import sys
import time
import urllib.request
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Callable

from uniqr import settings

# Set this to the app key from aptabase.com (Settings, Instructions). Empty
# means usage counts are switched off for everyone, and nobody is asked.
APP_KEY = ""
KEY_ENV = "UNIQR_USAGE_KEY"  # for tests and for trying a key without a new build

_KEY = re.compile(r"A-(EU|US)-[0-9]{6,16}")
HOSTS = {"EU": "https://eu.aptabase.com", "US": "https://us.aptabase.com"}
EVENTS_PATH = "/api/v0/events"
EVENT_NAME = "daily_summary"
TIMEOUT_S = 6
RETRY_AFTER_S = 60 * 60  # a failed send waits an hour before the next try
MAX_PENDING_DAYS = 7  # a week offline: older days are dropped, not piled up
MAX_IGNORED = 3

# Every count that can ever be sent. Anything else is refused by summary_event().
COUNTS = (
    "starts",
    "scans",
    "found_none",
    "found_one",
    "found_many",
    "picker_cancelled",
    "opened",
    "time_under_1s",
    "time_1_to_2s",
    "time_2_to_5s",
    "time_over_5s",
    "kind_qr",
    "kind_micro_qr",
    "kind_rmqr",
    "kind_data_matrix",
    "kind_aztec",
    "kind_pdf417",
    "kind_maxicode",
    "kind_other",
    "payload_link",
    "payload_other",
)
_KINDS = {
    "QR Code": "kind_qr",
    "Micro QR Code": "kind_micro_qr",
    "rMQR Code": "kind_rmqr",
    "Data Matrix": "kind_data_matrix",
    "Aztec": "kind_aztec",
    "PDF417": "kind_pdf417",
    "MaxiCode": "kind_maxicode",
}


# -- is it on? -------------------------------------------------------------------


def app_key() -> str:
    return os.environ.get(KEY_ENV) or APP_KEY


def configured() -> bool:
    """Whether a valid app key is set. Without one, nothing here does anything."""
    return _KEY.fullmatch(app_key()) is not None


def endpoint() -> str:
    match = _KEY.fullmatch(app_key())
    if match is None:
        raise ValueError("no usable app key")
    return HOSTS[match.group(1)] + EVENTS_PATH


def enabled() -> bool:
    return configured() and bool(settings.get("usage_stats", False))


def set_enabled(on: bool) -> bool:
    """Turn sharing on or off. Off also deletes everything counted so far."""
    saved = settings.set("usage_stats", bool(on))
    if not on:
        try:
            tally_path().unlink()
        except FileNotFoundError:
            pass
        except OSError as exc:
            print(f"could not delete the usage counts: {exc}")
    return saved


def should_ask(quiet: bool = False, restarted: bool = False) -> bool:
    """Only the packaged program asks, once, never when quiet or restarted, and
    only when there is somewhere to send to. Yes and no are final."""
    if quiet or restarted or not configured():
        return False
    if not getattr(sys, "frozen", False):
        return False
    if settings.get("usage_asked") or settings.get("usage_stats"):
        return False
    return int(settings.get("usage_ignored", 0)) < MAX_IGNORED


def record_answer(answered: bool | None, stopping: bool = False) -> None:
    if answered is not None:
        settings.set("usage_asked", True)
    elif not stopping:
        settings.set("usage_ignored", int(settings.get("usage_ignored", 0)) + 1)


# -- counting --------------------------------------------------------------------


def tally_path() -> Path:
    return settings.config_dir() / "usage.json"


def _today() -> str:
    return date.today().isoformat()


def _load() -> dict[str, Any]:
    try:
        data = json.loads(tally_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    counts = data.get("counts")
    pending = data.get("pending")
    return {
        "day": str(data.get("day") or _today()),
        "counts": {k: int(v) for k, v in counts.items() if k in COUNTS and isinstance(v, int)}
        if isinstance(counts, dict)
        else {},
        "pending": [p for p in pending if _valid_pending(p)] if isinstance(pending, list) else [],
    }


def _valid_pending(p: Any) -> bool:
    return isinstance(p, dict) and isinstance(p.get("day"), str) and isinstance(p.get("counts"), dict)


def _save(data: dict[str, Any]) -> None:
    try:
        target = tally_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError as exc:
        print(f"could not save the usage counts: {exc}")


def _bump(*names: str, today: str | None = None) -> None:
    if not enabled():
        return
    data = _roll(_load(), today or _today())
    for name in names:
        if name in COUNTS:
            data["counts"][name] = data["counts"].get(name, 0) + 1
    _save(data)


def _roll(data: dict[str, Any], today: str) -> dict[str, Any]:
    """Move a finished day's counts to the send queue and start a fresh day."""
    if data["day"] != today:
        if data["counts"]:
            data["pending"].append({"day": data["day"], "counts": data["counts"]})
            data["pending"] = sorted(data["pending"], key=lambda p: p["day"])[-MAX_PENDING_DAYS:]
        data["day"], data["counts"] = today, {}
    return data


def record_start() -> None:
    _bump("starts")


def record_scan(seconds: float, symbologies: list[str], links: int) -> None:
    """One finished scan. Only the number of codes, their kinds and the time are
    used. The caller passes no text, and nothing here could carry any."""
    found = len(symbologies)
    names = ["scans", "found_none" if found == 0 else "found_one" if found == 1 else "found_many"]
    names.append(
        "time_under_1s" if seconds < 1 else
        "time_1_to_2s" if seconds < 2 else
        "time_2_to_5s" if seconds < 5 else
        "time_over_5s"
    )
    names += [_KINDS.get(s, "kind_other") for s in symbologies]
    names += ["payload_link"] * links + ["payload_other"] * max(0, found - links)
    _bump(*names)


def record_picker_cancelled() -> None:
    _bump("picker_cancelled")


def record_opened() -> None:
    _bump("opened")


# -- sending ---------------------------------------------------------------------


def system_props(version: str) -> dict[str, Any]:
    """What Aptabase expects about the program. Locale and device are left blank:
    they say more about a person than this needs."""
    return {
        "locale": "",
        "osName": platform.system(),
        "osVersion": platform.release(),
        "deviceModel": "",
        "isDebug": not getattr(sys, "frozen", False),
        "appVersion": version,
        "sdkVersion": f"uniqr-usage@{version}",
    }


def summary_event(day_counts: dict[str, Any], version: str, now: float | None = None) -> dict[str, Any]:
    """One day's counts as an Aptabase event. Only whole numbers under known
    names get through. The session id is fresh for every send, so two days
    cannot be joined into one person."""
    props = {k: int(v) for k, v in day_counts.items() if k in COUNTS and isinstance(v, int) and v >= 0}
    stamp = datetime.fromtimestamp(time.time() if now is None else now, tz=UTC)
    return {
        "timestamp": stamp.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "sessionId": str(secrets.randbelow(10**16)),
        "eventName": EVENT_NAME,
        "systemProps": system_props(version),
        "props": props,
    }


def due(today: str | None = None) -> list[dict[str, Any]]:
    """Roll the day if it has ended, and return the days waiting to be sent."""
    if not enabled():
        return []
    data = _roll(_load(), today or _today())
    _save(data)
    return list(data["pending"])


def mark_sent(days: list[str]) -> None:
    data = _load()
    data["pending"] = [p for p in data["pending"] if p["day"] not in days]
    _save(data)


def send(
    pending: list[dict[str, Any]],
    version: str,
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> list[str]:
    """Send the waiting days in one request. Returns the days that went, or []
    if nothing did. Never raises: a failure only means trying again later."""
    if not pending or not configured():
        return []
    url = endpoint()
    body = json.dumps([summary_event(p["counts"], version) for p in pending]).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "App-Key": app_key(),
            "Content-Type": "application/json",
            "User-Agent": f"UniQR/{version}",
        },
    )
    try:
        with opener(request, timeout=TIMEOUT_S) as reply:
            if not str(reply.geturl()).startswith(url.rsplit(EVENTS_PATH, 1)[0] + "/"):
                print("usage counts: the reply came from somewhere unexpected")
                return []
            status = getattr(reply, "status", 200)
    except Exception as exc:  # noqa: BLE001 - offline, blocked, refused...
        print(f"usage counts: could not send ({type(exc).__name__})")
        return []
    if not 200 <= int(status) < 300:
        print(f"usage counts: the server said {status}")
        return []
    return [p["day"] for p in pending]


def describe(version: str) -> str:
    """Everything --show-usage prints: the state, and the exact request body."""
    lines = []
    if not configured():
        lines.append("Usage counts are switched off in this build: no app key is set.")
        lines.append("Nothing is counted, asked or sent.")
        return "\n".join(lines)
    lines.append(f"Sharing usage counts: {'on' if enabled() else 'off'}.")
    lines.append(f"Counts are kept in {tally_path()}")
    if not enabled():
        lines.append("Nothing is counted or sent while it is off.")
        return "\n".join(lines)
    data = _load()
    lines.append(f"Counting today ({data['day']}): {json.dumps(data['counts'], sort_keys=True)}")
    waiting = data["pending"] or [{"day": "(example)", "counts": {"scans": 3, "found_one": 2}}]
    lines.append(f"The next send goes to {endpoint()} and is exactly this:")
    lines.append(json.dumps([summary_event(p["counts"], version) for p in waiting], indent=2))
    return "\n".join(lines)
