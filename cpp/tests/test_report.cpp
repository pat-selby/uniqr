// "Report a problem": the pre-filled GitHub issue.

#include <doctest/doctest.h>

#include <string>

#include "report.hpp"

using namespace uniqr;

TEST_CASE("the address is a new issue on this project, with only a body") {
    const std::string url = issue_url("0.1.0", "Windows 10.0.26200", "%LOCALAPPDATA%\\UniQR\\uniqr-cpp.log");
    CHECK(url.rfind("https://github.com/pat-selby/uniqr/issues/new?body=", 0) == 0);
    CHECK(url.find('&') == std::string::npos);
    CHECK(url.size() < 2000);
}

TEST_CASE("the body asks the three questions and names the version and system") {
    const std::string body = issue_body("0.1.0", "Windows 10.0.26200", "LOG");
    CHECK(body.find("What happened?") != std::string::npos);
    CHECK(body.find("What did you expect to happen?") != std::string::npos);
    CHECK(body.find("Can you make it happen again?") != std::string::npos);
    CHECK(body.find("UniQR 0.1.0 (C++ version) on Windows 10.0.26200") != std::string::npos);
    CHECK(body.find("Log: LOG") != std::string::npos);
}

TEST_CASE("everything but letters, digits and -._~ is percent-encoded") {
    CHECK(percent_encode("a b/c?d=e&f") == "a%20b%2Fc%3Fd%3De%26f");
    CHECK(percent_encode("Az09-._~") == "Az09-._~");
    CHECK(percent_encode("\xC3\xA9") == "%C3%A9");  // UTF-8 bytes
    CHECK(percent_encode("\n") == "%0A");
}
