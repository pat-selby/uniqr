// Finding and reading every 2D code in a frame: the C++ port of
// uniqr/decode.py.
//
// The Python version runs three readers (zxing-cpp and two OpenCV detectors).
// This one runs zxing-cpp alone, with the image steps written in image.cpp, so
// it needs no OpenCV. The retry ladder, its order and its limits are the same,
// and so is the agreement check that stops a damaged code being read as a
// different, wrong message. The benchmark lab scores both, so the price of
// leaving OpenCV out is measured, not guessed.

#pragma once

#include <array>
#include <string>
#include <vector>

#include "image.hpp"

namespace uniqr {

struct PointF {
    float x = 0, y = 0;
};

struct Box {
    int left = 0, top = 0, width = 0, height = 0;
};

struct Detection {
    std::string text;
    std::array<PointF, 4> quad{};  // corners: top-left, top-right, bottom-right, bottom-left
    std::string symbology = "QR Code";
    std::string step;  // which step of the ladder read it, for the log and the lab

    Box bbox() const;
    PointF center() const;
    Detection offset(float dx, float dy) const;
    Detection divided(float k) const;  // map from an enlarged image back to the original
};

struct ScanOptions {
    bool thorough = true;        // false: the cheap whole-frame read only
    double budget_seconds = 10;  // stop starting new steps after this long
};

// The ladder's limits, the same numbers as the Python version.
inline constexpr int kUpscaleMaxDim = 1200;
inline constexpr int kRobustMaxPx = 2600;
inline constexpr double kSoftenSigma = 1.2;
inline constexpr int kBigFrameMaxPx = 8000;
inline constexpr int kBigFrameOverlap = 400;
inline constexpr float kSameCodePx = 40;

class Scanner {
public:
    // Every code it can read, each read a second way first unless it is a
    // plain QR code. `image` is grey or BGR.
    std::vector<Detection> scan(const Image& image, const ScanOptions& options = {}) const;

    // Below are the ladder's steps, public so tests and the lab can reach them.
    std::vector<Detection> scan_raw(const Image& image, const ScanOptions& options = {}) const;
    std::vector<Detection> whole_frame(const Image& image) const;
    std::vector<Detection> other_formats(const Image& image) const;
    std::vector<Detection> destylized(const Image& image) const;
    std::vector<Detection> softened(const Image& image) const;
    std::vector<Detection> enlarged_small_frame(const Image& image) const;
    std::vector<Detection> enlarged_big_frame(const Image& image) const;
    std::vector<Detection> robust_read(const Image& image, float scale_back) const;
    bool confirm(const Image& image, const Detection& det) const;
};

// Drop the same code found twice (same text, centres within kSameCodePx).
std::vector<Detection> merge(const std::vector<std::vector<Detection>>& groups);
// Overlapping (start, end) runs covering `length`, none longer than `limit`.
std::vector<std::pair<int, int>> spans(int length, int limit, int overlap);

}  // namespace uniqr
