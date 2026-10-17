// UniQR, the C++ version: press a hotkey, read every QR code on screen.
//
//   uniqr-cpp.exe                          run it (tray icon, Win+Shift+Q)
//   uniqr-cpp.exe --quiet                  no card at start-up
//   uniqr-cpp.exe --hotkey ctrl+alt+k      your own hotkey
//   uniqr-cpp.exe --install-autostart      start at login (add --hotkey to keep one)
//   uniqr-cpp.exe --uninstall-autostart
//   uniqr-cpp.exe --report-problem         open a pre-filled GitHub issue
//   uniqr-cpp.exe --version

#include "win.hpp"  // windows.h, before any other Windows header

#include <shellapi.h>

#include <string>
#include <vector>

#include "app.hpp"
#include "hotkeys.hpp"
#include "log.hpp"
#include "report.hpp"
#include "system.hpp"
#include "version.hpp"
#include "win.hpp"

using namespace uniqr;
using namespace uniqr::win;

namespace {

std::vector<std::string> arguments() {
    int n = 0;
    wchar_t** argv = CommandLineToArgvW(GetCommandLineW(), &n);
    std::vector<std::string> out;
    for (int i = 1; i < n; ++i) out.push_back(narrow(argv[i]));
    LocalFree(argv);
    return out;
}

std::string option(const std::vector<std::string>& args, const std::string& name) {
    for (size_t i = 0; i < args.size(); ++i) {
        if (args[i] == name && i + 1 < args.size()) return args[i + 1];
        if (args[i].rfind(name + "=", 0) == 0) return args[i].substr(name.size() + 1);
    }
    return {};
}

bool has(const std::vector<std::string>& args, const std::string& name) {
    for (const auto& a : args)
        if (a == name) return true;
    return false;
}

// The packaged program has no console, so results are shown in a small box
// (unless --quiet, which is what automated tests use).
int tell(bool quiet, const std::string& text, bool ok) {
    log(text);
    if (!quiet) message_box(text, ok);
    return ok ? 0 : 1;
}

}  // namespace

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE, PWSTR, int) {
    // Physical pixels everywhere: a scaled display would otherwise hand UniQR a
    // blurred copy of the screen, and blur is fatal to small codes.
    SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);

    const std::vector<std::string> args = arguments();
    const bool quiet = has(args, "--quiet");
    const std::string hotkey = option(args, "--hotkey");

    if (has(args, "--version")) return tell(quiet, std::string("UniQR (C++) ") + UNIQR_CPP_VERSION, true);

    if (has(args, "--install-autostart")) {
        std::string canonical;
        if (!hotkey.empty()) {
            std::string problem;
            const auto hk = parse_hotkey(hotkey, &problem);
            if (!hk) return tell(quiet, "That hotkey will not work: " + problem, false);
            canonical = canonical_hotkey(*hk);
        }
        if (!set_autostart(true, canonical)) return tell(quiet, "UniQR could not be set to start at login.", false);
        return tell(quiet,
                    "Done. UniQR will start the next time you log in to Windows.\n\nIt starts: " +
                        narrow(autostart_command()) +
                        "\n\nIf you move or rename that file, run this again. To see or switch it off: Settings, "
                        "Apps, Startup. To remove it: run UniQR with --uninstall-autostart.",
                    true);
    }
    if (has(args, "--uninstall-autostart")) {
        const bool was = autostart_enabled();
        if (!set_autostart(false)) return tell(quiet, "UniQR could not be removed from start at login.", false);
        return tell(quiet,
                    was ? "Removed. UniQR will no longer start when you log in to Windows."
                        : "UniQR was not set to start at login, so there is nothing to remove.",
                    true);
    }
    if (has(args, "--report-problem")) {
        const std::string url = issue_url(UNIQR_CPP_VERSION, windows_version(), "%LOCALAPPDATA%\\UniQR\\uniqr-cpp.log");
        return open_link(url) ? 0 : tell(quiet, "Could not open a browser. Open this address yourself:\n" + url, false);
    }

    log_start(narrow(GetCommandLineW()));
    // One copy at a time. A second would fight the first for the hotkey.
    HANDLE single = CreateMutexW(nullptr, TRUE, L"Local\\UniQR-cpp-single-instance");
    if (GetLastError() == ERROR_ALREADY_EXISTS) {
        log("UniQR (C++) is already running - check the system tray.");
        if (single) CloseHandle(single);
        return 1;
    }

    int code = 0;
    {
        App app(instance, AppOptions{quiet, hotkey});
        code = app.run();
    }
    if (single) {
        ReleaseMutex(single);
        CloseHandle(single);
    }
    return code;
}
