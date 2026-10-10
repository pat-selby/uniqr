"""The OS plumbing: permission probes and screen-to-window coordinates.

Detection is covered by the other three suites. This one covers the parts
that only misbehave on a real desktop - a denied permission, and a display
whose pixels and points are not the same size - by driving them with the
platform answers faked, so the same cases run everywhere.
"""

import sys
import tkinter as tk
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from uniqr import actions, capture, overlay  # noqa: E402
from uniqr.backends import portable  # noqa: E402
from uniqr.decode import Detection  # noqa: E402

results: list[tuple[str, bool, str]] = []


def case(name: str, fn) -> None:
    try:
        detail = fn()
        results.append((name, True, detail or ""))
    except AssertionError as exc:
        results.append((name, False, str(exc)))
    except Exception as exc:  # noqa: BLE001 - a crashed case is a failure too
        results.append((name, False, f"{type(exc).__name__}: {exc}"))


class patched:
    """Swap module attributes for the duration of a with-block."""

    def __init__(self, module, **values) -> None:
        self.module = module
        self.values = values
        self.saved: dict[str, object] = {}

    def __enter__(self):
        for key, value in self.values.items():
            self.saved[key] = getattr(self.module, key)
            setattr(self.module, key, value)
        return self.module

    def __exit__(self, *_exc) -> None:
        for key, value in self.saved.items():
            setattr(self.module, key, value)


def fake_grab(width: int, height: int, blank: bool):
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    if not blank:
        frame[:, : width // 2] = 200
    return lambda rect=None: frame


# -- capture permission ------------------------------------------------------


def c_probe_blank():
    """A denied permission that hands back an all-black frame, on a Mac."""
    with (
        patched(portable.sys, platform="darwin"),
        patched(portable, grab=fake_grab(64, 64, blank=True), screen_capture_allowed=lambda: None),
    ):
        ok, detail = portable.probe()
    assert not ok, "a blank frame was reported as working capture"
    assert "Screen Recording" in detail, f"unhelpful message: {detail!r}"
    return detail[:46]


def c_probe_blank_on_linux():
    """A blank frame on Linux must not tell the user to grant a macOS permission,
    and on Wayland must say what Wayland is doing."""
    import os

    saved = {k: os.environ.pop(k, None) for k in ("XDG_SESSION_TYPE", "WAYLAND_DISPLAY")}
    try:
        with (
            patched(portable.sys, platform="linux"),
            patched(portable, grab=fake_grab(64, 64, blank=True), screen_capture_allowed=lambda: None),
        ):
            ok, plain = portable.probe()
            os.environ["XDG_SESSION_TYPE"] = "wayland"
            _ok, wayland = portable.probe()
    finally:
        for key, value in saved.items():
            os.environ.pop(key, None)
            if value is not None:
                os.environ[key] = value
    assert not ok
    assert "macOS" not in plain and "Screen Recording" not in plain, plain
    assert "Wayland" in wayland and "Xorg" in wayland, wayland
    return "plain blank frame and Wayland each get their own message"


def c_probe_denied_but_lively():
    """The case the pixel-spread heuristic cannot see.

    Denied Screen Recording does not always mean a black frame - macOS may
    still hand back the desktop picture with every window omitted. That has a
    full pixel spread, so only the permission API itself can catch it.
    """
    with patched(
        portable, grab=fake_grab(64, 64, blank=False), screen_capture_allowed=lambda: False
    ):
        ok, detail = portable.probe()
    assert not ok, "capture with the permission denied was reported as working"
    assert "Screen Recording" in detail, f"unhelpful message: {detail!r}"
    return detail[:46]


def c_probe_granted():
    with patched(
        portable, grab=fake_grab(64, 64, blank=False), screen_capture_allowed=lambda: True
    ):
        ok, detail = portable.probe()
    assert ok, f"working capture was reported as broken: {detail}"
    return detail


def c_probe_unknown_platform():
    """Where there is no permission API, fall back to the pixel spread."""
    with patched(
        portable, grab=fake_grab(64, 64, blank=False), screen_capture_allowed=lambda: None
    ):
        ok, detail = portable.probe()
    assert ok, f"a lively frame was rejected with no permission API: {detail}"
    return detail


def c_input_status_shape():
    allowed, detail = portable.input_status()
    assert allowed in (True, False, None), f"unexpected answer {allowed!r}"
    assert detail, "no detail to show the user"
    return f"{allowed}: {detail[:34]}"


def c_input_status_names_the_right_switch():
    """macOS has two keyboard switches and pynput only cares about one.

    Input Monitoring granted while Accessibility is not is the state this VM
    was actually in, and telling someone to grant Input Monitoring there sends
    them to a checkbox that is already ticked.
    """
    if portable.sys.platform != "darwin":
        return "not macOS, nothing to name"
    with patched(
        portable,
        _ask_bool=lambda lib, sym: {
            "AXIsProcessTrusted": False,
            "CGPreflightListenEventAccess": True,
        }[sym],
    ):
        allowed, detail = portable.input_status()
    assert allowed is False, "an untrusted process was reported as trusted"
    assert "Accessibility" in detail, f"does not name Accessibility: {detail!r}"
    assert "Input Monitoring is granted" in detail, f"misleading advice: {detail!r}"
    return "names Accessibility, not the switch already ticked"


# -- coordinates -------------------------------------------------------------


def c_scale_factor_live():
    scale = portable.scale_factor()
    assert scale > 0, f"nonsense scale {scale}"
    rect = portable.virtual_screen()
    shot = portable.grab(rect)
    expected = shot.shape[1] / rect.width
    assert abs(scale - expected) < 0.01, f"reported {scale}, measured {expected}"
    return f"{scale:g}x on this display"


def c_to_points():
    assert overlay.to_points(200, 100, 1.0) == (200, 100)
    assert overlay.to_points(200, 100, 2.0) == (100, 50)
    return "1x and 2x round trip"


def c_below():
    """The toast anchor must be in points, gap included, not raw pixels."""
    bbox = (200, 100, 80, 80)
    assert overlay.below(bbox, origin=(0, 0), gap=14, scale=1.0) == (200, 194)
    assert overlay.below(bbox, origin=(0, 0), gap=14, scale=2.0) == (100, 104)
    assert overlay.below(bbox, origin=(-1600, -200), gap=14, scale=2.0) == (-1500, -96)
    return "anchors in points on 1x and 2x"


def _detection(left, top, size, text="https://example.com/one"):
    quad = np.array(
        [
            (left, top),
            (left + size, top),
            (left + size, top + size),
            (left, top + size),
        ],
        dtype=np.float32,
    )
    return Detection(text=text, quad=quad)


def _picker_at(scale: float):
    shot = np.full((400, 600, 3), 180, dtype=np.uint8)
    dets = [_detection(100, 80, 120), _detection(360, 220, 100)]
    with patched(capture, scale_factor=lambda: scale):
        picker = overlay.Picker(shot, dets, origin=(0, 0))
        picker.win.update_idletasks()
        info = {
            "canvas": (picker.canvas.winfo_reqwidth(), picker.canvas.winfo_reqheight()),
            "marker": picker.canvas.coords(picker._marker_ids[0]),
            "hit_inside": picker._hit(*overlay.to_points(150, 130, scale)),
            "hit_outside": picker._hit(*overlay.to_points(5, 5, scale)),
        }
        picker._close()
        picker.root.update()
    return info


def c_picker_1x():
    info = _picker_at(1.0)
    assert info["canvas"] == (600, 400), f"canvas {info['canvas']}"
    assert info["marker"][:2] == [100.0, 80.0], f"marker at {info['marker'][:2]}"
    assert info["hit_inside"] == 0, "hover missed a code it was over"
    assert info["hit_outside"] is None, "hover hit a code it was nowhere near"
    return f"canvas {info['canvas']}, first marker at {info['marker'][:2]}"


def c_picker_2x():
    """Retina: the screenshot is twice the size of the window it goes in.

    Every number the canvas sees has to be halved - its own size, the image,
    the outlines and the hit boxes - or the highlights sit at double the
    offset of the codes they are meant to be on.
    """
    info = _picker_at(2.0)
    assert info["canvas"] == (300, 200), f"canvas {info['canvas']} should be half of 600x400"
    assert info["marker"][:2] == [50.0, 40.0], f"marker at {info['marker'][:2]}, wanted [50, 40]"
    assert info["hit_inside"] == 0, "hover missed a code it was over"
    assert info["hit_outside"] is None, "hover hit a code it was nowhere near"
    return f"canvas {info['canvas']}, first marker at {info['marker'][:2]}"


def c_negative_origin():
    """A monitor left of the primary gives the virtual desktop a negative origin."""
    root = overlay.shared_root()
    win = tk.Toplevel(root)
    win.overrideredirect(True)
    win.geometry("120x40+-300+-100")
    win.update_idletasks()
    placed = (win.winfo_x(), win.winfo_y())
    win.destroy()
    assert placed == (-300, -100), f"Tk put it at {placed}"
    return "Tk accepts +-300+-100"


# -- safety ------------------------------------------------------------------


def c_open_stays_narrow():
    """The Open action must not have grown any new schemes."""
    for allowed in ("http://example.com", "HTTPS://Example.com/x"):
        assert actions.can_open(allowed), f"{allowed} should be openable"
    for blocked in (
        "file:///etc/passwd",
        "ms-settings:privacy",
        "javascript:alert(1)",
        "smb://host/share",
        "plain text",
        " data:text/html,<script>",
    ):
        assert not actions.can_open(blocked), f"{blocked} must stay copy-only"
    return "http(s) only, 6 other schemes refused"


# -- the card ----------------------------------------------------------------


def c_card_buttons_keep_their_colors():
    """Card buttons must honor the colors we give them on every platform.

    A real tk.Button on macOS is drawn by the native Aqua control, which
    throws the background color away and keeps the foreground one, so the
    dark-card "Dismiss" ended up pale text on a pale control. Labels obey
    both, and this asserts the card is still built from them.
    """
    root = overlay.shared_root()
    frame = tk.Frame(root)
    try:
        primary = overlay._button(frame, "Open", lambda: None, True)
        plain = overlay._button(frame, "Dismiss", lambda: None, False)
        for widget, want_bg, want_fg in (
            (primary, overlay.ACCENT, overlay.BADGE_TEXT),
            (plain, overlay.BUTTON_BG, overlay.CARD_FG),
        ):
            label = widget.cget("text")
            got_bg, got_fg = widget.cget("bg"), widget.cget("fg")
            assert got_bg == want_bg, f"{label} background is {got_bg}, wanted {want_bg}"
            assert got_fg == want_fg, f"{label} text is {got_fg}, wanted {want_fg}"
        return "Open and Dismiss both keep their own colors"
    finally:
        frame.destroy()


# -- the watchdog's heartbeat ------------------------------------------------


def c_heartbeat_survives_a_waiting_window():
    """A card or picker left open must not look like a freeze.

    Both block in a nested event loop until someone answers. If the heartbeat
    only ticked from the normal loop, it would stop for exactly as long as a
    person takes to decide, and the watchdog would restart UniQR under them.
    """
    from uniqr.shell_portable import PortableShell

    root = overlay.shared_root()
    shell = PortableShell(on_hotkey=lambda: None)
    beats: list[int] = []
    shell.set_heartbeat(lambda: beats.append(1))

    win = tk.Toplevel(root)
    root.after(2500, win.destroy)
    root.wait_window(win)  # the same call the card and the picker make
    shell.stop()
    assert len(beats) >= 2, f"only {len(beats)} beats in 2.5s of waiting"
    return f"{len(beats)} beats while a window waited"


def c_clipboard_without_a_helper():
    """On Linux a fresh install has no xclip or xsel, and pyperclip then raises.
    Copying must still work, through Tk, or a scan fails at the last step."""
    import pyperclip

    real = pyperclip.copy

    def no_helper(_text):
        raise pyperclip.PyperclipException("no copy/paste mechanism")

    pyperclip.copy = no_helper
    try:
        portable.copy_text("https://example.com/no-helper")
    finally:
        pyperclip.copy = real
    got = overlay.shared_root().clipboard_get()
    assert got == "https://example.com/no-helper", got
    return "falls back to Tk when pyperclip has no helper"


CASES = {
    "probe: blank frame": c_probe_blank,
    "probe: blank frame on Linux": c_probe_blank_on_linux,
    "probe: denied, frame lively": c_probe_denied_but_lively,
    "probe: granted": c_probe_granted,
    "probe: no permission API": c_probe_unknown_platform,
    "input status query": c_input_status_shape,
    "input status names switch": c_input_status_names_the_right_switch,
    "scale factor matches grab": c_scale_factor_live,
    "to_points": c_to_points,
    "toast anchor": c_below,
    "picker at 1x": c_picker_1x,
    "picker at 2x (Retina)": c_picker_2x,
    "negative screen origin": c_negative_origin,
    "open action stays narrow": c_open_stays_narrow,
    "clipboard without a helper": c_clipboard_without_a_helper,
    "card buttons keep colors": c_card_buttons_keep_their_colors,
    "heartbeat survives a waiting window": c_heartbeat_survives_a_waiting_window,
}


# The checks above are written to run as a script, which prints a readable
# table. Without this, pytest collects nothing from the file and CI skips all
# of it silently, which is worse than having no tests at all.
try:
    import pytest
except ImportError:  # running as a plain script, without pytest installed
    pytest = None

# These open a real window or grab a real screen, so they need a display.
# CI runs Linux headless, where both fail on $DISPLAY rather than on anything
# being wrong with the code.
NEEDS_DISPLAY = {
    "scale factor matches grab",
    "picker at 1x",
    "picker at 2x (Retina)",
    "negative screen origin",
    "clipboard without a helper",
    "card buttons keep colors",
    "heartbeat survives a waiting window",
}

_display: bool | None = None


def has_display() -> bool:
    """Whether a window can actually be opened here. Checked once.

    Asks for the app's own shared root rather than making a throwaway one.
    Creating a Tk root, destroying it, then creating another in the same
    process intermittently fails to re-initialise Tk, which showed up as
    "couldn't read button.tcl" on roughly one run in three.
    """
    global _display
    if _display is None:
        try:
            overlay.shared_root()
            _display = True
        except Exception:  # noqa: BLE001 - any failure means no usable display
            _display = False
    return _display


if pytest is not None:

    @pytest.mark.parametrize("name", list(CASES))
    def test_plumbing(name: str) -> None:
        if name in NEEDS_DISPLAY and not has_display():
            pytest.skip("needs a screen; this machine is headless")
        CASES[name]()


def main() -> int:
    print(f"{'case':<28} {'result':<7} detail")
    print("-" * 78)
    for name, fn in CASES.items():
        case(name, fn)
    for name, ok, detail in results:
        print(f"{name:<28} {'ok' if ok else 'FAIL':<7} {detail}")
    print("-" * 78)
    fails = [n for n, ok, _ in results if not ok]
    print(f"{len(results) - len(fails)}/{len(results)} passing")
    if fails:
        print("failing:", ", ".join(fails))
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
