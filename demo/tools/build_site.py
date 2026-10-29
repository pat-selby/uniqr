"""Build the landing page as a standalone site, ready for GitHub Pages.

site/index.html is written as page content without its own <html> and
<head> wrapper. This adds the wrapper and copies the web videos and poster in
next to it. There is one video per system; the page plays the visitor's.

site/download.html is the page a download button leads to. It becomes three
pages, download/windows/, download/mac/ and download/linux/, each with its
system set on <body>; the page shows that system's steps and starts its file.

Run from the demo folder, after `npm run render:web`, `render:web:mac`,
`render:web:linux` and a poster still:
    python tools/build_site.py
Writes out/site/: index.html, uniqr-demo.mp4 (Windows), uniqr-demo-mac.mp4,
uniqr-demo-linux.mp4, poster.jpg, and download/<system>/index.html.
"""

import shutil
from pathlib import Path

DEMO = Path(__file__).resolve().parent.parent
SRC = DEMO / "site" / "index.html"
DOWNLOAD = DEMO / "site" / "download.html"
OUT = DEMO / "out" / "site"
SYSTEMS = {"windows": "Windows", "mac": "Mac", "linux": "Linux"}

HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="UniQR reads any QR code on your laptop screen with one keypress. Free and open source for Windows, Mac and Linux.">
<style>body{margin:0}img,video{max-width:100%}[hidden]{display:none!important}</style>
"""


def wrap(page: str, body: str = "<body>") -> str:
    """Add <html> and <head>. Everything up to the end of the first <style>
    block belongs in <head>."""
    cut = page.index("</style>") + len("</style>")
    return HEAD + page[:cut] + "\n</head>\n" + body + "\n" + page[cut:].lstrip() + "\n</body>\n</html>\n"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "index.html").write_text(wrap(SRC.read_text(encoding="utf-8")), encoding="utf-8", newline="\n")
    thanks = DOWNLOAD.read_text(encoding="utf-8")
    for system, name in SYSTEMS.items():
        page = thanks.replace(
            "<title>Thanks for downloading UniQR</title>",
            f"<title>Thanks for downloading UniQR for {name}</title>",
        )
        folder = OUT / "download" / system
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "index.html").write_text(wrap(page, f'<body data-os="{system}">'), encoding="utf-8", newline="\n")
    for system in ["", "-mac", "-linux"]:
        shutil.copyfile(DEMO / "out" / f"uniqr-demo-web{system}.mp4", OUT / f"uniqr-demo{system}.mp4")
    shutil.copyfile(DEMO / "out" / "poster.jpg", OUT / "poster.jpg")
    for f in sorted(p for p in OUT.rglob("*") if p.is_file()):
        print(f"{f.relative_to(OUT).as_posix():28} {f.stat().st_size:>9,} bytes")


if __name__ == "__main__":
    main()
