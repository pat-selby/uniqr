"""The instant checks every scan runs on a link, with no network.

Short links hide the real site. Brand names on someone else's site are the
commonest phishing trick. .zip and .mov endings pass for file names. Each is a
warning on the card, and any warning means the picker shows the card first.
"""

import pytest
from uniqr import linkcheck
from uniqr.actions import describe_link, opens_on_click


@pytest.mark.parametrize(
    ("url", "brand"),
    [
        ("https://paypal.com.secure-login.xyz/a", "PayPal"),  # the brand as a subdomain
        ("https://paypa1.com", "PayPal"),  # a 1 for an l
        ("https://micr0soft-login.com", "Microsoft"),  # a 0 for an o
        ("https://arnazon.com", "Amazon"),  # rn for m
        ("https://dhl-tracking.info/parcel", "DHL"),
        ("https://paypal.support", "PayPal"),  # the name on an ending anyone can still buy
        ("https://login.bankofamerica.verify-now.top", "Bank of America"),
    ],
)
def test_a_brand_on_someone_elses_site_is_named(url, brand):
    view = describe_link(url)
    assert any(brand in w and "not" in w for w in view.warnings), view.warnings
    assert opens_on_click(url) is False


@pytest.mark.parametrize(
    "url",
    [
        "https://www.paypal.com/signin",
        "https://paypal.me/someone",
        "https://accounts.google.com",
        "https://google.co.uk",
        "https://amazon.de/dp/1",
        "https://s3.amazonaws.com/bucket/file",
        "https://go.bofa.com/q/7b5032",  # Bank of America's own short domain, from a real poster
        "https://pineapple.com",  # "apple" inside a word is not Apple
        "https://pop-ups.example",  # common words are not on the list
        "https://linktr.ee/qr/45d45578",
        "https://events.eventnoire.com/e/small-business-workshop",
    ],
)
def test_the_real_sites_and_ordinary_words_pass(url):
    assert describe_link(url).warnings == ()
    assert opens_on_click(url) is True


@pytest.mark.parametrize("url", ["https://bit.ly/3WHdJiw", "https://qrco.de/bgyYxV", "https://tinyurl.com/x"])
def test_a_short_link_says_it_hides_the_site(url):
    view = describe_link(url)
    assert any("short link" in w for w in view.warnings)
    assert opens_on_click(url) is False


@pytest.mark.parametrize("url", ["https://invoice.zip", "https://holiday-photos.mov/view"])
def test_a_file_like_ending_is_flagged(url):
    assert any("looks like a file name" in w for w in describe_link(url).warnings)


@pytest.mark.parametrize(
    ("host", "site"),
    [
        ("login.example.co.uk", "example.co.uk"),
        ("a.b.example.com", "example.com"),
        ("example.com", "example.com"),
        ("paypal.com.evil.xyz", "evil.xyz"),
    ],
)
def test_the_registered_site_is_found(host, site):
    assert linkcheck.site_of(host) == site


def test_the_warning_names_the_real_site():
    """The card says where it really goes, not only that something is off."""
    (warning,) = describe_link("https://paypal.com.secure-login.xyz/").warnings
    assert warning == "Mentions PayPal, but the site is secure-login.xyz, not PayPal's."
