#include "log.hpp"

#include <cstdio>
#include <ctime>
#include <filesystem>
#include <mutex>

#include "version.hpp"
#include "win.hpp"

namespace uniqr::win {

namespace {
std::mutex g_lock;
constexpr std::uintmax_t kRotateBytes = 1 << 20;  // keep the log to about a megabyte
}  // namespace

std::wstring log_path() {
    wchar_t buf[MAX_PATH] = {};
    const DWORD n = GetEnvironmentVariableW(L"LOCALAPPDATA", buf, MAX_PATH);
    std::filesystem::path dir = n ? std::filesystem::path(buf) : std::filesystem::temp_directory_path();
    dir /= L"UniQR";
    std::error_code ec;
    std::filesystem::create_directories(dir, ec);
    return (dir / L"uniqr-cpp.log").wstring();
}

void log(std::string_view line) {
    std::lock_guard<std::mutex> hold(g_lock);
    const std::time_t now = std::time(nullptr);
    std::tm local{};
    localtime_s(&local, &now);
    char stamp[32];
    std::strftime(stamp, sizeof stamp, "%Y-%m-%d %H:%M:%S", &local);
    FILE* f = nullptr;
    if (_wfopen_s(&f, log_path().c_str(), L"ab") == 0 && f) {
        std::fprintf(f, "%s  %.*s\n", stamp, static_cast<int>(line.size()), line.data());
        std::fclose(f);
    }
}

void log_start(std::string_view command_line) {
    {
        std::lock_guard<std::mutex> hold(g_lock);
        std::error_code ec;
        const std::filesystem::path p = log_path();
        if (std::filesystem::exists(p, ec) && std::filesystem::file_size(p, ec) > kRotateBytes) {
            std::filesystem::path old = p;
            old += L".1";
            std::filesystem::remove(old, ec);
            std::filesystem::rename(p, old, ec);
        }
    }
    log("------------------------------------------------------------");
    log(std::string("UniQR (C++) ") + UNIQR_CPP_VERSION + " starting");
    log("command: " + std::string(command_line));
}

}  // namespace uniqr::win
