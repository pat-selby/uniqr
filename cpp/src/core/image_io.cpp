// Reading and writing image files, through the stb single-file libraries.

#include <algorithm>

#include "image.hpp"

#define STB_IMAGE_IMPLEMENTATION
#define STBI_WINDOWS_UTF8  // file names are UTF-8, as everywhere else in UniQR
#define STBI_ONLY_PNG
#define STBI_ONLY_JPEG
#define STBI_ONLY_BMP
#include "stb_image.h"

#define STB_IMAGE_WRITE_IMPLEMENTATION
#define STBIW_WINDOWS_UTF8
#include "stb_image_write.h"

namespace uniqr {

Image load_image(const std::string& path, bool grey) {
    int w = 0, h = 0, n = 0;
    const int want = grey ? 1 : 3;
    unsigned char* data = stbi_load(path.c_str(), &w, &h, &n, want);
    if (data == nullptr) return {};
    Image out(w, h, want);
    std::copy_n(data, out.pixels.size(), out.pixels.data());
    stbi_image_free(data);
    if (!grey)  // stb gives red, green, blue; UniQR works in blue, green, red
        for (size_t i = 0; i + 2 < out.pixels.size(); i += 3) std::swap(out.pixels[i], out.pixels[i + 2]);
    return out;
}

bool save_png(const std::string& path, const Image& image) {
    Image rgb = image;
    if (rgb.channels == 3)
        for (size_t i = 0; i + 2 < rgb.pixels.size(); i += 3) std::swap(rgb.pixels[i], rgb.pixels[i + 2]);
    return stbi_write_png(path.c_str(), rgb.width, rgb.height, rgb.channels, rgb.pixels.data(), rgb.stride()) != 0;
}

}  // namespace uniqr
