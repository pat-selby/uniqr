#include "link.hpp"

#include <algorithm>
#include <cctype>

namespace uniqr {

namespace {

bool is_space(unsigned char c) { return c == ' ' || (c >= '\t' && c <= '\r'); }

bool starts_with(std::string_view s, std::string_view prefix) {
    return s.size() >= prefix.size() && s.substr(0, prefix.size()) == prefix;
}

bool is_hex(char c) { return std::isxdigit(static_cast<unsigned char>(c)) != 0; }

// Python's urlsplit pieces, for a string already known to start with http(s)://.
struct Split {
    std::string scheme, netloc, path, query, fragment;
};

Split split_url(std::string url) {
    // Like Python, drop tabs and line breaks anywhere in the link first.
    std::erase_if(url, [](char c) { return c == '\t' || c == '\r' || c == '\n'; });
    Split s;
    const size_t colon = url.find(':');
    s.scheme = ascii_lower(url.substr(0, colon));
    std::string rest = url.substr(colon + 1);
    if (starts_with(rest, "//")) {
        const size_t end = rest.find_first_of("/?#", 2);
        s.netloc = rest.substr(2, end == std::string::npos ? std::string::npos : end - 2);
        rest = end == std::string::npos ? "" : rest.substr(end);
    }
    if (const size_t hash = rest.find('#'); hash != std::string::npos) {
        s.fragment = rest.substr(hash + 1);
        rest = rest.substr(0, hash);
    }
    if (const size_t q = rest.find('?'); q != std::string::npos) {
        s.query = rest.substr(q + 1);
        rest = rest.substr(0, q);
    }
    s.path = rest;
    return s;
}

}  // namespace

std::string trim(std::string_view s) {
    size_t a = 0, b = s.size();
    while (a < b && is_space(static_cast<unsigned char>(s[a]))) ++a;
    while (b > a && is_space(static_cast<unsigned char>(s[b - 1]))) --b;
    return std::string(s.substr(a, b - a));
}

std::string ascii_lower(std::string_view s) {
    std::string out(s);
    for (auto& c : out) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    return out;
}

bool can_open(std::string_view text) {
    // A prefix test, never a substring test: "nothttps://" and
    // "myapp://open?url=https://..." must stay copy-only.
    const std::string t = ascii_lower(trim(text));
    return starts_with(t, "http://") || starts_with(t, "https://");
}

bool is_ipv4(std::string_view s) {
    // Python's ipaddress rules: four decimal parts, 0 to 255, no leading zeros.
    int parts = 0;
    size_t i = 0;
    while (true) {
        size_t j = i;
        while (j < s.size() && std::isdigit(static_cast<unsigned char>(s[j]))) ++j;
        const size_t len = j - i;
        if (len == 0 || len > 3) return false;
        if (len > 1 && s[i] == '0') return false;
        if (std::stoi(std::string(s.substr(i, len))) > 255) return false;
        ++parts;
        if (j == s.size()) break;
        if (s[j] != '.' || parts == 4) return false;
        i = j + 1;
    }
    return parts == 4;
}

bool is_ipv6(std::string_view sv) {
    std::string s(sv);
    if (const size_t pct = s.find('%'); pct != std::string::npos) {
        if (pct == 0 || pct + 1 == s.size()) return false;  // a scope needs a name
        s.resize(pct);
    }
    // A dotted IPv4 tail ("::ffff:1.2.3.4") stands for the last two groups.
    if (s.find('.') != std::string::npos) {
        const size_t last = s.rfind(':');
        if (last == std::string::npos || !is_ipv4(std::string_view(s).substr(last + 1))) return false;
        s = s.substr(0, last + 1) + "0:0";
    }
    const size_t dbl = s.find("::");
    if (dbl != std::string::npos && s.find("::", dbl + 1) != std::string::npos) return false;
    auto groups = [](std::string_view side) -> int {
        if (side.empty()) return 0;
        int n = 0;
        size_t i = 0;
        while (true) {
            const size_t j = side.find(':', i);
            const std::string_view g = side.substr(i, j == std::string_view::npos ? std::string_view::npos : j - i);
            if (g.empty() || g.size() > 4 || !std::all_of(g.begin(), g.end(), is_hex)) return -1;
            ++n;
            if (j == std::string_view::npos) return n;
            i = j + 1;
        }
    };
    if (dbl != std::string::npos) {
        const int left = groups(std::string_view(s).substr(0, dbl));
        const int right = groups(std::string_view(s).substr(dbl + 2));
        return left >= 0 && right >= 0 && left + right <= 7;
    }
    return groups(s) == 8;
}

bool opens_on_click(std::string_view text) {
    const auto view = describe_link(text);
    return view && view->warnings.empty();
}

std::optional<LinkView> describe_link(std::string_view text) {
    if (!can_open(text)) return std::nullopt;
    LinkView view;
    view.full = trim(text);
    const Split parts = split_url(view.full);

    // Everything before the last @ is a user name, which is how
    // https://paypal.com@evil.example/ really goes to evil.example.
    const size_t at = parts.netloc.rfind('@');
    const bool has_user = at != std::string::npos;
    const std::string hostinfo = has_user ? parts.netloc.substr(at + 1) : parts.netloc;

    std::string host, port;
    if (const size_t br = hostinfo.find('['); br != std::string::npos) {
        const std::string bracketed = hostinfo.substr(br + 1);
        const size_t close = bracketed.find(']');
        host = bracketed.substr(0, close);
        const std::string after = close == std::string::npos ? "" : bracketed.substr(close + 1);
        if (const size_t c = after.find(':'); c != std::string::npos) port = after.substr(c + 1);
        // Python refuses a bracketed host that is not an IPv6 address.
        if (!(is_ipv6(host) || (!host.empty() && (host[0] == 'v' || host[0] == 'V')))) return std::nullopt;
    } else {
        const size_t c = hostinfo.find(':');
        host = hostinfo.substr(0, c);
        if (c != std::string::npos) port = hostinfo.substr(c + 1);
    }
    host = ascii_lower(host);
    if (host.empty()) return std::nullopt;

    int port_number = -1;
    if (!port.empty()) {
        if (!std::all_of(port.begin(), port.end(), [](char ch) { return ch >= '0' && ch <= '9'; })) return std::nullopt;
        if (port.size() > 5 || std::stoi(port) > 65535) return std::nullopt;
        port_number = std::stoi(port);
    }

    if (parts.scheme != "https") view.warnings.push_back("Not secure: this link uses http, not https.");
    if (has_user) view.warnings.push_back("Text before the @ is ignored. This really goes to " + host + ".");
    // Labels starting xn-- are internationalised names, the lookalike trick.
    bool punycode = false;
    for (size_t i = 0; i <= host.size();) {
        const size_t dot = host.find('.', i);
        const std::string label = host.substr(i, dot == std::string::npos ? std::string::npos : dot - i);
        if (starts_with(label, "xn--")) punycode = true;
        if (dot == std::string::npos) break;
        i = dot + 1;
    }
    if (punycode)
        view.warnings.push_back(
            "Uses international characters, a common lookalike trick. Check the address carefully.");
    if (is_ipv4(host) || is_ipv6(host)) view.warnings.push_back("Goes to a raw IP address, not a website name.");
    // Short links, borrowed brand names, file-like endings.
    for (auto& w : link_checks(host)) view.warnings.push_back(std::move(w));

    view.rest = parts.path;
    if (!parts.query.empty()) view.rest += "?" + parts.query;
    if (!parts.fragment.empty()) view.rest += "#" + parts.fragment;
    view.host = port_number > 0 ? host + ":" + std::to_string(port_number) : host;
    return view;
}

namespace {

std::vector<std::string> split_any(std::string_view s, std::string_view seps) {
    std::vector<std::string> out;
    size_t start = 0;
    for (size_t i = 0; i <= s.size(); ++i) {
        if (i == s.size() || seps.find(s[i]) != std::string_view::npos) {
            out.emplace_back(s.substr(start, i - start));
            start = i + 1;
        }
    }
    return out;
}

std::string replace_all(std::string s, std::string_view from, std::string_view to) {
    for (size_t at = s.find(from); at != std::string::npos; at = s.find(from, at + to.size()))
        s.replace(at, from.size(), to);
    return s;
}

// Digits and letter pairs that pass for letters at a glance: paypa1, micr0soft, arnazon.
std::string unswap(std::string word) {
    static constexpr std::pair<std::string_view, std::string_view> swaps[] = {
        {"rn", "m"}, {"vv", "w"}, {"0", "o"}, {"1", "l"}, {"3", "e"}, {"5", "s"}, {"4", "a"}};
    for (const auto& [fake, real] : swaps) word = replace_all(std::move(word), fake, real);
    return word;
}

// Services whose whole job is to hide a longer address. A brand's own short
// links (amzn.to, wa.me) are left out: they only lead to that brand.
constexpr std::string_view kShorteners[] = {
    "bit.ly", "tinyurl.com", "t.co",    "ow.ly", "is.gd",   "v.gd",   "buff.ly", "rebrand.ly", "cutt.ly", "shorturl.at",
    "tiny.cc", "rb.gy",      "t.ly",    "s.id",  "bl.ink", "qrco.de", "goo.gl", "shorte.st", "adf.ly"};

struct Brand {
    std::string_view word, shown;
    std::vector<std::string_view> own;
};

// The same list as uniqr/linkcheck.py. Words that are also ordinary English
// (chase, ups, office, steam) are left out on purpose.
const std::vector<Brand>& brands() {
    static const std::vector<Brand> list = {
        {"paypal", "PayPal", {"paypal.com", "paypal.me"}},
        {"apple", "Apple", {"apple.com", "icloud.com", "apple.co"}},
        {"icloud", "iCloud", {"icloud.com", "apple.com"}},
        {"microsoft", "Microsoft", {"microsoft.com", "microsoftonline.com", "live.com", "office.com", "aka.ms"}},
        {"outlook", "Outlook", {"outlook.com", "live.com", "office.com", "microsoft.com"}},
        {"google", "Google", {"google.com", "googleusercontent.com", "googleapis.com", "gstatic.com", "g.co", "goo.gl"}},
        {"gmail", "Gmail", {"gmail.com", "google.com"}},
        {"amazon", "Amazon", {"amazon.com", "amazonaws.com", "amzn.to", "a.co"}},
        {"netflix", "Netflix", {"netflix.com"}},
        {"facebook", "Facebook", {"facebook.com", "fb.com", "fb.me", "meta.com"}},
        {"instagram", "Instagram", {"instagram.com"}},
        {"whatsapp", "WhatsApp", {"whatsapp.com", "whatsapp.net", "wa.me"}},
        {"linkedin", "LinkedIn", {"linkedin.com", "lnkd.in"}},
        {"github", "GitHub", {"github.com", "github.io", "githubusercontent.com"}},
        {"dropbox", "Dropbox", {"dropbox.com"}},
        {"docusign", "DocuSign", {"docusign.com", "docusign.net"}},
        {"adobe", "Adobe", {"adobe.com"}},
        {"coinbase", "Coinbase", {"coinbase.com"}},
        {"binance", "Binance", {"binance.com"}},
        {"venmo", "Venmo", {"venmo.com"}},
        {"zelle", "Zelle", {"zellepay.com"}},
        {"bankofamerica", "Bank of America", {"bankofamerica.com", "bofa.com"}},
        {"wellsfargo", "Wells Fargo", {"wellsfargo.com"}},
        {"dhl", "DHL", {"dhl.com"}},
        {"fedex", "FedEx", {"fedex.com"}},
        {"usps", "USPS", {"usps.com"}},
        {"irs", "the IRS", {"irs.gov"}},
    };
    return list;
}

bool is_brands_own(const Brand& b, const std::string& site) {
    if (std::find(b.own.begin(), b.own.end(), site) != b.own.end()) return true;
    // Its own country sites (google.de, amazon.co.uk) count; its name on a
    // newer ending anyone can still buy (paypal.support) does not.
    const size_t dot = site.find('.');
    if (site.substr(0, dot) != b.word) return false;
    const std::string ending = site.substr(dot + 1);
    return ending == "com" || ending == "net" || ending == "org" || ending.size() == 2 ||
           std::count(ending.begin(), ending.end(), '.') == 1;
}

std::optional<std::string> brand_warning(const std::string& host) {
    const std::string site = site_of(host);
    for (const auto& word : split_any(host, ".-")) {
        for (const std::string& candidate : {word, unswap(word)}) {
            for (const auto& b : brands()) {
                if (candidate != b.word) continue;
                if (is_brands_own(b, site)) return std::nullopt;
                const std::string shown(b.shown);
                return "Mentions " + shown + ", but the site is " + site + ", not " + shown + "'s.";
            }
        }
    }
    return std::nullopt;
}

}  // namespace

std::string site_of(std::string_view host) {
    std::string h = ascii_lower(host);
    while (!h.empty() && h.back() == '.') h.pop_back();
    const auto labels = split_any(h, ".");
    const size_t n = labels.size();
    static constexpr std::string_view second_level[] = {"co", "com", "net", "org", "gov", "edu", "ac"};
    const bool country_pair = n >= 3 && labels[n - 1].size() == 2 &&
                              std::find(std::begin(second_level), std::end(second_level), labels[n - 2]) !=
                                  std::end(second_level);
    const size_t keep = std::min(n, country_pair ? size_t{3} : size_t{2});
    std::string out;
    for (size_t i = n - keep; i < n; ++i) out += (out.empty() ? "" : ".") + labels[i];
    return out;
}

std::vector<std::string> link_checks(std::string_view host_view) {
    const std::string host = ascii_lower(host_view);
    std::vector<std::string> warnings;
    const std::string site = site_of(host);
    if (std::find(std::begin(kShorteners), std::end(kShorteners), site) != std::end(kShorteners) ||
        std::find(std::begin(kShorteners), std::end(kShorteners), host) != std::end(kShorteners))
        warnings.push_back("A short link: it hides the real site until you open it.");
    if (auto b = brand_warning(host)) warnings.push_back(*b);
    const std::string ending = host.substr(host.rfind('.') == std::string::npos ? 0 : host.rfind('.') + 1);
    if (ending == "zip" || ending == "mov")
        warnings.push_back("Ends in ." + ending + ", which looks like a file name. Scammers use that trick.");
    return warnings;
}

std::string payload_kind(std::string_view text) {
    const std::string t = ascii_lower(trim(text));
    auto any = [&](std::initializer_list<std::string_view> prefixes) {
        return std::any_of(prefixes.begin(), prefixes.end(), [&](std::string_view p) { return starts_with(t, p); });
    };
    if (any({"http://", "https://"})) return "url";
    if (any({"wifi:"})) return "wifi";
    if (any({"mailto:"})) return "email";
    if (any({"tel:", "sms:", "smsto:"})) return "phone";
    if (any({"geo:"})) return "geo";
    if (any({"begin:vcard", "mecard:"})) return "contact";
    if (any({"begin:vevent"})) return "event";
    if (any({"bitcoin:", "ethereum:", "otpauth:"})) return "secret";
    if (t.find("://") != std::string::npos) return "uri";
    return "text";
}

std::string kind_label(std::string_view kind) {
    static const std::pair<std::string_view, std::string_view> labels[] = {
        {"url", "Link"},       {"wifi", "Wi-Fi"},   {"email", "Email"},  {"phone", "Phone"},
        {"geo", "Location"},   {"contact", "Contact"}, {"event", "Event"}, {"secret", "Secret"},
        {"uri", "App link"},   {"text", "Text"},
    };
    for (const auto& [k, v] : labels)
        if (k == kind) return std::string(v);
    return "Text";
}

std::string summarize(std::string_view text, size_t limit) {
    std::string flat;
    bool gap = false;
    for (const char c : text) {
        if (is_space(static_cast<unsigned char>(c))) {
            gap = !flat.empty();
            continue;
        }
        if (gap) flat += ' ';
        gap = false;
        flat += c;
    }
    // Count characters, not bytes: a UTF-8 continuation byte is 10xxxxxx.
    auto is_cont = [](char c) { return (static_cast<unsigned char>(c) & 0xC0) == 0x80; };
    const size_t chars = std::count_if(flat.begin(), flat.end(), [&](char c) { return !is_cont(c); });
    if (chars <= limit) return flat;
    size_t kept = 0, cut = 0;
    while (cut < flat.size()) {
        if (!is_cont(flat[cut])) {
            if (kept == limit - 1) break;
            ++kept;
        }
        ++cut;
    }
    return flat.substr(0, cut) + "\xE2\x80\xA6";  // an ellipsis
}

}  // namespace uniqr
