// "Report a problem": the address of a pre-filled GitHub issue. UniQR sends
// nothing itself; the person reads the form, changes it and submits it in their
// own browser. A port of uniqr/report.py.

#pragma once

#include <string>
#include <string_view>

namespace uniqr {

inline constexpr std::string_view kNewIssue = "https://github.com/pat-selby/uniqr/issues/new";
// The tray's "Send feedback": a new post in the project's Discussions.
inline constexpr std::string_view kFeedbackUrl = "https://github.com/pat-selby/uniqr/discussions/new?category=general";

// `system` names the operating system and its version, never the computer or
// the person. `log` is where the log lives, written without anyone's name.
std::string issue_body(std::string_view version, std::string_view system, std::string_view log);
std::string issue_url(std::string_view version, std::string_view system, std::string_view log);

// Percent-encode everything but letters, digits and -._~, as UTF-8 bytes.
std::string percent_encode(std::string_view text);

}  // namespace uniqr
