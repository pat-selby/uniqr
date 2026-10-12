"""The few things UniQR remembers between runs.

Today that is one thing: whether it has already asked about starting at login,
so it asks once and not on every start. They live in one small JSON file.

    Windows   %LOCALAPPDATA%\\UniQR\\settings.json
    Linux     ~/.config/uniqr/settings.json   (or under $XDG_CONFIG_HOME)

UNIQR_CONFIG_DIR puts it somewhere else, which is how the tests keep their own.
A missing or damaged file reads as empty. A setting that cannot be saved is
reported and ignored: UniQR works the same, it just asks again next time.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


def config_dir() -> Path:
    override = os.environ.get("UNIQR_CONFIG_DIR")
    if override:
        return Path(override)
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "UniQR"
    base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base) / "uniqr"


def path() -> Path:
    return config_dir() / "settings.json"


def load() -> dict[str, Any]:
    try:
        data = json.loads(path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def get(key: str, default: Any = None) -> Any:
    return load().get(key, default)


def set(key: str, value: Any) -> bool:  # noqa: A001 - reads well as settings.set
    """Remember a setting. False if the file could not be written."""
    data = load()
    data[key] = value
    try:
        target = path()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError as exc:
        print(f"could not save the setting {key}: {exc}")
        return False
    return True
