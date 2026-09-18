"""How the result card presents a link.

The card shows the real host in large type because that's the part that
decides where a link goes, and it's the part attackers disguise.
"""

import pytest
from uniqr.actions import describe_link


def test_plain_link_splits_into_host_and_rest():
    view = describe_link("https://events.eventnoire.com/e/small-business-workshop")
    assert view.host == "events.eventnoire.com"
    assert view.rest == "/e/small-business-workshop"
    assert view.warnings == ()


def test_the_at_sign_trick_shows_the_real_destination():
    """Everything before an @ is a user name, so this goes to evil.example."""
    view = describe_link("https://paypal.com@evil.example/login")
    assert view.host == "evil.example"
    assert any("evil.example" in w for w in view.warnings)


def test_http_is_flagged_as_not_secure():
    view = describe_link("http://example.com/")
    assert any("Not secure" in w for w in view.warnings)


def test_international_lookalike_domains_are_flagged():
    view = describe_link("https://xn--pypal-4ve.com/")
    assert any("international characters" in w for w in view.warnings)


def test_raw_ip_address_is_flagged():
    view = describe_link("https://192.168.4.20/pay")
    assert view.host == "192.168.4.20"
    assert any("IP address" in w for w in view.warnings)


def test_several_problems_are_all_reported():
    view = describe_link("http://bank.com@203.0.113.9/")
    assert len(view.warnings) == 3  # http, the @ trick, and a raw IP


def test_unusual_port_stays_visible_in_the_host():
    assert describe_link("https://example.com:8443/x").host == "example.com:8443"


def test_rest_keeps_query_and_fragment():
    view = describe_link("https://example.com/search?q=qr#top")
    assert view.rest == "/search?q=qr#top"


def test_host_is_lowercased_and_whitespace_trimmed():
    view = describe_link("  HTTPS://EXAMPLE.COM/Path  ")
    assert view.host == "example.com"
    assert view.full == "HTTPS://EXAMPLE.COM/Path"


def test_full_link_is_kept_for_the_hover_pop_up():
    url = "https://example.com/" + "a" * 300
    assert describe_link(url).full == url


@pytest.mark.parametrize(
    "payload",
    [
        "WIFI:S:Net;T:WPA;P:pw;;",
        "file:///C:/Windows/System32/cmd.exe",
        "javascript:alert(1)",
        "just some text",
        "",
    ],
)
def test_anything_that_cannot_be_opened_is_not_shown_as_a_link(payload):
    """Same allowlist as the Open button: no link view, no Open."""
    assert describe_link(payload) is None


@pytest.mark.parametrize("payload", ["https:///no-host", "https://example.com:99999/"])
def test_malformed_links_are_rejected_rather_than_guessed(payload):
    assert describe_link(payload) is None
