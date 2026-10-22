// A plain-text log, so a person (or a smoke test) can see what UniQR did.
// %LOCALAPPDATA%\UniQR\uniqr-cpp.log, next to the Python version's own log.

#pragma once

#include <string>
#include <string_view>

namespace uniqr::win {

std::wstring log_path();
void log_start(std::string_view command_line);
void log(std::string_view line);

}  // namespace uniqr::win
