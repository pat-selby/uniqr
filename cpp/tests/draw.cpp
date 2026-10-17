#include "draw.hpp"

#include <algorithm>
#include <stdexcept>

#include "CreateBarcode.h"
#include "WriteBarcode.h"

namespace test {

uniqr::Image draw_code(const std::string& text, const std::string& kind, int module) {
    const ZXing::BarcodeFormat format = ZXing::BarcodeFormatFromString(kind);
    const ZXing::Barcode barcode = ZXing::CreateBarcodeFromText(text, ZXing::CreatorOptions(format));
    const ZXing::Image drawn = ZXing::WriteBarcodeToImage(barcode, ZXing::WriterOptions().scale(module).addQuietZones(true));
    // The writer draws grey; read the first channel whatever the layout.
    uniqr::Image out(drawn.width(), drawn.height(), 1);
    for (int y = 0; y < drawn.height(); ++y)
        for (int x = 0; x < drawn.width(); ++x) out.at(x, y) = drawn.data(x, y)[0];
    return out;
}

uniqr::Image on_page(const uniqr::Image& code, int width, int height, int x, int y, uint8_t page) {
    uniqr::Image out(width, height, 3, page);
    uniqr::paste(out, uniqr::to_bgr(code), x, y);
    return out;
}

std::string repo_path(const std::string& relative) { return std::string(UNIQR_REPO_ROOT) + "/" + relative; }

}  // namespace test
