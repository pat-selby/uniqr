// The hand-written image steps that stand in for OpenCV.

#include <doctest/doctest.h>

#include <algorithm>
#include <numeric>

#include "image.hpp"
#include "scanner.hpp"

using namespace uniqr;

namespace {
Image ramp(int w, int h) {
    Image img(w, h, 1);
    for (int y = 0; y < h; ++y)
        for (int x = 0; x < w; ++x) img.at(x, y) = static_cast<uint8_t>((x * 255) / std::max(1, w - 1));
    return img;
}
double mean(const Image& img) {
    return std::accumulate(img.pixels.begin(), img.pixels.end(), 0.0) / img.pixels.size();
}
}  // namespace

TEST_CASE("resizing gives the size asked for, with every method") {
    const Image src = ramp(37, 23);
    for (Interp m : {Interp::Nearest, Interp::Linear, Interp::Cubic, Interp::Area, Interp::Lanczos}) {
        const Image up = resize(src, 111, 69, m);
        CHECK(up.width == 111);
        CHECK(up.height == 69);
        const Image down = resize(src, 10, 7, m);
        CHECK(down.width == 10);
        CHECK(down.height == 7);
    }
}

TEST_CASE("resizing a flat image keeps it flat") {
    const Image flat(50, 40, 3, 137);
    for (Interp m : {Interp::Linear, Interp::Cubic, Interp::Area, Interp::Lanczos}) {
        const Image out = scale(flat, 2.5, m);
        CHECK(std::all_of(out.pixels.begin(), out.pixels.end(), [](uint8_t p) { return p == 137; }));
    }
}

TEST_CASE("an enlarged ramp stays a ramp: left dark, right light, in order") {
    const Image out = scale(ramp(64, 4), 3.0, Interp::Lanczos);
    CHECK(out.at(0, 0) < 10);
    CHECK(out.at(out.width - 1, 0) > 245);
    int drops = 0;
    for (int x = 1; x < out.width; ++x) drops += out.at(x, 1) + 2 < out.at(x - 1, 1);
    CHECK(drops == 0);
}

TEST_CASE("area shrinking averages") {
    Image checker(4, 4, 1);
    for (int y = 0; y < 4; ++y)
        for (int x = 0; x < 4; ++x) checker.at(x, y) = ((x + y) % 2) ? 255 : 0;
    const Image out = resize(checker, 2, 2, Interp::Area);
    for (auto p : out.pixels) CHECK(std::abs(int(p) - 128) <= 1);
}

TEST_CASE("grey uses the same weights as zxing") {
    Image bgr(1, 1, 3);
    bgr.at(0, 0, 0) = 10;   // blue
    bgr.at(0, 0, 1) = 200;  // green
    bgr.at(0, 0, 2) = 100;  // red
    CHECK(to_grey(bgr).at(0, 0) == static_cast<uint8_t>((306 * 100 + 601 * 200 + 117 * 10 + 0x200) >> 10));
    CHECK(channel(bgr, 2).at(0, 0) == 100);
}

TEST_CASE("invert, crop, paste and pad") {
    const Image img = ramp(10, 10);
    CHECK(invert(img).at(0, 0) == 255);
    CHECK(crop(img, -5, -5, 4, 3).width == 4);
    CHECK(crop(img, -5, -5, 4, 3).height == 3);
    CHECK(crop(img, 20, 20, 30, 30).empty());
    Image page(20, 20, 3, 255);
    paste(page, Image(5, 5, 1, 0), 18, 18);  // partly off the page: clipped, not a crash
    CHECK(page.at(19, 19, 2) == 0);
    CHECK(page.at(17, 17, 2) == 255);
    CHECK(pad(img, 3, 7).width == 16);
    CHECK(pad(img, 3, 7).at(0, 0) == 7);
}

TEST_CASE("a blur keeps a flat image flat and softens an edge") {
    CHECK(mean(gaussian_blur(Image(30, 30, 1, 90), 1.2)) == doctest::Approx(90));
    Image edge(30, 1, 1, 0);
    for (int x = 15; x < 30; ++x) edge.at(x, 0) = 255;
    const Image soft = gaussian_blur(edge, 1.5);
    CHECK(soft.at(14, 0) > 0);
    CHECK(soft.at(15, 0) < 255);
}

TEST_CASE("Otsu splits two groups between them") {
    Image img(100, 1, 1);
    for (int x = 0; x < 100; ++x) img.at(x, 0) = x < 60 ? 40 : 200;
    const int t = otsu_threshold(img);
    CHECK(t >= 40);
    CHECK(t < 200);
    const Image bw = threshold(img, t);
    CHECK(bw.at(0, 0) == 0);
    CHECK(bw.at(99, 0) == 255);
}

TEST_CASE("CLAHE keeps the size and stretches low contrast") {
    Image dull(64, 64, 1);
    for (int y = 0; y < 64; ++y)
        for (int x = 0; x < 64; ++x) dull.at(x, y) = static_cast<uint8_t>(120 + ((x / 4 + y / 4) % 2) * 10);
    const Image eq = clahe(dull);
    CHECK(eq.width == 64);
    CHECK(eq.height == 64);
    const auto [lo, hi] = std::minmax_element(eq.pixels.begin(), eq.pixels.end());
    CHECK(int(*hi) - int(*lo) > 10);  // the 10-level difference got wider
}

TEST_CASE("CLAHE works on sizes the tiles do not divide") {
    const Image eq = clahe(ramp(101, 37));
    CHECK(eq.width == 101);
    CHECK(eq.height == 37);
}

TEST_CASE("an adaptive threshold separates a dark square from its page") {
    Image img(60, 60, 1, 200);
    for (int y = 20; y < 40; ++y)
        for (int x = 20; x < 40; ++x) img.at(x, y) = 50;
    const Image bw = adaptive_gaussian_threshold(img, 11, 6);
    CHECK(bw.at(21, 21) == 0);
    CHECK(bw.at(5, 5) == 255);
}

TEST_CASE("erosion grows dark and dilation grows light") {
    Image dot(9, 9, 1, 255);
    dot.at(4, 4) = 0;
    const Image grown = erode(dot, 3);
    CHECK(grown.at(3, 3) == 0);
    CHECK(grown.at(5, 5) == 0);
    CHECK(grown.at(2, 2) == 255);
    // Growing the light back by the same amount removes the block's edge but
    // keeps its middle: the dark 3 x 3 block shrinks back to its centre.
    const Image back = dilate(grown, 3);
    CHECK(back.at(4, 4) == 0);
    CHECK(back.at(3, 3) == 255);
}

TEST_CASE("pieces cover a frame, overlap, and none is too long") {
    for (int length : {1, 100, 3999, 4000, 4001, 5120, 7680, 12000}) {
        const auto runs = spans(length, 4000, 400);
        CHECK(runs.front().first == 0);
        CHECK(runs.back().second == length);
        for (const auto& [a, b] : runs) CHECK(b - a <= 4000);
        for (size_t i = 1; i < runs.size(); ++i) CHECK(runs[i].first < runs[i - 1].second);
    }
    CHECK(spans(1920, 4000, 400).size() == 1);
}
