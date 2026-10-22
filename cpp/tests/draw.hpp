// Drawing test codes with zxing-cpp's own writer, so every test knows the answer.

#pragma once

#include <string>

#include "image.hpp"

namespace test {

// Kinds the writer can draw: "QRCode", "MicroQRCode", "RMQRCode", "DataMatrix",
// "Aztec", "PDF417". `module` is pixels per module; a quiet zone is included.
uniqr::Image draw_code(const std::string& text, const std::string& kind = "QRCode", int module = 6);

// A code placed on a plain page of the given size and grey level, as BGR.
uniqr::Image on_page(const uniqr::Image& code, int width, int height, int x, int y, uint8_t page = 255);

std::string repo_path(const std::string& relative);

}  // namespace test
