"""Crop test photos down to the codes they are testing.

The originals are photographs of conference tables: they carry other people's
contact details and identifiable venues, none of which is the point of the
test. This keeps the code, its quiet zone and enough surrounding context that
the locator still has real work to do, and moves the untouched originals into a
git-ignored folder.

    python tools/crop_fixtures.py            # report only
    python tools/crop_fixtures.py --apply
"""

import argparse
import shutil
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from uniqr.decode import Scanner  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PRIVATE = ROOT / "fixtures_private"

# Only the payloads the tests assert on. Codes outside this set are cropped
# away deliberately - the small CBRE flyer code in american.png sits on the
# flyer carrying the contact details.
KEEP = {
    "sap_flyer.png": {
        "https://bit.ly/4jQ5iLN",
        "https://bit.ly/40HVnio",
        "https://bit.ly/3WHdJiw",
    },
    "american.png": {"https://go.bofa.com/q/7b5032"},
    "morningstar.png": {
        "https://linktr.ee/qr/45d45578-8152-4e47-8609-2fb8a62923c4"
    },
}

# Fraction of the kept codes' span left around them. Generous on purpose: the
# locator should still have to find a code in context, not in a tight cutout.
MARGIN = 0.28


def crop_for(scanner: Scanner, path: Path, wanted: set[str]):
    image = cv2.imread(str(path))
    if image is None:
        return None, "could not read"

    found = [d for d in scanner.scan(image) if d.text in wanted]
    if len(found) != len(wanted):
        got = {d.text for d in found}
        return None, f"expected {len(wanted)} codes, found {len(got)}"

    xs = [v for d in found for v in (d.quad[:, 0].min(), d.quad[:, 0].max())]
    ys = [v for d in found for v in (d.quad[:, 1].min(), d.quad[:, 1].max())]
    span = max(max(xs) - min(xs), max(ys) - min(ys))
    pad = int(span * MARGIN)

    h, w = image.shape[:2]
    x0 = max(0, int(min(xs)) - pad)
    y0 = max(0, int(min(ys)) - pad)
    x1 = min(w, int(max(xs)) + pad)
    y1 = min(h, int(max(ys)) + pad)
    return image[y0:y1, x0:x1], f"{w}x{h} -> {x1 - x0}x{y1 - y0}"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--apply", action="store_true", help="write the crops")
    args = p.parse_args()

    scanner = Scanner()
    failures = 0

    for name, wanted in KEEP.items():
        path = ROOT / name
        if not path.exists():
            print(f"{name:<20} skip (missing)")
            continue

        cropped, detail = crop_for(scanner, path, wanted)
        if cropped is None:
            print(f"{name:<20} FAIL {detail}")
            failures += 1
            continue

        # The crop is only useful if the scanner still reads every code in it.
        still = {d.text for d in scanner.scan(cropped)}
        missing = wanted - still
        if missing:
            print(f"{name:<20} FAIL crop loses {len(missing)} code(s)")
            failures += 1
            continue

        print(f"{name:<20} ok   {detail}  ({len(wanted)} code(s) still decode)")

        if args.apply:
            PRIVATE.mkdir(exist_ok=True)
            shutil.copy2(path, PRIVATE / name)
            cv2.imwrite(str(path), cropped)

    if args.apply and not failures:
        print(f"\noriginals preserved in {PRIVATE.name}/ (git-ignored)")
    elif not args.apply:
        print("\ndry run - pass --apply to write")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
