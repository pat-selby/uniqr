// The link-safety rules and how a link is shown. Every case is ported from the
// Python tests (tests/test_link_view.py and tests/test_payload_safety.py), so
// the two versions are held to the same rules.

#include <doctest/doctest.h>

#include <algorithm>
#include <string>

#include "link.hpp"

using uniqr::can_open;
using uniqr::describe_link;
using uniqr::payload_kind;
using uniqr::summarize;

namespace {
bool any_warning(const uniqr::LinkView& v, const std::string& part) {
    return std::any_of(v.warnings.begin(), v.warnings.end(),
                       [&](const std::string& w) { return w.find(part) != std::string::npos; });
}
}  // namespace

TEST_CASE("web links can be opened") {
    for (const char* p : {"https://example.com", "http://example.com", "https://example.com/path?query=1#frag",
                          "HTTPS://EXAMPLE.COM", "  https://example.com  "})
        CHECK_MESSAGE(can_open(p), p);
}

TEST_CASE("everything else is copy-only") {
    for (const char* p : {"file:///C:/Windows/System32/cmd.exe", "file:///etc/passwd", "ms-settings:windowsupdate",
                          "ms-windows-store://home", "javascript:alert(1)", "data:text/html,<script>alert(1)</script>",
                          "vbscript:msgbox", "smb://attacker/share", "ftp://example.com/payload.exe",
                          "WIFI:S:MyNet;T:WPA;P:hunter2;;", "otpauth://totp/Example:me?secret=JBSWY3DPEHPK3PXP",
                          "bitcoin:1BoatSLRHtKNngkdXEeobR76b53LETtpyT", "MECARD:N:Someone;TEL:5551234;;",
                          "BEGIN:VCARD\nVERSION:3.0\nEND:VCARD", "just some plain text", "", "   "})
        CHECK_MESSAGE(!can_open(p), p);
}

TEST_CASE("scheme lookalikes are refused: a prefix test, not a substring test") {
    for (const char* p : {"nothttps://example.com", "x-https://example.com", "myapp://open?url=https://example.com",
                          "https//example.com"})
        CHECK_MESSAGE(!can_open(p), p);
}

TEST_CASE("leading whitespace cannot smuggle a scheme") {
    CHECK(can_open("\n\thttps://example.com"));
    CHECK(!can_open("\n\tfile:///etc/passwd"));
}

TEST_CASE("a plain link splits into host and rest") {
    const auto v = describe_link("https://events.eventnoire.com/e/small-business-workshop");
    REQUIRE(v);
    CHECK(v->host == "events.eventnoire.com");
    CHECK(v->rest == "/e/small-business-workshop");
    CHECK(v->warnings.empty());
}

TEST_CASE("the @ trick shows the real destination") {
    const auto v = describe_link("https://paypal.com@evil.example/login");
    REQUIRE(v);
    CHECK(v->host == "evil.example");
    CHECK(any_warning(*v, "evil.example"));
}

TEST_CASE("http is flagged as not secure") {
    CHECK(any_warning(*describe_link("http://example.com/"), "Not secure"));
}

TEST_CASE("international lookalike domains are flagged") {
    CHECK(any_warning(*describe_link("https://xn--pypal-4ve.com/"), "international characters"));
}

TEST_CASE("a raw IP address is flagged") {
    const auto v = describe_link("https://192.168.4.20/pay");
    REQUIRE(v);
    CHECK(v->host == "192.168.4.20");
    CHECK(any_warning(*v, "IP address"));
}

TEST_CASE("an IPv6 address is flagged too") {
    const auto v = describe_link("https://[2001:db8::1]/pay");
    REQUIRE(v);
    CHECK(v->host == "2001:db8::1");
    CHECK(any_warning(*v, "IP address"));
}

TEST_CASE("several problems are all reported") {
    CHECK(describe_link("http://bank.com@203.0.113.9/")->warnings.size() == 3);  // http, @, raw IP
}

TEST_CASE("an unusual port stays visible in the host") {
    CHECK(describe_link("https://example.com:8443/x")->host == "example.com:8443");
}

TEST_CASE("rest keeps the query and fragment") {
    CHECK(describe_link("https://example.com/search?q=qr#top")->rest == "/search?q=qr#top");
}

TEST_CASE("the host is lowercased and whitespace trimmed") {
    const auto v = describe_link("  HTTPS://EXAMPLE.COM/Path  ");
    REQUIRE(v);
    CHECK(v->host == "example.com");
    CHECK(v->full == "HTTPS://EXAMPLE.COM/Path");
}

TEST_CASE("the full link is kept for the hover pop-up") {
    const std::string url = "https://example.com/" + std::string(300, 'a');
    CHECK(describe_link(url)->full == url);
}

TEST_CASE("anything that cannot be opened is not shown as a link") {
    for (const char* p : {"WIFI:S:Net;T:WPA;P:pw;;", "file:///C:/Windows/System32/cmd.exe", "javascript:alert(1)",
                          "just some text", ""})
        CHECK_MESSAGE(!describe_link(p), p);
}

TEST_CASE("malformed links are rejected rather than guessed") {
    for (const char* p : {"https:///no-host", "https://example.com:99999/", "https://example.com:12ab/",
                          "https://[not-an-address]/"})
        CHECK_MESSAGE(!describe_link(p), p);
}

TEST_CASE("tabs and line breaks inside a link are dropped, as a browser does") {
    const auto v = describe_link("https://exa\tmple.com/a\nb");
    REQUIRE(v);
    CHECK(v->host == "example.com");
    CHECK(v->rest == "/ab");
}

TEST_CASE("payload kinds") {
    const std::pair<const char*, const char*> cases[] = {
        {"https://example.com", "url"},
        {"http://example.com", "url"},
        {"WIFI:S:Net;T:WPA;P:pw;;", "wifi"},
        {"mailto:someone@example.com", "email"},
        {"tel:+15551234567", "phone"},
        {"smsto:+15551234567:hi", "phone"},
        {"geo:37.7,-122.4", "geo"},
        {"MECARD:N:Someone;;", "contact"},
        {"BEGIN:VCARD\nEND:VCARD", "contact"},
        {"BEGIN:VEVENT\nEND:VEVENT", "event"},
        {"otpauth://totp/x?secret=abc", "secret"},
        {"bitcoin:1BoatSLRHtKNngkdXEeobR76b53LETtpyT", "secret"},
        {"ftp://example.com", "uri"},
        {"plain text", "text"},
    };
    for (const auto& [payload, kind] : cases) CHECK_MESSAGE(payload_kind(payload) == kind, payload);
}

TEST_CASE("authenticator seeds are labelled secret and never openable") {
    CHECK(payload_kind("otpauth://totp/Acme:me?secret=JBSWY3DP") == "secret");
    CHECK(!can_open("otpauth://totp/Acme:me?secret=JBSWY3DP"));
    CHECK(uniqr::kind_label("secret") == "Secret");
}

TEST_CASE("summarize collapses whitespace") { CHECK(summarize("a\n\tb   c") == "a b c"); }

TEST_CASE("summarize truncates long payloads to a number of characters") {
    const std::string out = summarize(std::string(500, 'x'), 40);
    CHECK(out.size() == 39 + 3);  // 39 x's and a three-byte ellipsis
    CHECK(out.substr(out.size() - 3) == "\xE2\x80\xA6");
}

TEST_CASE("summarize never cuts a character in half") {
    // 50 copies of a two-byte character: cutting by bytes would split one.
    std::string text;
    for (int i = 0; i < 50; ++i) text += "\xC3\xA9";
    const std::string out = summarize(text, 10);
    CHECK(out == std::string("\xC3\xA9\xC3\xA9\xC3\xA9\xC3\xA9\xC3\xA9\xC3\xA9\xC3\xA9\xC3\xA9\xC3\xA9") + "\xE2\x80\xA6");
}

TEST_CASE("summarize leaves short payloads alone") {
    CHECK(summarize("https://example.com", 40) == "https://example.com");
}

TEST_CASE("IP address rules match Python's ipaddress module") {
    CHECK(uniqr::is_ipv4("192.168.0.1"));
    CHECK(!uniqr::is_ipv4("256.1.1.1"));
    CHECK(!uniqr::is_ipv4("01.2.3.4"));  // leading zeros are refused
    CHECK(!uniqr::is_ipv4("1.2.3"));
    CHECK(uniqr::is_ipv6("::1"));
    CHECK(uniqr::is_ipv6("2001:db8::8a2e:370:7334"));
    CHECK(uniqr::is_ipv6("::ffff:192.0.2.128"));
    CHECK(!uniqr::is_ipv6("2001:db8::1::1"));
    CHECK(!uniqr::is_ipv6("12345::"));
    CHECK(!uniqr::is_ipv6("example.com"));
}

TEST_CASE("one click opens only a link with nothing to warn about") {
    CHECK(uniqr::opens_on_click("https://example.com/menu"));
    CHECK(!uniqr::opens_on_click("http://example.com"));
    CHECK(!uniqr::opens_on_click("https://paypal.com@evil.example/login"));
    CHECK(!uniqr::opens_on_click("https://xn--pypal-4ve.com"));
    CHECK(!uniqr::opens_on_click("https://192.0.2.10/login"));
    CHECK(!uniqr::opens_on_click("WIFI:S:Home;T:WPA;P:secret;;"));
}
