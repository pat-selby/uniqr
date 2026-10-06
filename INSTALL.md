# Installing UniQR

Press a hotkey, read any QR code on your screen.

You need **Python 3.11 or newer**. Check with `python --version` on Windows, or
`python3 --version` on macOS and Linux. If you don't have it, get it from
[python.org](https://www.python.org/downloads/).

Pick your system below. Each takes about two minutes.

---

## Windows

**1. Get it.**

```
git clone https://github.com/pat-selby/uniqr.git
cd uniqr
pip install -e ".[windows]"
```

**2. Run it.**

```
uniqr
```

A card appears saying UniQR is running and which hotkey it took. The app then
sits in the system tray, next to the clock.

**3. Use it.** Put a QR code on screen and press **Win+Shift+Q**.

- One code: copied to your clipboard, with a card showing where the link goes
- Several: the screen dims and each code is numbered, so you pick
- Right-click the tray icon to quit

If another app already owns Win+Shift+Q, UniQR takes Ctrl+Alt+Q instead, then
Ctrl+Shift+9. The startup card tells you which one it got.

### Start it with Windows

Press `Win+R`, type `shell:startup`, press Enter. Put a shortcut in that folder
pointing to:

```
pythonw.exe C:\path\to\uniqr\app.py
```

Use `pythonw.exe`, not `python.exe`, or you get a black console window that
never goes away.

---

## macOS

macOS is stricter, so there are two extra steps. Skip them and UniQR starts
but sees nothing and hears nothing.

**1. Get it.**

```
git clone https://github.com/pat-selby/uniqr.git
cd uniqr
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

**2. Grant two permissions.** Open **System Settings → Privacy & Security** and
turn on **Terminal** in both of these lists:

- **Screen Recording**, or UniQR cannot see your screen
- **Accessibility**, or the hotkey never reaches it

If Terminal is not in a list, click **+** and add it from Applications →
Utilities. If the hotkey still does nothing afterwards, add Terminal to
**Input Monitoring** too.

Grant these to **Terminal**, not to Python. macOS credits the app that
launched the process.

**Then quit Terminal fully with Cmd+Q and open it again.** Closing the window
is not enough; the permission only applies on relaunch.

**3. Run it.**

```
cd uniqr
source .venv/bin/activate
uniqr
```

**4. Use it.** Put a QR code on screen and press **Control+Option+Q**.

### Choosing a different hotkey

macOS has claimed most shortcuts, and unlike Windows it cannot tell you a
combination is already taken: both actions simply fire. Avoid **Cmd+Q** (quits
the app you are in), **Cmd+Shift+Q** (logs you out) and **Cmd+Ctrl+Q** (locks
the screen).

To use your own:

```
UNIQR_HOTKEY='<cmd>+<shift>+8' uniqr
```

### Two things to expect on macOS

- **No tray icon.** The library that draws it needs the main thread, and the
  window toolkit already has it. The hotkey is the real interface. Press
  `Ctrl+C` in the Terminal window to quit.
- **It stops when you close that Terminal window.** See below to keep it
  running.

### Start it at login

```
cp tools/com.patselby.uniqr.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.patselby.uniqr.plist
```

Open that file first and fix the paths inside it if your copy is not in
`~/Downloads/uniqr`.

One catch. macOS grants permission to the **program that runs**, and you gave
it to Terminal. Started at login the program is the venv's Python instead,
which counts as something different. So grant Screen Recording and
Accessibility once more, this time to:

```
~/Downloads/uniqr/.venv/bin/python
```

In the **+** dialog, press **Cmd+Shift+G** to type that path.

---

## Linux

Works under X11. Wayland blocks screen capture and global hotkeys by design,
so UniQR cannot work there yet.

```
git clone https://github.com/pat-selby/uniqr.git
cd uniqr
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
uniqr
```

The hotkey is **Ctrl+Alt+Q**.

---

## When something is wrong

**Run the check.** It tests everything in order and says what failed and why:

```
python tools/diagnose.py
```

It ends by asking you to press the hotkey, so it can confirm the keypress
actually arrives.

**Read the log.** UniQR writes everything it does to a file, which matters
because a background app has nowhere to print:

| | |
|---|---|
| Windows | `%LOCALAPPDATA%\UniQR\uniqr.log` |
| macOS | `~/Library/Logs/UniQR/uniqr.log` |
| Linux | `~/.local/state/uniqr/uniqr.log` |

### Common ones

**"No QR code found" but I can see a code.** It is almost certainly drawn too
small. Below roughly 1.3 pixels per module the black and white squares have
blurred into grey and the information is gone, for any reader including your
phone. Zoom the page in with `Ctrl +` or `Cmd +` and scan again. Zooming makes
the browser redraw the code larger, which is not the same as enlarging a
picture of it.

**Nothing happens at all when I press the hotkey.** Another app may have the
same combination, or on macOS the Accessibility permission is missing. Press
the hotkey with no QR code on screen: if you get a short "No QR code found"
card, UniQR heard you fine and the problem is the code, not the key.

**It was working, now it is not.** Check the app is still running. On Windows
look for the tray icon; on macOS check the Terminal window is still open.

UniQR watches itself. If it stops answering for 10 seconds, it writes where it
got stuck to the log. After 45 seconds it starts a fresh copy of itself. If it
freezes again right away, three times in a row, it stops trying and stays
closed. Look in the log for lines like these:

- `UniQR has not answered for N seconds` followed by a list of code locations.
  Send that list to whoever maintains UniQR; it names the exact cause.
- `UniQR restarted itself` means a freeze happened and it recovered.
- `The last run did not exit cleanly` at startup means the last copy was closed
  by something other than Exit. A shutdown, a crash and a freeze all look the
  same here, and the line gives the last time it was seen alive.

---

## Removing it

```
pip uninstall uniqr
```

Then delete the folder, and:

- **Windows**: delete the shortcut from `shell:startup`
- **macOS**: `launchctl unload ~/Library/LaunchAgents/com.patselby.uniqr.plist`
  and delete that file, then remove the entries you added under Privacy &
  Security

Nothing else is written anywhere except the log file listed above.
