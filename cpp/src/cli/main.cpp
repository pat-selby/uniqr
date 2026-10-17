// uniqr-scan: read every 2D code in image files, from the command line.
//
//   uniqr-scan photo.png [more.png ...]      one line per code: kind, text
//   uniqr-scan --json photo.png               one JSON object per file
//   uniqr-scan --serve                        read file paths from stdin, one per
//                                             line, answer each with a JSON line
//   uniqr-scan --fast ...                     only the cheap whole-frame read
//   uniqr-scan --version
//
// --serve is how the Python benchmark lab drives the C++ scanner: one process
// stays up, so the lab measures scanning, not starting a program 1,000 times.

#include <chrono>
#include <cstdio>
#include <iostream>
#include <string>
#include <vector>

#include "image.hpp"
#include "json.hpp"
#include "link.hpp"
#include "scanner.hpp"
#include "version.hpp"

#ifdef _WIN32
#define NOMINMAX
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#endif

namespace {

std::string result_json(const std::string& path, const std::vector<uniqr::Detection>& found, double ms, bool loaded) {
    std::string out = "{\"path\":" + uniqr::json_string(path) + ",\"loaded\":" + (loaded ? "true" : "false") +
                      ",\"ms\":" + std::to_string(ms) + ",\"codes\":[";
    for (size_t i = 0; i < found.size(); ++i) {
        const auto& d = found[i];
        out += i ? "," : "";
        out += "{\"text\":" + uniqr::json_string(d.text) + ",\"symbology\":" + uniqr::json_string(d.symbology) +
               ",\"step\":" + uniqr::json_string(d.step) + ",\"quad\":[";
        for (int k = 0; k < 4; ++k) {
            out += k ? "," : "";
            out += "[" + std::to_string(d.quad[k].x) + "," + std::to_string(d.quad[k].y) + "]";
        }
        out += "]}";
    }
    return out + "]}";
}

struct Scanned {
    std::vector<uniqr::Detection> found;
    double ms = 0;
    bool loaded = false;
};

Scanned scan_file(const uniqr::Scanner& scanner, const std::string& path, const uniqr::ScanOptions& options) {
    Scanned s;
    const uniqr::Image image = uniqr::load_image(path);
    if (image.empty()) return s;
    s.loaded = true;
    const auto t0 = std::chrono::steady_clock::now();
    s.found = scanner.scan(image, options);
    s.ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count();
    return s;
}

#ifdef _WIN32
// Windows hands main() its arguments in the local code page. Ask for them as
// UTF-16 and convert, so a file name with any characters works.
std::vector<std::string> utf8_args() {
    int n = 0;
    wchar_t** wargv = CommandLineToArgvW(GetCommandLineW(), &n);
    std::vector<std::string> out;
    for (int i = 1; i < n; ++i) {
        const int len = WideCharToMultiByte(CP_UTF8, 0, wargv[i], -1, nullptr, 0, nullptr, nullptr);
        std::string s(static_cast<size_t>(std::max(0, len - 1)), '\0');
        WideCharToMultiByte(CP_UTF8, 0, wargv[i], -1, s.data(), len, nullptr, nullptr);
        out.push_back(std::move(s));
    }
    LocalFree(wargv);
    return out;
}
#endif

}  // namespace

int main(int argc, char** argv) {
#ifdef _WIN32
    SetConsoleOutputCP(CP_UTF8);
    const std::vector<std::string> args = utf8_args();
#else
    const std::vector<std::string> args(argv + 1, argv + argc);
#endif
    (void)argc;
    (void)argv;

    bool json = false, serve = false;
    uniqr::ScanOptions options;
    std::vector<std::string> files;
    for (const auto& a : args) {
        if (a == "--json") json = true;
        else if (a == "--serve") serve = true;
        else if (a == "--fast") options.thorough = false;
        else if (a == "--version") {
            std::printf("uniqr-scan %s\n", UNIQR_CPP_VERSION);
            return 0;
        } else if (a == "--help" || a == "-h") {
            std::printf("usage: uniqr-scan [--json] [--fast] image...\n       uniqr-scan --serve\n");
            return 0;
        } else files.push_back(a);
    }

    const uniqr::Scanner scanner;
    if (serve) {
        std::string line;
        while (std::getline(std::cin, line)) {
            if (!line.empty() && line.back() == '\r') line.pop_back();
            if (line.empty()) continue;
            const Scanned s = scan_file(scanner, line, options);
            std::cout << result_json(line, s.found, s.ms, s.loaded) << '\n' << std::flush;
        }
        return 0;
    }
    if (files.empty()) {
        std::fprintf(stderr, "usage: uniqr-scan [--json] [--fast] image...\n");
        return 2;
    }
    int status = 0;
    for (const auto& path : files) {
        const Scanned s = scan_file(scanner, path, options);
        if (!s.loaded) {
            std::fprintf(stderr, "could not read %s\n", path.c_str());
            status = 1;
            continue;
        }
        if (json) {
            std::cout << result_json(path, s.found, s.ms, true) << '\n';
            continue;
        }
        if (s.found.empty()) std::printf("%s: no code found (%.0f ms)\n", path.c_str(), s.ms);
        for (const auto& d : s.found)
            std::printf("%s [%s] %s\n", d.symbology.c_str(),
                        uniqr::kind_label(uniqr::payload_kind(d.text)).c_str(), d.text.c_str());
    }
    return status;
}
