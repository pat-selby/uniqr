#include "report.hpp"

#include <cctype>

namespace uniqr {

std::string percent_encode(std::string_view text) {
    static const char* hex = "0123456789ABCDEF";
    std::string out;
    for (const char ch : text) {
        const auto c = static_cast<unsigned char>(ch);
        if (std::isalnum(c) || c == '-' || c == '.' || c == '_' || c == '~') {
            out += static_cast<char>(c);
        } else {
            out += '%';
            out += hex[c >> 4];
            out += hex[c & 15];
        }
    }
    return out;
}

std::string issue_body(std::string_view version, std::string_view system, std::string_view log) {
    std::string body;
    body += "**What happened?**\n";
    body += "(Say what you did and what went wrong, in a sentence or two.)\n\n";
    body += "**What did you expect to happen?**\n\n";
    body += "**Can you make it happen again? How?**\n\n";
    body += "---\n";
    body += "UniQR " + std::string(version) + " (C++ version) on " + std::string(system) + "\n\n";
    body += "The log can help, but it may contain links you scanned. Look through it ";
    body += "and paste only what you are happy to share.\n";
    body += "Log: " + std::string(log) + "\n";
    return body;
}

std::string issue_url(std::string_view version, std::string_view system, std::string_view log) {
    return std::string(kNewIssue) + "?body=" + percent_encode(issue_body(version, system, log));
}

}  // namespace uniqr
