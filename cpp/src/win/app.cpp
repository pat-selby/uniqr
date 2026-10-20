#include "app.hpp"  // brings windows.h first

#include <shellapi.h>

#include <chrono>
#include <cstdio>

#include "capture.hpp"
#include "card.hpp"
#include "link.hpp"
#include "log.hpp"
#include "picker.hpp"
#include "report.hpp"
#include "resource.h"
#include "system.hpp"
#include "version.hpp"

namespace uniqr::win {

namespace {

constexpr wchar_t kWindowClass[] = L"UniQRCppHiddenWindow";
constexpr int kHotkeyId = 1;
constexpr UINT kTrayId = 1;
enum Command : UINT { kScanNow = 1001, kExit = 1002, kAutostart = 1003, kReport = 1006 };

std::string ms_text(double ms) {
    char buf[32];
    std::snprintf(buf, sizeof buf, "%.0f ms", ms);
    return buf;
}

}  // namespace

App::App(HINSTANCE instance, AppOptions options) : instance_(instance), options_(std::move(options)) {}

App::~App() {
    if (worker_.joinable()) worker_.join();
    if (icon_) DestroyIcon(icon_);
}

bool App::create_window() {
    WNDCLASSEXW wc{sizeof(wc)};
    wc.lpfnWndProc = window_proc;
    wc.hInstance = instance_;
    wc.lpszClassName = kWindowClass;
    if (!RegisterClassExW(&wc)) return false;
    // Windows talks to a program through a window's messages, so a program with
    // nothing to show still needs one: a hidden mailbox, never shown.
    // A normal top-level window that is never shown, rather than a message-only
    // one: only a real window can own the tray menu, and hear that Explorer has
    // restarted and the tray icon must be added again.
    hwnd_ = CreateWindowExW(0, kWindowClass, L"UniQR", WS_OVERLAPPED, 0, 0, 0, 0, nullptr, nullptr, instance_, this);
    taskbar_created_ = RegisterWindowMessageW(L"TaskbarCreated");
    return hwnd_ != nullptr;
}

void App::add_tray_icon() {
    if (!icon_)
        icon_ = static_cast<HICON>(LoadImageW(instance_, MAKEINTRESOURCEW(IDI_UNIQR), IMAGE_ICON,
                                              GetSystemMetrics(SM_CXSMICON), GetSystemMetrics(SM_CYSMICON), 0));
    NOTIFYICONDATAW nid{sizeof(nid)};
    nid.hWnd = hwnd_;
    nid.uID = kTrayId;
    nid.uFlags = NIF_ICON | NIF_MESSAGE | NIF_TIP;
    nid.uCallbackMessage = WM_APP_TRAY;
    nid.hIcon = icon_;
    wcscpy_s(nid.szTip, L"UniQR");
    Shell_NotifyIconW(NIM_ADD, &nid);
}

void App::remove_tray_icon() {
    NOTIFYICONDATAW nid{sizeof(nid)};
    nid.hWnd = hwnd_;
    nid.uID = kTrayId;
    Shell_NotifyIconW(NIM_DELETE, &nid);
}

void App::set_tooltip(const std::string& text) {
    NOTIFYICONDATAW nid{sizeof(nid)};
    nid.hWnd = hwnd_;
    nid.uID = kTrayId;
    nid.uFlags = NIF_TIP;
    wcsncpy_s(nid.szTip, widen(summarize(text, 120)).c_str(), _TRUNCATE);
    Shell_NotifyIconW(NIM_MODIFY, &nid);
}

std::optional<Hotkey> App::register_hotkey() {
    // The person's own hotkey first; if it is unreadable or another program has
    // it, say so and fall back to the usual list, so UniQR still starts.
    const HotkeyChoices choices = hotkey_choices(options_.hotkey);
    if (!choices.problem.empty()) log("The hotkey you asked for was not used. " + choices.problem);
    for (const Hotkey& hk : choices.order) {
        if (RegisterHotKey(hwnd_, kHotkeyId, hk.modifiers | MOD_NOREPEAT, hk.key)) {
            if (choices.wanted && !(hk == *choices.wanted))
                log(shown_hotkey(choices.wanted->label) + " is already used by another program, so UniQR is using " + shown_hotkey(hk.label) +
                    " instead.");
            return hk;
        }
    }
    return std::nullopt;
}

void App::greet() {
    const std::string message = hotkey_ ? "UniQR is running. Press " + shown_hotkey(hotkey_->label) + " to scan."
                                        : "UniQR is running, but no hotkey was free. Use the tray icon.";
    log(hotkey_ ? "UniQR is running. Press " + shown_hotkey(hotkey_->label) + " to scan the screen."
                : "UniQR is running, but no hotkey was free. Use the tray icon.");
    log("Right-click the tray icon to exit.");
    set_tooltip(hotkey_ ? "UniQR - press " + shown_hotkey(hotkey_->label) + " to scan" : "UniQR");
    if (options_.quiet) return;
    const RECT work = work_area_at(POINT{0, 0});
    const double s = dpi_scale_at(POINT{0, 0});
    show_card(instance_, "", message,
              POINT{work.right - static_cast<LONG>(360 * s), work.bottom - static_cast<LONG>(130 * s)}, CardOptions{});
}

void App::show_menu() {
    HMENU menu = CreatePopupMenu();
    const std::wstring scan = hotkey_ ? L"Scan now (" + widen(shown_hotkey(hotkey_->label)) + L")" : L"Scan now";
    AppendMenuW(menu, MF_STRING, kScanNow, scan.c_str());
    AppendMenuW(menu, MF_STRING | (autostart_enabled() ? MF_CHECKED : 0), kAutostart, L"Start at login");
    AppendMenuW(menu, MF_STRING, kReport, L"Report a problem");
    AppendMenuW(menu, MF_SEPARATOR, 0, nullptr);
    AppendMenuW(menu, MF_STRING, kExit, L"Exit UniQR");
    POINT p;
    GetCursorPos(&p);
    // Required, or the menu will not close when the person clicks elsewhere.
    SetForegroundWindow(hwnd_);
    TrackPopupMenu(menu, TPM_RIGHTBUTTON | TPM_BOTTOMALIGN, p.x, p.y, 0, hwnd_, nullptr);
    PostMessageW(hwnd_, WM_NULL, 0, 0);
    DestroyMenu(menu);
}

void App::start_scan() {
    // One at a time: a second press while a scan or the picker is up is ignored.
    if (scanning_.exchange(true)) return;
    if (picker_open_) {
        scanning_ = false;
        return;
    }
    if (worker_.joinable()) worker_.join();
    // The capture is quick and happens here, at the moment of the keypress; the
    // reading happens on the worker thread.
    shot_area_ = virtual_screen();
    shot_ = capture(shot_area_);
    if (shot_.empty()) {
        log("screen capture failed");
        scanning_ = false;
        return;
    }
    worker_ = std::thread([this] {
        const auto t0 = std::chrono::steady_clock::now();
        found_ = scanner_.scan(shot_);
        scan_ms_ = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count();
        PostMessageW(hwnd_, WM_APP_SCAN_DONE, 0, 0);
    });
}

void App::scan_done() {
    if (worker_.joinable()) worker_.join();
    log("scan of " + std::to_string(shot_.width) + "x" + std::to_string(shot_.height) + " took " + ms_text(scan_ms_) +
        ", found " + std::to_string(found_.size()));
    for (const auto& d : found_) log("[" + payload_kind(d.text) + "] " + summarize(d.text, 200) + "  (" + d.step + ")");
    if (found_.empty()) {
        POINT p;
        GetCursorPos(&p);
        CardOptions o;
        o.timeout_ms = 1200;
        show_card(instance_, "", "No QR code found on screen", p, o);
        scanning_ = false;
        return;
    }
    if (found_.size() == 1) {
        take(found_.front(), false);
        scanning_ = false;
        return;
    }
    picker_open_ = true;
    show_picker(instance_, shot_, shot_area_, found_, hwnd_);
    scanning_ = false;
}

void App::picked(int index, bool open) {
    picker_open_ = false;
    if (index < 0 || index >= static_cast<int>(found_.size())) return;
    take(found_[index], open);
}

void App::take(const Detection& det, bool open) {
    // Copy always; open only when asked, and only a plain web link.
    copy_to_clipboard(hwnd_, det.text);
    if (open && open_link(det.text)) {
        set_tooltip("UniQR - opened " + summarize(det.text, 60));
        return;
    }
    const Box b = det.bbox();
    const POINT at{shot_area_.left + b.left, shot_area_.top + b.top + b.height + 14};
    const std::string heading = det.symbology == "QR Code" ? "Copied" : "Copied \xC2\xB7 " + det.symbology;
    const std::string text = det.text;
    show_card(instance_, det.text, heading, at, CardOptions{}, [this, text] {
        if (open_link(text)) set_tooltip("UniQR - opened " + summarize(text, 60));
    });
    set_tooltip("UniQR - copied " + summarize(det.text, 60));
}

void App::toggle_autostart() {
    const bool turn_on = !autostart_enabled();
    const std::string hk = options_.hotkey.empty() || !hotkey_ ? "" : canonical_hotkey(*hotkey_);
    if (set_autostart(turn_on, hk)) log(std::string("start at login is now ") + (turn_on ? "on" : "off"));
    else log("could not change start at login");
}

void App::report_problem() {
    const std::string url = issue_url(UNIQR_CPP_VERSION, windows_version(), "%LOCALAPPDATA%\\UniQR\\uniqr-cpp.log");
    log("opening the report page");
    if (!open_link(url)) {
        copy_to_clipboard(hwnd_, url);
        POINT p;
        GetCursorPos(&p);
        show_card(instance_, "", "Could not open your browser. The report page address is on your clipboard.", p);
    }
}

LRESULT CALLBACK App::window_proc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
    if (msg == WM_NCCREATE) {
        auto* self = static_cast<App*>(reinterpret_cast<CREATESTRUCTW*>(lp)->lpCreateParams);
        SetWindowLongPtrW(hwnd, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(self));
        self->hwnd_ = hwnd;
    }
    auto* self = reinterpret_cast<App*>(GetWindowLongPtrW(hwnd, GWLP_USERDATA));
    return self ? self->handle(msg, wp, lp) : DefWindowProcW(hwnd, msg, wp, lp);
}

LRESULT App::handle(UINT msg, WPARAM wp, LPARAM lp) {
    if (msg == taskbar_created_ && taskbar_created_ != 0) {  // Explorer restarted
        add_tray_icon();
        set_tooltip(hotkey_ ? "UniQR - press " + shown_hotkey(hotkey_->label) + " to scan" : "UniQR");
        return 0;
    }
    switch (msg) {
        case WM_HOTKEY:
            if (wp == kHotkeyId) start_scan();
            return 0;
        case WM_APP_TRAY:
            if (LOWORD(lp) == WM_LBUTTONUP) start_scan();
            else if (LOWORD(lp) == WM_RBUTTONUP || LOWORD(lp) == WM_CONTEXTMENU) show_menu();
            return 0;
        case WM_APP_SCAN_DONE:
            scan_done();
            return 0;
        case WM_APP_PICKED:
            picked(static_cast<int>(static_cast<INT_PTR>(wp)), lp != 0);
            return 0;
        case WM_COMMAND:
            switch (LOWORD(wp)) {
                case kScanNow: start_scan(); break;
                case kAutostart: toggle_autostart(); break;
                case kReport: report_problem(); break;
                case kExit: DestroyWindow(hwnd_); break;
            }
            return 0;
        case WM_DESTROY:
            UnregisterHotKey(hwnd_, kHotkeyId);
            remove_tray_icon();
            log("UniQR is exiting");
            PostQuitMessage(0);
            return 0;
    }
    return DefWindowProcW(hwnd_, msg, wp, lp);
}

int App::run() {
    register_card_class(instance_);
    register_picker_class(instance_);
    if (!create_window()) {
        log("could not create the hidden window");
        return 3;
    }
    add_tray_icon();
    hotkey_ = register_hotkey();
    if (!hotkey_) log("Could not register any hotkey. UniQR still works: use the tray icon to scan.");
    greet();
    MSG m;
    while (GetMessageW(&m, nullptr, 0, 0) > 0) {
        TranslateMessage(&m);
        DispatchMessageW(&m);
    }
    return 0;
}

}  // namespace uniqr::win
