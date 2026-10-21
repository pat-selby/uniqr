"""Web addresses written without http:// or https://.

A poster's code held "emberfellows.org/pages/apply". Every browser opens that,
but UniQR called it text and offered no Open button. A bare address now opens,
always with https, while anything that only might be an address stays text.
The endings are IANA's full list, in uniqr/tlds.py.
"""

import pytest
from uniqr.actions import can_open, describe_link, opens_on_click
from uniqr.address import web_address
from uniqr.decode import payload_kind

BARE = [
    "emberfellows.org/pages/apply",
    "example.com",
    "www.example.com",
    "Example.COM/Path",
    "docs.example.co.uk/guide?page=2#top",
    "example.com:8443/admin",
    "  example.org  ",
    "allegro.pl",  # endings outside the old short list
    "brand.inc",
    "museum.museum/visit",
    "site.py/menu",  # a file-type ending with a path
    "www.setup.py",  # or with www.
]

NOT_ADDRESSES = [
    "someone@example.com",  # an email address
    "setup.py",  # file names whose ending is also a country
    "notes.md",
    "photo.zip",
    "main.cc",
    "clip.mov",
    "Main.java",
    "notes.md?next=/home",  # a slash in the query is not a path
    "visit example.com today",  # a sentence
    "example",  # no dot
    "localhost:8080",
    "192.168.1.1",  # a raw IP needs a scheme to open
    "example.notarealtld",
    "-bad-.com",
    "exa_mple.com",
    "example.com:99999",
    "example.com:abc",
    "example.com:",
    "javascript:alert(1)",
    "ftp.example.com://x",
    "",
]


@pytest.mark.parametrize("text", BARE)
def test_a_bare_web_address_opens_with_https(text):
    assert web_address(text) == "https://" + text.strip()
    assert can_open(text) is True
    assert payload_kind(text) == "url"


@pytest.mark.parametrize("text", NOT_ADDRESSES)
def test_anything_that_only_might_be_an_address_stays_text(text):
    assert web_address(text) is None
    assert can_open(text) is False
    assert describe_link(text) is None


def test_the_card_shows_the_real_host_and_says_https_was_added():
    view = describe_link("emberfellows.org/pages/apply")
    assert view.host == "emberfellows.org"
    assert view.rest == "/pages/apply"
    assert view.full == "https://emberfellows.org/pages/apply"
    assert view.warnings == ()
    assert view.notes == ("The code has no https://, so UniQR adds it.",)


def test_a_full_link_gets_no_note():
    assert describe_link("https://example.com").notes == ()


def test_a_bare_address_opens_in_one_click_like_any_safe_link():
    assert opens_on_click("example.com/menu") is True
    assert opens_on_click("xn--pypal-4ve.com") is False  # the lookalike warning still applies


def test_open_url_hands_the_browser_the_https_link(monkeypatch):
    from uniqr import actions

    opened = []
    monkeypatch.setattr(actions, "_linux", lambda: False)
    monkeypatch.setattr(actions.webbrowser, "open", lambda url: opened.append(url) or True)
    assert actions.open_url("emberfellows.org/pages/apply") is True
    assert opened == ["https://emberfellows.org/pages/apply"]


def test_the_domain_lists_for_python_and_cpp_match():
    """Both are written by tools/update_tlds.py; a hand edit to one would split them."""
    import re
    from pathlib import Path

    from uniqr.tlds import TLDS

    inc = Path(__file__).resolve().parent.parent / "cpp" / "src" / "core" / "tlds.inc"
    words = " ".join(re.findall(r'"([^"]*)"', inc.read_text(encoding="utf-8"))).split()
    assert set(words) == TLDS
    assert len(TLDS) > 1000
