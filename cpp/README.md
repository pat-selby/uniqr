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
every read. On the benchmark below that cost one code in 1,064, and it takes
work out of every step of the ladder.

### Not ported yet

- The opt-in update check and the first-run questions
- The watchdog that restarts a stuck app
- The macOS and Linux desktop apps (the scanner and its tests do build on Linux)

## How it compares

1,064 generated codes from the benchmark lab (seed 11, which neither scanner
was tuned on), plus 48 images with no code in them:

| | decoded | wrong | false alarms | median ms per image | total seconds |
|---|---:|---:|---:|---:|---:|
| Python | 1,027 | 0 | 0 | 70 | 214 |
| C++ | 1,026 | 0 | 0 | 4 | 83 |

Both read the same 1,026 codes. The one only Python read is a tilted,
inverted QR code that zxing-cpp cannot read and OpenCV's QR detector can.
That is the cost of leaving OpenCV out. MaxiCode is slow in both, because
both make the same zxing-cpp reads there, so there is little for C++ to save.

Each lab image holds one code, and most are small images. On a screen-sized
page, C++ takes about 180 ms, against about 400 to 470 ms for Python. That is
because C++ always enlarges a screen to look for small codes, even after it
has found some (see below).

"Not decoded" here includes codes damaged past reading, which the main lab
report counts separately. Both scanners saw the same images, one at a time,
on one process each, on one Windows laptop, so the times shift with whatever
else the laptop is doing. To run it yourself:

```bash
python -m benchmarks.compare_cpp --exe cpp/build/uniqr-scan.exe --per-cell 4 --seed 11
```

### Several codes on one screen

`benchmarks/many_codes.py` builds 1920x1080 pages holding 2 to 12 QR codes in
the lab's styles, none overlapping. `--hard` makes them smaller (1.8 to 3.2
pixels per module) and damages each one: tilt, glare, blur, low contrast,
noise or JPEG. Seed 33, 30 pages and 198 codes in each mode, which neither
scanner was tuned on:

| | clean: found | clean: median ms | hard: found | hard: median ms | wrong |
|---|---:|---:|---:|---:|---:|
| Python | 198 of 198 | 729 | 180 of 198 | 544 | 0 |
| C++ | 198 of 198 | 198 | 195 of 198 | 191 | 0 |

Before this change C++ read 170 of 198 hard codes on seed 21. Once it found
one code it stopped looking, so small codes next to big ones were never
enlarged. It now enlarges the screen every time, which costs about 150 ms on
1080p and puts a 4K screen at about 0.7 s.

```bash
python -m benchmarks.many_codes --exe cpp/build/uniqr-scan.exe --hard --seed 33
```
