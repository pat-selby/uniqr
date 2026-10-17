# UniQR, the C++ version

The same idea as the Python UniQR: press a hotkey, and every QR code on your
screen is read, checked and copied. This folder is a full port of the scanner
and the Windows app to C++20, with no OpenCV and no Python.

| | Python UniQR | C++ UniQR |
|---|---|---|
| Download | about 77 MB (PyInstaller) | about 1.9 MB, one exe |
| Libraries | OpenCV, zxing-cpp, NumPy, pywin32 | zxing-cpp, stb |
| Platforms | Windows, macOS, Linux | scanner: Windows and Linux. App: Windows |
| Status | released | new, not released |

## Build

You need CMake 3.24 or newer, Ninja, and a C++20 compiler (tested with
MSVC 14.5 on Windows and the GCC on GitHub's Ubuntu runner). CMake downloads zxing-cpp, stb and doctest itself.

```bash
cmake -S cpp -B cpp/build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build cpp/build
ctest --test-dir cpp/build --output-on-failure
```

On Windows, run these from a "Developer PowerShell for VS" so the compiler is
on the path. You get three programs:

| Program | What it is |
|---|---|
| `cpp/build/src/win/uniqr-cpp.exe` | the desktop app, with a tray icon and a hotkey |
| `cpp/build/uniqr-scan(.exe)` | a command-line scanner for image files |
| `cpp/build/tests/uniqr_tests(.exe)` | the unit tests |

## Use it

```bash
uniqr-cpp.exe                          # Win+Shift+Q scans the screen
uniqr-cpp.exe --hotkey ctrl+alt+k      # your own hotkey
uniqr-cpp.exe --install-autostart      # start at login (add --hotkey to keep one)
uniqr-cpp.exe --uninstall-autostart
uniqr-cpp.exe --report-problem         # a pre-filled GitHub issue
uniqr-scan --json photo.png            # read codes from a file
```

It behaves like the Python app. One code is copied and a card shows where
it goes. Several codes open a picker: hover to inspect, press 1 to 9 to copy,
Esc to cancel. Only http and https links can be opened, and the same safety
warnings appear (plain http, the @ trick, lookalike letters, raw IP
addresses). It stores its start-at-login entry as `UniQR-cpp`, so it never
touches the Python app's entry.

## How it is built

```
src/core/   the scanner and the safety rules. No operating system code.
  image     greyscale, resize (OpenCV's Lanczos, cubic and area), blur,
            CLAHE, Otsu, adaptive threshold, erode and dilate
  scanner   the retry ladder, ported step by step from uniqr/decode.py
  link      which links can open, and the warnings on the card
  hotkeys   the hotkey parser, with the same rules and messages as Python
  report    the "Report a problem" issue text
src/cli/    uniqr-scan
src/win/    the Windows app: hotkey, tray, screen capture, card, picker
tests/      doctest unit tests, plus the real photos from tests/fixtures
```

The image steps are written by hand to match OpenCV's results, so the port
needs no OpenCV. Big images are split across CPU threads by rows.

### What changed from the Python ladder

The Python scanner also runs OpenCV's two QR detectors and a "locate, then
straighten" pass. The C++ version leaves those out and uses zxing-cpp for
every read. On the benchmark below that cost no accuracy, and it is most of
the speed difference.

### Not ported yet

- The opt-in update check and the first-run questions
- The watchdog that restarts a stuck app
- The macOS and Linux desktop apps (the scanner and its tests do build on Linux)

## How it compares

RESULTS_TABLE

Both scanners saw the same images, one at a time, on one process each. To
run it yourself:

```bash
python -m benchmarks.compare_cpp --exe cpp/build/uniqr-scan.exe --per-cell 4 --seed 11
```
