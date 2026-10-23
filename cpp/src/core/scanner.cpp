#include "scanner.hpp"

#include "ReadBarcode.h"  // zxing-cpp

#include <algorithm>
#include <chrono>
#include <cmath>

namespace uniqr {

namespace {

using ZXing::Barcode;
using ZXing::BarcodeFormat;
using ZXing::BarcodeFormats;
using ZXing::Binarizer;

// The QR family: cheap, and read in every step of the ladder.
const BarcodeFormats& qr_family() {
    static const BarcodeFormats f{std::vector<BarcodeFormat>{
        BarcodeFormat::QRCode, BarcodeFormat::MicroQRCode, BarcodeFormat::RMQRCode}};
    return f;
}

// The other 2D codes, read once per scan rather than at every step. Linear
// barcodes are left out on purpose: a screen is full of them, and nobody pressed
// a hotkey to read a product label.
const BarcodeFormats& other_family() {
    static const BarcodeFormats f{std::vector<BarcodeFormat>{
        BarcodeFormat::DataMatrix, BarcodeFormat::Aztec, BarcodeFormat::PDF417}};
    return f;
}

const BarcodeFormats& every_2d() {
    static const BarcodeFormats f{std::vector<BarcodeFormat>{
        BarcodeFormat::QRCode, BarcodeFormat::MicroQRCode, BarcodeFormat::RMQRCode, BarcodeFormat::DataMatrix,
        BarcodeFormat::Aztec, BarcodeFormat::PDF417, BarcodeFormat::MaxiCode}};
    return f;
}

std::string label_for(BarcodeFormat f) {
    switch (f) {
        case BarcodeFormat::QRCode:
        case BarcodeFormat::QRCodeModel1:
        case BarcodeFormat::QRCodeModel2: return "QR Code";
        case BarcodeFormat::MicroQRCode: return "Micro QR";
        case BarcodeFormat::RMQRCode: return "rMQR";
        case BarcodeFormat::DataMatrix: return "Data Matrix";
        case BarcodeFormat::Aztec:
        case BarcodeFormat::AztecCode:
        case BarcodeFormat::AztecRune: return "Aztec";
        case BarcodeFormat::PDF417:
        case BarcodeFormat::CompactPDF417:
        case BarcodeFormat::MicroPDF417: return "PDF417";
        case BarcodeFormat::MaxiCode: return "MaxiCode";
        default: return ZXing::ToString(f);
    }
}

BarcodeFormat format_for(const std::string& label) {
    if (label == "Micro QR") return BarcodeFormat::MicroQRCode;
    if (label == "rMQR") return BarcodeFormat::RMQRCode;
    if (label == "Data Matrix") return BarcodeFormat::DataMatrix;
    if (label == "Aztec") return BarcodeFormat::Aztec;
    if (label == "PDF417") return BarcodeFormat::PDF417;
    if (label == "MaxiCode") return BarcodeFormat::MaxiCode;
    return BarcodeFormat::QRCode;
}

// One zxing read, keeping each code's corners.
std::vector<Detection> zx(const Image& image, const BarcodeFormats& formats, Binarizer binarizer, const char* step) {
    std::vector<Detection> out;
    if (image.empty()) return out;
    const ZXing::ImageView view(image.pixels.data(), image.width, image.height,
                                image.channels == 1 ? ZXing::ImageFormat::Lum : ZXing::ImageFormat::BGR,
                                image.stride());
    // The same options the Python version passes.
    ZXing::ReaderOptions options;
    options.setFormats(formats)
        .setTryHarder(true)
        .setTryRotate(true)
        .setTryInvert(true)
        .setTryDownscale(true)
        .setTextMode(ZXing::TextMode::HRI)
        .setBinarizer(binarizer);
    try {
        for (const Barcode& b : ZXing::ReadBarcodes(view, options)) {
            if (!b.isValid()) continue;
            std::string text = b.text();
            if (text.empty()) continue;
            Detection d;
            d.text = std::move(text);
            const auto& p = b.position();
            d.quad = {PointF{float(p.topLeft().x), float(p.topLeft().y)},
                      PointF{float(p.topRight().x), float(p.topRight().y)},
                      PointF{float(p.bottomRight().x), float(p.bottomRight().y)},
                      PointF{float(p.bottomLeft().x), float(p.bottomLeft().y)}};
            d.symbology = label_for(b.format());
            d.step = step;
            out.push_back(std::move(d));
        }
    } catch (...) {
        // A reader failure is not a scan failure.
    }
    return out;
}

std::vector<Detection> divided_all(std::vector<Detection> found, float k) {
    if (k != 1.f)
        for (auto& d : found) d = d.divided(k);
    return found;
}

}  // namespace

Box Detection::bbox() const {
    float x0 = quad[0].x, x1 = quad[0].x, y0 = quad[0].y, y1 = quad[0].y;
    for (const auto& p : quad) {
        x0 = std::min(x0, p.x);
        x1 = std::max(x1, p.x);
        y0 = std::min(y0, p.y);
        y1 = std::max(y1, p.y);
    }
    const int left = static_cast<int>(x0), top = static_cast<int>(y0);
    return {left, top, static_cast<int>(x1) - left, static_cast<int>(y1) - top};
}

PointF Detection::center() const {
    PointF c;
    for (const auto& p : quad) {
        c.x += p.x / 4;
        c.y += p.y / 4;
    }
    return c;
}

Detection Detection::offset(float dx, float dy) const {
    Detection d = *this;
    for (auto& p : d.quad) {
        p.x += dx;
        p.y += dy;
    }
    return d;
}

Detection Detection::divided(float k) const {
    Detection d = *this;
    for (auto& p : d.quad) {
        p.x /= k;
        p.y /= k;
    }
    return d;
}

std::vector<Detection> merge(const std::vector<std::vector<Detection>>& groups) {
    std::vector<Detection> merged;
    for (const auto& group : groups)
        for (const auto& det : group) {
            const PointF c = det.center();
            const bool seen = std::any_of(merged.begin(), merged.end(), [&](const Detection& o) {
                const PointF oc = o.center();
                return o.text == det.text && std::abs(oc.x - c.x) < kSameCodePx && std::abs(oc.y - c.y) < kSameCodePx;
            });
            if (!seen) merged.push_back(det);
        }
    return merged;
}

std::vector<std::pair<int, int>> spans(int length, int limit, int overlap) {
    if (length <= limit) return {{0, length}};
    const int step = std::max(1, limit - overlap);
    std::vector<std::pair<int, int>> runs;
    int start = 0;
    while (start + limit < length) {
        runs.emplace_back(start, start + limit);
        start += step;
    }
    runs.emplace_back(length - limit, length);  // the last run ends exactly at the edge
    return runs;
}

std::vector<Detection> Scanner::whole_frame(const Image& image) const {
    // zxing inverts by itself (tryInvert), so one call covers light-on-dark too.
    return zx(image, qr_family(), Binarizer::LocalAverage, "whole frame");
}

std::vector<Detection> Scanner::other_formats(const Image& image) const {
    std::vector<Detection> found = zx(image, other_family(), Binarizer::LocalAverage, "other formats");
    // MaxiCode is a bullseye and hexagons: no single threshold reads it in every
    // light, so the fixed one is tried when the adaptive default finds nothing.
    const Image grey = to_grey(image);
    auto maxi = zx(grey, BarcodeFormats(BarcodeFormat::MaxiCode), Binarizer::LocalAverage, "other formats");
    if (maxi.empty()) maxi = zx(grey, BarcodeFormats(BarcodeFormat::MaxiCode), Binarizer::FixedThreshold, "other formats");
    found.insert(found.end(), maxi.begin(), maxi.end());
    return found;
}

std::vector<Detection> Scanner::robust_read(const Image& image, float scale_back) const {
    // Every 2D format, on grey, under each of zxing's thresholds: the default
    // adapts to local brightness, the global one ignores local noise, the fixed
    // one survives flat low contrast. Past kRobustMaxPx only the default runs.
    const Image grey = to_grey(image);
    std::vector<Binarizer> modes = {Binarizer::LocalAverage, Binarizer::GlobalHistogram, Binarizer::FixedThreshold};
    if (std::max(image.width, image.height) > kRobustMaxPx) modes.resize(1);
    for (const Binarizer b : modes) {
        auto found = zx(grey, every_2d(), b, "enlarged");
        if (!found.empty()) return divided_all(std::move(found), scale_back);
    }
    return {};
}

std::vector<Detection> Scanner::destylized(const Image& image) const {
    // Marketing codes drawn as dots with gaps: threshold, then grow the dark
    // (or light) modules by about a module, which restores a normal grid.
    const Image grey = to_grey(image);
    const Image binary = threshold(grey, otsu_threshold(grey));
    for (const int k : {3, 5})
        for (const bool grow_dark : {true, false}) {
            const Image fixed = grow_dark ? erode(binary, k) : dilate(binary, k);
            auto found = zx(fixed, qr_family(), Binarizer::LocalAverage, "destyled");
            if (!found.empty()) return found;
        }
    return {};
}

std::vector<Detection> Scanner::softened(const Image& image) const {
    // Rings and dots melted into solid shapes by a blur of about a quarter of a
    // module, then the same with local contrast evened out.
    const Image soft = gaussian_blur(image, kSoftenSigma);
    auto found = zx(soft, qr_family(), Binarizer::LocalAverage, "softened");
    if (!found.empty()) return found;
    found = zx(clahe(to_grey(soft)), qr_family(), Binarizer::LocalAverage, "softened");
    if (!found.empty()) return found;
    if (std::max(image.width, image.height) > kUpscaleMaxDim) return {};
    for (auto& d : robust_read(scale(soft, 2.0, Interp::Cubic), 2.f)) {
        d.step = "softened";
        found.push_back(d);
    }
    return found;
}

std::vector<Detection> Scanner::enlarged_small_frame(const Image& image) const {
    for (const double f : {2.0, 4.0}) {
        auto hits = robust_read(scale(to_grey(image), f, Interp::Lanczos), static_cast<float>(f));
        if (!hits.empty()) return hits;
    }
    return robust_read(scale(to_grey(image), 3.0, Interp::Cubic), 3.f);
}

std::vector<Detection> Scanner::enlarged_big_frame(const Image& image) const {
    // A screen is too big to enlarge with every step, but zxing alone reads one
    // enlarged twice in a fraction of a second. A frame that would pass the cap
    // enlarged (two monitors) is read in overlapping pieces.
    const Image grey = to_grey(image);
    const float f = 2.f;
    const int limit = static_cast<int>(kBigFrameMaxPx / f);
    std::vector<Detection> hits;
    for (const auto& [y0, y1] : spans(grey.height, limit, kBigFrameOverlap))
        for (const auto& [x0, x1] : spans(grey.width, limit, kBigFrameOverlap)) {
            const Image piece = crop(grey, x0, y0, x1, y1);
            for (auto& d : robust_read(scale(piece, f, Interp::Lanczos), f)) {
                d.step = "enlarged screen";
                hits.push_back(d.offset(static_cast<float>(x0), static_cast<float>(y0)));
            }
        }
    return merge({hits});
}

std::vector<Detection> Scanner::scan_raw(const Image& image, const ScanOptions& options) const {
    const auto start = std::chrono::steady_clock::now();
    auto out_of_time = [&] {
        return std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count() > options.budget_seconds;
    };

    std::vector<Detection> found = merge({whole_frame(image), other_formats(image)});
    if (!options.thorough) return found;
    if (!found.empty()) {
        // Finding some codes says nothing about the small ones beside them. A
        // screen can hold a big code and a code about two pixels per module,
        // and only the enlarged read sees the second. On pages of 2 to 12
        // small, damaged codes (benchmarks/many_codes.py --hard) this took the
        // codes read from 170 to 198 of 198, for about 150 ms more on 1080p.
        if (std::max(image.width, image.height) > kUpscaleMaxDim && !out_of_time())
            return merge({found, enlarged_big_frame(image)});
        return found;
    }

    // Nothing by the usual route: the code may be stylised, then too small.
    if (out_of_time()) return {};
    found = destylized(image);
    if (!found.empty() || out_of_time()) return found;
    found = softened(image);
    if (!found.empty() || out_of_time()) return found;
    if (std::max(image.width, image.height) > kUpscaleMaxDim) return enlarged_big_frame(image);
    return enlarged_small_frame(image);
}

bool Scanner::confirm(const Image& image, const Detection& det) const {
    // Error correction can, rarely, "correct" a badly damaged code into a
    // different valid message. So every code that is not a plain QR code is read
    // again, differently, and believed only if the first thing read agrees.
    const BarcodeFormat fmt = format_for(det.symbology);
    const Box b = det.bbox();
    const int padding = static_cast<int>(0.3 * std::max(b.width, b.height)) + 8;
    const Image grey = to_grey(crop(image, b.left - padding, b.top - padding, b.left + b.width + padding,
                                    b.top + b.height + padding));
    if (grey.empty()) return false;
    auto enlarged = [&](double k) { return scale(grey, k, Interp::Cubic); };
    const Image treatments[] = {
        grey, enlarged(2), enlarged(3), enlarged(4), gaussian_blur(grey, 1.2), clahe(grey), gaussian_blur(enlarged(2), 1.5),
    };
    for (const Image& treated : treatments)
        for (const Binarizer b2 : {Binarizer::LocalAverage, Binarizer::GlobalHistogram, Binarizer::FixedThreshold}) {
            const auto reads = zx(treated, BarcodeFormats(fmt), b2, "confirm");
            if (!reads.empty()) return reads.front().text == det.text;  // the first read decides
        }
    return false;
}

std::vector<Detection> Scanner::scan(const Image& image, const ScanOptions& options) const {
    std::vector<Detection> out;
    for (const auto& d : scan_raw(image, options))
        if (d.symbology == "QR Code" || confirm(image, d)) out.push_back(d);
    return out;
}

}  // namespace uniqr
