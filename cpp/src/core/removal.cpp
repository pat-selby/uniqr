#include "removal.hpp"

namespace uniqr {

std::string removal_script(const std::vector<std::string>& files, const std::vector<std::string>& folders,
                           const std::string& exe) {
    // chcp: cmd reads the script in the console code page, and the file is UTF-8.
    std::vector<std::string> lines = {"@echo off", "chcp 65001 >nul", "set tries=0"};
    if (!exe.empty()) {
        // The exe stays locked for a moment after UniQR quits, so retry for up
        // to half a minute. ping is the sleep: `timeout` refuses to run without
        // a console.
        const std::string quoted = "\"" + exe + "\"";
        lines.insert(lines.end(), {
                                      ":retry",
                                      "del /f /q " + quoted + " >nul 2>&1",
                                      "if not exist " + quoted + " goto files",
                                      "set /a tries+=1",
                                      "if %tries% geq 30 goto files",
                                      "ping -n 2 127.0.0.1 >nul",
                                      "goto retry",
                                      ":files",
                                  });
    } else {
        lines.push_back("ping -n 3 127.0.0.1 >nul");
    }
    for (const auto& f : files) lines.push_back("del /f /q \"" + f + "\" >nul 2>&1");
    for (const auto& d : folders) lines.push_back("rmdir \"" + d + "\" >nul 2>&1");
    // Deletes itself. The (goto) first stops cmd from complaining it vanished.
    lines.push_back("(goto) 2>nul & del /f /q \"%~f0\"");
    std::string out;
    for (const auto& line : lines) out += line + "\r\n";
    return out;
}

}  // namespace uniqr
