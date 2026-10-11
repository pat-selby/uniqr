# Code signing policy

UniQR is a free, open-source program that reads QR codes on your screen. This
page says how its Windows download, `UniQR.exe`, is built and signed, and who is
responsible for it.

## Status

**UniQR.exe is not signed yet.** The project has applied, or is about to apply,
for free code signing from SignPath Foundation. Until that is accepted, the file
is unsigned and Windows shows an "unknown publisher" warning when you run it.

This page will be updated when that changes. If it is out of date, the
[releases page](https://github.com/pat-selby/uniqr/releases) is the thing to
trust: a release that is signed will say so.

## Who signs it

Once approved, the signature on `UniQR.exe` will come from SignPath Foundation,
which means Windows will show **SignPath Foundation** as the publisher, not the
author's name. This line applies from that point:

Free code signing provided by [SignPath.io](https://signpath.io), certificate by
[SignPath Foundation](https://signpath.org)

## How the file is made

- `UniQR.exe` is built by [GitHub Actions](.github/workflows/windows-build.yml)
  from the public source in this repository, using
  [`tools/build_exe.py`](tools/build_exe.py). It is not built on anyone's own
  computer.
- Before it is kept, the workflow starts the built file and checks that it runs
  and exits cleanly.
- Every signing request is approved by hand before the file is signed. Nothing
  is signed automatically.
- The signing request is set up to expect this project's product name (UniQR)
  and the release version, so a file with different details is not signed.

## Team and roles

UniQR is maintained by one person.

| Role | Who | What it means |
|---|---|---|
| Author, committer and reviewer | Patrick Selby ([pat-selby](https://github.com/pat-selby)) | Writes and reviews the source code and the build scripts. |
| Approver | Patrick Selby ([pat-selby](https://github.com/pat-selby)) | Approves each signing request. |

One person holding both roles is allowed when there is only one maintainer. If
contributors join, their changes will be reviewed by the maintainer before they
are merged, and only the approver can approve signing.

## Privacy

UniQR does not send information anywhere. It looks at your screen only when you
press the hotkey, decodes any codes it finds on your own computer, and copies the
result to your clipboard. It makes no network connections. The one exception is
yours to choose: if you click **Open** on a web link, your browser opens that
link.

UniQR writes a log file on your own computer, so you can see what it did:

- Windows: `%LOCALAPPDATA%\UniQR\uniqr.log`
- macOS: `~/Library/Logs/UniQR/uniqr.log`
- Linux: `~/.local/state/uniqr/uniqr.log`

The log records the text of codes it reads, such as links. It is never uploaded.

## What the program changes on your computer

It writes the log file, and a small icon file under
`%LOCALAPPDATA%\UniQR` on Windows. It does not install anything, change system
settings, or start itself with Windows. If you choose to start it with Windows,
that is a shortcut you add yourself, and you remove it by deleting the shortcut.
To uninstall, delete `UniQR.exe`, and optionally the `UniQR` folder named above.

## Checking a signed file

After signing is active, you can check any copy of `UniQR.exe`:

1. Right-click the file, choose **Properties**, open the **Digital Signatures**
   tab, and confirm the signer is SignPath Foundation.
2. Or in PowerShell: `Get-AuthenticodeSignature .\UniQR.exe`

The release page also lists the file's SHA-256 fingerprint. You can compare it
with:

```
certutil -hashfile UniQR.exe SHA256
```

## Reporting a problem

If you think a copy of `UniQR.exe` is not what this page describes, **do not run
it**. Open an issue at
[github.com/pat-selby/uniqr/issues](https://github.com/pat-selby/uniqr/issues)
with the file's SHA-256 fingerprint and where you downloaded it.

## Other systems

SignPath signs the Windows file only. The Linux program has no signing step. A
Mac version is not built yet.
