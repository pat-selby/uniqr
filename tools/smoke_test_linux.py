"""Start the packaged Linux program and check it really reads a QR code.

    xvfb-run -a python tools/smoke_test_linux.py dist/UniQR-linux-x86_64

xvfb-run gives it a fake screen, so this works on a machine with no monitor, like
a CI runner. The test does what a person would: start UniQR, put a QR code on
screen, press the hotkey, and look for the link. It checks two things:

  the log      the scan wrote the link, so the hotkey arrived and the code read
  the clipboard the link was copied. No clipboard helper (xclip, xsel) is
               installed on the runner, which is how a new install looks, so
               this also covers UniQR copying without one.

Then it checks the Open button's path: it runs the program with --open-url and a
fake xdg-open first on the PATH, and checks the link arrives and that the program
hands the launcher the user's own library path, not its unpacked folder's.

Then it checks the first-run question: a fresh start with no saved settings asks
whether to start at login, the keypress "y" answers yes, and the autostart file
appears. A second start asks nothing.

Then it checks start-at-login: it asks the program to write its autostart file,
reads the command back out of that file, starts UniQR with exactly that command
as a login would, and presses the custom hotkey the file sets.

It needs xdotool to press the key, and Tk, OpenCV and Pillow in the Python that
runs it, to draw the code and read the clipboard.
"""

import configparser
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PAYLOAD = "https://example.com/uniqr-linux-test"
SECOND = "https://example.com/uniqr-linux-second"
HOTKEY = "ctrl+alt+q"
# The combination the install guide recommends, written the way pynput wants it
# and the way xdotool presses it.
CUSTOM_PYNPUT = "<ctrl>+<alt>+<shift>+q"
CUSTOM_XDOTOOL = "ctrl+alt+shift+q"

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


def check_open_link(program: Path) -> int:
    """Open a link from the packaged program, with a fake xdg-open to catch it."""
    folder = Path(tempfile.mkdtemp(prefix="uniqr-open-"))
    record = folder / "record"
    launcher = folder / "xdg-open"
    launcher.write_text(
        "#!/bin/sh\n"
        f'printf "%s\\n%s\\n" "$1" "$LD_LIBRARY_PATH" > "{record}"\n',
        encoding="utf-8",
    )
    launcher.chmod(0o755)
    users_libs = "/opt/uniqr-test-libs"
    env = {**os.environ, "PATH": f"{folder}:{os.environ['PATH']}", "LD_LIBRARY_PATH": users_libs}
    url = "https://example.com/uniqr-open-test"
    result = subprocess.run(
        [str(program), "--open-url", url], capture_output=True, text=True, env=env, timeout=120
    )
    if result.returncode != 0 or not record.exists():
        print("FAIL: --open-url did not reach the launcher:")
        print(result.stdout, result.stderr)
        return 1
    got_url, got_libs = record.read_text(encoding="utf-8").splitlines()[:2]
    if got_url != url:
        print(f"FAIL: the launcher was handed {got_url!r}, not the link")
        return 1
    if got_libs != users_libs:
        print(f"FAIL: the launcher got LD_LIBRARY_PATH={got_libs!r}, not the user's {users_libs!r}")
        return 1
    print("ok: --open-url reached the launcher, with the user's own library path")
    return 0


def check_first_run(program: Path) -> int:
    """A first run asks about start at login. Answering yes sets it up, once."""
    settings_dir = Path(tempfile.mkdtemp(prefix="uniqr-first-"))  # empty: a first run
    xdg = Path(tempfile.mkdtemp(prefix="uniqr-xdg-"))  # where the desktop file goes
    env = {**os.environ, "UNIQR_CONFIG_DIR": str(settings_dir), "XDG_CONFIG_HOME": str(xdg)}
    desktop = xdg / "autostart" / "uniqr.desktop"

    qr_window = subprocess.Popen([sys.executable, "-c", SHOW_QR])
    time.sleep(4)
    before = len(read_log())
    app = subprocess.Popen([str(program)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        if not wait_for("asking whether to start at login", 90, start=before):
            print("FAIL: a first run never asked about start at login. Its log:")
            print(read_log()[before:])
            return 1
        if desktop.exists():
            print("FAIL: the autostart file was written before anyone answered")
            return 1
        print("ok: a first run asks, and has turned nothing on")
        time.sleep(2)  # the card is up
        # A fake screen has no window manager, so keys go to the window under the
        # pointer. The card sits in the bottom right corner; put the pointer on it,
        # as a person who wanted to answer would.
        size = re.search(r"captured (\d+)x(\d+)", read_log()[before:])
        width, height = (int(size.group(1)), int(size.group(2))) if size else (1280, 1024)
        subprocess.run(["xdotool", "mousemove", str(width - 300), str(height - 110)], check=True)
        time.sleep(0.5)
        subprocess.run(["xdotool", "key", "y"], check=True)
        if not wait_for("start at login: on", 20, start=before) or not desktop.exists():
            print("FAIL: pressed y, and start at login was not set up. Its log:")
            print(read_log()[before:])
            focus = subprocess.run(["xdotool", "getmouselocation"], capture_output=True, text=True)
            print("pointer:", focus.stdout.strip(), "screen:", width, height)
            return 1
        saved = json.loads((settings_dir / "settings.json").read_text(encoding="utf-8"))
        if saved.get("autostart_asked") is not True:
            print(f"FAIL: the answer was not remembered: {saved}")
            return 1
        print("ok: pressing y wrote the autostart file and remembered the answer")
    finally:
        app.terminate()
        app.wait(timeout=30)

    # The second start must not ask again.
    before = len(read_log())
    app = subprocess.Popen([str(program)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        if not wait_for("UniQR is running", 90, start=before):
            print("FAIL: the second start never said it was running. Its log:")
            print(read_log()[before:])
            return 1
        time.sleep(3)
        if "asking whether to start at login" in read_log()[before:]:
            print("FAIL: it asked a second time")
            return 1
        print("ok: a second start does not ask again")
    finally:
        qr_window.terminate()
        app.terminate()
    return 0


def check_autostart(program: Path) -> int:
    """Install start-at-login, then start UniQR the way a login would."""
    config = tempfile.mkdtemp(prefix="uniqr-autostart-")
    env = {**os.environ, "XDG_CONFIG_HOME": config}
    install = subprocess.run(
        [str(program), "--install-autostart", "--hotkey", CUSTOM_PYNPUT],
        capture_output=True, text=True, env=env, timeout=60,
    )
    entry_file = Path(config) / "autostart" / "uniqr.desktop"
    if install.returncode != 0 or not entry_file.exists():
        print("FAIL: --install-autostart did not write the file:")
        print(install.stdout, install.stderr)
        return 1
    print("ok: --install-autostart wrote " + str(entry_file))

    parser = configparser.RawConfigParser(interpolation=None)
    parser.optionxform = str
    parser.read(entry_file, encoding="utf-8")
    exec_line = parser["Desktop Entry"]["Exec"]
    command = shlex.split(exec_line)
    print("    Exec=" + exec_line)

    # The same command the desktop would run. If the quoting in the file were
    # wrong, this is where it would show.
    qr_window = subprocess.Popen([sys.executable, "-c", SHOW_QR])
    time.sleep(4)
    before = len(read_log())
    app = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        if not wait_for("UniQR is running", 90, start=before):
            print("FAIL: the command from the autostart file did not start UniQR. Its log:")
            print(read_log()[before:])
            return 1
        if CUSTOM_PYNPUT not in read_log()[before:]:
            print(f"FAIL: it started, but did not take the hotkey {CUSTOM_PYNPUT}. Its log:")
            print(read_log()[before:])
            return 1
        print(f"ok: started from the autostart file, and took {CUSTOM_PYNPUT}")

        # Wait for the log line of this run only, so an earlier scan cannot satisfy it.
        mark = len(read_log())
        subprocess.run(["xdotool", "key", CUSTOM_XDOTOOL], check=True)
        if not wait_for(PAYLOAD, 20, start=mark):
            print(f"FAIL: pressed {CUSTOM_XDOTOOL}, and the code was never read. Its log:")
            print(read_log()[before:])
            return 1
        print(f"ok: the custom hotkey ({CUSTOM_XDOTOOL}) read the code")
    finally:
        qr_window.terminate()
        app.terminate()

    removed = subprocess.run(
        [str(program), "--uninstall-autostart"], capture_output=True, text=True, env=env, timeout=60
    )
    if removed.returncode != 0 or entry_file.exists():
        print("FAIL: --uninstall-autostart did not remove the file")
        return 1
    print("ok: --uninstall-autostart removed it")
    return 0


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
    # The program asks about start at login on a first run, which would hold the
    # hotkey for a few seconds. Say it has already asked; check_first_run tests
    # the question on its own.
    settings_dir = tempfile.mkdtemp(prefix="uniqr-settings-")
    Path(settings_dir, "settings.json").write_text(json.dumps({"autostart_asked": True}), encoding="utf-8")
    os.environ["UNIQR_CONFIG_DIR"] = settings_dir

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
        qr_window.terminate()
        app.terminate()
        app.wait(timeout=30)
        return check_open_link(program) or check_first_run(program) or check_autostart(program)
    finally:
        for proc in (qr_window, app):
            if proc is not None:
                proc.terminate()


if __name__ == "__main__":
    raise SystemExit(main())
