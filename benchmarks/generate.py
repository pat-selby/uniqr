"""Make codes to test UniQR against: many styles, many symbologies.

Everything here is deterministic. A case is a description (a few numbers and
words), and the same description always renders the same pixels, so a failure
found today can be rebuilt exactly next month from its metadata alone.

Two sources of codes:

  qrcode (the library)  QR in rounded, dotted, gapped, bar and gradient
                        styles, at every error-correction level.
  our own renderer      what the library cannot do: custom finder patterns
                        (round and ring eyes), colored and inverted codes,
                        and a logo over the middle.
  zxing-cpp (writer)    Micro QR, rMQR, Data Matrix, Aztec, PDF417, MaxiCode.

Size is controlled by pixels per module (ppm), the number that decides whether
a code is readable at all. Below about 1.3 ppm the squares have blurred into
grey and the information is gone for every reader, so cases there measure the
floor, not a bug.
"""

from dataclasses import dataclass, field

import cv2
import numpy as np
import qrcode
import zxingcpp
from qrcode.constants import (
    ERROR_CORRECT_H,
    ERROR_CORRECT_L,
    ERROR_CORRECT_M,
    ERROR_CORRECT_Q,
)
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.colormasks import (
    HorizontalGradiantColorMask,
    RadialGradiantColorMask,
    SolidFillColorMask,
)
from qrcode.image.styles.moduledrawers.pil import (
    CircleModuleDrawer,
    GappedSquareModuleDrawer,
    HorizontalBarsDrawer,
    RoundedModuleDrawer,
    SquareModuleDrawer,
    VerticalBarsDrawer,
)

EC_LEVELS = {
    "L": ERROR_CORRECT_L,
    "M": ERROR_CORRECT_M,
    "Q": ERROR_CORRECT_Q,
    "H": ERROR_CORRECT_H,
}
# Share of the code the error correction can lose, roughly. Used to size the
# "damaged" distortion so it is fair: damage beyond this cannot be recovered
# by anyone, and scoring it would measure physics rather than UniQR.
EC_CAPACITY = {"L": 0.07, "M": 0.15, "Q": 0.25, "H": 0.30}

QR_STYLES = [
    "square",
    "rounded",
    "dots",
    "gapped",
    "bars_vertical",
    "bars_horizontal",
    "gradient_radial",
    "gradient_horizontal",
    "colored",
    "inverted",
    "logo",
    "eyes_round",
    "eyes_ring",
]

# Everything zxing-cpp can write that is a 2D code. Linear barcodes are left
# out on purpose: see NEGATIVE_FORMATS.
OTHER_FORMATS = {
    "micro_qr": "MicroQRCode",
    "rmqr": "RMQRCode",
    "data_matrix": "DataMatrix",
    "aztec": "Aztec",
    "pdf417": "PDF417",
    "maxicode": "MaxiCode",
}
# Linear barcodes are not something UniQR reads, so they must not trigger it
# either. They go in the no-code set to prove that.
NEGATIVE_FORMATS = ["EAN13", "Code128", "Code39", "ITF"]

_ALNUM = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
_URL_CHARS = "abcdefghijklmnopqrstuvwxyz0123456789-_/"


@dataclass
class Case:
    """Everything needed to rebuild one test image."""

    id: str
    fmt: str  # "qr", or a key of OTHER_FORMATS
    style: str  # one of QR_STYLES, or "plain" for the other formats
    ec: str  # L/M/Q/H, only meaningful for qr
    ppm: float  # pixels per module in the final image
    payload: str
    tags: list[str] = field(default_factory=list)  # distortions applied, in order
    seed: int = 0

    def to_json(self) -> dict:
        return dict(self.__dict__)


def make_payload(rng: np.random.Generator, fmt: str) -> str:
    if fmt == "micro_qr":
        # Micro QR holds very little. Short alphanumeric fits every version.
        return "".join(rng.choice(list(_ALNUM), int(rng.integers(5, 11))))
    if fmt == "rmqr":
        return "".join(rng.choice(list(_ALNUM), int(rng.integers(12, 28))))
    if fmt == "pdf417":
        return "ID-" + "".join(rng.choice(list(_ALNUM), int(rng.integers(20, 60))))
    if fmt == "maxicode":
        return "".join(rng.choice(list(_ALNUM), int(rng.integers(20, 40))))
    n = int(rng.integers(8, 70))
    token = "".join(rng.choice(list(_URL_CHARS), n))
    return f"https://example.com/{token}"


def _rgb_to_bgr(c: tuple[int, int, int]) -> tuple[int, int, int]:
    return (c[2], c[1], c[0])


def _luma(c: tuple[int, int, int]) -> float:
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def pick_colors(rng: np.random.Generator) -> tuple[tuple, tuple]:
    """A dark foreground and a light background that stay clearly different.

    Real marketing codes are colored but still need contrast to be scanned by
    a phone. A pair with luma gap under 90 is skipped, because that is not a
    readable code on any reader and would only add noise to the score.
    """
    for _ in range(100):
        fg = tuple(int(v) for v in rng.integers(0, 200, 3))
        bg = tuple(int(v) for v in rng.integers(90, 256, 3))
        if _luma(bg) - _luma(fg) >= 90:
            return fg, bg
    return (20, 20, 80), (240, 240, 255)


# -- QR via the library -----------------------------------------------------


def _qr_matrix(payload: str, ec: str, border: int = 4) -> list[list[bool]]:
    qr = qrcode.QRCode(
        error_correction=EC_LEVELS[ec], box_size=1, border=border, version=None
    )
    qr.add_data(payload)
    qr.make(fit=True)
    return qr.get_matrix()


def _styled(payload: str, ec: str, style: str, box: int, rng: np.random.Generator):
    drawers = {
        "square": SquareModuleDrawer(),
        "rounded": RoundedModuleDrawer(),
        "dots": CircleModuleDrawer(),
        "gapped": GappedSquareModuleDrawer(),
        "bars_vertical": VerticalBarsDrawer(),
        "bars_horizontal": HorizontalBarsDrawer(),
        "gradient_radial": SquareModuleDrawer(),
        "gradient_horizontal": RoundedModuleDrawer(),
    }
    fg, bg = pick_colors(rng)
    edge = tuple(int(v) for v in rng.integers(0, 160, 3))
    if style == "gradient_radial":
        mask = RadialGradiantColorMask(back_color=bg, center_color=edge, edge_color=fg)
    elif style == "gradient_horizontal":
        mask = HorizontalGradiantColorMask(back_color=bg, left_color=fg, right_color=edge)
    else:
        mask = SolidFillColorMask(back_color=(255, 255, 255), front_color=(0, 0, 0))
    qr = qrcode.QRCode(
        error_correction=EC_LEVELS[ec], box_size=box, border=4, version=None
    )
    qr.add_data(payload)
    img = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=drawers[style],
        color_mask=mask,
    )
    return cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)


# -- our own renderer: eyes, colors, logo -----------------------------------


def _rounded_rect(img, x, y, w, h, radius, color) -> None:
    radius = int(min(radius, w // 2, h // 2))
    cv2.rectangle(img, (x + radius, y), (x + w - radius, y + h), color, -1)
    cv2.rectangle(img, (x, y + radius), (x + w, y + h - radius), color, -1)
    for cx in (x + radius, x + w - radius):
        for cy in (y + radius, y + h - radius):
            cv2.circle(img, (cx, cy), radius, color, -1, cv2.LINE_AA)


def _finder_cells(n: int, border: int) -> list[tuple[int, int]]:
    """Top-left module of each 7x7 finder pattern."""
    return [
        (border, border),
        (n - border - 7, border),
        (border, n - border - 7),
    ]


def render_custom(
    payload: str,
    ec: str,
    box: int,
    fg: tuple,
    bg: tuple,
    eyes: str = "square",
    dots: bool = False,
) -> np.ndarray:
    """Draw a QR ourselves: any eye shape, any colors, dotted or square."""
    border = 4
    matrix = _qr_matrix(payload, ec, border)
    n = len(matrix)
    out = np.empty((n * box, n * box, 3), dtype=np.uint8)
    out[:] = _rgb_to_bgr(bg)
    fg_b, bg_b = _rgb_to_bgr(fg), _rgb_to_bgr(bg)
    finders = _finder_cells(n, border)

    def in_finder(r: int, c: int) -> bool:
        return any(fc <= c < fc + 7 and fr <= r < fr + 7 for fc, fr in finders)

    for r in range(n):
        for c in range(n):
            if not matrix[r][c] or in_finder(r, c):
                continue
            x, y = c * box, r * box
            if dots:
                cv2.circle(
                    out, (x + box // 2, y + box // 2), max(1, int(box * 0.46)), fg_b, -1,
                    cv2.LINE_AA,
                )
            else:
                out[y : y + box, x : x + box] = fg_b

    for fc, fr in finders:
        x, y = fc * box, fr * box
        if eyes == "square":
            out[y : y + 7 * box, x : x + 7 * box] = fg_b
            out[y + box : y + 6 * box, x + box : x + 6 * box] = bg_b
            out[y + 2 * box : y + 5 * box, x + 2 * box : x + 5 * box] = fg_b
        elif eyes == "round":
            _rounded_rect(out, x, y, 7 * box, 7 * box, 2 * box, fg_b)
            _rounded_rect(out, x + box, y + box, 5 * box, 5 * box, int(1.5 * box), bg_b)
            _rounded_rect(out, x + 2 * box, y + 2 * box, 3 * box, 3 * box, box, fg_b)
        else:  # ring: a circular outer ring with a round dot inside
            c0 = (x + 7 * box // 2, y + 7 * box // 2)
            cv2.circle(out, c0, int(3.5 * box), fg_b, -1, cv2.LINE_AA)
            cv2.circle(out, c0, int(2.5 * box), bg_b, -1, cv2.LINE_AA)
            cv2.circle(out, c0, int(1.5 * box), fg_b, -1, cv2.LINE_AA)
    return out


def add_logo(img: np.ndarray, rng: np.random.Generator, frac: float = 0.2) -> np.ndarray:
    """A solid logo over the middle, sized inside what level H can lose."""
    h, w = img.shape[:2]
    s = int(min(h, w) * frac)
    y, x = (h - s) // 2, (w - s) // 2
    pad = max(2, s // 12)
    cv2.rectangle(img, (x - pad, y - pad), (x + s + pad, y + s + pad), (255, 255, 255), -1)
    color = tuple(int(v) for v in rng.integers(0, 220, 3))
    if rng.random() < 0.5:
        cv2.circle(img, (x + s // 2, y + s // 2), s // 2, color, -1, cv2.LINE_AA)
    else:
        _rounded_rect(img, x, y, s, s, s // 4, color)
    return img


# -- the other symbologies --------------------------------------------------


def render_other(fmt: str, payload: str, scale: int = 10) -> np.ndarray:
    barcode = zxingcpp.create_barcode(payload, getattr(zxingcpp.BarcodeFormat, OTHER_FORMATS[fmt]))
    img = np.array(zxingcpp.write_barcode_to_image(barcode, scale=scale))
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    return img


# -- one case to pixels -----------------------------------------------------


# Where the image is made large enough to scale down cleanly: an integer box
# size, then a resize to the ppm the case actually asks for. That is also how
# a screenshot of a zoomed-out page behaves.
_RENDER_BOX = 12


def render(case: Case) -> np.ndarray:
    """Draw the clean code for a case, at its ppm, before any distortion."""
    rng = np.random.default_rng(case.seed)
    if case.fmt != "qr":
        img = render_other(case.fmt, case.payload, scale=_RENDER_BOX)
        modules_per_side = None
    else:
        style = case.style
        if style in {
            "square", "rounded", "dots", "gapped", "bars_vertical",
            "bars_horizontal", "gradient_radial", "gradient_horizontal",
        }:
            img = _styled(case.payload, case.ec, style, _RENDER_BOX, rng)
        elif style == "colored":
            fg, bg = pick_colors(rng)
            img = render_custom(case.payload, case.ec, _RENDER_BOX, fg, bg)
        elif style == "inverted":
            fg, bg = pick_colors(rng)
            img = render_custom(case.payload, case.ec, _RENDER_BOX, bg, fg)
        elif style == "logo":
            img = render_custom(case.payload, "H", _RENDER_BOX, (0, 0, 0), (255, 255, 255))
            img = add_logo(img, rng)
        elif style == "eyes_round":
            fg, bg = pick_colors(rng)
            img = render_custom(case.payload, case.ec, _RENDER_BOX, fg, bg, eyes="round", dots=True)
        elif style == "eyes_ring":
            fg, bg = pick_colors(rng)
            img = render_custom(case.payload, case.ec, _RENDER_BOX, fg, bg, eyes="ring", dots=True)
        else:
            raise ValueError(f"unknown style {style}")
        modules_per_side = img.shape[0] / _RENDER_BOX

    # Scale so each module ends up `ppm` pixels across.
    factor = case.ppm / _RENDER_BOX
    interp = cv2.INTER_AREA if factor < 1 else cv2.INTER_LINEAR
    img = cv2.resize(img, None, fx=factor, fy=factor, interpolation=interp)
    _ = modules_per_side
    return img
