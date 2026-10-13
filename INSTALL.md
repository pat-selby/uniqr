# Installing UniQR

Press a hotkey, read any QR code on your screen.

You need **Python 3.11 or newer**. Check with `python --version` on Windows, or
`python3 --version` on macOS and Linux. If you don't have it, get it from
[python.org](https://www.python.org/downloads/).

Pick your system below. Each takes about two minutes.

---

## Windows

### Easiest: the .exe

Download **UniQR.exe** from the
[latest release](https://github.com/pat-selby/uniqr/releases/latest). You don't
need Python or anything else.

1. Put it somewhere permanent, like `C:\Users\you\UniQR\`.
2. Double-click it. The first start takes a few seconds, because the file
   unpacks itself.
3. A card says UniQR is running, and asks whether to start it when you log in.
   Click **Yes, start at login** if you want that, or **Not now**. It sits in the
   system tray, next to the clock. Press **Win+Shift+Q** on a QR code.

The first time, Windows may say **"Windows protected your PC"** and name an
unknown publisher. That is because the file isn't code-signed, which costs money
every year. Click **More info**, then **Run anyway**. Only do that for a copy you
got from this repo's release page or from the person who made it. The release
page lists the file's SHA-256 fingerprint, and you can check yours against it:

```
certutil -hashfile UniQR.exe SHA256
```

To quit, right-click the tray icon and choose Exit.

### Start it when you log in

The first time you run the file, the card asks whether to start UniQR when you log
in. It asks once, and it never turns anything on unless you click Yes. If you
ignore the card three times it stops asking. You can change your mind at any time:
right-click the tray icon and click **Start at login**. A tick next to it means
it is on. This needs **version 0.1.6 or newer**.

The same thing from a command line, which works on version 0.1.4 and newer: open
PowerShell in the folder where you saved the file and run this once:

```
.\UniQR.exe --install-autostart
```

A small box tells you it worked. It takes a few seconds to appear, because the
file unpacks itself first. UniQR will start at your next login. It adds an entry
to Windows' list of programs that start at login, which needs no administrator
rights, and which you can see, and switch off, under **Settings, Apps, Startup**.

The entry records where the file is. If you move or rename it, run the command
again. To remove the entry:

```
.\UniQR.exe --uninstall-autostart
```

An older file ignores options it does not know, so it would just start normally.
The older way still works: press `Win+R`,
type `shell:startup`, press Enter, and drop a shortcut to UniQR.exe in that folder.

GitHub tests that the entry is written correctly, that the command stored in it
starts UniQR, and that quitting while the question is on screen works. It cannot
test a real login, so if UniQR does not start after you log in, tell me.

### Choosing a different hotkey

UniQR uses **Win+Shift+Q**. If another program already has it, UniQR tries
Ctrl+Alt+Q, then Ctrl+Shift+9. To use your own, start it with `--hotkey`. In
PowerShell, in the folder where you saved the file:

```
.\UniQR.exe --hotkey ctrl+alt+k
```

Write one or more of `ctrl`, `alt`, `shift` and `win`, then one letter, digit or
F1 to F24, joined by plus signs. Capital letters don't matter. You need at least
one of ctrl, alt, shift or win, so a plain letter can't be taken from every other
program.

To keep it every time you log in, add the same option when you set up start at
login:

```
.\UniQR.exe --install-autostart --hotkey ctrl+alt+k
```

If your hotkey is already used by another program, or can't be read, UniQR says so
in its log and uses one of the usual ones instead. The card on startup names the
hotkey it took. Starting without `--hotkey` goes back to Win+Shift+Q. This needs
**version 0.1.7 or newer**.

### Or run it from the source

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

If you installed from the source, run this once (from version 0.1.4 on). It points
at `pythonw.exe` for you, so no console window opens:

```
python app.py --install-autostart
```

Or by hand: press `Win+R`, type `shell:startup`, press Enter. Put a shortcut in
that folder pointing to:

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
python3 tools/install_mac_agent.py
```

Run it from the UniQR folder. It writes the startup file with this Mac's own
paths, creates the log folder, and starts UniQR. If you chose a different
hotkey above, add it: `python3 tools/install_mac_agent.py --hotkey '<cmd>+<shift>+8'`.

Do not copy the plist file from `tools/` by hand. It holds example paths, and
macOS cannot expand `~`, so a copy fails with status 78 and no explanation.

One catch. macOS grants permission to the **program that runs**, and you gave
it to Terminal. Started at login the program is the venv's Python instead,
which counts as something different. The script opens a Finder window with that
program selected. In **System Settings → Privacy & Security**, drag it into both
**Screen Recording** and **Accessibility**, and switch each on. The folder is
hidden, so in a file picker press **Cmd+Shift+.** to show it.

Then restart UniQR so it sees the new permission:

```
launchctl unload ~/Library/LaunchAgents/com.patselby.uniqr.plist && launchctl load ~/Library/LaunchAgents/com.patselby.uniqr.plist
```

To check it: `launchctl list | grep uniqr`. A number in the first column means it
is running. A dash and a number mean it started and stopped, and the reason is in
`~/Library/Logs/UniQR/uniqr.log`.

---

## Linux

UniQR works under **X11**. Many Linux desktops, Ubuntu among them, use Wayland
by default, and Wayland blocks screen capture and global hotkeys by design, so
UniQR cannot work there yet. Check which one you have:

```
echo $XDG_SESSION_TYPE
```

If it says `wayland`, log out and choose the Xorg or X11 option on the login
screen (on Ubuntu, "Ubuntu on Xorg"), then come back here. When UniQR cannot
read the screen it says so in its log (see "When something is wrong" below).

### Easiest: download the program

Download **UniQR-linux-x86_64** from the
[latest release](https://github.com/pat-selby/uniqr/releases/latest). You don't
need Python. In a terminal, in the folder where you saved it:

```
chmod +x UniQR-linux-x86_64
./UniQR-linux-x86_64
```

The first time, a card asks whether to start UniQR when you log in. Click **Yes,
start at login** or press **Y**, or click **Not now** or press **N**.

Press **Ctrl+Alt+Q** on a QR code. A card appears under it and the link is
copied. To quit, press Ctrl+C in that terminal, or run `pkill UniQR-linux`.
Closing the terminal usually stops it too. Some desktops show no tray icon, and the
hotkey still works.

To check you have the exact file published, download `UniQR-linux-x86_64.sha256`
into the same folder and run:

```
sha256sum -c UniQR-linux-x86_64.sha256
```

It should say `OK`.

This file is built for 64-bit Intel and AMD computers on Ubuntu 22.04, and
should run on systems that have a C library as new as Ubuntu 22.04's or newer.
It was tested by GitHub on a fake screen, not on every kind of Linux desktop. On
an ARM computer or an older system, use the source instead.

### Or run it from the source

This works on any Linux that has Python 3.11 or newer.

```
git clone https://github.com/pat-selby/uniqr.git
cd uniqr
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
uniqr
```

The hotkey is **Ctrl+Alt+Q**.

### Choosing a different hotkey

If **Ctrl+Alt+Q** is already used by something else on your desktop, pick another
combination. On Linux UniQR listens to the keyboard but cannot reserve a key, so
it cannot tell that another program has the combination. Both react when you
press it.

Set `UNIQR_HOTKEY` when you start UniQR, and put the whole combination in quotes
so the terminal leaves the angle brackets alone:

```
UNIQR_HOTKEY='<ctrl>+<alt>+<shift>+q' ./UniQR-linux-x86_64
```

You can also write it as an option, which does the same thing:

```
./UniQR-linux-x86_64 --hotkey '<ctrl>+<alt>+<shift>+q'
```

If you installed from the source, it is the same, with `uniqr` instead of
`./UniQR-linux-x86_64`.

The `--hotkey` option and the start-at-login commands below need **version 0.1.3
or newer**. `UNIQR_HOTKEY` works in every version. An older file ignores options it does not
know, so it would just start normally.

How to write one:

- Modifier keys go in angle brackets: `<ctrl>`, `<alt>`, `<shift>`, `<super>` (the
  Windows key). Join keys with `+`.
- Letters and digits go bare, in lowercase.
- Two to try: `<ctrl>+<shift>+9` and `<ctrl>+<alt>+<shift>+q`. Avoid
  **Ctrl+Shift+U**, which many Linux desktops use for typing special characters.

To keep it, add this line to `~/.bashrc` and open a new terminal:

```
export UNIQR_HOTKEY='<ctrl>+<alt>+<shift>+q'
```

The log shows which hotkey UniQR took, on the line that says it is running (see
"When something is wrong" below). `UNIQR_HOTKEY` and `--hotkey` work on Linux, on a
Mac and on Windows. On Windows they are written differently: see "Choosing a
different hotkey" in the Windows section.

### Start it at login

The first time you run the downloaded file, the card asks whether to start UniQR
when you log in. It asks once, and it never turns anything on unless you say yes.
If you ignore it three times it stops asking. If your desktop shows a tray icon,
right-click it and click **Start at login** to change your mind later. This needs
**version 0.1.6 or newer**, and only the downloaded file asks: a copy run from
the source does not.

The same thing from a terminal, which works on version 0.1.3 and newer. Run this
once, from the same folder as the file:

```
./UniQR-linux-x86_64 --install-autostart
```

From the source, with the virtual environment switched on, it is
`uniqr --install-autostart`.

If you use a different hotkey, say so here, because the line in `~/.bashrc` is not
read when the desktop starts a program at login:

```
./UniQR-linux-x86_64 --install-autostart --hotkey '<ctrl>+<alt>+<shift>+q'
```

That writes `~/.config/autostart/uniqr.desktop`, the standard place most Linux
desktops look for programs to start at login. It takes effect the next time you
log in. The command prints how to start UniQR right now without logging out.

The file records where the program is, so if you move or rename it, run the
command again. To undo it:

```
./UniQR-linux-x86_64 --uninstall-autostart
```

GitHub tests that the file is written correctly and that the command in it starts
UniQR with your hotkey. It cannot test a real login on a real desktop, so if it
does not start after you log in, tell me which desktop you use.

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
same combination (on Linux or a Mac, pick another with `UNIQR_HOTKEY`: see
"Choosing a different hotkey" in that section), or on macOS the Accessibility
permission is missing. Press
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

**If you downloaded the Windows or Linux file,** quit UniQR and delete the file
(`UniQR.exe` or `UniQR-linux-x86_64`). On Windows, also delete the shortcut from
`shell:startup` if you added one. If you set it to start at login with
`--install-autostart`, run `.\UniQR.exe --uninstall-autostart` (Windows) or
`./UniQR-linux-x86_64 --uninstall-autostart` (Linux) first, then delete the file.

**If you installed it from the source,** run this, then delete the folder:

```
pip uninstall uniqr
```

On a Mac, also run `python3 tools/install_mac_agent.py --uninstall` if you set it
to start at login, then remove the entries you added under Privacy & Security.

Nothing else is written anywhere except the log file listed under "When something
is wrong". Delete its folder too if you want no trace.
