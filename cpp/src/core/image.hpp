// Small, dependency-free image processing: the handful of OpenCV operations the
// Python UniQR leans on, written out so the C++ build needs no OpenCV.
//
// Images are 8 bits per channel, either 1 channel (grey) or 3 (blue, green, red,
// the order a Windows screen capture arrives in). Rows are tightly packed.
// Where a function has an OpenCV twin, it follows OpenCV's conventions (pixel
// centres, border handling), so the two versions treat a frame the same way.

#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace uniqr {

struct Image {
    int width = 0;
    int height = 0;
    int channels = 1;  // 1 = grey, 3 = BGR
    std::vector<uint8_t> pixels;

    Image() = default;
    Image(int w, int h, int c, uint8_t fill = 0);

    bool empty() const { return width <= 0 || height <= 0; }
    int stride() const { return width * channels; }
    uint8_t* row(int y) { return pixels.data() + static_cast<size_t>(y) * stride(); }
    const uint8_t* row(int y) const { return pixels.data() + static_cast<size_t>(y) * stride(); }
    uint8_t& at(int x, int y, int c = 0) { return row(y)[x * channels + c]; }
    uint8_t at(int x, int y, int c = 0) const { return row(y)[x * channels + c]; }
};

enum class Interp { Nearest, Linear, Cubic, Area, Lanczos };

// Colour.
Image to_grey(const Image& image);        // luminance, the weights zxing uses
Image channel(const Image& bgr, int index);  // one channel as grey: 0 blue, 1 green, 2 red
Image to_bgr(const Image& grey);
Image invert(const Image& image);

// Geometry. crop() clamps to the image and may return an empty image.
Image crop(const Image& image, int x0, int y0, int x1, int y1);
void paste(Image& into, const Image& piece, int x, int y);
Image resize(const Image& image, int new_width, int new_height, Interp interp);
Image scale(const Image& image, double factor, Interp interp);
Image pad(const Image& image, int border, uint8_t value);

// Filters.
Image gaussian_blur(const Image& image, double sigma, int ksize = 0);
// Contrast-limited adaptive histogram equalisation, on a grey image.
Image clahe(const Image& grey, double clip_limit = 3.0, int tiles = 8);

// Thresholds, on a grey image. Results are 0 or 255.
int otsu_threshold(const Image& grey);
Image threshold(const Image& grey, int t);  // above t -> 255
Image adaptive_gaussian_threshold(const Image& grey, int block, int c);

// Morphology with a k x k square, on a grey image.
Image erode(const Image& grey, int k);   // darkest in the window
Image dilate(const Image& grey, int k);  // lightest in the window

// Files, through stb_image. load() returns an empty image on failure, and
// always 3 channels (BGR) or 1 (grey) as asked.
Image load_image(const std::string& path, bool grey = false);
bool save_png(const std::string& path, const Image& image);

}  // namespace uniqr
