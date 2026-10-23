"""Pack UniQR for the Microsoft Store, as an MSIX package.

    python tools/build_exe.py --store
    python tools/build_msix.py

The first line builds the program as a folder, dist/store/UniQR. This one wraps
it, with a manifest and icons, into dist/store/UniQR-<version>.msix, the file
uploaded to Partner Center. The Store signs it; nothing here needs a
certificate. Windows only: makeappx.exe comes with the Windows SDK.

The package's identity has to match what Partner Center reserved for the app.
Its three values come from the environment, and from Partner Center's
"Product identity" page:

  STORE_IDENTITY_NAME         Package/Identity/Name
  STORE_PUBLISHER             Package/Identity/Publisher, which starts CN=
  STORE_PUBLISHER_DISPLAY     Package/Properties/PublisherDisplayName

Left unset, test values are used. Such a package installs on a test machine
(signed with a matching test certificate) but the Store would refuse it.

What the manifest declares:

  runFullTrust     UniQR is an ordinary desktop program, not a sandboxed app.
                   It reads the screen and hears a hotkey like the downloaded
                   exe does.
  a startup task   start at login, off until the person turns it on in
                   Settings > Apps > Startup. A Store app may not use the
                   registry entry the downloaded exe writes. See uniqr/store.py.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from uniqr import __version__  # noqa: E402
from uniqr.icon import _draw  # noqa: E402
from uniqr.store import APP_ID  # noqa: E402

PROGRAM = ROOT / "dist" / "store" / "UniQR"
STAGE = ROOT / "build" / "msix"
TEST_NAME = "UniQR.Test"
TEST_PUBLISHER = "CN=UniQR Test"

MANIFEST = """<?xml version="1.0" encoding="utf-8"?>
<Package
  xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"
  xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10"
  xmlns:desktop="http://schemas.microsoft.com/appx/manifest/desktop/windows10"
  xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"
  IgnorableNamespaces="uap desktop rescap">
  <Identity Name={name} Publisher={publisher} Version={version} ProcessorArchitecture="x64" />
  <Properties>
    <DisplayName>UniQR</DisplayName>
    <PublisherDisplayName>{publisher_display}</PublisherDisplayName>
    <Logo>Assets\\StoreLogo.png</Logo>
  </Properties>
  <Dependencies>
    <TargetDeviceFamily Name="Windows.Desktop" MinVersion="10.0.17763.0" MaxVersionTested="10.0.26100.0" />
  </Dependencies>
  <Resources>
    <Resource Language="en-us" />
  </Resources>
  <Applications>
    <Application Id="{app_id}" Executable="UniQR\\UniQR.exe" EntryPoint="Windows.FullTrustApplication">
      <uap:VisualElements
        DisplayName="UniQR"
        Description="Read any QR code on your screen with a hotkey."
        BackgroundColor="transparent"
        Square150x150Logo="Assets\\Square150x150Logo.png"
        Square44x44Logo="Assets\\Square44x44Logo.png">
        <uap:DefaultTile Wide310x150Logo="Assets\\Wide310x150Logo.png" />
      </uap:VisualElements>
      <Extensions>
        <desktop:Extension Category="windows.startupTask" Executable="UniQR\\UniQR.exe" EntryPoint="Windows.FullTrustApplication">
          <desktop:StartupTask TaskId="UniQRStartup" Enabled="false" DisplayName="UniQR" />
        </desktop:Extension>
      </Extensions>
    </Application>
  </Applications>
  <Capabilities>
    <rescap:Capability Name="runFullTrust" />
  </Capabilities>
</Package>
"""

# The sizes the manifest names. The Store also asks for screenshots and a
# listing logo, which are uploaded in Partner Center, not packed here.
ICONS = {"StoreLogo": (50, 50), "Square44x44Logo": (44, 44), "Square150x150Logo": (150, 150), "Wide310x150Logo": (310, 150)}


def package_version() -> str:
    """The Store wants four numbers and the last one 0: 0.2.8 becomes 0.2.8.0."""
    parts = [int(p) for p in __version__.split(".")[:3]]
    return ".".join(str(p) for p in [*parts, 0])


def manifest(name: str, publisher: str, publisher_display: str) -> str:
    return MANIFEST.format(
        name=quoteattr(name),
        publisher=quoteattr(publisher),
        version=quoteattr(package_version()),
        publisher_display=escape(publisher_display),
        app_id=APP_ID,
    )


def write_icons(folder: Path) -> None:
    from PIL import Image

    folder.mkdir(parents=True, exist_ok=True)
    for name, (width, height) in ICONS.items():
        side = min(width, height)
        icon = _draw(side * 4).resize((side, side), Image.LANCZOS)
        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        canvas.paste(icon, ((width - side) // 2, (height - side) // 2))
        canvas.save(folder / f"{name}.png")


def find_makeappx() -> Path:
    kits = Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Windows Kits" / "10" / "bin"
    found = sorted(kits.glob("10.*/x64/makeappx.exe"))
    if not found:
        raise SystemExit("makeappx.exe not found. Install the Windows SDK.")
    return found[-1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", type=Path, default=ROOT / "dist" / "store")
    args = parser.parse_args()
    if sys.platform != "win32":
        print("Store packages are made on Windows.", file=sys.stderr)
        return 1
    if not (PROGRAM / "UniQR.exe").exists():
        print("Build the program first: python tools/build_exe.py --store", file=sys.stderr)
        return 1

    name = os.environ.get("STORE_IDENTITY_NAME") or TEST_NAME
    publisher = os.environ.get("STORE_PUBLISHER") or TEST_PUBLISHER
    publisher_display = os.environ.get("STORE_PUBLISHER_DISPLAY") or "UniQR"
    if name == TEST_NAME:
        print("No STORE_IDENTITY_NAME: using test values. The Store would refuse this package.")

    shutil.rmtree(STAGE, ignore_errors=True)
    shutil.copytree(PROGRAM, STAGE / "UniQR")
    write_icons(STAGE / "Assets")
    (STAGE / "AppxManifest.xml").write_text(manifest(name, publisher, publisher_display), encoding="utf-8")

    args.out.mkdir(parents=True, exist_ok=True)
    package = args.out / f"UniQR-{package_version()}.msix"
    subprocess.run([str(find_makeappx()), "pack", "/o", "/d", str(STAGE), "/p", str(package)], check=True)
    print(f"Built {package}  ({package.stat().st_size / 1_000_000:.0f} MB, identity {name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
