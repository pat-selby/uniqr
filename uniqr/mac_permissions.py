"""Helping a Mac user switch on the two permissions UniQR needs.

A downloaded UniQR.app has no Terminal window to print advice in. Without
Screen Recording it could only quit, and without Accessibility its hotkey never
arrives: either way, nothing visible happened. So on a Mac UniQR asks macOS to
show its own prompt, which also puts UniQR in the right list in System
Settings, and shows a card with a button that opens that page.

Everything here is a no-op off a Mac, and nothing here can fail loudly: a Mac
too old for a call, or a missing library, only means less help.
"""

from __future__ import annotations

import subprocess
import sys

SETTINGS = {
    "screen": "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture",
    "keys": "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
}
NAMES = {"screen": "Screen Recording", "keys": "Accessibility"}


def who() -> str:
    """What to switch on: the app itself, or the Terminal it was started from."""
    return "UniQR" if getattr(sys, "frozen", False) else "Terminal"


def message(kind: str) -> tuple[str, str]:
    """(heading, note) for the card."""
    need = "see your screen" if kind == "screen" else "hear the hotkey"
    heading = f"UniQR needs permission to {need}"
    note = (
        f"In System Settings > Privacy & Security > {NAMES[kind]}, "
        f"switch on {who()}. Then quit UniQR and open it again."
    )
    return heading, note


def ask_macos(kind: str) -> None:
    """Show macOS's own prompt, which also lists UniQR on that settings page."""
    if sys.platform != "darwin":
        return
    try:
        if kind == "screen":
            import ctypes
            import ctypes.util

            path = ctypes.util.find_library("CoreGraphics")
            if path:
                fn = ctypes.CDLL(path).CGRequestScreenCaptureAccess
                fn.restype = ctypes.c_bool
                fn()
        else:
            from ApplicationServices import (
                AXIsProcessTrustedWithOptions,
                kAXTrustedCheckOptionPrompt,
            )

            AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: True})
    except Exception as exc:  # noqa: BLE001 - older macOS or no pyobjc: the card still helps
        print(f"could not show the macOS permission prompt: {exc}")


def open_settings(kind: str) -> bool:
    """Open the System Settings page for that permission."""
    if sys.platform != "darwin":
        return False
    try:
        return subprocess.run(["open", SETTINGS[kind]], check=False, timeout=10).returncode == 0
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"could not open System Settings: {exc}")
        return False
