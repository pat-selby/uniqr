# Installing UniQR

Pick your system. Each takes a couple of minutes.

- [Windows](#windows)
- [macOS](#macos)
- [Linux](#linux)
- [Updates, problems, removing it](#updates)

---

## Windows

1. Download **UniQR.exe** from the [latest release](https://github.com/pat-selby/uniqr/releases/latest). Put it somewhere you'll keep it.
2. Double-click it. If Windows says **"Windows protected your PC"**, click **More info**, then **Run anyway**. It warns because the file isn't code-signed.
3. A card asks whether to start UniQR when you log in. Choose **Yes** or **Not now**.
4. Press **<img src="docs/windows-key.svg" alt="Windows logo key" height="14"> + Shift + Q** on any QR code.

UniQR sits in the tray next to the clock. Right-click its icon to quit, to turn start at login on or off, or to report a problem.

**Check the file** (optional): run `certutil -hashfile UniQR.exe SHA256` in that folder and compare with the release page.

**Another hotkey:** if another app has <img src="docs/windows-key.svg" alt="Windows logo key" height="14"> + Shift + Q, UniQR takes Ctrl + Alt + Q, then Ctrl + Shift + 9, and its start-up card says which. To pick your own, open PowerShell in the folder and run:

```
.\UniQR.exe --hotkey ctrl+alt+k
```

Use `ctrl`, `alt`, `shift` or `win`, then one letter, digit or F1 to F24. To keep it at login, run `.\UniQR.exe --install-autostart --hotkey ctrl+alt+k` once.

<details>
<summary>Run it from the source instead</summary>

You need Python 3.11 or newer.

```
git clone https://github.com/pat-selby/uniqr.git
cd uniqr
pip install -e ".[windows]"
uniqr
```

To start it at login: `python app.py --install-autostart`.
</details>

---

## macOS

There's no Mac download yet, so you run it from the source. You need Python 3.11 or newer (`python3 --version`).

1. In Terminal:

   ```
   git clone https://github.com/pat-selby/uniqr.git
   cd uniqr
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```

2. Open **System Settings → Privacy & Security** and switch on **Terminal** under **Screen Recording** and **Accessibility**. If the hotkey still does nothing later, add it under **Input Monitoring** too.
3. Quit Terminal fully with **Command + Q**, and open it again.
4. Start UniQR:

   ```
   cd uniqr
   source .venv/bin/activate
   uniqr
   ```

5. Press **Command + Shift + 8** on any QR code.

To quit, press **Control + C** in that Terminal window. There's no tray icon on a Mac.

**Another hotkey:** `UNIQR_HOTKEY='<cmd>+<shift>+9' uniqr`. Avoid Command + Q, Command + Shift + Q and Command + Control + Q: they quit, log out and lock.

**Start at login:** run `python3 tools/install_mac_agent.py` from the UniQR folder. It opens a Finder window showing the Python it uses: add that program under **Screen Recording** and **Accessibility** too.

**Known issue:** scanning inside a full-screen app takes you out of full screen to show the picker.

---

## Linux

UniQR needs an **X11** session. Run `echo $XDG_SESSION_TYPE`. If it says `wayland`, log out and choose the Xorg or X11 option on the login screen (on Ubuntu, "Ubuntu on Xorg").

1. Download **UniQR-linux-x86_64** from the [latest release](https://github.com/pat-selby/uniqr/releases/latest).
2. In a terminal, in that folder:

   ```
   chmod +x UniQR-linux-x86_64
   ./UniQR-linux-x86_64
   ```

3. A card asks whether to start UniQR when you log in. Press **Y** or **N**.
4. Press **Ctrl + Alt + Q** on any QR code.

To quit, press **Ctrl + C** in that terminal, or run `pkill UniQR-linux`.

**Check the file** (optional): put `UniQR-linux-x86_64.sha256` in the same folder and run `sha256sum -c UniQR-linux-x86_64.sha256`.

**Another hotkey:** `./UniQR-linux-x86_64 --hotkey '<ctrl>+<alt>+<shift>+q'`. To keep it at login: `./UniQR-linux-x86_64 --install-autostart --hotkey '<ctrl>+<alt>+<shift>+q'`.

The file is built for 64-bit Intel and AMD computers, on Ubuntu 22.04 or newer. On anything else, run it from the source: `git clone https://github.com/pat-selby/uniqr.git`, `cd uniqr`, `python3 -m venv .venv`, `source .venv/bin/activate`, `pip install -e .`, then `uniqr`.

---

## Updates

UniQR can tell you when a new version is out. It asks once, and it's off unless you say yes. Change it from the tray menu: **Check for updates automatically**. It never downloads or installs anything. It only asks GitHub for the newest version number.

## Reporting a problem

Right-click the tray icon and choose **Report a problem**. It opens a pre-filled GitHub page. Nothing is sent until you press **Submit**. Without a tray icon, run UniQR with `--report-problem`, or [open an issue](https://github.com/pat-selby/uniqr/issues/new?template=bug_report.md).

## When something is wrong

**Read the log:**

| | |
|---|---|
| Windows | `%LOCALAPPDATA%\UniQR\uniqr.log` |
| macOS | `~/Library/Logs/UniQR/uniqr.log` |
| Linux | `~/.local/state/uniqr/uniqr.log` |

- **"No QR code found", but I can see one:** it's drawn too small. Zoom the page in (**Ctrl + +** or **Command + +**) and scan again.
- **Nothing happens when I press the hotkey:** press it with no code on screen. If a "No QR code found" card appears, the hotkey works. If not, another app may have the same keys (pick another, above), or on a Mac a permission is missing.
- **It stopped working:** check it's still running (the tray icon on Windows, the Terminal window on a Mac). UniQR restarts itself if it freezes, and the log says so.
- **Running from the source:** `python tools/diagnose.py` checks everything in order and says what failed.

## Removing it

1. If it starts at login, run it once with `--uninstall-autostart` (on a Mac: `python3 tools/install_mac_agent.py --uninstall`).
2. Delete the file, or the `uniqr` folder if you ran it from the source.
3. To leave no trace, also delete its settings and log folders: `%LOCALAPPDATA%\UniQR` on Windows; `~/.config/uniqr` and `~/Library/Logs/UniQR` on a Mac; `~/.config/uniqr` and `~/.local/state/uniqr` on Linux.
