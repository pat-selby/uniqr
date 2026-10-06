"""For every saved failure, find out what would have read it.

    python -m benchmarks.run            # saves misses to benchmarks/failures/
    python -m benchmarks.search         # which fixes recover them?

This is the "learn from failures" loop, done with arithmetic instead of
guesswork. For each miss it tries many image treatments (grayscale, contrast
equalising, blur, sharpen, enlarge, two at a time) against several zxing
settings, and reports the recipes that decode it. Misses that nothing recovers
are named too: those are either unreadable or need something new.

It only ever suggests. A recipe that fixes three misses is a lead, not a
change: put it in the scanner, then run the benchmark on a seed you did not
tune against, to see whether it generalises. A fix that helps the failures it
was found on and nothing else is overfitting.

Skips failures marked unreadable and failures that returned the wrong text.
"""

import argparse
import collections
import itertools
import json
import warnings
from pathlib import Path

import cv2
import numpy as np
import zxingcpp

HERE = Path(__file__).parent
BF = zxingcpp.BarcodeFormat
BIN = zxingcpp.Binarizer

FORMAT_OF = {
    "qr": BF.QRCode, "micro_qr": BF.MicroQRCode, "rmqr": BF.RMQRCode,
    "data_matrix": BF.DataMatrix, "aztec": BF.Aztec, "pdf417": BF.PDF417,
    "maxicode": BF.MaxiCode,
}


def _gray(i: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(i, cv2.COLOR_BGR2GRAY)


def _bg_normalised(i: np.ndarray) -> np.ndarray:
    g = _gray(i).astype(np.float32)
    flat = g / (cv2.GaussianBlur(g, (0, 0), 25) + 1) * 200
    return np.clip(flat, 0, 255).astype(np.uint8)


TREATMENTS = {
    "as is": lambda i: i,
    "gray": _gray,
    "clahe": lambda i: cv2.createCLAHE(3.0, (8, 8)).apply(_gray(i)),
    "enlarge 2x": lambda i: cv2.resize(i, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC),
    "enlarge 3x": lambda i: cv2.resize(i, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC),
    "shrink 2x": lambda i: cv2.resize(i, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA),
    "sharpen": lambda i: cv2.addWeighted(i, 1.8, cv2.GaussianBlur(i, (0, 0), 2), -0.8, 0),
    "median": lambda i: cv2.medianBlur(i, 3),
    "soften": lambda i: cv2.GaussianBlur(i, (0, 0), 1.2),
    "flatten lighting": _bg_normalised,
}
SETTINGS = {
    "default": {},
    "global threshold": {"binarizer": BIN.GlobalHistogram},
    "fixed threshold": {"binarizer": BIN.FixedThreshold},
    "no downscale": {"try_downscale": False},
}
PAIRABLE = ["gray", "clahe", "flatten lighting", "enlarge 2x", "sharpen", "median", "soften"]


def reads(image: np.ndarray, formats: list, payload: str, **settings) -> bool:
    try:
        return payload in [r.text for r in zxingcpp.read_barcodes(image, formats=formats, **settings)]
    except Exception:  # noqa: BLE001 - a treatment that breaks is just one that fails
        return False


def recipes_for(image: np.ndarray, fmt: str, payload: str) -> list[str]:
    formats = [FORMAT_OF[fmt]]
    found = []

    def attempt(label: str, img: np.ndarray) -> None:
        for sname, settings in SETTINGS.items():
            if reads(img, formats, payload, **settings):
                found.append(f"{label} + {sname}")

    for name, fn in TREATMENTS.items():
        attempt(name, fn(image))
    for a, b in itertools.permutations(PAIRABLE, 2):
        try:
            attempt(f"{a}, then {b}", TREATMENTS[b](TREATMENTS[a](image)))
        except cv2.error:
            continue
    return found


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--failures", type=Path, default=HERE / "failures")
    p.add_argument("--top", type=int, default=6, help="recipes to list per group")
    args = p.parse_args()
    warnings.simplefilter("ignore")

    metas = sorted(args.failures.glob("*.json"))
    if not metas:
        print("no saved failures; run `python -m benchmarks.run` first")
        return 0

    by_group: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    sizes: collections.Counter = collections.Counter()
    unrecovered: list[str] = []
    for path in metas:
        m = json.loads(path.read_text())
        if m.get("unreadable") or m.get("wrong"):
            continue
        group = f"{m['fmt']} / {m['style']} / {m['tags'][0]}"
        sizes[group] += 1
        found = recipes_for(cv2.imread(str(path.with_suffix(".png"))), m["fmt"], m["payload"])
        if not found:
            unrecovered.append(f"{path.stem} ({group})")
        for r in set(found):
            by_group[group][r] += 1

    if not sizes:
        print("every saved failure is unreadable or a wrong answer; nothing to search")
        return 0
    for group, count in sizes.items():
        print(f"\n{group}   ({count} misses)")
        for recipe, n in by_group[group].most_common(args.top):
            print(f"   {n}/{count}  {recipe}")
        if not by_group[group]:
            print("   nothing recovers these")
    if unrecovered:
        print(f"\nNothing recovered {len(unrecovered)} misses: " + ", ".join(unrecovered))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
