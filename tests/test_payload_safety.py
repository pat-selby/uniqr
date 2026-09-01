"""The link-safety rules.

A decoded QR code is untrusted input read off the screen. Handing an arbitrary
string to the OS is how you launch things nobody asked for, so only ordinary
web links get an Open action. These tests exist so that rule cannot be widened
by accident.
"""

import pytest
from uniqr.actions import can_open, summarize
from uniqr.decode import payload_kind

OPENABLE = [
    "https://example.com",
    "http://example.com",
    "https://example.com/path?query=1#frag",
    "HTTPS://EXAMPLE.COM",
    "  https://example.com  ",
]

REFUSED = [
    "file:///C:/Windows/System32/cmd.exe",
    "file:///etc/passwd",
    "ms-settings:windowsupdate",
    "ms-windows-store://home",
    "javascript:alert(1)",
    "data:text/html,<script>alert(1)</script>",
    "vbscript:msgbox",
    "smb://attacker/share",
    "ftp://example.com/payload.exe",
    "WIFI:S:MyNet;T:WPA;P:hunter2;;",
    "otpauth://totp/Example:me?secret=JBSWY3DPEHPK3PXP",
    "bitcoin:1BoatSLRHtKNngkdXEeobR76b53LETtpyT",
    "MECARD:N:Someone;TEL:5551234;;",
    "BEGIN:VCARD\nVERSION:3.0\nEND:VCARD",
    "just some plain text",
    "",
    "   ",
]


@pytest.mark.parametrize("payload", OPENABLE)
def test_web_links_can_be_opened(payload):
    assert can_open(payload) is True


@pytest.mark.parametrize("payload", REFUSED)
def test_everything_else_is_copy_only(payload):
    assert can_open(payload) is False, f"{payload!r} must not be openable"


def test_scheme_lookalikes_are_refused():
    """Substring matching would let these through; prefix matching must not."""
    for payload in (
        "nothttps://example.com",
        "x-https://example.com",
        "myapp://open?url=https://example.com",
        "https//example.com",
    ):
        assert can_open(payload) is False, payload


def test_whitespace_prefix_cannot_smuggle_a_scheme():
    assert can_open("\n\thttps://example.com") is True
    assert can_open("\n\tfile:///etc/passwd") is False


# -- payload classification ------------------------------------------------


@pytest.mark.parametrize(
    "payload,kind",
    [
        ("https://example.com", "url"),
        ("http://example.com", "url"),
        ("WIFI:S:Net;T:WPA;P:pw;;", "wifi"),
        ("mailto:someone@example.com", "email"),
        ("tel:+15551234567", "phone"),
        ("smsto:+15551234567:hi", "phone"),
        ("geo:37.7,-122.4", "geo"),
        ("MECARD:N:Someone;;", "contact"),
        ("BEGIN:VCARD\nEND:VCARD", "contact"),
        ("BEGIN:VEVENT\nEND:VEVENT", "event"),
        ("otpauth://totp/x?secret=abc", "secret"),
        ("bitcoin:1BoatSLRHtKNngkdXEeobR76b53LETtpyT", "secret"),
        ("ftp://example.com", "uri"),
        ("plain text", "text"),
    ],
)
def test_payload_kind(payload, kind):
    assert payload_kind(payload) == kind


def test_credential_payloads_are_labelled_as_secret():
    """Authenticator seeds and wallet addresses deserve a distinct label."""
    assert payload_kind("otpauth://totp/Acme:me?secret=JBSWY3DP") == "secret"
    assert can_open("otpauth://totp/Acme:me?secret=JBSWY3DP") is False


# -- summarize -------------------------------------------------------------


def test_summarize_collapses_whitespace():
    assert summarize("a\n\tb   c") == "a b c"


def test_summarize_truncates_long_payloads():
    out = summarize("x" * 500, limit=40)
    assert len(out) == 40
    assert out.endswith("\u2026")


def test_summarize_leaves_short_payloads_alone():
    assert summarize("https://example.com", limit=40) == "https://example.com"
