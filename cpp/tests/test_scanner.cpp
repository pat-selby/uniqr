// The scanner, on codes drawn with known contents.

#include <doctest/doctest.h>

#include <random>
#include <set>
#include <string>

#include "draw.hpp"
#include "scanner.hpp"

using namespace uniqr;

namespace {
std::set<std::string> texts(const std::vector<Detection>& found) {
    std::set<std::string> s;
    for (const auto& d : found) s.insert(d.text);
    return s;
}
const Scanner scanner;
}  // namespace

TEST_CASE("a plain QR code is read and labelled") {
    const auto found = scanner.scan(test::on_page(test::draw_code("https://example.com/plain"), 400, 400, 40, 40));
    REQUIRE(found.size() == 1);
    CHECK(found[0].text == "https://example.com/plain");
    CHECK(found[0].symbology == "QR Code");
    CHECK(found[0].step == "whole frame");
}

TEST_CASE("the corners are where the code is") {
    const Image code = test::draw_code("https://example.com/where", "QRCode", 5);
    const auto found = scanner.scan(test::on_page(code, 800, 600, 300, 200));
    REQUIRE(found.size() == 1);
    const PointF c = found[0].center();
    CHECK(c.x > 300);
    CHECK(c.x < 300 + code.width);
    CHECK(c.y > 200);
    CHECK(c.y < 200 + code.height);
}

TEST_CASE("a light-on-dark code is read too") {
    const Image code = invert(test::draw_code("https://example.com/dark-mode"));
    CHECK(texts(scanner.scan(test::on_page(code, 400, 400, 40, 40, 0))).count("https://example.com/dark-mode") == 1);
}

TEST_CASE("every code on the page is found, not just the first") {
    Image page(900, 400, 3, 255);
    paste(page, to_bgr(test::draw_code("https://example.com/one")), 20, 40);
    paste(page, to_bgr(test::draw_code("https://example.com/two")), 320, 40);
    paste(page, to_bgr(test::draw_code("https://example.com/three")), 620, 40);
    const auto found = texts(scanner.scan(page));
    CHECK(found == std::set<std::string>{"https://example.com/one", "https://example.com/two", "https://example.com/three"});
}

TEST_CASE("each of the other code kinds is read and named") {
    const std::pair<const char*, const char*> kinds[] = {
        {"MicroQRCode", "Micro QR"}, {"RMQRCode", "rMQR"}, {"DataMatrix", "Data Matrix"},
        {"Aztec", "Aztec"},          {"PDF417", "PDF417"},
    };
    for (const auto& [kind, label] : kinds) {
        const std::string text = std::string(kind) == "MicroQRCode" ? "UNIQR42" : "UniQR C++ test";
        const auto found = scanner.scan(test::on_page(test::draw_code(text, kind, 6), 700, 500, 30, 30));
        REQUIRE_MESSAGE(found.size() == 1, kind);
        CHECK_MESSAGE(found[0].text == text, kind);
        CHECK_MESSAGE(found[0].symbology == label, kind);
    }
}

// A page with a code just too small for the first, cheap read: the biggest size,
// shrinking a little at a time, at which that read finds nothing. This is the
// case the rest of the ladder exists for.
Image too_small_for_first_read(const std::string& text, int width, int height, int x, int y) {
    const Image drawn = test::draw_code(text, "QRCode", 4);
    for (double f = 0.40; f > 0.20; f -= 0.01) {
        const Image page = test::on_page(scale(drawn, f, Interp::Area), width, height, x, y);
        if (scanner.whole_frame(page).empty()) return page;
    }
    return {};
}

TEST_CASE("a tiny code on a small frame is found by enlarging") {
    const Image page = too_small_for_first_read("https://example.com/tiny", 300, 200, 50, 40);
    REQUIRE(!page.empty());
    const auto found = scanner.scan(page);
    REQUIRE(found.size() == 1);
    CHECK(found[0].text == "https://example.com/tiny");
    CHECK(found[0].step != "whole frame");
}

TEST_CASE("a tiny code on a full-size screen is found by enlarging the screen") {
    const Image page = too_small_for_first_read("https://example.com/small-on-screen", 1920, 1080, 900, 500);
    REQUIRE(!page.empty());
    const auto found = scanner.scan(page);
    REQUIRE(found.size() == 1);
    CHECK(found[0].text == "https://example.com/small-on-screen");
    CHECK(found[0].step == "enlarged screen");
    const PointF c = found[0].center();
    CHECK(c.x > 900);
    CHECK(c.x < 1000);
}

TEST_CASE("the fast setting does only the cheap read") {
    const Image page = too_small_for_first_read("https://example.com/fast", 300, 200, 50, 40);
    REQUIRE(!page.empty());
    ScanOptions fast;
    fast.thorough = false;
    CHECK(scanner.scan(page, fast).empty());
    CHECK(!scanner.scan(page).empty());
}

TEST_CASE("the time budget stops a scan from starting new steps") {
    const Image page = too_small_for_first_read("https://example.com/budget", 300, 200, 50, 40);
    REQUIRE(!page.empty());
    ScanOptions none;
    none.budget_seconds = 0;  // only the first read may run
    CHECK(scanner.scan(page, none).empty());
}

TEST_CASE("nothing is invented on screens with no code") {
    CHECK(scanner.scan(Image(1920, 1080, 3, 128)).empty());
    std::mt19937 rng(1);
    Image noise(1280, 720, 3);
    for (auto& p : noise.pixels) p = static_cast<uint8_t>(rng() & 0xFF);
    CHECK(scanner.scan(noise).empty());
    Image checker(240, 240, 3);
    for (int y = 0; y < 240; ++y)
        for (int x = 0; x < 240; ++x)
            for (int c = 0; c < 3; ++c) checker.at(x, y, c) = ((x / 10 + y / 10) % 2) ? 255 : 0;
    CHECK(scanner.scan(checker).empty());
}

TEST_CASE("the agreement check vetoes a reading that a second look does not repeat") {
    const Image page = test::on_page(test::draw_code("REAL CONTENT", "DataMatrix", 6), 400, 400, 40, 40);
    const auto found = scanner.scan_raw(page);
    REQUIRE(found.size() == 1);
    CHECK(scanner.confirm(page, found[0]));
    Detection tampered = found[0];
    tampered.text = "SOMETHING ELSE";  // a "corrected" wrong message
    CHECK(!scanner.confirm(page, tampered));
}

TEST_CASE("the same code found twice is reported once") {
    Detection a;
    a.text = "x";
    a.quad = {PointF{0, 0}, PointF{10, 0}, PointF{10, 10}, PointF{0, 10}};
    Detection b = a.offset(5, 5);
    Detection far = a.offset(300, 0);
    CHECK(merge({{a}, {b}}).size() == 1);
    CHECK(merge({{a}, {far}}).size() == 2);
    Detection other = b;
    other.text = "y";
    CHECK(merge({{a}, {other}}).size() == 2);
}
