"""Score UniQR on thousands of generated codes.

    python -m benchmarks.run                      # a quick, balanced run
    python -m benchmarks.run --per-cell 10        # more cases, tighter numbers
    python -m benchmarks.run --formats qr --tags rotate,blur
    python -m benchmarks.run --replay             # re-run saved failures only

Every case is a code whose true contents we know, drawn in some style at some
size, then damaged. UniQR scans it and either returns the right text, returns
something else (a false decode: the dangerous one), or returns nothing.

Three numbers matter and they are kept apart:

  decoded    the right text came back
  wrong      text came back but it was not the right text
  missed     nothing came back

"Wrong" is reported on its own because a scanner that sometimes confidently
hands you the wrong link is worse than one that sometimes says nothing.

Failures are written to benchmarks/failures/ with everything needed to rebuild
them. That folder stays out of git: it is a scratch pad, not a record.
"""

import argparse
import json
import multiprocessing as mp
import statistics
import sys
import time
from collections import defaultdict
from dataclasses import replace
from pathlib import Path

import cv2
import numpy as np
import zxingcpp

from benchmarks import distort, generate
from benchmarks.generate import OTHER_FORMATS, QR_STYLES, Case

HERE = Path(__file__).parent
FAILURES = HERE / "failures"
RESULTS = HERE / "RESULTS.md"

TAGS = ["clean", "small", *distort.DISTORTIONS, "combined", "scene"]
FORMATS = ["qr", *OTHER_FORMATS]
PAGE = (1920, 1080)
ORACLE_PPM = 12.0
_BF = zxingcpp.BarcodeFormat
ALL_2D = [
    _BF.QRCode, _BF.MicroQRCode, _BF.RMQRCode, _BF.DataMatrix,
    _BF.Aztec, _BF.PDF417, _BF.MaxiCode,
]

_scanner = None


def _init_worker() -> None:
    global _scanner
    sys.path.insert(0, str(HERE.parent))
    from uniqr.decode import Scanner

    _scanner = Scanner()


def build_cases(
    per_cell: int, seed: int, formats: list[str], tags: list[str], styles: list[str]
) -> list[Case]:
    cases: list[Case] = []
    for fmt in formats:
        for style in styles if fmt == "qr" else ["plain"]:
            for tag in tags:
                for _ in range(per_cell):
                    i = len(cases)
                    rng = np.random.default_rng(seed * 1_000_003 + i)
                    ec = str(rng.choice(list(generate.EC_LEVELS)))
                    ppm = float(rng.uniform(1.6, 2.4) if tag == "small" else rng.uniform(3.0, 6.0))
                    if fmt == "maxicode":
                        ppm *= 1.5  # its modules are hexagons drawn far larger
                    cases.append(
                        Case(
                            id=f"{i:05d}",
                            fmt=fmt,
                            style=style,
                            ec=ec,
                            ppm=ppm,
                            payload=generate.make_payload(rng, fmt),
                            tags=[tag],
                            seed=seed * 1_000_003 + i,
                        )
                    )
    return cases


def make_image(case: Case) -> np.ndarray:
    """The final pixels for a case: render, damage, and place."""
    rng = np.random.default_rng(case.seed + 7)
    img = generate.render(case)
    # Room around the code, so rotation and perspective have somewhere to go.
    pad = max(12, int(case.ppm * 3))
    bgc = tuple(int(v) for v in img[2, 2])
    img = cv2.copyMakeBorder(img, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=bgc)

    tag = case.tags[0]
    # Only QR has a level to size damage by; the others get the flat default.
    ec = case.ec if case.fmt == "qr" else "-"
    if tag == "combined":
        names = [str(n) for n in rng.choice(distort.STACKABLE, 3, replace=False)]
        img = distort.apply(img, names, rng, case.ppm, ec, 0.5)
    elif tag in distort.DISTORTIONS:
        img = distort.apply(img, [tag], rng, case.ppm, ec, 1.0)
    if tag == "scene":
        img = distort.on_page(img, PAGE, rng)
    return img


def run_case(case: Case) -> dict:
    img = make_image(case)
    t0 = time.perf_counter()
    found = _scanner.scan(img)  # type: ignore[union-attr]
    ms = (time.perf_counter() - t0) * 1000
    texts = [d.text for d in found]
    ok = case.payload in texts
    wrong = bool(texts) and not ok
    unreadable = False
    if not ok and not wrong:
        # A miss is only UniQR's fault if a reader could have done better.
        # Redraw the same code and the same damage, 12 pixels per module, and
        # try again. If that fails too, the damage destroyed the information.
        big = make_image(replace(case, ppm=ORACLE_PPM))
        found_big = [d.text for d in _scanner.scan(big)]  # type: ignore[union-attr]
        # Also ask zxing directly, for every 2D format. UniQR may not look for
        # a format at all yet, and "UniQR can't read it" must not be allowed to
        # pass for "nobody can read it".
        found_big += [r.text for r in zxingcpp.read_barcodes(big, formats=ALL_2D)]
        unreadable = case.payload not in found_big
    if not ok:
        FAILURES.mkdir(exist_ok=True)
        cv2.imwrite(str(FAILURES / f"{case.id}.png"), img)
        meta = case.to_json() | {"got": texts, "wrong": wrong, "unreadable": unreadable}
        (FAILURES / f"{case.id}.json").write_text(json.dumps(meta, indent=1))
    return {
        **case.to_json(), "ok": ok, "wrong": wrong, "unreadable": unreadable, "ms": ms,
    }


# -- images with no code in them --------------------------------------------


def negative_images(count: int, seed: int) -> list[tuple[str, np.ndarray]]:
    """Pages with nothing to find. Anything read from these is a false alarm."""
    rng = np.random.default_rng(seed)
    out: list[tuple[str, np.ndarray]] = []
    for i in range(count):
        kind = i % 6
        if kind == 0:
            img = np.full((720, 1280, 3), int(rng.integers(0, 256)), np.uint8)
            name = "blank page"
        elif kind == 1:
            img = rng.integers(0, 256, (720, 1280, 3), dtype=np.uint8)
            name = "random noise"
        elif kind == 2:
            img = distort.on_page(
                np.full((8, 8, 3), 255, np.uint8), PAGE, rng
            )
            name = "text and boxes"
        elif kind == 3:
            n = int(rng.integers(12, 40))
            cells = (rng.random((n, n)) > 0.5).astype(np.uint8) * 255
            img = cv2.resize(cells, None, fx=12, fy=12, interpolation=cv2.INTER_NEAREST)
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            name = "random squares, no finder"
        elif kind == 4:
            cells = np.indices((24, 24)).sum(axis=0) % 2
            img = cv2.resize(
                (cells * 255).astype(np.uint8), None, fx=10, fy=10, interpolation=cv2.INTER_NEAREST
            )
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            name = "checkerboard"
        else:
            fmt = generate.NEGATIVE_FORMATS[(i // 6) % len(generate.NEGATIVE_FORMATS)]
            text = {"EAN13": "5901234123457", "ITF": "12345678"}.get(fmt, "HELLO12345")
            bc = zxingcpp.create_barcode(text, getattr(zxingcpp.BarcodeFormat, fmt))
            raw = np.array(zxingcpp.write_barcode_to_image(bc, scale=4))
            img = cv2.cvtColor(raw, cv2.COLOR_GRAY2BGR) if raw.ndim == 2 else raw
            name = f"linear barcode ({fmt})"
        out.append((name, img))
    return out


def run_negative(item: tuple[str, np.ndarray]) -> dict:
    name, img = item
    found = _scanner.scan(img)  # type: ignore[union-attr]
    return {"kind": name, "found": [d.text for d in found]}


# -- reporting ---------------------------------------------------------------


def _rate(rows: list[dict], key: str) -> float:
    return 100 * sum(1 for r in rows if r[key]) / len(rows) if rows else 0.0


def _missed(r: dict) -> bool:
    return not r["ok"] and not r["wrong"] and not r["unreadable"]


def table(title: str, groups: dict[str, list[dict]]) -> list[str]:
    lines = [
        f"### {title}",
        "",
        "| | cases | decoded | wrong | missed | unreadable | median ms |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, rows in groups.items():
        missed = 100 * sum(1 for r in rows if _missed(r)) / len(rows)
        lines.append(
            f"| {name} | {len(rows)} | {_rate(rows, 'ok'):.1f}% | "
            f"{_rate(rows, 'wrong'):.1f}% | {missed:.1f}% | {_rate(rows, 'unreadable'):.1f}% | "
            f"{statistics.median(r['ms'] for r in rows):.0f} |"
        )
    return [*lines, ""]


def group_by(rows: list[dict], key) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[key(r)].append(r)
    return dict(sorted(groups.items()))


def _headline(rows: list[dict]) -> str:
    readable = [r for r in rows if not r["unreadable"]]
    return (
        f"**Overall: {_rate(rows, 'ok'):.1f}% decoded of all {len(rows)} codes, "
        f"{_rate(readable, 'ok'):.1f}% of the {len(readable)} a reader could read. "
        f"Wrong answers: {sum(1 for r in rows if r['wrong'])}.**"
    )


def report(rows: list[dict], negatives: list[dict], args, seconds: float) -> str:
    lines = [
        "# UniQR benchmark",
        "",
        f"Generated by `python -m benchmarks.run --per-cell {args.per_cell} --seed {args.seed}`.",
        f"{len(rows)} generated codes, {len(negatives)} images with no code, "
        f"scored in {seconds:.0f} seconds.",
        "",
        "Every code is drawn at a known size and damaged in a way sized to be bad "
        "but fair.",
        "",
        "- **decoded**: the exact text came back.",
        "- **wrong**: different text came back. The dangerous failure.",
        "- **missed**: nothing came back, but the same code enlarged to 12 pixels "
        "per module does decode, so a better scanner could have read it.",
        "- **unreadable**: nothing came back, and the enlarged copy fails too. The "
        "damage destroyed the information. Not counted against UniQR.",
        "",
        _headline(rows),
        "",
    ]
    lines += table("By format", group_by(rows, lambda r: r["fmt"]))
    qr_rows = [r for r in rows if r["fmt"] == "qr"]
    if qr_rows:
        lines += table("QR codes, by style", group_by(qr_rows, lambda r: r["style"]))
        lines += table("QR codes, by condition", group_by(qr_rows, lambda r: r["tags"][0]))
    other = [r for r in rows if r["fmt"] != "qr"]
    if other:
        lines += table("Other formats, by condition", group_by(other, lambda r: r["tags"][0]))

    if negatives:
        bad = [n for n in negatives if n["found"]]
        lines += [
            "### Images with no code in them",
            "",
            f"{len(negatives) - len(bad)} of {len(negatives)} came back empty, as they should. "
            f"**{len(bad)} false alarms.**",
            "",
        ]
        for n in bad[:10]:
            lines.append(f"- {n['kind']}: read {n['found']!r}")
        lines.append("")
    return "\n".join(lines)


def replay() -> int:
    """Re-scan every saved failure with the current scanner."""
    files = sorted(FAILURES.glob("*.png"))
    if not files:
        print("no saved failures")
        return 0
    _init_worker()
    fixed = 0
    for f in files:
        meta = json.loads(f.with_suffix(".json").read_text())
        found = _scanner.scan(cv2.imread(str(f)))  # type: ignore[union-attr]
        ok = any(d.text == meta["payload"] for d in found)
        fixed += ok
        label = "NOW DECODES" if ok else ("unreadable" if meta.get("unreadable") else "still fails")
        print(f"{f.stem}  {meta['fmt']:<11} {meta['style']:<18} {meta['tags'][0]:<12} {label}")
    print(f"\n{fixed} of {len(files)} saved failures now decode")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--per-cell", type=int, default=3)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--workers", type=int, default=max(1, (mp.cpu_count() or 2) - 1))
    p.add_argument("--formats", default=",".join(FORMATS))
    p.add_argument("--styles", default=",".join(QR_STYLES))
    p.add_argument("--tags", default=",".join(TAGS))
    p.add_argument("--negatives", type=int, default=48)
    p.add_argument("--no-report", action="store_true", help="do not rewrite RESULTS.md")
    p.add_argument("--replay", action="store_true")
    args = p.parse_args()

    if args.replay:
        return replay()

    # Old failures would be mistaken for new ones.
    for old in FAILURES.glob("*"):
        old.unlink()

    cases = build_cases(
        args.per_cell, args.seed, args.formats.split(","), args.tags.split(","),
        args.styles.split(","),
    )
    negs = negative_images(args.negatives, args.seed) if args.negatives else []
    print(f"{len(cases)} codes, {len(negs)} no-code images, {args.workers} workers")

    t0 = time.perf_counter()
    with mp.Pool(args.workers, initializer=_init_worker) as pool:
        rows = []
        for n, row in enumerate(pool.imap_unordered(run_case, cases, chunksize=4), 1):
            rows.append(row)
            if n % 100 == 0:
                print(f"  {n}/{len(cases)}", flush=True)
        negatives = pool.map(run_negative, negs, chunksize=4)
    seconds = time.perf_counter() - t0

    text = report(rows, negatives, args, seconds)
    print()
    print(text)
    if not args.no_report:
        RESULTS.write_text(text, encoding="utf-8")
        print(f"wrote {RESULTS}")
    print(f"failures saved to {FAILURES} (replay with --replay)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
