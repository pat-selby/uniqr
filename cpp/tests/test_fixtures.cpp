// Real images that the Python UniQR is tested on: photos of real codes, and a
// poster code that was missed on a real desktop. The C++ scanner must read them
// all. Expected answers are the ones in tests/helpers/qr_synth.py.

#include <doctest/doctest.h>

#include <fstream>
#include <map>
#include <set>
#include <string>

#include "draw.hpp"
#include "image.hpp"
#include "scanner.hpp"

using namespace uniqr;

namespace {
const Scanner scanner;
std::set<std::string> read_file(const std::string& relative) {
    const Image img = load_image(test::repo_path(relative));
    REQUIRE_MESSAGE(!img.empty(), "missing " << relative);
    std::set<std::string> out;
    for (const auto& d : scanner.scan(img)) out.insert(d.text);
    return out;
}
}  // namespace

TEST_CASE("the real photos read, every code on them") {
    const std::map<std::string, std::set<std::string>> expected = {
        {"sap_flyer.png", {"https://bit.ly/4jQ5iLN", "https://bit.ly/40HVnio", "https://bit.ly/3WHdJiw"}},
        {"american.png", {"https://go.bofa.com/q/7b5032"}},
        {"morningstar.png", {"https://linktr.ee/qr/45d45578-8152-4e47-8609-2fb8a62923c4"}},
        {"codesignal_card.png",
         {"https://codesignal.com/learn/get-cosmo?utm_source=learn&utm_medium=qr_code&utm_content=celebration"}},
    };
    for (const auto& [file, want] : expected) {
        const auto got = read_file(file);
        for (const auto& w : want) CHECK_MESSAGE(got.count(w) == 1, file << " missing " << w);
    }
}

TEST_CASE("the poster code that was missed on a real desktop reads, on its own and on screens") {
    const Image code = load_image(test::repo_path("tests/fixtures/small_poster_code.png"));
    REQUIRE(!code.empty());
    CHECK(read_file("tests/fixtures/small_poster_code.png") == std::set<std::string>{"https://qrco.de/bgyYxV"});
    const int screens[][4] = {{1280, 800, 500, 300}, {1920, 1080, 600, 400}, {1920, 1080, 1700, 900}, {4600, 900, 4400, 400}};
    for (const auto& s : screens) {
        Image page(s[0], s[1], 3, 24);
        paste(page, code, s[2], s[3]);
        const auto found = scanner.scan(page);
        REQUIRE_MESSAGE(found.size() == 1, s[0] << "x" << s[1]);
        CHECK(found[0].text == "https://qrco.de/bgyYxV");
        const PointF c = found[0].center();
        CHECK(c.x > s[2]);
        CHECK(c.x < s[2] + code.width);
    }
}
