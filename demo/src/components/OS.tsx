import React, { createContext, useContext } from "react";
import { AbsoluteFill } from "remotion";
import { Platform, usePlatform } from "../platform";
import { C } from "../theme";
import { Icon } from "./Icon";

// Desktops in the style of Windows 11, macOS and a GNOME-style Linux, drawn
// from plain shapes: no logos, no screenshots, no real windows. Sizes are at 150% display scaling,
// so text reads on a phone and on a conference screen.

const WIN_FONT = '"Segoe UI Variable", "Segoe UI", system-ui, sans-serif';
const MAC_FONT = '-apple-system, "SF Pro Text", "Helvetica Neue", Arial, sans-serif';
const LINUX_FONT = '"Ubuntu", "Cantarell", "DejaVu Sans", system-ui, sans-serif';

export const WIN_TASKBAR = 72;
export const MAC_MENU = 36;
const MAC_DOCK = 108; // the dock and the gap under it
const LINUX_BAR = 44;

// -- Windows ----------------------------------------------------------------

const AppIcon: React.FC<{ color: string; glyph?: React.ReactNode; size?: number }> = ({
  color,
  glyph,
  size = 40,
}) => (
  <div
    style={{
      width: size,
      height: size,
      borderRadius: size * 0.22,
      background: color,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      color: "#fff",
      fontSize: size * 0.5,
      fontWeight: 700,
      boxShadow: "0 1px 2px rgba(0,0,0,0.3)",
    }}
  >
    {glyph}
  </div>
);

const TrayGlyph: React.FC<{ d: string; color?: string }> = ({ d, color = "#fff" }) => (
  <svg width={22} height={22} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.8} strokeLinecap="round">
    <path d={d} />
  </svg>
);

const WIFI = "M2 9a15 15 0 0 1 20 0M5 12.5a10 10 0 0 1 14 0M8.5 16a5 5 0 0 1 7 0M12 19.5h.01";
const SPEAKER = "M4 9v6h4l5 4V5L8 9H4zM16.5 8.5a5 5 0 0 1 0 7M19 6a8.5 8.5 0 0 1 0 12";
const BATTERY = "M3 8h15v8H3zM21 11v2M5 10h9v4H5z";

export const WinDesktop: React.FC<{ children?: React.ReactNode; active?: number }> = ({
  children,
  active = 1,
}) => (
  <AbsoluteFill
    style={{
      fontFamily: WIN_FONT,
      // A warm, photo-like landscape: evening sky, sun, and dunes.
      background:
        "radial-gradient(ellipse 60% 40% at 78% 112%, #9c6045 0%, #9c6045 60%, transparent 61%)," +
        "radial-gradient(ellipse 80% 45% at 18% 118%, #b8734f 0%, #b8734f 60%, transparent 61%)," +
        "radial-gradient(ellipse 120% 50% at 50% 125%, #d99a6c 0%, #d99a6c 60%, transparent 61%)," +
        "radial-gradient(circle at 70% 46%, #fff4d6 0%, #ffe2a8 5%, transparent 12%)," +
        "linear-gradient(180deg, #f3c9a0 0%, #f5d8b5 45%, #f2b98c 100%)",
    }}
  >
    {children}
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        bottom: 0,
        height: WIN_TASKBAR,
        background: "rgba(243, 243, 245, 0.92)",
        borderTop: "1px solid rgba(0,0,0,0.08)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 10,
      }}
    >
      {/* A generic start button: four soft tiles. */}
      <div style={{ width: 54, height: 54, display: "grid", placeItems: "center" }}>
        <div style={{ display: "grid", gridTemplateColumns: "15px 15px", gap: 3 }}>
          {[0, 1, 2, 3].map((i) => (
            <div key={i} style={{ width: 15, height: 15, borderRadius: 3, background: "linear-gradient(135deg,#7cc4ff,#2f7cf6)" }} />
          ))}
        </div>
      </div>
      <div
        style={{
          width: 230,
          height: 44,
          borderRadius: 22,
          background: "rgba(0,0,0,0.05)",
          color: "#4a4f5a",
          fontSize: 19,
          display: "flex",
          alignItems: "center",
          gap: 12,
          paddingLeft: 18,
          boxSizing: "border-box",
        }}
      >
        <TrayGlyph d="M10.5 17a6.5 6.5 0 1 1 0-13 6.5 6.5 0 0 1 0 13zM15.5 15.5 20 20" color="#4a4f5a" />
        Search
      </div>
      {[
        ["#f2b632", "▬"],
        ["#2f7cf6", "◉"],
        ["#0f6cbd", "✉"],
        ["#6264a7", "▶"],
        ["#d35230", "▤"],
      ].map(([color, glyph], i) => (
        <div key={i} style={{ width: 54, height: 54, borderRadius: 8, display: "grid", placeItems: "center", background: i === active ? "rgba(0,0,0,0.06)" : "transparent", position: "relative" }}>
          <AppIcon color={color} glyph={glyph} />
          {i === active ? (
            <div style={{ position: "absolute", bottom: 2, width: 18, height: 4, borderRadius: 2, background: "#2f7cf6" }} />
          ) : null}
        </div>
      ))}
      <div
        style={{
          position: "absolute",
          right: 18,
          display: "flex",
          alignItems: "center",
          gap: 16,
          color: "#1b1d22",
        }}
      >
        <span style={{ fontSize: 18, opacity: 0.7 }}>⌃</span>
        <Icon size={22} color="#1b1d22" />
        <TrayGlyph d={WIFI} color="#1b1d22" />
        <TrayGlyph d={SPEAKER} color="#1b1d22" />
        <TrayGlyph d={BATTERY} color="#1b1d22" />
        <div style={{ textAlign: "right", fontSize: 17, lineHeight: 1.25, marginLeft: 6 }}>
          10:24 AM
          <br />
          10/18/2026
        </div>
      </div>
    </div>
  </AbsoluteFill>
);

export const WinWindow: React.FC<{
  x: number;
  y: number;
  w: number;
  h: number;
  title: string;
  icon: string; // icon colour
  children: React.ReactNode;
}> = ({ x, y, w, h, title, icon, children }) => (
  <div
    style={{
      position: "absolute",
      left: x,
      top: y,
      width: w,
      height: h,
      borderRadius: 12,
      overflow: "hidden",
      background: "#ffffff",
      boxShadow: "0 32px 80px rgba(0,0,0,0.45), 0 0 0 1px rgba(0,0,0,0.25)",
      display: "flex",
      flexDirection: "column",
      fontFamily: WIN_FONT,
    }}
  >
    <div
      style={{
        height: 48,
        background: "#f3f3f3",
        display: "flex",
        alignItems: "center",
        paddingLeft: 16,
        gap: 12,
        color: "#1b1b1b",
        fontSize: 18,
        flexShrink: 0,
      }}
    >
      <AppIcon color={icon} size={22} />
      <span style={{ flex: 1 }}>{title}</span>
      {["─", "▢", "✕"].map((g) => (
        <span key={g} style={{ width: 69, textAlign: "center", fontSize: 17, color: "#333" }}>
          {g}
        </span>
      ))}
    </div>
    <div style={{ position: "relative", flex: 1 }}>{children}</div>
  </div>
);

// A browser in the same style: one tab, an address bar, then the page.
export const WinBrowser: React.FC<{
  x: number;
  y: number;
  w: number;
  h: number;
  tab: string;
  url: string;
  children: React.ReactNode;
}> = ({ x, y, w, h, tab, url, children }) => (
  <div
    style={{
      position: "absolute",
      left: x,
      top: y,
      width: w,
      height: h,
      borderRadius: 12,
      overflow: "hidden",
      background: "#ffffff",
      boxShadow: "0 32px 80px rgba(0,0,0,0.45), 0 0 0 1px rgba(0,0,0,0.25)",
      display: "flex",
      flexDirection: "column",
      fontFamily: WIN_FONT,
    }}
  >
    <div style={{ height: 50, background: "#dfe3ea", display: "flex", alignItems: "flex-end", paddingLeft: 12, flexShrink: 0 }}>
      <div
        style={{
          height: 40,
          width: 300,
          background: "#f7f8fa",
          borderRadius: "10px 10px 0 0",
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "0 14px",
          fontSize: 16,
          color: "#222",
        }}
      >
        <AppIcon color="#2f7cf6" size={18} />
        <span style={{ flex: 1, overflow: "hidden", whiteSpace: "nowrap" }}>{tab}</span>
        <span style={{ color: "#666" }}>✕</span>
      </div>
      <span style={{ fontSize: 22, color: "#555", margin: "0 0 8px 14px" }}>+</span>
      <span style={{ flex: 1 }} />
      {["─", "▢", "✕"].map((g) => (
        <span key={g} style={{ width: 69, textAlign: "center", fontSize: 17, color: "#333", alignSelf: "center" }}>
          {g}
        </span>
      ))}
    </div>
    <div
      style={{
        height: 54,
        background: "#f7f8fa",
        borderBottom: "1px solid #e3e6eb",
        display: "flex",
        alignItems: "center",
        gap: 18,
        padding: "0 18px",
        color: "#555",
        fontSize: 20,
        flexShrink: 0,
      }}
    >
      <span>←</span>
      <span style={{ opacity: 0.4 }}>→</span>
      <span>⟳</span>
      <div
        style={{
          flex: 1,
          height: 36,
          borderRadius: 18,
          background: "#eceff3",
          display: "flex",
          alignItems: "center",
          padding: "0 16px",
          gap: 10,
          fontSize: 17,
          color: "#333",
        }}
      >
        <span style={{ fontSize: 14 }}>🔒</span>
        {url}
      </div>
    </div>
    <div style={{ position: "relative", flex: 1 }}>{children}</div>
  </div>
);

// -- macOS ------------------------------------------------------------------

export const MacDesktop: React.FC<{ app: string; children?: React.ReactNode }> = ({ app, children }) => (
  <AbsoluteFill
    style={{
      fontFamily: MAC_FONT,
      background:
        "radial-gradient(ellipse at 20% 80%, #f29b4b 0%, transparent 45%)," +
        "radial-gradient(ellipse at 80% 30%, #7a4fd6 0%, transparent 55%)," +
        "radial-gradient(ellipse at 50% 60%, #e05a8a 0%, transparent 45%)," +
        "linear-gradient(160deg, #2a1a5e 0%, #12123a 100%)",
    }}
  >
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        right: 0,
        height: MAC_MENU,
        background: "rgba(30, 20, 60, 0.35)",
        backdropFilter: "blur(20px)",
        display: "flex",
        alignItems: "center",
        gap: 26,
        padding: "0 22px",
        color: "#fff",
        fontSize: 19,
        zIndex: 5,
      }}
    >
      <span style={{ fontSize: 20 }}>●</span>
      <span style={{ fontWeight: 700 }}>{app}</span>
      {["File", "Edit", "View", "Go", "Window", "Help"].map((m) => (
        <span key={m}>{m}</span>
      ))}
      <span style={{ flex: 1 }} />
      <TrayGlyph d={WIFI} />
      <TrayGlyph d={BATTERY} />
      <span>Sat Oct 18  10:24 AM</span>
    </div>
    {children}
    <div
      style={{
        position: "absolute",
        bottom: 12,
        left: "50%",
        transform: "translateX(-50%)",
        height: 96,
        padding: "0 14px",
        borderRadius: 28,
        background: "rgba(255,255,255,0.22)",
        border: "1px solid rgba(255,255,255,0.3)",
        backdropFilter: "blur(20px)",
        display: "flex",
        alignItems: "center",
        gap: 12,
      }}
    >
      {["#3b9bf5", "#4cd964", "#ff9500", "#ff3b30", "#af52de", "#5ac8fa", "#ffcc00", "#8e8e93"].map((c, i) => (
        <AppIcon key={i} color={c} size={70} />
      ))}
    </div>
  </AbsoluteFill>
);

export const MacWindow: React.FC<{
  x: number;
  y: number;
  w: number;
  h: number;
  title: string;
  children: React.ReactNode;
}> = ({ x, y, w, h, title, children }) => (
  <div
    style={{
      position: "absolute",
      left: x,
      top: y,
      width: w,
      height: h,
      borderRadius: 16,
      overflow: "hidden",
      background: "#ffffff",
      boxShadow: "0 36px 90px rgba(0,0,0,0.5), 0 0 0 1px rgba(0,0,0,0.25)",
      display: "flex",
      flexDirection: "column",
      fontFamily: MAC_FONT,
    }}
  >
    <div
      style={{
        height: 56,
        background: "#ececec",
        borderBottom: "1px solid #d6d6d6",
        display: "flex",
        alignItems: "center",
        padding: "0 20px",
        position: "relative",
        flexShrink: 0,
      }}
    >
      {["#ff5f57", "#febc2e", "#28c840"].map((c) => (
        <span key={c} style={{ width: 18, height: 18, borderRadius: 9, background: c, marginRight: 12 }} />
      ))}
      <span style={{ position: "absolute", left: 0, right: 0, textAlign: "center", fontSize: 19, fontWeight: 600, color: "#333", pointerEvents: "none" }}>
        {title}
      </span>
    </div>
    <div style={{ position: "relative", flex: 1 }}>{children}</div>
  </div>
);


// Safari in the same style: one toolbar with the window buttons, the arrows,
// and the address in the middle.
const MAC_TOOLBAR = 60;
export const MacBrowser: React.FC<{
  x: number;
  y: number;
  w: number;
  h: number;
  tab: string;
  url: string;
  children: React.ReactNode;
}> = ({ x, y, w, h, url, children }) => (
  <div
    style={{
      position: "absolute",
      left: x,
      top: y,
      width: w,
      height: h,
      borderRadius: 16,
      overflow: "hidden",
      background: "#ffffff",
      boxShadow: "0 36px 90px rgba(0,0,0,0.5), 0 0 0 1px rgba(0,0,0,0.25)",
      display: "flex",
      flexDirection: "column",
      fontFamily: MAC_FONT,
    }}
  >
    <div style={{ height: MAC_TOOLBAR, background: "#f2f2f4", borderBottom: "1px solid #d9d9dc", display: "flex", alignItems: "center", gap: 22, padding: "0 20px", color: "#6b6b70", fontSize: 26, flexShrink: 0, position: "relative" }}>
      <span style={{ display: "flex" }}>
        {["#ff5f57", "#febc2e", "#28c840"].map((c) => (
          <span key={c} style={{ width: 18, height: 18, borderRadius: 9, background: c, marginRight: 12 }} />
        ))}
      </span>
      <span>‹</span>
      <span style={{ opacity: 0.4 }}>›</span>
      <div style={{ position: "absolute", left: "50%", transform: "translateX(-50%)", width: 680, height: 38, borderRadius: 10, background: "#e4e4e8", display: "flex", alignItems: "center", justifyContent: "center", gap: 10, fontSize: 18, color: "#333" }}>
        <span style={{ fontSize: 14 }}>🔒</span>
        {url}
      </div>
    </div>
    <div style={{ position: "relative", flex: 1 }}>{children}</div>
  </div>
);

// -- Linux --------------------------------------------------------------------

// A generic Linux desktop: a dark top bar with the clock in the middle, a dock
// down the left side, and a calm wallpaper. No distribution's branding.
export const LinuxDesktop: React.FC<{ children?: React.ReactNode; dock?: boolean }> = ({ children, dock = true }) => (
  <AbsoluteFill
    style={{
      fontFamily: LINUX_FONT,
      background:
        "radial-gradient(ellipse at 75% 80%, #e8a463 0%, transparent 45%)," +
        "radial-gradient(ellipse at 20% 30%, #3f8f8a 0%, transparent 55%)," +
        "linear-gradient(160deg, #24575a 0%, #1d3b4a 100%)",
    }}
  >
    <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: LINUX_BAR, background: "#1b1b1d", color: "#f2f2f2", display: "flex", alignItems: "center", padding: "0 22px", fontSize: 20, zIndex: 5 }}>
      <span style={{ fontWeight: 600 }}>Activities</span>
      <span style={{ position: "absolute", left: "50%", transform: "translateX(-50%)", fontWeight: 600 }}>Sat 10:24</span>
      <span style={{ marginLeft: "auto", display: "flex", gap: 14 }}>
        <TrayGlyph d={WIFI} />
        <TrayGlyph d={SPEAKER} />
        <TrayGlyph d={BATTERY} />
      </span>
    </div>
    {dock ? (
      <div style={{ position: "absolute", top: LINUX_BAR, left: 0, bottom: 0, width: 92, background: "rgba(20,20,22,0.7)", display: "flex", flexDirection: "column", alignItems: "center", gap: 16, paddingTop: 20, zIndex: 4 }}>
        {["#e95420", "#3584e4", "#2ec27e", "#9141ac", "#f6d32d"].map((c, i) => (
          <AppIcon key={i} color={c} size={58} />
        ))}
      </div>
    ) : null}
    {children}
  </AbsoluteFill>
);


// GNOME-style window buttons: small round ones on the right of the header bar.
const LinuxButtons: React.FC = () => (
  <span style={{ display: "flex", gap: 12 }}>
    {["–", "□", "✕"].map((g) => (
      <span key={g} style={{ width: 28, height: 28, borderRadius: 14, background: "#dcdcdc", display: "grid", placeItems: "center", fontSize: 14, color: "#2e2e2e" }}>
        {g}
      </span>
    ))}
  </span>
);

const LINUX_HEADER = 52;
export const LinuxWindow: React.FC<{
  x: number;
  y: number;
  w: number;
  h: number;
  title: string;
  icon: string;
  children: React.ReactNode;
}> = ({ x, y, w, h, title, children }) => (
  <div style={{ position: "absolute", left: x, top: y, width: w, height: h, borderRadius: "12px 12px 0 0", overflow: "hidden", background: "#ffffff", display: "flex", flexDirection: "column", fontFamily: LINUX_FONT }}>
    <div style={{ height: LINUX_HEADER, background: "#ebebeb", borderBottom: "1px solid #d5d5d5", display: "flex", alignItems: "center", justifyContent: "flex-end", padding: "0 16px", position: "relative", flexShrink: 0 }}>
      <span style={{ position: "absolute", left: 0, right: 0, textAlign: "center", fontSize: 19, fontWeight: 700, color: "#2e2e2e", pointerEvents: "none" }}>{title}</span>
      <LinuxButtons />
    </div>
    <div style={{ position: "relative", flex: 1 }}>{children}</div>
  </div>
);

// Firefox in the same style: a tab row with the window buttons, then the
// address bar.
const LINUX_TABS = 44;
const LINUX_ADDRESS = 50;
export const LinuxBrowser: React.FC<{
  x: number;
  y: number;
  w: number;
  h: number;
  tab: string;
  url: string;
  children: React.ReactNode;
}> = ({ x, y, w, h, tab, url, children }) => (
  <div style={{ position: "absolute", left: x, top: y, width: w, height: h, borderRadius: "12px 12px 0 0", overflow: "hidden", background: "#ffffff", display: "flex", flexDirection: "column", fontFamily: LINUX_FONT }}>
    <div style={{ height: LINUX_TABS, background: "#e3e3e6", display: "flex", alignItems: "flex-end", padding: "0 16px 0 10px", flexShrink: 0 }}>
      <div style={{ height: 36, width: 300, background: "#f9f9fb", borderRadius: "8px 8px 0 0", display: "flex", alignItems: "center", gap: 10, padding: "0 14px", fontSize: 16, color: "#222" }}>
        <AppIcon color="#e66000" size={18} />
        <span style={{ flex: 1, overflow: "hidden", whiteSpace: "nowrap" }}>{tab}</span>
        <span style={{ color: "#666" }}>✕</span>
      </div>
      <span style={{ fontSize: 22, color: "#555", margin: "0 0 6px 14px" }}>+</span>
      <span style={{ flex: 1 }} />
      <span style={{ alignSelf: "center" }}>
        <LinuxButtons />
      </span>
    </div>
    <div style={{ height: LINUX_ADDRESS, background: "#f9f9fb", borderBottom: "1px solid #e0e0e3", display: "flex", alignItems: "center", gap: 18, padding: "0 18px", color: "#555", fontSize: 20, flexShrink: 0 }}>
      <span>←</span>
      <span style={{ opacity: 0.4 }}>→</span>
      <span>⟳</span>
      <div style={{ flex: 1, height: 34, borderRadius: 6, background: "#ededf0", display: "flex", alignItems: "center", padding: "0 14px", gap: 10, fontSize: 17, color: "#333" }}>
        <span style={{ fontSize: 14 }}>🔒</span>
        {url}
      </div>
    </div>
    <div style={{ position: "relative", flex: 1 }}>{children}</div>
  </div>
);

// -- any system ---------------------------------------------------------------

// Where a window that fills the screen sits on each system, and how tall its
// title bar and a browser's bars are. Pages are laid out inside the window,
// so a code's place on screen is the window's corner plus its place inside.
export const FRAME: Record<Platform, { full: { x: number; y: number; w: number; h: number }; appBar: number; browserBar: number }> = {
  windows: { full: { x: 0, y: 0, w: 1920, h: 1080 - WIN_TASKBAR }, appBar: 48, browserBar: 104 },
  mac: { full: { x: 0, y: MAC_MENU, w: 1920, h: 1080 - MAC_MENU - MAC_DOCK }, appBar: 56, browserBar: MAC_TOOLBAR },
  linux: { full: { x: 0, y: LINUX_BAR, w: 1920, h: 1080 - LINUX_BAR }, appBar: LINUX_HEADER, browserBar: LINUX_TABS + LINUX_ADDRESS },
};

// The desktop of this cut's system. `full` is true when a window fills the
// screen, which hides the Linux dock the way GNOME does.
export const Desktop: React.FC<{ active?: number; app: string; full?: boolean; children?: React.ReactNode }> = ({ active, app, full = false, children }) => {
  const os = usePlatform();
  if (os === "mac") return <MacDesktop app={app}>{children}</MacDesktop>;
  if (os === "linux") return <LinuxDesktop dock={!full}>{children}</LinuxDesktop>;
  return <WinDesktop active={active}>{children}</WinDesktop>;
};

type WindowProps = { x: number; y: number; w: number; h: number; title: string; icon: string; children: React.ReactNode };
export const AppWindow: React.FC<WindowProps> = (props) => {
  const os = usePlatform();
  if (os === "mac") return <MacWindow {...props} />;
  if (os === "linux") return <LinuxWindow {...props} />;
  return <WinWindow {...props} />;
};

type BrowserProps = { x: number; y: number; w: number; h: number; tab: string; url: string; children: React.ReactNode };
export const Browser: React.FC<BrowserProps> = (props) => {
  const os = usePlatform();
  if (os === "mac") return <MacBrowser {...props} />;
  if (os === "linux") return <LinuxBrowser {...props} />;
  return <WinBrowser {...props} />;
};

// -- shared -----------------------------------------------------------------

// True inside the square cut, which shows the use case in its own band
// instead, since its crop would cut this tag off.
export const InSquare = createContext(false);

// A small "use case" tag in the corner, so a room can follow without captions.
export const UseCase: React.FC<{ label: string; opacity: number; kicker?: string }> = ({
  label,
  opacity,
  kicker = "USE CASE",
}) =>
  useContext(InSquare) ? null : (
  <div
    style={{
      position: "absolute",
      bottom: 104,
      left: 32,
      zIndex: 60,
      opacity,
      display: "flex",
      alignItems: "center",
      gap: 12,
      background: "rgba(11, 18, 32, 0.82)",
      border: `1px solid ${C.border}`,
      borderRadius: 14,
      padding: "10px 20px",
      fontFamily: WIN_FONT,
      color: C.cardFg,
      fontSize: 26,
      boxShadow: "0 10px 30px rgba(0,0,0,0.35)",
    }}
  >
    <span style={{ color: C.accent, fontWeight: 800, letterSpacing: 2, fontSize: 18 }}>{kicker}</span>
    <span style={{ fontWeight: 600 }}>{label}</span>
  </div>

  );
