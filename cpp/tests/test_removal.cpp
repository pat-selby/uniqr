// The uninstall script, held to the same cases as tests/test_uninstall.py.

#include <doctest/doctest.h>

#include <string>

#include "removal.hpp"

using uniqr::removal_script;

TEST_CASE("the script waits for the exe, then deletes only what UniQR wrote") {
    const std::string exe = R"(C:\Apps\uniqr-cpp.exe)";
    const std::string log = R"(C:\Users\a\AppData\Local\UniQR\uniqr-cpp.log)";
    const std::string folder = R"(C:\Users\a\AppData\Local\UniQR)";
    const std::string script = removal_script({log}, {folder}, exe);
    CHECK(script.find("del /f /q \"" + exe + "\"") != std::string::npos);
    CHECK(script.find("goto retry") != std::string::npos);
    CHECK(script.find("geq 30") != std::string::npos);
    CHECK(script.find("del /f /q \"" + log + "\"") != std::string::npos);
    CHECK(script.find("rmdir \"" + folder + "\"") != std::string::npos);
    CHECK(script.find("/s") == std::string::npos);  // never a folder with what is inside
    CHECK(script.find("\r\n") != std::string::npos);
    CHECK(script.rfind("(goto) 2>nul & del /f /q \"%~f0\"\r\n") == script.size() - 33);
}

TEST_CASE("without an exe there is nothing to wait for") {
    const std::string script = removal_script({"a.log"}, {}, "");
    CHECK(script.find(":retry") == std::string::npos);
    CHECK(script.find("del /f /q \"a.log\"") != std::string::npos);
}
