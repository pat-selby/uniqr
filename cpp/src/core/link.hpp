// What to do with a decoded payload: the safety rules, and how a link is shown.
//
// A QR code is untrusted input read off the screen. These are the same rules
// as the Python UniQR (uniqr/actions.py), and the tests are the same cases.

#pragma once

#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace uniqr {

// Only ordinary web links get an Open action. Everything else is copy-only.
bool can_open(std::string_view text);

// The link to open for this payload, or none. A bare address such as
// "example.org/apply" opens with https; see web_address in link.cpp.
std::optional<std::string> web_address(std::string_view text);

// Whether one click in the picker should open this straight away: only a web
// link with nothing to warn about. Anything else is copied and shown on a card.
bool opens_on_click(std::string_view text);

// A web link split up so the real destination is easy to see.
struct LinkView {
    std::string host;  // where the link really goes, with an unusual port
    std::string rest;  // path, query and fragment
    std::string full;  // the whole link, trimmed
    std::vector<std::string> warnings;
    std::vector<std::string> notes;  // plain remarks, not warnings
};

// None for anything that is not an openable web link, or is malformed.
std::optional<LinkView> describe_link(std::string_view text);

// The part of a host someone registered: login.example.co.uk -> example.co.uk.
// An approximation of the public suffix list, good for the common cases.
std::string site_of(std::string_view host);
// The instant checks on a host, as in uniqr/linkcheck.py: a short link, a
// brand's name on someone else's site, a .zip or .mov ending. Plain sentences.
std::vector<std::string> link_checks(std::string_view host);

// "url", "wifi", "email", "phone", "geo", "contact", "event", "secret", "uri" or "text".
std::string payload_kind(std::string_view text);
// The badge on the card: "Link", "Wi-Fi", ... "Text".
std::string kind_label(std::string_view kind);

// One line, whitespace collapsed, at most `limit` characters (not bytes).
std::string summarize(std::string_view text, size_t limit = 120);

// Small string helpers shared with the rest of UniQR.
std::string trim(std::string_view s);
std::string ascii_lower(std::string_view s);
bool is_ipv4(std::string_view s);
bool is_ipv6(std::string_view s);

}  // namespace uniqr
