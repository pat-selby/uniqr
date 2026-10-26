"""Screen capture on Wayland, through the desktop's screenshot portal.

Wayland does not let one app read another's pixels. The supported way is to
ask the desktop itself, through the XDG desktop portal over D-Bus
(org.freedesktop.portal.Screenshot). GNOME, KDE Plasma and most other Wayland
desktops provide it. The first time, the desktop asks the person whether
UniQR may take screenshots; after that it answers without asking.

It is only called when the hotkey or `--scan` asks for a scan, the same as the
capture on every other system. The desktop writes the screenshot to a file and
hands back its address. UniQR reads it and deletes it at once, so no picture of
the screen is left behind.

D-Bus is spoken with jeepney, a small pure-Python library with nothing to
compile, so the Linux build needs no system libraries for it.
"""

import os
import secrets
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

import numpy as np

BUS_NAME = "org.freedesktop.portal.Desktop"
OBJECT = "/org/freedesktop/portal/desktop"
SCREENSHOT = "org.freedesktop.portal.Screenshot"
REQUEST = "org.freedesktop.portal.Request"
TIMEOUT_S = 60.0  # the first request waits for the person to answer the desktop's question

# Response codes, from the portal specification.
OK, CANCELLED = 0, 1


class PortalError(Exception):
    """The portal is missing, refused, or answered with something unusable."""


def request_path(unique_name: str, token: str) -> str:
    """Where the portal will post its answer, per the Request specification.

    The sender's bus name, such as ":1.42", loses its colon and has dots turned
    into underscores.
    """
    sender = unique_name.lstrip(":").replace(".", "_")
    return f"{OBJECT}/request/{sender}/{token}"


def path_from_uri(uri: str) -> Path:
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        raise PortalError(f"the portal returned a non-file address: {uri}")
    return Path(url2pathname(parsed.path))  # undoes %20 and the like


def available() -> bool:
    """Whether this desktop offers the screenshot portal. Takes no screenshot."""
    try:
        from jeepney import DBusAddress, new_method_call
        from jeepney.io.blocking import open_dbus_connection
    except ImportError:
        return False
    try:
        with open_dbus_connection(bus="SESSION") as conn:
            props = DBusAddress(OBJECT, bus_name=BUS_NAME, interface="org.freedesktop.DBus.Properties")
            reply = conn.send_and_get_reply(
                new_method_call(props, "Get", "ss", (SCREENSHOT, "version")), timeout=5
            )
            return reply.header.message_type.name == "method_return"
    except Exception:  # noqa: BLE001 - no session bus, no portal: all mean "not available"
        return False


def screenshot() -> np.ndarray:
    """The whole desktop as a BGR image. Raises PortalError if it cannot."""
    import cv2

    try:
        from jeepney import DBusAddress, MatchRule, new_method_call
        from jeepney.bus_messages import message_bus
        from jeepney.io.blocking import open_dbus_connection
    except ImportError as exc:
        raise PortalError("the jeepney library is missing") from exc

    token = "uniqr" + secrets.token_hex(6)
    try:
        conn = open_dbus_connection(bus="SESSION")
    except Exception as exc:  # noqa: BLE001
        raise PortalError(f"no D-Bus session: {exc}") from exc
    with conn:
        path = request_path(conn.unique_name, token)
        rule = MatchRule(type="signal", interface=REQUEST, member="Response", path=path)
        with conn.filter(rule) as answers:
            # Subscribe before asking, or a quick answer could arrive unheard.
            conn.send_and_get_reply(message_bus.AddMatch(rule), timeout=5)
            portal = DBusAddress(OBJECT, bus_name=BUS_NAME, interface=SCREENSHOT)
            options = {"handle_token": ("s", token), "interactive": ("b", False)}
            reply = conn.send_and_get_reply(
                new_method_call(portal, "Screenshot", "sa{sv}", ("", options)), timeout=10
            )
            if reply.header.message_type.name != "method_return":
                raise PortalError(f"the screenshot portal refused: {reply.body}")
            try:
                signal = conn.recv_until_filtered(answers, timeout=TIMEOUT_S)
            except TimeoutError as exc:
                raise PortalError("the screenshot portal did not answer") from exc

    code, results = signal.body
    if code == CANCELLED:
        raise PortalError("the screenshot was cancelled or not allowed")
    if code != OK or "uri" not in results:
        raise PortalError(f"the screenshot portal answered {code}")
    file = path_from_uri(results["uri"][1])
    try:
        image = cv2.imread(str(file), cv2.IMREAD_COLOR)
    finally:
        # Ours, made just now for this scan: leave no picture of the screen behind.
        try:
            os.remove(file)
        except OSError:
            pass
    if image is None:
        raise PortalError(f"could not read the screenshot at {file}")
    return image
