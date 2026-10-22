#include "image.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <numbers>
#include <stdexcept>

#include "parallel.hpp"

namespace uniqr {

namespace {

uint8_t clamp_u8(double v) {
    // OpenCV's saturate_cast: round to nearest, then clamp.
    const long r = std::lround(v);
    return static_cast<uint8_t>(std::clamp(r, 0L, 255L));
}

// OpenCV's default border: mirror without repeating the edge pixel.
int reflect101(int i, int n) {
    if (n == 1) return 0;
    while (i < 0 || i >= n) {
        if (i < 0) i = -i;
        if (i >= n) i = 2 * n - 2 - i;
    }
    return i;
}

int replicate(int i, int n) { return std::clamp(i, 0, n - 1); }

// For each output position along one axis: which source pixels it reads, and
// with what weight. Every position reads `taps` pixels starting at `first`.
struct Taps {
    int taps = 0;
    std::vector<int> index;    // size out * taps, already clamped into the source
    std::vector<float> weight;  // size out * taps, summing to 1 per position
};

double cubic(double x) {
    // OpenCV's bicubic kernel, a = -0.75.
    const double a = -0.75;
    x = std::abs(x);
    if (x <= 1) return ((a + 2) * x - (a + 3)) * x * x + 1;
    if (x < 2) return ((a * x - 5 * a) * x + 8 * a) * x - 4 * a;
    return 0;
}

double lanczos4(double x) {
    if (std::abs(x) < 1e-9) return 1;
    if (std::abs(x) >= 4) return 0;
    const double px = std::numbers::pi * x;
    return 4 * std::sin(px) * std::sin(px / 4) / (px * px);
}

Taps make_taps(int in, int out, Interp interp) {
    Taps t;
    const double ratio = static_cast<double>(in) / out;
    if (interp == Interp::Area && out < in) {
        // Each output pixel averages the source pixels it covers, weighted by
        // how much of each it covers.
        t.taps = static_cast<int>(std::ceil(ratio)) + 1;
        t.index.assign(static_cast<size_t>(out) * t.taps, 0);
        t.weight.assign(static_cast<size_t>(out) * t.taps, 0.f);
        for (int o = 0; o < out; ++o) {
            const double lo = o * ratio, hi = (o + 1) * ratio;
            int k = 0;
            for (int s = static_cast<int>(std::floor(lo)); s < hi && k < t.taps; ++s, ++k) {
                const double cover = std::min<double>(s + 1, hi) - std::max<double>(s, lo);
                t.index[o * t.taps + k] = replicate(s, in);
                t.weight[o * t.taps + k] = static_cast<float>(std::max(0.0, cover) / ratio);
            }
        }
        return t;
    }
    if (interp == Interp::Area) interp = Interp::Linear;  // OpenCV does the same when enlarging

    int radius = 1;
    if (interp == Interp::Cubic) radius = 2;
    if (interp == Interp::Lanczos) radius = 4;
    if (interp == Interp::Nearest) {
        t.taps = 1;
        t.index.resize(out);
        t.weight.assign(out, 1.f);
        for (int o = 0; o < out; ++o) t.index[o] = std::min(in - 1, static_cast<int>(std::floor(o * ratio)));
        return t;
    }
    t.taps = 2 * radius;
    t.index.resize(static_cast<size_t>(out) * t.taps);
    t.weight.resize(static_cast<size_t>(out) * t.taps);
    for (int o = 0; o < out; ++o) {
        const double src = (o + 0.5) * ratio - 0.5;
        const int base = static_cast<int>(std::floor(src));
        const double frac = src - base;
        double sum = 0;
        for (int k = 0; k < t.taps; ++k) {
            const int s = base - radius + 1 + k;
            const double d = frac - (k - radius + 1);
            double w = 0;
            if (interp == Interp::Linear) w = std::max(0.0, 1 - std::abs(d));
            else if (interp == Interp::Cubic) w = cubic(d);
            else w = lanczos4(d);
            t.index[o * t.taps + k] = replicate(s, in);
            t.weight[o * t.taps + k] = static_cast<float>(w);
            sum += w;
        }
        if (sum != 0)
            for (int k = 0; k < t.taps; ++k) t.weight[o * t.taps + k] = static_cast<float>(t.weight[o * t.taps + k] / sum);
    }
    return t;
}

// A separable filter: the same 1-D kernel across rows, then down columns.
Image separable(const Image& src, const std::vector<float>& kernel, bool reflect) {
    const int r = static_cast<int>(kernel.size() / 2);
    const int w = src.width, h = src.height, c = src.channels;
    std::vector<float> mid(static_cast<size_t>(w) * h * c);
    parallel_rows(h, [&](int y0, int y1) {
        for (int y = y0; y < y1; ++y) {
            const uint8_t* in = src.row(y);
            float* out = mid.data() + static_cast<size_t>(y) * w * c;
            for (int x = 0; x < w; ++x)
                for (int ch = 0; ch < c; ++ch) {
                    float acc = 0;
                    for (int k = -r; k <= r; ++k) {
                        const int xx = reflect ? reflect101(x + k, w) : replicate(x + k, w);
                        acc += kernel[k + r] * in[xx * c + ch];
                    }
                    out[x * c + ch] = acc;
                }
        }
    });
    Image dst(w, h, c);
    parallel_rows(h, [&](int y0, int y1) {
        for (int y = y0; y < y1; ++y) {
            uint8_t* out = dst.row(y);
            for (int x = 0; x < w * c; ++x) {
                float acc = 0;
                for (int k = -r; k <= r; ++k) {
                    const int yy = reflect ? reflect101(y + k, h) : replicate(y + k, h);
                    acc += kernel[k + r] * mid[static_cast<size_t>(yy) * w * c + x];
                }
                out[x] = clamp_u8(acc);
            }
        }
    });
    return dst;
}

std::vector<float> gaussian_kernel(int ksize, double sigma) {
    if (sigma <= 0) sigma = 0.3 * ((ksize - 1) * 0.5 - 1) + 0.8;  // OpenCV's rule
    std::vector<float> k(ksize);
    const int r = ksize / 2;
    double sum = 0;
    for (int i = 0; i < ksize; ++i) {
        const double x = i - r;
        k[i] = static_cast<float>(std::exp(-(x * x) / (2 * sigma * sigma)));
        sum += k[i];
    }
    for (auto& v : k) v = static_cast<float>(v / sum);
    return k;
}

Image morph(const Image& grey, int k, bool take_min) {
    // A k x k square is separable: the min (or max) over rows, then columns.
    // The window is clipped at the edges, which is what OpenCV's default
    // border for erosion and dilation amounts to.
    const int r = k / 2, w = grey.width, h = grey.height;
    Image mid(w, h, 1), dst(w, h, 1);
    parallel_rows(h, [&](int y0, int y1) {
        for (int y = y0; y < y1; ++y)
            for (int x = 0; x < w; ++x) {
                uint8_t v = take_min ? 255 : 0;
                for (int xx = std::max(0, x - r); xx <= std::min(w - 1, x + r); ++xx)
                    v = take_min ? std::min(v, grey.at(xx, y)) : std::max(v, grey.at(xx, y));
                mid.at(x, y) = v;
            }
    });
    parallel_rows(h, [&](int y0, int y1) {
        for (int y = y0; y < y1; ++y)
            for (int x = 0; x < w; ++x) {
                uint8_t v = take_min ? 255 : 0;
                for (int yy = std::max(0, y - r); yy <= std::min(h - 1, y + r); ++yy)
                    v = take_min ? std::min(v, mid.at(x, yy)) : std::max(v, mid.at(x, yy));
                dst.at(x, y) = v;
            }
    });
    return dst;
}

void need_grey(const Image& image, const char* what) {
    if (image.channels != 1) throw std::invalid_argument(std::string(what) + " needs a grey image");
}

}  // namespace

Image::Image(int w, int h, int c, uint8_t fill)
    : width(w), height(h), channels(c), pixels(static_cast<size_t>(std::max(0, w)) * std::max(0, h) * c, fill) {}

Image to_grey(const Image& image) {
    if (image.channels == 1) return image;
    Image out(image.width, image.height, 1);
    parallel_rows(image.height, [&](int y0, int y1) {
        for (int y = y0; y < y1; ++y) {
            const uint8_t* in = image.row(y);
            uint8_t* o = out.row(y);
            for (int x = 0; x < image.width; ++x) {
                const unsigned b = in[3 * x], g = in[3 * x + 1], r = in[3 * x + 2];
                o[x] = static_cast<uint8_t>((306 * r + 601 * g + 117 * b + 0x200) >> 10);
            }
        }
    });
    return out;
}

Image channel(const Image& bgr, int index) {
    if (bgr.channels == 1) return bgr;
    Image out(bgr.width, bgr.height, 1);
    for (int y = 0; y < bgr.height; ++y)
        for (int x = 0; x < bgr.width; ++x) out.at(x, y) = bgr.at(x, y, index);
    return out;
}

Image to_bgr(const Image& grey) {
    if (grey.channels == 3) return grey;
    Image out(grey.width, grey.height, 3);
    for (size_t i = 0; i < grey.pixels.size(); ++i)
        out.pixels[3 * i] = out.pixels[3 * i + 1] = out.pixels[3 * i + 2] = grey.pixels[i];
    return out;
}

Image invert(const Image& image) {
    Image out = image;
    for (auto& p : out.pixels) p = static_cast<uint8_t>(255 - p);
    return out;
}

Image crop(const Image& image, int x0, int y0, int x1, int y1) {
    x0 = std::clamp(x0, 0, image.width);
    x1 = std::clamp(x1, 0, image.width);
    y0 = std::clamp(y0, 0, image.height);
    y1 = std::clamp(y1, 0, image.height);
    if (x1 <= x0 || y1 <= y0) return {};
    Image out(x1 - x0, y1 - y0, image.channels);
    for (int y = y0; y < y1; ++y)
        std::copy_n(image.row(y) + x0 * image.channels, out.stride(), out.row(y - y0));
    return out;
}

void paste(Image& into, const Image& piece, int x, int y) {
    for (int py = 0; py < piece.height; ++py) {
        const int ty = y + py;
        if (ty < 0 || ty >= into.height) continue;
        for (int px = 0; px < piece.width; ++px) {
            const int tx = x + px;
            if (tx < 0 || tx >= into.width) continue;
            for (int c = 0; c < into.channels; ++c)
                into.at(tx, ty, c) = piece.at(px, py, piece.channels == 1 ? 0 : std::min(c, piece.channels - 1));
        }
    }
}

Image resize(const Image& image, int new_width, int new_height, Interp interp) {
    if (image.empty() || new_width <= 0 || new_height <= 0) return {};
    if (new_width == image.width && new_height == image.height) return image;
    const Taps tx = make_taps(image.width, new_width, interp);
    const Taps ty = make_taps(image.height, new_height, interp);
    const int c = image.channels;

    // Across rows first, at the source height, then down the columns.
    std::vector<float> mid(static_cast<size_t>(new_width) * image.height * c);
    parallel_rows(image.height, [&](int y0, int y1) {
        for (int y = y0; y < y1; ++y) {
            const uint8_t* in = image.row(y);
            float* out = mid.data() + static_cast<size_t>(y) * new_width * c;
            for (int x = 0; x < new_width; ++x) {
                const int* idx = &tx.index[static_cast<size_t>(x) * tx.taps];
                const float* wt = &tx.weight[static_cast<size_t>(x) * tx.taps];
                for (int ch = 0; ch < c; ++ch) {
                    float acc = 0;
                    for (int k = 0; k < tx.taps; ++k) acc += wt[k] * in[idx[k] * c + ch];
                    out[x * c + ch] = acc;
                }
            }
        }
    });
    Image dst(new_width, new_height, c);
    parallel_rows(new_height, [&](int y0, int y1) {
        for (int y = y0; y < y1; ++y) {
            const int* idx = &ty.index[static_cast<size_t>(y) * ty.taps];
            const float* wt = &ty.weight[static_cast<size_t>(y) * ty.taps];
            uint8_t* out = dst.row(y);
            for (int x = 0; x < new_width * c; ++x) {
                float acc = 0;
                for (int k = 0; k < ty.taps; ++k) acc += wt[k] * mid[static_cast<size_t>(idx[k]) * new_width * c + x];
                out[x] = clamp_u8(acc);
            }
        }
    });
    return dst;
}

Image scale(const Image& image, double factor, Interp interp) {
    const int w = std::max(1, static_cast<int>(std::lround(image.width * factor)));
    const int h = std::max(1, static_cast<int>(std::lround(image.height * factor)));
    return resize(image, w, h, interp);
}

Image pad(const Image& image, int border, uint8_t value) {
    Image out(image.width + 2 * border, image.height + 2 * border, image.channels, value);
    paste(out, image, border, border);
    return out;
}

Image gaussian_blur(const Image& image, double sigma, int ksize) {
    if (ksize <= 0) ksize = static_cast<int>(std::lround(sigma * 3 * 2 + 1)) | 1;  // OpenCV, 8-bit
    return separable(image, gaussian_kernel(ksize, sigma), true);
}

Image clahe(const Image& grey, double clip_limit, int tiles) {
    need_grey(grey, "clahe");
    const int w = grey.width, h = grey.height;
    // Tiles must divide the frame; OpenCV pads the bottom and right by mirroring.
    const int pw = (w + tiles - 1) / tiles * tiles, ph = (h + tiles - 1) / tiles * tiles;
    const int tw = pw / tiles, th = ph / tiles;
    const int tile_area = tw * th;
    const int limit = clip_limit > 0 ? std::max(static_cast<int>(clip_limit * tile_area / 256), 1) : tile_area;
    const float lut_scale = 255.f / tile_area;

    std::vector<std::array<uint8_t, 256>> lut(static_cast<size_t>(tiles) * tiles);
    for (int ty = 0; ty < tiles; ++ty)
        for (int tx = 0; tx < tiles; ++tx) {
            std::array<int, 256> hist{};
            for (int y = ty * th; y < (ty + 1) * th; ++y)
                for (int x = tx * tw; x < (tx + 1) * tw; ++x)
                    ++hist[grey.at(reflect101(x, w), reflect101(y, h))];
            int clipped = 0;
            for (auto& v : hist)
                if (v > limit) {
                    clipped += v - limit;
                    v = limit;
                }
            const int batch = clipped / 256;
            int residual = clipped - batch * 256;
            for (auto& v : hist) v += batch;
            if (residual > 0) {
                const int step = std::max(256 / residual, 1);
                for (int i = 0; i < 256 && residual > 0; i += step, --residual) ++hist[i];
            }
            int sum = 0;
            auto& table = lut[static_cast<size_t>(ty) * tiles + tx];
            for (int i = 0; i < 256; ++i) {
                sum += hist[i];
                table[i] = clamp_u8(sum * lut_scale);
            }
        }

    Image out(w, h, 1);
    const float inv_tw = 1.f / tw, inv_th = 1.f / th;
    parallel_rows(h, [&](int y0, int y1) {
        for (int y = y0; y < y1; ++y) {
            const float tyf = y * inv_th - 0.5f;
            int ty1 = static_cast<int>(std::floor(tyf));
            const float ya = tyf - ty1;
            int ty2 = ty1 + 1;
            ty1 = std::max(ty1, 0);
            ty2 = std::min(ty2, tiles - 1);
            for (int x = 0; x < w; ++x) {
                const float txf = x * inv_tw - 0.5f;
                int tx1 = static_cast<int>(std::floor(txf));
                const float xa = txf - tx1;
                int tx2 = tx1 + 1;
                tx1 = std::max(tx1, 0);
                tx2 = std::min(tx2, tiles - 1);
                const uint8_t v = grey.at(x, y);
                const float top = lut[ty1 * tiles + tx1][v] * (1 - xa) + lut[ty1 * tiles + tx2][v] * xa;
                const float bottom = lut[ty2 * tiles + tx1][v] * (1 - xa) + lut[ty2 * tiles + tx2][v] * xa;
                out.at(x, y) = clamp_u8(top * (1 - ya) + bottom * ya);
            }
        }
    });
    return out;
}

int otsu_threshold(const Image& grey) {
    need_grey(grey, "otsu_threshold");
    // The cut that best separates the histogram into two groups: the one with
    // the largest variance between the groups' means.
    std::array<double, 256> hist{};
    for (auto p : grey.pixels) ++hist[p];
    const double total = static_cast<double>(grey.pixels.size());
    double sum_all = 0;
    for (int i = 0; i < 256; ++i) sum_all += i * hist[i];
    double w0 = 0, sum0 = 0, best = -1;
    int t_best = 0;
    for (int t = 0; t < 256; ++t) {
        w0 += hist[t];
        if (w0 == 0) continue;
        const double w1 = total - w0;
        if (w1 == 0) break;
        sum0 += t * hist[t];
        const double m0 = sum0 / w0, m1 = (sum_all - sum0) / w1;
        const double between = w0 * w1 * (m0 - m1) * (m0 - m1);
        if (between > best) {
            best = between;
            t_best = t;
        }
    }
    return t_best;
}

Image threshold(const Image& grey, int t) {
    need_grey(grey, "threshold");
    Image out(grey.width, grey.height, 1);
    for (size_t i = 0; i < grey.pixels.size(); ++i) out.pixels[i] = grey.pixels[i] > t ? 255 : 0;
    return out;
}

Image adaptive_gaussian_threshold(const Image& grey, int block, int c) {
    need_grey(grey, "adaptive_gaussian_threshold");
    // The local mean is a Gaussian blur of the block size, with OpenCV's
    // replicated border; a pixel is white when it is brighter than mean - c.
    const Image mean = separable(grey, gaussian_kernel(block, 0), false);
    Image out(grey.width, grey.height, 1);
    for (size_t i = 0; i < grey.pixels.size(); ++i)
        out.pixels[i] = static_cast<int>(grey.pixels[i]) - static_cast<int>(mean.pixels[i]) > -c ? 255 : 0;
    return out;
}

Image erode(const Image& grey, int k) {
    need_grey(grey, "erode");
    return morph(grey, k, true);
}

Image dilate(const Image& grey, int k) {
    need_grey(grey, "dilate");
    return morph(grey, k, false);
}

}  // namespace uniqr
