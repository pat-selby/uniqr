// The desktop app: a tray icon, a hotkey, and what happens when it is pressed.

#pragma once

#include <atomic>
#include <memory>
#include <optional>
#include <string>
#include <thread>
#include <vector>

#include "hotkeys.hpp"
#include "image.hpp"
#include "scanner.hpp"
#include "win.hpp"

namespace uniqr::win {

struct AppOptions {
    bool quiet = false;      // no card at start-up
    std::string hotkey;      // the person's own hotkey, or empty
};

class App {
public:
    App(HINSTANCE instance, AppOptions options);
    ~App();
    int run();  // the message loop; returns the exit code

private:
    static LRESULT CALLBACK window_proc(HWND, UINT, WPARAM, LPARAM);
    LRESULT handle(UINT msg, WPARAM wp, LPARAM lp);

    bool create_window();
    void add_tray_icon();
    void remove_tray_icon();
    void set_tooltip(const std::string& text);
    std::optional<Hotkey> register_hotkey();
    void show_menu();
    void greet();

    void start_scan();
    void scan_done();
    void picked(int index, bool open);
    void take(const Detection& det, bool open);
    void toggle_autostart();
    void report_problem();

    HINSTANCE instance_;
    AppOptions options_;
    HWND hwnd_ = nullptr;
    HICON icon_ = nullptr;
    UINT taskbar_created_ = 0;  // sent to every window when Explorer restarts
    std::optional<Hotkey> hotkey_;
    Scanner scanner_;

    // A scan runs on its own thread, so the tray and cards stay responsive.
    std::thread worker_;
    std::atomic<bool> scanning_{false};
    Image shot_;      // the screen the current scan is reading
    RECT shot_area_{};
    std::vector<Detection> found_;
    double scan_ms_ = 0;
    bool picker_open_ = false;
};

}  // namespace uniqr::win
