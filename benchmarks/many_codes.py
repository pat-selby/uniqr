"""Screens with several codes on them: how many does each scanner find, and how fast?

    python -m benchmarks.many_codes --exe cpp/build/uniqr-scan.exe
    python -m benchmarks.many_codes --exe ... --pages 8 --seed 21

The main lab puts one code on each image. A real screen often holds several, and
that is where the picker opens and where slowness shows. Each page here is a
1920x1080 page with text and boxes (the lab's background), holding 2 to 12 QR
codes in the lab's styles, at 2.5 to 6 pixels per module, none overlapping.

Both scanners read the same PNGs, one at a time. For every page the report
counts the codes found, the codes missed and any text that is not one of the
page's codes (a wrong answer).
"""

import argparse
import json
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import cv2
import numpy as np

from benchmarks import distort, generate
from benchmarks.generate import QR_STYLES, Case

HERE = Path(__file__).parent
PAGE = (1920, 1080)
COUNTS = (2, 4, 6, 9, 12)
HARD = ["rotate", "perspective", "blur", "low_contrast", "jpeg", "noise", "glare"]


def make_page(n: int, seed: int, hard: bool = False) -> tuple[np.ndarray, list[str]]:
    rng = np.random.default_rng(seed)
    page = distort.on_page(np.full((8, 8, 3), 255, np.uint8), PAGE, rng)
    cols = 4 if n > 6 else 3
    rows = -(-n // cols)
    cw, ch = PAGE[0] // cols, PAGE[1] // rows
    payloads = []
    for i in range(n):
        case = Case(
            id=f"{seed}-{i}", fmt="qr", style=str(rng.choice(QR_STYLES)),
            ec=str(rng.choice(list(generate.EC_LEVELS))), ppm=float(rng.uniform(1.8, 3.2) if hard else rng.uniform(2.5, 6.0)),
            payload=f"https://example.com/many/{seed}/{i}/{int(rng.integers(1e6))}",
            tags=["clean"], seed=seed * 1000 + i,
        )
        img = generate.render(case)
        pad = max(8, int(case.ppm * 3))  # a quiet zone in the code's own background
        img = cv2.copyMakeBorder(img, pad, pad, pad, pad, cv2.BORDER_CONSTANT,
                                 value=tuple(int(v) for v in img[2, 2]))
        if hard:  # one of the lab's kinds of damage, at full strength
            img = distort.apply(img, [str(rng.choice(HARD))], rng, case.ppm, case.ec, 1.0)
        h, w = img.shape[:2]
        r, c = divmod(i, cols)
        if h > ch - 10 or w > cw - 10:  # too big for its cell: shrink it
            s = min((ch - 10) / h, (cw - 10) / w)
            img = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
            h, w = img.shape[:2]
        y = r * ch + int(rng.integers(0, max(1, ch - h)))
        x = c * cw + int(rng.integers(0, max(1, cw - w)))
        page[y:y + h, x:x + w] = img
        payloads.append(case.payload)
    return page, payloads


def scan_python(paths):
    sys.path.insert(0, str(HERE.parent))
    from uniqr.decode import Scanner

    sc = Scanner()
    sc.scan(np.full((200, 200, 3), 128, np.uint8))
    out = []
    for p in paths:
        img = cv2.imread(str(p))
        t = time.perf_counter()
        found = sc.scan(img)
        out.append(([d.text for d in found], (time.perf_counter() - t) * 1000))
    return out


def scan_cpp(exe, paths):
    proc = subprocess.Popen([str(Path(exe).resolve()), "--serve"], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, text=True, encoding="utf-8")
    out = []
    for p in paths:
        proc.stdin.write(f"{p}\n")
        proc.stdin.flush()
        row = json.loads(proc.stdout.readline())
        out.append(([c["text"] for c in row["codes"]], row["ms"]))
    proc.stdin.close()
    proc.wait()
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--exe", help="uniqr-scan(.exe); leave out to score Python alone")
    ap.add_argument("--pages", type=int, default=6, help="pages per code count")
    ap.add_argument("--seed", type=int, default=21)
    ap.add_argument("--keep", help="also save the pages to this folder")
    ap.add_argument("--hard", action="store_true", help="smaller codes, each damaged one way")
    args = ap.parse_args()

    pages = [(n, args.seed * 100 + n * 10 + k) for n in COUNTS for k in range(args.pages)]
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(args.keep or tmp)
        folder.mkdir(parents=True, exist_ok=True)
        truth, paths = [], []
        for n, seed in pages:
            img, payloads = make_page(n, seed, args.hard)
            path = folder / f"page_{n:02d}_{seed}.png"
            cv2.imwrite(str(path), img)
            truth.append(set(payloads))
            paths.append(path)
        engines = {"Python": scan_python(paths)}
        if args.exe:
            engines["C++"] = scan_cpp(args.exe, paths)

    print(f"{len(pages)} pages, {sum(len(t) for t in truth)} codes (seed {args.seed})\n")
    print("| codes on page | " + " | ".join(f"{e} found | {e} median ms" for e in engines) + " |")
    print("|---:|" + "---:|---:|" * len(engines))
    for n in COUNTS:
        idx = [i for i, (m, _) in enumerate(pages) if m == n]
        cells = []
        for rows in engines.values():
            got = sum(len(truth[i] & set(rows[i][0])) for i in idx)
            cells.append(f"{got}/{n * len(idx)}")
            cells.append(f"{statistics.median(rows[i][1] for i in idx):.0f}")
        print(f"| {n} | " + " | ".join(cells) + " |")
    for name, rows in engines.items():
        found = sum(len(t & set(r[0])) for t, r in zip(truth, rows, strict=True))
        wrong = sum(len(set(r[0]) - t) for t, r in zip(truth, rows, strict=True))
        total = sum(len(t) for t in truth)
        print(f"\n{name}: {found}/{total} found, {wrong} wrong, "
              f"median {statistics.median(r[1] for r in rows):.0f} ms")
        missed = [(p.name, sorted(t - set(r[0]))) for p, t, r in zip(paths, truth, rows, strict=True)
                  if t - set(r[0])]
        for page_name, codes in missed[:12]:
            print(f"  missed on {page_name}: {len(codes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
