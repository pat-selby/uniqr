"""Which payloads are web addresses, and the link to open for each.

A code may hold "https://example.org/apply" or just "example.org/apply". A
browser's address bar opens both, so UniQR should too. A bare address is
opened with https, never http.

A bare address has to look like one beyond doubt: no spaces, no scheme, no @
(that is an email address), and a name ending in a common top-level domain.
The list is short on purpose. An address it misses stays copy-only, as before.
Some domains it leaves out are also file extensions ("setup.py", "notes.md",
"main.cc"), and those codes are far likelier to be file names than links.
"""

import re

SCHEMES = ("http://", "https://")

_TLDS = """
    com org net edu gov mil int info biz name pro mobi
    io co ai app dev me tv ly gg fm to ws
    xyz online site website store shop tech blog cloud page link live news
    art club top one design agency media studio space world global
    us uk ca au nz ie de fr it es pt nl be lu ch at se no dk fi is
    cz sk hu ro bg gr hr si ee lv lt tr ru ua il ae sa qa kw om bh jo lb eg ma tn dz
    ng gh ke tz ug rw et za zm zw cm sn ci bw na mu
    in lk bd np cn hk tw jp kr sg my ph id th vn
    br mx ar cl pe uy ve ec bo cr pa do jm tt
"""
COMMON_TLDS = frozenset(_TLDS.split())

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
    if len(host) > 253 or len(labels) < 2 or labels[-1] not in COMMON_TLDS:
        return None
    if not all(_LABEL.match(label) for label in labels):
        return None
    return "https://" + t


def is_bare(text: str) -> bool:
    """A web address written without http:// or https://."""
    return web_address(text) is not None and not text.strip().lower().startswith(SCHEMES)
