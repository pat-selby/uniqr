"""Generate a demo scene of QR codes that are not black on white.

Each tile is a colour combination that defeats a naive grey-scale threshold in
a different way - low luminance separation, inverted polarity, or stylised
modules. Useful as a demo backdrop and as a visual regression check.

    python tools/make_color_scene.py -o color_scene.png
"""

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from uniqr.decode import Scanner  # noqa: E402

W, H = 1920, 1080
BG = (28, 24, 22)
LABEL = (225, 225, 230)

# (label, payload, dark BGR, light BGR, dotted)
TILES = [
    ("black on white", "https://uniqr.dev/plain", (20, 20, 20), (255, 255, 255), False),
    ("white on black", "https://uniqr.dev/inverted", (245, 245, 245), (18, 18, 18), False),
    ("navy on crimson", "https://uniqr.dev/crimson", (60, 25, 20), (60, 20, 140), False),
    ("green on cream", "https://uniqr.dev/green", (40, 90, 20), (205, 245, 255), False),
    ("purple on pink", "https://uniqr.dev/purple", (110, 20, 70), (235, 220, 255), False),
    ("teal, dotted", "https://uniqr.dev/dotted", (110, 95, 15), (250, 250, 245), True),
]


def render(payload, dark, light, dotted, scale=7):
    grid = (cv2.QRCodeEncoder.create().encode(payload) < 128).astype(np.uint8)
    n = grid.shape[0]
    out = np.zeros((n * scale, n * scale, 3), dtype=np.uint8)
    out[:] = light
    for y in range(n):
        for x in range(n):
            if not grid[y, x]:
                continue
            cx, cy = x * scale, y * scale
            if dotted:
                cv2.circle(
                    out,
                    (cx + scale // 2, cy + scale // 2),
                    max(1, int(scale * 0.44)),
                    dark,
                    -1,
                )
            else:
                out[cy : cy + scale, cx : cx + scale] = dark
    quiet = scale * 4
    canvas = np.zeros((out.shape[0] + quiet * 2, out.shape[1] + quiet * 2, 3), np.uint8)
    canvas[:] = light
    canvas[quiet:-quiet, quiet:-quiet] = out
    return canvas


def build() -> np.ndarray:
    scene = np.zeros((H, W, 3), dtype=np.uint8)
    scene[:] = BG
    cv2.putText(
        scene, "UniQR - colour and style stress test", (60, 78),
        cv2.FONT_HERSHEY_SIMPLEX, 1.1, LABEL, 2, cv2.LINE_AA,
    )

    cols, margin, top = 3, 90, 150
    cell_w = (W - margin * 2) // cols
    cell_h = 400
    for i, (label, payload, dark, light, dotted) in enumerate(TILES):
        tile = render(payload, dark, light, dotted)
        tile = cv2.resize(tile, (250, 250), interpolation=cv2.INTER_NEAREST)
        col, row = i % cols, i // cols
        x = margin + col * cell_w + (cell_w - 250) // 2
        y = top + row * cell_h
        scene[y : y + 250, x : x + 250] = tile
        (tw, _), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.62, 1)
        cv2.putText(
            scene, label, (x + (250 - tw) // 2, y + 290),
            cv2.FONT_HERSHEY_SIMPLEX, 0.62, LABEL, 1, cv2.LINE_AA,
        )
    return scene


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("-o", "--out", default="color_scene.png")
    args = p.parse_args()

    scene = build()
    cv2.imwrite(args.out, scene)

    found = {d.text for d in Scanner().scan(scene)}
    expected = {payload for _, payload, *_ in TILES}
    print(f"wrote {args.out}  {scene.shape[1]}x{scene.shape[0]}")
    print(f"decoded {len(found & expected)}/{len(expected)}")
    for label, payload, *_ in TILES:
        print(f"  {'ok  ' if payload in found else 'FAIL'} {label}")
    return 0 if expected <= found else 1


if __name__ == "__main__":
    raise SystemExit(main())
