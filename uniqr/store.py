"""Whether UniQR runs as a Microsoft Store app, and what changes when it does.

A Store app is installed from an MSIX package and has a "package identity".
Windows then takes over three jobs UniQR otherwise does itself:

  updates        the Store delivers new versions, so UniQR does not check GitHub
  uninstalling   Settings > Apps, or right-click in the Start menu, removes it
  start at login a switch in Settings > Apps > Startup, declared in the package
                 (tools/build_msix.py). A Store app may not add itself to the
                 registry list the downloaded exe uses.

Windows also keeps a Store app's files under AppData in the package's own
folder, so the log moves too. See log_path().
"""

import ctypes
import sys
from functools import cache

ERROR_INSUFFICIENT_BUFFER = 122
APP_ID = "UniQR"  # the Application Id in the package manifest


@cache
def family_name() -> str | None:
    """The package family name, like UniQR_abc123xyz, or None outside the Store."""
    if sys.platform != "win32":
        return None
    try:
        get = ctypes.windll.kernel32.GetCurrentPackageFamilyName
    except AttributeError:  # Windows older than 8
        return None
    length = ctypes.c_uint32(0)
    # Asked with no buffer, a packaged process answers "buffer too small" and the
    # size; any other process answers APPMODEL_ERROR_NO_PACKAGE.
    if get(ctypes.byref(length), None) != ERROR_INSUFFICIENT_BUFFER:
        return None
    buffer = ctypes.create_unicode_buffer(length.value)
    if get(ctypes.byref(length), buffer) != 0:
        return None
    return buffer.value


def packaged() -> bool:
    return family_name() is not None


def log_path() -> str:
    """Where a person finds the log of the Store app, written so it holds no name."""
    return f"%LOCALAPPDATA%\\Packages\\{family_name()}\\LocalCache\\Local\\UniQR\\uniqr.log"
