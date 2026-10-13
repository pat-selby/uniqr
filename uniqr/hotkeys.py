"""Reading a hotkey a person typed, for Windows.

    ctrl+alt+k       Ctrl+Alt+Shift+K       <ctrl>+<alt>+k       win+shift+q

All four work. Case does not matter, and angle brackets around a name are
allowed so the same text that Linux wants also works here. The last part is the
key: one letter or digit, or F1 to F24. Everything before it is a modifier:
Ctrl, Alt, Shift or Win (cmd and super mean Win).

At least one modifier is required. A bare letter would take that letter away
from every other program. This file has no Windows-only imports, so it can be
tested anywhere.
"""

from __future__ import annotations

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

_MODIFIERS = {
    "ctrl": MOD_CONTROL,
    "control": MOD_CONTROL,
    "alt": MOD_ALT,
    "shift": MOD_SHIFT,
    "win": MOD_WIN,
    "windows": MOD_WIN,
    "cmd": MOD_WIN,
    "super": MOD_WIN,
    "meta": MOD_WIN,
}
# The order a label is written in, and the name each modifier goes by there.
_LABEL_ORDER = [(MOD_CONTROL, "Ctrl"), (MOD_ALT, "Alt"), (MOD_SHIFT, "Shift"), (MOD_WIN, "Win")]
_VK_F1 = 0x70

# Tried in order when no hotkey was asked for, or the one asked for is taken.
# Win+Shift+Q is the one we want; the rest are escape hatches.
WINDOWS_DEFAULTS: list[tuple[int, int, str]] = [
    (MOD_WIN | MOD_SHIFT, ord("Q"), "Win+Shift+Q"),
    (MOD_CONTROL | MOD_ALT, ord("Q"), "Ctrl+Alt+Q"),
    (MOD_CONTROL | MOD_SHIFT, ord("9"), "Ctrl+Shift+9"),
]

EXAMPLE = "ctrl+alt+k"


def _key(name: str) -> tuple[int, str]:
    """The Windows key code and display name for the last part of a hotkey."""
    if len(name) == 1 and name.isascii() and name.isalnum():
        return ord(name.upper()), name.upper()
    if name.startswith("f") and name[1:].isdigit() and 1 <= int(name[1:]) <= 24:
        number = int(name[1:])
        return _VK_F1 + number - 1, f"F{number}"
    raise ValueError(
        f"'{name}' is not a key UniQR can use. Use one letter or digit, or F1 to F24."
    )


def parse_windows(text: str) -> tuple[int, int, str]:
    """(modifiers, key code, label) for what a person typed. ValueError says what is wrong."""
    parts = [p.strip().strip("<>").strip().lower() for p in text.split("+")]
    if len(parts) < 2 or any(not p for p in parts):
        raise ValueError(
            f"Write it like {EXAMPLE}: one or more of ctrl, alt, shift or win, "
            "then one key, joined by plus signs."
        )
    *names, key_name = parts
    mods = 0
    for name in names:
        if name not in _MODIFIERS:
            raise ValueError(f"'{name}' is not ctrl, alt, shift or win.")
        mods |= _MODIFIERS[name]
    vk, key_label = _key(key_name)
    label = "+".join([word for flag, word in _LABEL_ORDER if mods & flag] + [key_label])
    return mods, vk, label


def canonical(text: str) -> str:
    """The same hotkey written one plain way, safe to store on a command line."""
    return parse_windows(text)[2].lower()


def windows_choices(
    custom: str | None,
) -> tuple[list[tuple[int, int, str]], tuple[int, int, str] | None, str | None]:
    """What to try registering, in order.

    Returns (list, wanted, problem). `wanted` is the person's own hotkey if it
    could be read, and comes first in the list. `problem` is why it could not be
    read, or None. The default list always follows, so UniQR still starts.
    """
    if not custom or not custom.strip():
        return list(WINDOWS_DEFAULTS), None, None
    try:
        wanted = parse_windows(custom)
    except ValueError as exc:
        return list(WINDOWS_DEFAULTS), None, str(exc)
    rest = [c for c in WINDOWS_DEFAULTS if c[:2] != wanted[:2]]
    return [wanted, *rest], wanted, None
