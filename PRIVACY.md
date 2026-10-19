# Privacy

UniQR reads your screen, so it should tell you exactly what leaves your computer.
Here is all of it.

## What never leaves

- Screenshots. UniQR looks at your screen only when you press the hotkey, and
  only in memory. It never saves or sends a picture.
- What you scan. Links, Wi-Fi passwords, contact cards and any other text in a
  code stay on your computer, on your clipboard.
- Who you are. No name, email, account or ID is ever sent.

## What can leave, and only if you say yes

**Update checks.** If you agree, once a day UniQR asks GitHub for the newest
version number. GitHub sees your internet address and the words `UniQR/` plus
your version. Nothing else is sent. Turn it off with the tray menu's "Check for
updates automatically".

**Usage counts.** If you agree, once a day UniQR sends a summary of the day
before to Aptabase, a privacy-first analytics service. The summary holds only
whole numbers:

- how many times UniQR started, and how many scans you made
- how many scans found nothing, one code, or several
- how long scans took, in bands: under 1 second, 1 to 2, 2 to 5, over 5
- how many codes of each kind turned up (QR, Data Matrix and so on)
- how many were links and how many were something else
- how many times you cancelled the picker or opened a link

It also sends the UniQR version and the name and version of your operating
system. It does not send your language or your computer's model. Each summary
gets a new random session number, so one day's summary can't be linked to the
next. Aptabase sees your internet address when the summary arrives, as any
server does.

The counts are kept in `usage.json`, next to UniQR's settings, where you can
read them. To see exactly what the next send would be:

```
UniQR.exe --show-usage
```

Turn it off with the tray menu's "Share anonymous usage counts". Turning it off
also deletes everything counted so far. UniQR asks once, on a start where no
other question is waiting, and doesn't count or send anything unless you say yes.

## Reporting a problem

"Report a problem" opens a GitHub issue page in your browser with your UniQR
version and system filled in. Nothing is sent until you read it and press
Submit yourself.
