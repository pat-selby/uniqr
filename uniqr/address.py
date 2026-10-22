"""Which payloads are web addresses, and the link to open for each.

A code may hold "https://example.org/apply" or just "example.org/apply". A
browser's address bar opens both, so UniQR should too. A bare address is
opened with https, never http.

A bare address has to look like one beyond doubt: no spaces, no scheme, no @
(that is an email address), and a name ending in a real top-level domain. The
list of those is IANA's, kept in uniqr/tlds.py and refreshed by
tools/update_tlds.py, so the check needs no network.

A few domains are also common file types. "setup.py" or "notes.md" in a code is
far likelier a file name than a site in Paraguay or Moldova, so those count
only when the text clearly looks like an address: a path after the name
("site.py/menu") or a leading "www.". .zip and .mov are also a known phishing
trick, which is one more reason to be careful with them.
"""

import re

from uniqr.tlds import TLDS

SCHEMES = ("http://", "https://")

# File types that are also domains. Left out on purpose: .ai, .app and .pl,
# where real sites (and Poland) far outnumber files in QR codes.
FILE_LIKE = frozenset(
    {"py", "md", "zip", "mov", "sh", "rs", "cc", "so", "ps", "java", "ml", "mm", "pm", "pub"}
)

_LABEL = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)$")


def web_address(text: str) -> str | None:
    """The link to open for this payload, or None if it is not a web address."""
    t = text.strip()
    if t.lower().startswith(SCHEMES):
        return t
    if not t or any(c.isspace() for c in t) or "://" in t:
        return None
    end = min((i for i in (t.find(c) for c in "/?#") if i >= 0), default=len(t))
    authority = t[:end]
    if "@" in authority:
        return None
    host, colon, port = authority.partition(":")
    if colon and not (port.isdigit() and len(port) <= 5 and 0 < int(port) <= 65535):
        return None
    labels = host.lower().split(".")
    if len(host) > 253 or len(labels) < 2 or labels[-1] not in TLDS:
        return None
    if not all(_LABEL.match(label) for label in labels):
        return None
    if labels[-1] in FILE_LIKE and labels[0] != "www" and t[end : end + 1] != "/":
        return None
    return "https://" + t


def is_bare(text: str) -> bool:
    """A web address written without http:// or https://."""
    has_scheme = text.strip().lower().startswith(SCHEMES)
    return not has_scheme and web_address(text) is not None
