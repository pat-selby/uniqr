"""Every kind of code UniQR claims to read, and things it must leave alone.

The generated codes come from the benchmark lab (benchmarks/), so what these
tests cover and what the published numbers measure are the same codes. Clean
and at a comfortable size here: the benchmark is where damage lives. These are
the quick guarantee that no style or format has stopped working at all.
"""

import sys
from pathlib import Path

import cv2
import numpy as np
import pytest
import zxingcpp

# benchmarks/ sits beside uniqr/ but is not an installed package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks import distort, generate  # noqa: E402
from benchmarks.generate import OTHER_FORMATS, QR_STYLES, Case  # noqa: E402

LABELS = {
    "qr": "QR Code",
    "micro_qr": "Micro QR",
    "rmqr": "rMQR",
    "data_matrix": "Data Matrix",
    "aztec": "Aztec",
    "pdf417": "PDF417",
    "maxicode": "MaxiCode",
}


def clean_case(fmt: str, style: str, seed: int = 11) -> Case:
    rng = np.random.default_rng(seed)
    return Case(
        id="t", fmt=fmt, style=style, ec="M", ppm=8.0,
        payload=generate.make_payload(rng, fmt), tags=["clean"], seed=seed,
    )


def padded(img: np.ndarray) -> np.ndarray:
    bg = tuple(int(v) for v in img[2, 2])
    return cv2.copyMakeBorder(img, 30, 30, 30, 30, cv2.BORDER_CONSTANT, value=bg)


@pytest.mark.parametrize("style", QR_STYLES)
def test_every_qr_style_reads(scanner, style):
    case = clean_case("qr", style)
    found = scanner.scan(padded(generate.render(case)))
    assert [d.text for d in found] == [case.payload]
    assert found[0].symbology == "QR Code"


@pytest.mark.parametrize("fmt", list(OTHER_FORMATS))
def test_every_other_format_reads_and_is_named(scanner, fmt):
    case = clean_case(fmt, "plain")
    found = scanner.scan(padded(generate.render(case)))
    assert [d.text for d in found] == [case.payload]
    assert found[0].symbology == LABELS[fmt]


def test_two_different_formats_in_one_frame(scanner):
    """A screen can hold a QR code and a Data Matrix at once."""
    qr = generate.render(clean_case("qr", "square", seed=3))
    dm = generate.render(clean_case("data_matrix", "plain", seed=4))
    h = max(qr.shape[0], dm.shape[0])
    page = np.full((h + 60, qr.shape[1] + dm.shape[1] + 90, 3), 255, np.uint8)
    page[30 : 30 + qr.shape[0], 30 : 30 + qr.shape[1]] = qr
    x = 60 + qr.shape[1]
    page[30 : 30 + dm.shape[0], x : x + dm.shape[1]] = dm
    found = scanner.scan(page)
    assert {d.symbology for d in found} == {"QR Code", "Data Matrix"}


def _linear(fmt: str, text: str) -> np.ndarray:
    barcode = zxingcpp.create_barcode(text, getattr(zxingcpp.BarcodeFormat, fmt))
    raw = np.array(zxingcpp.write_barcode_to_image(barcode, scale=4))
    return cv2.cvtColor(raw, cv2.COLOR_GRAY2BGR) if raw.ndim == 2 else raw


def _nothing_here():
    rng = np.random.default_rng(5)
    cells = np.indices((24, 24)).sum(axis=0) % 2
    yield "blank page", np.full((720, 1280, 3), 240, np.uint8)
    yield "noise", rng.integers(0, 256, (720, 1280, 3), dtype=np.uint8)
    yield "text and boxes", distort.on_page(np.full((8, 8, 3), 255, np.uint8), (1920, 1080), rng)
    yield "checkerboard", cv2.cvtColor(
        cv2.resize((cells * 255).astype(np.uint8), None, fx=10, fy=10,
                   interpolation=cv2.INTER_NEAREST), cv2.COLOR_GRAY2BGR)
    # What a screen is full of, and what nobody pressed the hotkey to read.
    yield "EAN-13 product barcode", _linear("EAN13", "5901234123457")
    yield "Code 128 label", _linear("Code128", "HELLO12345")
    yield "ITF carton barcode", _linear("ITF", "12345678")


@pytest.mark.parametrize("name,image", list(_nothing_here()), ids=lambda v: v if isinstance(v, str) else "")
def test_things_that_are_not_codes_stay_empty(scanner, name, image):
    found = scanner.scan(image)
    assert found == [], f"{name}: read {[d.text for d in found]!r}"


def test_a_case_always_renders_the_same_pixels():
    """A failure found today must be rebuildable from its metadata alone."""
    a = generate.render(clean_case("qr", "eyes_ring", seed=21))
    b = generate.render(clean_case("qr", "eyes_ring", seed=21))
    c = generate.render(clean_case("qr", "eyes_ring", seed=22))
    assert np.array_equal(a, b)
    assert not (a.shape == c.shape and np.array_equal(a, c))


# -- believing what was read -------------------------------------------------


def test_a_second_read_that_disagrees_vetoes_a_detection(scanner):
    """Garbage that a reader calls valid must not reach the clipboard."""
    from dataclasses import replace

    case = clean_case("aztec", "plain", seed=31)
    img = padded(generate.render(case))
    (real,) = scanner.scan(img)
    assert real.text == case.payload

    fabricated = replace(real, text="MDPYWBGDMMS*AJKSIIjnbccclqenoq6")
    assert scanner._validated(img, [fabricated]) == []
    assert scanner._validated(img, [real]) == [real]


def test_a_plain_qr_code_is_not_second_guessed(scanner):
    """QR error correction has earned trust the other formats have not."""
    from dataclasses import replace

    case = clean_case("qr", "square", seed=32)
    img = padded(generate.render(case))
    (real,) = scanner.scan(img)
    other = replace(real, text="https://not-what-it-says.example")
    assert scanner._validated(img, [other]) == [other]


def test_the_pdf417_that_once_read_as_garbage_does_not_any_more(scanner):
    """Benchmark seed 4, case 00931: three kinds of damage on a PDF417.

    Rebuilt from its recorded numbers. UniQR used to return 51 characters of
    garbage for it. Returning nothing is acceptable; returning the wrong text
    is not.
    """
    from benchmarks.run import make_image

    case = Case(
        id="00931", fmt="pdf417", style="plain", ec="M", ppm=3.6902863664483325,
        payload="ID-7OQ6ACQLXNK95SAJFPYWBGFV00DMQRA0CI376O2C2",
        tags=["combined"], seed=4000943,
    )
    texts = [d.text for d in scanner.scan(make_image(case))]
    assert all(t == case.payload for t in texts), f"read the wrong text: {texts!r}"
