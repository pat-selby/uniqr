"""Reporting a problem: the address of a pre-filled GitHub issue.

UniQR sends nothing. It opens this page in the person's own browser, and they read
it, change it and press Submit themselves (GitHub asks them to sign in). What is
pre-filled is only the version of UniQR and a plain description of the system, so
a report arrives with what is needed to reproduce it.

Not pre-filled: the log. A log can hold links the person scanned, so the issue
only says where it is and asks them to look it over before pasting any of it.
"""

from __future__ import annotations

import platform
import sys
from urllib.parse import quote, urlencode

REPO = "pat-selby/uniqr"
NEW_ISSUE = f"https://github.com/{REPO}/issues/new"
# The tray's "Send feedback": a new post in the project's Discussions, for
# ideas and opinions rather than bugs.
FEEDBACK_URL = f"https://github.com/{REPO}/discussions/new?category=general"


def how_it_is_run() -> str:
    return "downloaded file" if getattr(sys, "frozen", False) else "run from the source"


def system_summary() -> str:
    """The operating system and its version, such as Windows-10-10.0.26200-SP0.

    Not the computer's name, the person's name, or anything about the screen.
    """
    return platform.platform()


def log_location() -> str:
    """Where this system keeps UniQR's log, written so it holds no one's name."""
    if sys.platform == "win32":
        return "%LOCALAPPDATA%\\UniQR\\uniqr.log"
    if sys.platform == "darwin":
        return "~/Library/Logs/UniQR/uniqr.log"
    return "~/.local/state/uniqr/uniqr.log"


def issue_body(version: str) -> str:
    return (
        "**What happened?**\n"
        "(Say what you did and what went wrong, in a sentence or two.)\n\n"
        "**What did you expect to happen?**\n\n"
        "**Can you make it happen again? How?**\n\n"
        "---\n"
        f"UniQR {version} ({how_it_is_run()}) on {system_summary()}\n\n"
        "The log can help, but it may contain links you scanned. Look through it "
        "and paste only what you are happy to share.\n"
        f"Log: {log_location()}\n"
    )


def issue_url(version: str) -> str:
    """The address of a new GitHub issue with the report form filled in."""
    query = urlencode({"body": issue_body(version)}, quote_via=quote)
    return f"{NEW_ISSUE}?{query}"
