import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Card } from "../components/Card";
import { LightStage } from "../components/Laptop";
import { LinuxDesktop, MacDesktop, WinDesktop } from "../components/OS";
import { QRStyle, StyledQR } from "../components/StyledQR";
import { L, UI, WIDTH } from "../theme";
import { KeyFace } from "../components/WinLogo";
import { SceneProps, within } from "../timeline";

export const PLATFORMS = 150;

// "Windows, Mac, or Linux. And the hotkey is yours to change." Three laptops
// side by side; each reads a code with its own default hotkey (uniqr/hotkeys.py
// and shell_portable.py), and the keys light up as its card appears. Then the
// code keeps changing style, like the codes on adverts and slides (README, "the
// harder ones it also handles"), and each one is read again. Every code is real
// and holds its own address.

const MINI = 540; // screen width of each small laptop
const SCALE = MINI / WIDTH;
const SCREEN_H = Math.round(1080 * SCALE);
const GAP = 60;
const LEFT0 = (WIDTH - (3 * MINI + 2 * GAP)) / 2;
const TOP = 300;

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

// The window and code drawn on each screen, in that screen's 1920 x 1080 pixels.
const WINDOW = { x: 560, y: 150, w: 800, h: 520 };
const CODE = { left: WINDOW.x + 230, top: WINDOW.y + 90, size: 340 };

type Kind = { name: string; style: QRStyle };
const PLAIN: Kind = { name: "Plain", style: "plain" };
const OTHER: Kind[] = [
  { name: "Dark mode", style: "dark" },
  { name: "Dots", style: "dots" },
  { name: "Logo in the middle", style: "logo" },
  { name: "Colors", style: "color" },
  { name: "Gradient", style: "gradient" },
  { name: "Tilted", style: "tilted" },
];
const SWAP = 30; // frames between code changes
const RE_PRESS = 6; // frames after a change that the keys go down again

const SYSTEMS: { name: string; keys: string[]; desk: (c: React.ReactNode) => React.ReactNode }[] = [
  { name: "Windows", keys: ["Win", "Shift", "Q"], desk: (c) => <WinDesktop active={1}>{c}</WinDesktop> },
  { name: "Mac", keys: ["Cmd", "Shift", "8"], desk: (c) => <MacDesktop app="Viewer">{c}</MacDesktop> },
  { name: "Linux", keys: ["Ctrl", "Alt", "Q"], desk: (c) => <LinuxDesktop>{c}</LinuxDesktop> },
];

const Cap: React.FC<{ label: string; on: boolean }> = ({ label, on }) => (
  <span
    style={{
      minWidth: 52,
      height: 52,
      padding: "0 14px",
      boxSizing: "border-box",
      display: "inline-flex",
      alignItems: "center",
      justifyContent: "center",
      borderRadius: 10,
      fontFamily: UI,
      fontSize: 22,
      fontWeight: 700,
      background: on ? L.ink : "#ffffff",
      color: on ? "#ffffff" : L.ink,
      boxShadow: on ? "0 2px 0 #000000" : `0 5px 0 ${L.line}`,
      border: on ? "none" : `1px solid ${L.line}`,
      transform: `translateY(${on ? 4 : 0}px)`,
    }}
  >
    <KeyFace k={label} size={24} />
  </span>
);

export const Platforms: React.FC<SceneProps> = ({ t }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const at = [0.06, 0.24, 0.42].map((p) => within(t, 0, p, 20 + p * 100));
  const own = within(t, 0, 0.66, 110); // "the hotkey is yours to change"

  return (
    <LightStage>
      {SYSTEMS.map((sys, i) => {
        const x = LEFT0 + i * (MINI + GAP);
        const show = spring({ frame: frame - 4 - i * 4, fps, config: { damping: 15 } });
        // Change k (0 = the first QR code) starts at `since`; each laptop starts
        // its run of styles at a different place, so the three never match.
        const last = Math.floor((t.duration - 30 - at[i]) / SWAP); // no change in the scene's last second
        const k = Math.min(last, Math.max(0, Math.floor((frame - at[i]) / SWAP)));
        const since = at[i] + k * SWAP;
        const kind = k === 0 ? PLAIN : OTHER[(k - 1 + 2 * i) % OTHER.length];
        const press = k === 0 ? since : since + RE_PRESS;
        const card = interpolate(frame, [press + 8, press + 12], [0, 1], clamp);
        const pressed = frame >= press && frame < press + 12;
        const pop = k === 0 ? 1 : spring({ frame: frame - since, fps, config: { damping: 14 } });
        const label = frame >= at[i] ? interpolate(frame, [since, since + 6], [0, 1], clamp) : 0;
        const url = `https://example.com/on/${sys.name.toLowerCase()}${k === 0 ? "" : `/${kind.style}`}`;
        return (
          <div key={sys.name} style={{ position: "absolute", left: x, top: TOP, width: MINI, opacity: show, transform: `translateY(${(1 - show) * 30}px)` }}>
            <div style={{ position: "absolute", left: 0, right: 0, top: -62, textAlign: "center", fontFamily: UI, fontSize: 28, fontWeight: 700, color: L.sub, opacity: label, transform: `translateY(${(1 - label) * 8}px)` }}>
              {kind.name}
            </div>
            <div style={{ position: "absolute", left: -10, top: -10, width: MINI + 20, height: SCREEN_H + 20, borderRadius: 16, background: "linear-gradient(180deg,#2a2d33,#1b1d22)", boxShadow: "0 20px 44px rgba(20,24,32,0.22)" }} />
            <div style={{ position: "relative", width: MINI, height: SCREEN_H, overflow: "hidden", borderRadius: 4 }}>
              <div style={{ position: "absolute", left: 0, top: 0, width: WIDTH, height: 1080, transform: `scale(${SCALE})`, transformOrigin: "0 0" }}>
                {sys.desk(
                  <>
                    <div style={{ position: "absolute", left: WINDOW.x, top: WINDOW.y, width: WINDOW.w, height: WINDOW.h, background: "#fff", borderRadius: 18, boxShadow: "0 20px 60px rgba(0,0,0,0.35)" }} />
                    <div style={{ position: "absolute", left: CODE.left, top: CODE.top, opacity: Math.min(1, pop * 1.5), transform: `scale(${0.85 + 0.15 * pop})` }}>
                      <StyledQR text={url} style={kind.style} size={CODE.size} />
                    </div>
                    <Card
                      scale={2.6}
                      kind="Link"
                      status="Copied"
                      host="example.com"
                      rest={url.slice("https://example.com".length)}
                      style={{ left: CODE.left - 60, top: CODE.top + CODE.size + 40, opacity: card }}
                    />
                  </>,
                )}
              </div>
            </div>
            <div style={{ position: "absolute", left: -26, top: SCREEN_H + 10, width: MINI + 52, height: 18, borderRadius: "0 0 14px 14px", background: "linear-gradient(180deg,#d9dce1,#b9bdc4)" }} />
            <div style={{ position: "absolute", left: 0, right: 0, top: SCREEN_H + 60, display: "flex", flexDirection: "column", alignItems: "center", gap: 18, fontFamily: UI }}>
              <div style={{ fontSize: 40, fontWeight: 800, color: L.ink }}>{sys.name}</div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                {sys.keys.map((k, j) => (
                  <React.Fragment key={k}>
                    {j > 0 ? <span style={{ color: L.sub, fontSize: 20 }}>+</span> : null}
                    <Cap label={k} on={pressed} />
                  </React.Fragment>
                ))}
              </div>
            </div>
          </div>
        );
      })}
      <AbsoluteFill style={{ pointerEvents: "none" }}>
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            top: 830,
            textAlign: "center",
            fontFamily: UI,
            fontSize: 34,
            fontWeight: 600,
            color: L.sub,
            opacity: interpolate(frame, [own, own + 10], [0, 1], clamp),
          }}
        >
          Or set your own hotkey.
        </div>
      </AbsoluteFill>
    </LightStage>
  );
};
