"""One-shot environment report. Run this first on a new OS.

    python tools/diagnose.py             # includes a live hotkey test
    python tools/diagnose.py --no-input  # skip anything interactive

Every check is isolated, so one failure still leaves a full report. Paste the
whole output when reporting a problem.
"""

import argparse
import platform
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

PASS, WARN, FAIL = "ok  ", "warn", "FAIL"
results: list[tuple[str, str, str]] = []


def check(name: str, fn) -> None:
    try:
        status, detail = fn()
    except Exception as exc:  # noqa: BLE001 - a crashed check is a result too
        status, detail = FAIL, f"{type(exc).__name__}: {exc}"
    results.append((status, name, detail))
    print(f"[{status}] {name:<24} {detail}")


def c_python():
    return PASS, (
        f"{platform.python_version()} on {sys.platform} "
        f"{platform.machine()} ({platform.platform()})"
    )


def c_deps():
    missing, versions = [], []
    for mod in ("cv2", "numpy", "PIL", "mss", "pynput", "pystray", "pyperclip"):
        try:
            m = __import__(mod)
            versions.append(f"{mod}={getattr(m, '__version__', '?')}")
        except ImportError:
            missing.append(mod)
    if missing:
        return FAIL, f"missing {', '.join(missing)}"
    return PASS, " ".join(versions)


def c_backend():
    from uniqr import backends

    return PASS, f"{backends.NAME}"


def c_decode():
    import cv2
    import numpy as np

    from uniqr.decode import Scanner

    expected = "https://example.com/uniqr-diagnose"
    qr = cv2.QRCodeEncoder.create().encode(expected)
    qr = cv2.resize(qr, (240, 240), interpolation=cv2.INTER_NEAREST)
    canvas = np.full((400, 400), 255, dtype=np.uint8)
    canvas[80:320, 80:320] = qr
    found = Scanner().scan(cv2.cvtColor(canvas, cv2.COLOR_GRAY2BGR))
    if any(d.text == expected for d in found):
        return PASS, "encoded and decoded a known payload"
    return FAIL, f"decode failed, got {[d.text for d in found]}"


def c_screen():
    from uniqr import capture

    capture.set_dpi_aware()
    rect = capture.virtual_screen()
    return PASS, f"virtual screen {rect.width}x{rect.height} at ({rect.left},{rect.top})"


def c_capture():
    from uniqr import capture

    t = time.perf_counter()
    shot = capture.grab()
    ms = (time.perf_counter() - t) * 1000
    ok, detail = capture.probe()
    spread = int(shot.max()) - int(shot.min())
    info = f"{shot.shape[1]}x{shot.shape[0]} in {ms:.0f}ms, pixel spread {spread}"
    if not ok:
        return FAIL, f"{info} - {detail}"
    return PASS, info


def c_clipboard():
    from uniqr import actions

    token = f"uniqr-diagnose-{int(time.time())}"
    actions.copy(token)
    try:
        import pyperclip

        got = pyperclip.paste()
    except Exception as exc:  # noqa: BLE001
        return WARN, f"wrote ok, could not read back ({exc})"
    return (PASS, "round trip ok") if got == token else (WARN, f"read back {got!r}")


def c_tk():
    import tkinter as tk

    root = tk.Tk()
    root.withdraw()
    win = tk.Toplevel(root)
    win.overrideredirect(True)
    win.attributes("-topmost", True)
    win.geometry("120x40+50+50")
    win.update()
    placed = (win.winfo_x(), win.winfo_y())
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    win.destroy()
    root.destroy()
    return PASS, f"borderless topmost window ok at {placed}, tk screen {sw}x{sh}"


def c_tray():
    from uniqr.shell_portable import PortableShell

    shell = PortableShell(on_hotkey=lambda: None)
    ok = shell.start_tray()
    shell.stop()
    if ok:
        return PASS, "tray icon started"
    return WARN, "no tray icon (expected on macOS) - hotkey still works"


def c_hotkey_listener():
    from uniqr.shell_portable import PortableShell, hotkey_choices

    shell = PortableShell(on_hotkey=lambda: None)
    label = shell.register_hotkey()
    shell.stop()
    candidates = ", ".join(lbl for _, lbl in hotkey_choices())
    if label:
        return PASS, f"listener started on {label} (candidates: {candidates})"
    return FAIL, f"no listener would start (tried {candidates})"


def c_hotkey_live(timeout: int = 12):
    """Does the OS actually deliver the keys to us?

    The listener starting proves nothing on macOS - without Input Monitoring
    permission it starts happily and then receives nothing at all.
    """
    from uniqr.shell_portable import PortableShell, hotkey_choices

    label = hotkey_choices()[0][1]
    shell = PortableShell(on_hotkey=lambda: None)
    started = shell.register_hotkey()
    if not started:
        shell.stop()
        return FAIL, "listener would not start"

    print(f"\n    >>> press {started} now (waiting {timeout}s)...", flush=True)
    deadline = time.time() + timeout
    got = False
    while time.time() < deadline:
        if not shell._queue.empty():
            got = True
            break
        time.sleep(0.1)
    shell.stop()

    if got:
        return PASS, f"{started} received"
    return FAIL, (
        f"{started} never arrived. On macOS grant Input Monitoring in System "
        f"Settings > Privacy & Security. In a VM the hypervisor may be eating "
        f"it - try UNIQR_HOTKEY='<cmd>+<shift>+8'"
    )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--no-input", action="store_true", help="skip the live key test")
    p.add_argument("--timeout", type=int, default=12)
    args = p.parse_args()

    print("UniQR diagnostics\n" + "=" * 68)
    check("python", c_python)
    check("dependencies", c_deps)
    check("backend selected", c_backend)
    check("decode engine", c_decode)
    check("screen geometry", c_screen)
    check("screen capture", c_capture)
    check("clipboard", c_clipboard)
    check("tkinter overlay", c_tk)
    check("tray icon", c_tray)
    check("hotkey listener", c_hotkey_listener)
    if not args.no_input:
        check("hotkey delivery", lambda: c_hotkey_live(args.timeout))

    print("=" * 68)
    failed = [n for s, n, _ in results if s == FAIL]
    warned = [n for s, n, _ in results if s == WARN]
    print(f"{len(results) - len(failed) - len(warned)} ok, "
          f"{len(warned)} warnings, {len(failed)} failures")
    if warned:
        print("warnings:", ", ".join(warned))
    if failed:
        print("failures:", ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
