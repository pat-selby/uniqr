#include "system.hpp"  // brings windows.h first

#include <shellapi.h>

#include <cstdio>
#include <cstring>
#include <filesystem>

#include "link.hpp"
#include "log.hpp"
#include "removal.hpp"

namespace uniqr::win {

namespace {
constexpr wchar_t kRunKey[] = L"Software\\Microsoft\\Windows\\CurrentVersion\\Run";
}

bool copy_to_clipboard(HWND owner, std::string_view utf8) {
    const std::wstring text = widen(utf8);
    // Another program can hold the clipboard for a moment; try a few times.
    for (int attempt = 0; attempt < 10; ++attempt) {
        if (OpenClipboard(owner)) {
            EmptyClipboard();
            const size_t bytes = (text.size() + 1) * sizeof(wchar_t);
            HGLOBAL mem = GlobalAlloc(GMEM_MOVEABLE, bytes);
            bool ok = false;
            if (mem) {
                std::memcpy(GlobalLock(mem), text.c_str(), bytes);
                GlobalUnlock(mem);
                ok = SetClipboardData(CF_UNICODETEXT, mem) != nullptr;
                if (!ok) GlobalFree(mem);
            }
            CloseClipboard();
            return ok;
        }
        Sleep(20);
    }
    return false;
}

bool open_link(std::string_view url) {
    if (!can_open(url)) return false;
    const std::wstring w = widen(trim(url));
    const auto result = reinterpret_cast<INT_PTR>(ShellExecuteW(nullptr, L"open", w.c_str(), nullptr, nullptr, SW_SHOWNORMAL));
    return result > 32;
}

std::wstring exe_path() {
    std::wstring buf(MAX_PATH, L'\0');
    while (true) {
        const DWORD n = GetModuleFileNameW(nullptr, buf.data(), static_cast<DWORD>(buf.size()));
        if (n < buf.size()) {
            buf.resize(n);
            return buf;
        }
        buf.resize(buf.size() * 2);
    }
}

std::string windows_version() {
    // GetVersionEx lies to programs without a matching manifest; ntdll does not.
    using RtlGetVersionFn = LONG(WINAPI*)(OSVERSIONINFOW*);
    OSVERSIONINFOW v{sizeof(v)};
    if (HMODULE ntdll = GetModuleHandleW(L"ntdll.dll")) {
        if (auto fn = reinterpret_cast<RtlGetVersionFn>(GetProcAddress(ntdll, "RtlGetVersion"))) fn(&v);
    }
    return "Windows " + std::to_string(v.dwMajorVersion) + "." + std::to_string(v.dwMinorVersion) + "." +
           std::to_string(v.dwBuildNumber);
}

std::wstring autostart_command() {
    HKEY key = nullptr;
    if (RegOpenKeyExW(HKEY_CURRENT_USER, kRunKey, 0, KEY_QUERY_VALUE, &key) != ERROR_SUCCESS) return {};
    wchar_t buf[2048] = {};
    DWORD size = sizeof(buf), type = 0;
    const LSTATUS st = RegQueryValueExW(key, kRunValue, nullptr, &type, reinterpret_cast<BYTE*>(buf), &size);
    RegCloseKey(key);
    return st == ERROR_SUCCESS && type == REG_SZ ? std::wstring(buf) : std::wstring();
}

bool autostart_enabled() { return !autostart_command().empty(); }

bool set_autostart(bool on, std::string_view hotkey_canonical) {
    HKEY key = nullptr;
    if (RegCreateKeyExW(HKEY_CURRENT_USER, kRunKey, 0, nullptr, 0, KEY_SET_VALUE, nullptr, &key, nullptr) != ERROR_SUCCESS)
        return false;
    LSTATUS st;
    if (on) {
        // Quoted, so a path with spaces is one program, not a program and arguments.
        std::wstring command = L"\"" + exe_path() + L"\"";
        if (!hotkey_canonical.empty()) command += L" --hotkey " + widen(hotkey_canonical);
        st = RegSetValueExW(key, kRunValue, 0, REG_SZ, reinterpret_cast<const BYTE*>(command.c_str()),
                            static_cast<DWORD>((command.size() + 1) * sizeof(wchar_t)));
    } else {
        st = RegDeleteValueW(key, kRunValue);
        if (st == ERROR_FILE_NOT_FOUND) st = ERROR_SUCCESS;  // already off
    }
    RegCloseKey(key);
    return st == ERROR_SUCCESS;
}

bool schedule_removal() {
    namespace fs = std::filesystem;
    const fs::path log = log_path();
    fs::path old = log;
    old += L".1";
    // Only the C++ version's own files. The Python version shares the folder.
    const std::string script = removal_script({narrow(log.wstring()), narrow(old.wstring())},
                                              {narrow(log.parent_path().wstring())}, narrow(exe_path()));
    const fs::path where = fs::temp_directory_path() / L"uniqr-cpp-uninstall.cmd";
    FILE* f = nullptr;
    if (_wfopen_s(&f, where.c_str(), L"wb") != 0 || !f) return false;
    std::fwrite(script.data(), 1, script.size(), f);
    std::fclose(f);

    std::wstring command = L"cmd.exe /c \"" + where.wstring() + L"\"";
    STARTUPINFOW si{sizeof(si)};
    PROCESS_INFORMATION pi{};
    // A hidden console, not none: the script's chcp needs one.
    if (!CreateProcessW(nullptr, command.data(), nullptr, nullptr, FALSE, CREATE_NO_WINDOW, nullptr, nullptr, &si,
                        &pi))
        return false;
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    return true;
}

void message_box(std::string_view text, bool ok) {
    MessageBoxW(nullptr, widen(text).c_str(), L"UniQR", ok ? MB_ICONINFORMATION : MB_ICONERROR);
}

}  // namespace uniqr::win
