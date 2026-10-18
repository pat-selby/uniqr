import React from "react";
import { AbsoluteFill } from "remotion";
import { C, UI } from "../theme";
import { Icon } from "./Icon";

// A made-up desktop: a plain wallpaper, one window, and a taskbar with the
// UniQR icon in the tray. Nothing here comes from a real screen.

export const TASKBAR = 64;

export const Desktop: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AbsoluteFill
    style={{
      background:
        "radial-gradient(circle at 20% 15%, #2d4a7a 0%, transparent 45%)," +
        "radial-gradient(circle at 85% 80%, #3b2f6b 0%, transparent 50%)," +
        "linear-gradient(135deg, #18233b 0%, #0f1626 100%)",
      fontFamily: UI,
    }}
  >
    {children}
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        bottom: 0,
        height: TASKBAR,
        background: "rgba(20, 26, 40, 0.92)",
        borderTop: "1px solid rgba(255,255,255,0.08)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 14,
      }}
    >
      {[0, 1, 2, 3, 4].map((i) => (
        <div
          key={i}
          style={{
            width: 38,
            height: 38,
            borderRadius: 9,
            background: i === 2 ? "#3a4a6a" : "#2a3550",
          }}
        />
      ))}
      <div
        style={{
          position: "absolute",
          right: 24,
          display: "flex",
          alignItems: "center",
          gap: 18,
          color: "#c9d3e8",
          fontSize: 17,
        }}
      >
        <Icon size={24} />
        <span>10:24</span>
      </div>
    </div>
  </AbsoluteFill>
);

// A plain app window with a title bar and an optional address bar.
export const Window: React.FC<{
  x: number;
  y: number;
  w: number;
  h: number;
  title: string;
  address?: string;
  children: React.ReactNode;
}> = ({ x, y, w, h, title, address, children }) => (
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
      boxShadow: "0 30px 80px rgba(0,0,0,0.5)",
      border: "1px solid rgba(255,255,255,0.12)",
      display: "flex",
      flexDirection: "column",
    }}
  >
    <div
      style={{
        height: 46,
        background: "#e9edf4",
        display: "flex",
        alignItems: "center",
        padding: "0 18px",
        gap: 16,
        color: "#3a4560",
        fontSize: 17,
        flexShrink: 0,
      }}
    >
      <span style={{ fontWeight: 600 }}>{title}</span>
      {address ? (
        <span
          style={{
            flex: 1,
            background: "#ffffff",
            borderRadius: 16,
            padding: "5px 16px",
            color: "#55607a",
            fontSize: 16,
          }}
        >
          {address}
        </span>
      ) : (
        <span style={{ flex: 1 }} />
      )}
      <span style={{ letterSpacing: 22, color: "#6a7590" }}>– ☐ ✕</span>
    </div>
    <div style={{ position: "relative", flex: 1 }}>{children}</div>
  </div>
);

export const Stage: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AbsoluteFill
    style={{
      background:
        `radial-gradient(circle at 50% 35%, #16233d 0%, ${C.stage} 65%)`,
      fontFamily: UI,
      color: C.cardFg,
    }}
  >
    {children}
  </AbsoluteFill>
);
