"""Start the packaged Linux program and check it really reads a QR code.

    xvfb-run -a python tools/smoke_test_linux.py dist/UniQR-linux-x86_64

xvfb-run gives it a fake screen, so this works on a machine with no monitor, like
a CI runner. The test does what a person would: start UniQR, put a QR code on
screen, press the hotkey, and look for the link. It checks two things:

  the log      the scan wrote the link, so the hotkey arrived and the code read
  the clipboard the link was copied. No clipboard helper (xclip, xsel) is
               installed on the runner, which is how a new install looks, so
               this also covers UniQR copying without one.

It needs xdotool to press the key, and Tk, OpenCV and Pillow in the Python that
runs it, to draw the code and read the clipboard.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

PAYLOAD = "https://example.com/uniqr-linux-test"
SECOND = "https://example.com/uniqr-linux-second"
HOTKEY = "ctrl+alt+q"

# One code first, for the card. Then two, which opens the picker: a different
# part of the program, with its own imports. A published build was missing one
# of them, and a test that only ever showed one code passed.
SHOW_QR = f"""
import cv2, numpy as np, sys, tkinter as tk
from PIL import Image, ImageTk
def code(text):
    qr = cv2.QRCodeEncoder.create().encode(text)
    qr = cv2.resize(qr, (260, 260), interpolation=cv2.INTER_NEAREST)
    return cv2.copyMakeBorder(qr, 40, 40, 40, 40, cv2.BORDER_CONSTANT, value=255)
first = code("{PAYLOAD}")
img = first if len(sys.argv) < 2 else np.hstack([first, code("{SECOND}")])
root = tk.Tk()
root.overrideredirect(True)
root.attributes("-topmost", True)
root.geometry("+100+100")
photo = ImageTk.PhotoImage(Image.fromarray(img))
tk.Label(root, image=photo, bd=0).pack()
root.after(60000, root.destroy)
root.mainloop()
"""

READ_CLIPBOARD = """
import tkinter as tk
root = tk.Tk()
root.withdraw()
try:
    print(root.clipboard_get())
except tk.TclError:
    print("")
"""


def clipboard() -> str:
    return subprocess.run(
        [sys.executable, "-c", READ_CLIPBOARD], capture_output=True, text=True, timeout=30
    ).stdout.strip()


def log_path() -> Path:
    state = os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state"
    return Path(state) / "uniqr" / "uniqr.log"


def read_log() -> str:
    path = log_path()
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def wait_for(text: str, seconds: float, start: int = 0) -> bool:
    end = time.time() + seconds
    while time.time() < end:
        if text in read_log()[start:]:
            return True
        time.sleep(0.5)
    return False


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    program = Path(sys.argv[1]).resolve()
    if not program.exists():
        print(f"no program at {program}")
        return 2

    # Something has to be on the screen first. A fake screen starts out
    # completely black, and UniQR refuses to run when it can only see a blank
    # frame, as it should: a real desktop is never one flat color.
    qr_window = subprocess.Popen([sys.executable, "-c", SHOW_QR])
    time.sleep(4)

    started = time.time()
    app = subprocess.Popen([str(program)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        if not wait_for("UniQR is running", 90):
            print("FAIL: the program never said it was running. Its log:")
            print(read_log() or "(no log at all)")
            return 1
        print(f"ok: started in {time.time() - started:.1f} s")
        print("    " + [line for line in read_log().splitlines() if "UniQR is running" in line][-1])

        before = len(read_log())
        subprocess.run(["xdotool", "key", HOTKEY], check=True)
        if not wait_for(PAYLOAD, 20, start=before):
            print(f"FAIL: pressed {HOTKEY}, and the link never reached the log. Its log:")
            print(read_log())
            return 1
        print("ok: the hotkey arrived and the code was read")

        time.sleep(1)
        copied = clipboard()
        if copied != PAYLOAD:
            print(f"FAIL: the clipboard held {copied!r}, not the link")
            return 1
        print("ok: the link is on the clipboard")

        # Now two codes on screen, so the picker has to open and draw them.
        qr_window.terminate()
        qr_window = subprocess.Popen([sys.executable, "-c", SHOW_QR, "two"])
        time.sleep(4)
        before = len(read_log())
        subprocess.run(["xdotool", "key", HOTKEY], check=True)
        if not wait_for(SECOND, 20, start=before):
            print("FAIL: with two codes on screen, the second never reached the log. Its log:")
            print(read_log())
            return 1
        time.sleep(2)  # the picker is up now; choose the SECOND code, as a person would.
        # The clipboard already holds the first, so only a real pick can change it.
        subprocess.run(["xdotool", "key", "2"], check=True)
        time.sleep(2)
        if "scan failed" in read_log()[before:] or "Traceback" in read_log()[before:]:
            print("FAIL: the picker crashed. Its log:")
            print(read_log()[before:])
            return 1
        picked = clipboard()
        if picked != SECOND:
            print(f"FAIL: the picker was used, and the clipboard held {picked!r}, not the second code")
            print(read_log()[before:])
            return 1
        print("ok: the picker opened, and choosing 2 copied the second code")
        return 0
    finally:
        for proc in (qr_window, app):
            if proc is not None:
                proc.terminate()


if __name__ == "__main__":
    raise SystemExit(main())
