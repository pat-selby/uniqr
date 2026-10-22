// Uninstall: the batch file that removes UniQR once it has quit.
//
// The same script as the Python UniQR writes (uniqr/uninstall.py). A running
// program cannot delete itself on Windows, so this waits for the exe to come
// free, deletes it and UniQR's own files, removes each folder only if it is
// then empty, and deletes itself. Never a folder with what is inside.

#pragma once

#include <string>
#include <vector>

namespace uniqr {

// Paths are UTF-8. An empty `exe` skips the wait and the exe.
std::string removal_script(const std::vector<std::string>& files, const std::vector<std::string>& folders,
                           const std::string& exe);

}  // namespace uniqr
