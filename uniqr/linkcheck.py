"""Instant checks on where a link goes, done on this computer.

Every scan runs these before anything can open, with no network: a short link
that hides the real site, a name dressed up as a well-known brand, and a site
ending in .zip or .mov. Each finding is a plain sentence for the card, and any
finding means the picker shows the card first instead of opening on one click.

They are hints, not a verdict. A link that passes has only passed these
checks; one that fails may still be fine. The card says what was seen and lets
the person decide.
"""

import re

# Services whose whole job is to hide a longer address behind a short one. A
# brand's own short links (amzn.to, wa.me) are left out: they only lead to
# that brand.
_SHORTENERS = """
    bit.ly tinyurl.com t.co ow.ly is.gd v.gd buff.ly rebrand.ly cutt.ly
    shorturl.at tiny.cc rb.gy t.ly s.id bl.ink qrco.de goo.gl shorte.st adf.ly
"""
SHORTENERS = frozenset(_SHORTENERS.split())

# Brands scammers copy most, and the sites that really are theirs. Words that
# are also ordinary English (chase, ups, office, steam) are left out: a site
# about a chase or pop-ups is not pretending to be a bank.
BRANDS: dict[str, tuple[str, frozenset[str]]] = {
    "paypal": ("PayPal", frozenset({"paypal.com", "paypal.me"})),
    "apple": ("Apple", frozenset({"apple.com", "icloud.com", "apple.co"})),
    "icloud": ("iCloud", frozenset({"icloud.com", "apple.com"})),
    "microsoft": (
        "Microsoft",
        frozenset({"microsoft.com", "microsoftonline.com", "live.com", "office.com", "aka.ms"}),
    ),
    "outlook": ("Outlook", frozenset({"outlook.com", "live.com", "office.com", "microsoft.com"})),
    "google": (
        "Google",
        frozenset({"google.com", "googleusercontent.com", "googleapis.com", "gstatic.com", "g.co", "goo.gl"}),
    ),
    "gmail": ("Gmail", frozenset({"gmail.com", "google.com"})),
    "amazon": ("Amazon", frozenset({"amazon.com", "amazonaws.com", "amzn.to", "a.co"})),
    "netflix": ("Netflix", frozenset({"netflix.com"})),
    "facebook": ("Facebook", frozenset({"facebook.com", "fb.com", "fb.me", "meta.com"})),
    "instagram": ("Instagram", frozenset({"instagram.com"})),
    "whatsapp": ("WhatsApp", frozenset({"whatsapp.com", "whatsapp.net", "wa.me"})),
    "linkedin": ("LinkedIn", frozenset({"linkedin.com", "lnkd.in"})),
    "github": ("GitHub", frozenset({"github.com", "github.io", "githubusercontent.com"})),
    "dropbox": ("Dropbox", frozenset({"dropbox.com"})),
    "docusign": ("DocuSign", frozenset({"docusign.com", "docusign.net"})),
    "adobe": ("Adobe", frozenset({"adobe.com"})),
    "coinbase": ("Coinbase", frozenset({"coinbase.com"})),
    "binance": ("Binance", frozenset({"binance.com"})),
    "venmo": ("Venmo", frozenset({"venmo.com"})),
    "zelle": ("Zelle", frozenset({"zellepay.com"})),
    "bankofamerica": ("Bank of America", frozenset({"bankofamerica.com", "bofa.com"})),
    "wellsfargo": ("Wells Fargo", frozenset({"wellsfargo.com"})),
    "dhl": ("DHL", frozenset({"dhl.com"})),
    "fedex": ("FedEx", frozenset({"fedex.com"})),
    "usps": ("USPS", frozenset({"usps.com"})),
    "irs": ("the IRS", frozenset({"irs.gov"})),
}

# A brand's own country sites (google.de, amazon.co.uk) count as real. Its name
# on one of the newer endings (paypal.support) does not: those are the ones a
# scammer can still register.
_HOME_ENDINGS = frozenset({"com", "net", "org"})

# Endings that look like a file. "invoice.zip" reads as a download, not a site.
FILE_ENDINGS = {"zip": ".zip", "mov": ".mov"}

# Digits and letter pairs that pass for letters at a glance: paypa1, micr0soft, arnazon.
_SWAPS = (("rn", "m"), ("vv", "w"), ("0", "o"), ("1", "l"), ("3", "e"), ("5", "s"), ("4", "a"))

# Second-level names under a country ending: example.co.uk is one site, not uk's.
_SECOND_LEVEL = frozenset({"co", "com", "net", "org", "gov", "edu", "ac"})


def site_of(host: str) -> str:
    """The part of a host name someone registered: login.example.co.uk -> example.co.uk.

    An approximation of the public suffix list, good for the common cases.
    """
    labels = host.lower().rstrip(".").split(".")
    if len(labels) >= 3 and len(labels[-1]) == 2 and labels[-2] in _SECOND_LEVEL:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def _unswap(word: str) -> str:
    for fake, real in _SWAPS:
        word = word.replace(fake, real)
    return word


def _is_brands_own(brand: str, site: str, own: frozenset[str]) -> bool:
    if site in own:
        return True
    name, _, ending = site.partition(".")
    return name == brand and (ending in _HOME_ENDINGS or len(ending) == 2 or ending.count(".") == 1)


def brand_warning(host: str) -> str | None:
    """A warning when a host borrows a brand's name but is not that brand's site."""
    site = site_of(host)
    for word in re.split(r"[.-]", host.lower()):
        for candidate in {word, _unswap(word)}:
            entry = BRANDS.get(candidate)
            if entry is None:
                continue
            shown, own = entry
            if _is_brands_own(candidate, site, own):
                return None
            return f"Mentions {shown}, but the site is {site}, not {shown}'s."
    return None


def check(host: str) -> list[str]:
    """Plain-sentence warnings about a link's host. Empty when nothing stands out."""
    host = host.lower()
    warnings = []
    site = site_of(host)
    if site in SHORTENERS or host in SHORTENERS:
        warnings.append("A short link: it hides the real site until you open it.")
    brand = brand_warning(host)
    if brand:
        warnings.append(brand)
    ending = host.rsplit(".", 1)[-1]
    if ending in FILE_ENDINGS:
        warnings.append(
            f"Ends in {FILE_ENDINGS[ending]}, which looks like a file name. Scammers use that trick."
        )
    return warnings
