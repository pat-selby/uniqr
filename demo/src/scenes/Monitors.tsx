import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Code } from "../components/Code";
import { Keys } from "../components/Keys";
import { LightStage } from "../components/Laptop";
import { UseCase, WinDesktop } from "../components/OS";
import { C, HEIGHT, UI, WIDTH } from "../theme";
import { SceneProps, cue, within } from "../timeline";

export const MONITORS = 120;

// "Two monitors?" / "It scans every screen at once." One keypress captures the
// whole desktop, every monitor (capture.virtual_screen() in the app), so the
// picker numbers the codes on both screens together.

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

const SCREEN_W = 780;
const SCALE = SCREEN_W / WIDTH;
const SCREEN_H = Math.round(HEIGHT * SCALE);
const MON = [
  { x: 150, y: 200 },
  { x: WIDTH - 150 - SCREEN_W, y: 200 },
];
// Each screen's window and code, in that screen's 1920 x 1080 pixels.
const WINDOWS = [
  { x: 260, y: 150, w: 1400, h: 720, title: "Workshop sign-up", code: { left: 1040, top: 300, size: 420 }, url: "https://example.com/screens/one" },
  { x: 260, y: 150, w: 1400, h: 720, title: "Demo repo", code: { left: 1040, top: 300, size: 420 }, url: "https://example.org/screens/two" },
];
// Where each code lands in the video frame.
const BOXES = WINDOWS.map((w, i) => ({
  left: MON[i].x + w.code.left * SCALE,
  top: MON[i].y + w.code.top * SCALE,
  size: w.code.size * SCALE,
}));

export const Monitors: React.FC<SceneProps> = ({ t }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const KEYS_AT = within(t, 0, 0.6, 20);
  const PICK = cue(t, 1, 50) + 4; // "It scans every screen at once"
  const dim = interpolate(frame, [PICK, PICK + 8], [0, 0.62], clamp);
  const pad = 8;

  return (
    <AbsoluteFill>
      <LightStage>
        {MON.map((m, i) => (
          <React.Fragment key={i}>
            {/* stand */}
            <div style={{ position: "absolute", left: m.x + SCREEN_W / 2 - 34, top: m.y + SCREEN_H + 12, width: 68, height: 110, background: "linear-gradient(180deg,#c9ccd2,#aeb2ba)" }} />
            <div style={{ position: "absolute", left: m.x + SCREEN_W / 2 - 150, top: m.y + SCREEN_H + 118, width: 300, height: 18, borderRadius: 9, background: "#b9bdc4", boxShadow: "0 10px 24px rgba(20,24,32,0.18)" }} />
            {/* bezel */}
            <div style={{ position: "absolute", left: m.x - 14, top: m.y - 14, width: SCREEN_W + 28, height: SCREEN_H + 28, borderRadius: 18, background: "linear-gradient(180deg,#2a2d33,#1b1d22)", boxShadow: "0 26px 60px rgba(20,24,32,0.25)" }} />
            {/* screen */}
            <div style={{ position: "absolute", left: m.x, top: m.y, width: SCREEN_W, height: SCREEN_H, overflow: "hidden", borderRadius: 4 }}>
              <div style={{ position: "absolute", left: 0, top: 0, width: WIDTH, height: HEIGHT, transform: `scale(${SCALE})`, transformOrigin: "0 0" }}>
                <WinDesktop active={1}>
                  <div style={{ position: "absolute", left: WINDOWS[i].x, top: WINDOWS[i].y, width: WINDOWS[i].w, height: WINDOWS[i].h, background: "#fff", borderRadius: 16, boxShadow: "0 20px 60px rgba(0,0,0,0.3)", fontFamily: UI, color: "#1b2333" }}>
                    <div style={{ position: "absolute", left: 90, top: 150, fontSize: 30, letterSpacing: 4, fontWeight: 700, color: "#b0552f" }}>{i === 0 ? "MONITOR 1" : "MONITOR 2"}</div>
                    <div style={{ position: "absolute", left: 90, top: 200, fontSize: 84, fontWeight: 800, width: 640, lineHeight: 1.05 }}>{WINDOWS[i].title}</div>
                  </div>
                  <div style={{ position: "absolute", left: WINDOWS[i].code.left, top: WINDOWS[i].code.top }}>
                    <Code bcid="qrcode" text={WINDOWS[i].url} width={WINDOWS[i].code.size} color="#1b2333" />
                  </div>
                </WinDesktop>
              </div>
            </div>
          </React.Fragment>
        ))}
        {/* The picker: one overlay over both screens, each code left bright. */}
        <svg width={WIDTH} height={HEIGHT} style={{ position: "absolute", left: 0, top: 0 }}>
          <defs>
            <mask id="two-monitors">
              {MON.map((m, i) => (
                <rect key={i} x={m.x} y={m.y} width={SCREEN_W} height={SCREEN_H} fill="white" />
              ))}
              {BOXES.map((b, i) => (
                <rect key={i} x={b.left - pad} y={b.top - pad} width={b.size + 2 * pad} height={b.size + 2 * pad} fill="black" />
              ))}
            </mask>
          </defs>
          <rect width={WIDTH} height={HEIGHT} fill="black" opacity={dim} mask="url(#two-monitors)" />
        </svg>
        {frame >= PICK
          ? BOXES.map((b, i) => {
              const pop = spring({ frame: frame - PICK - 2 - i * 6, fps, config: { damping: 12 } });
              return (
                <React.Fragment key={i}>
                  <div style={{ position: "absolute", left: b.left - 2, top: b.top - 2, width: b.size + 4, height: b.size + 4, boxSizing: "border-box", border: `4px solid ${C.accent}`, opacity: Math.min(1, pop * 2) }} />
                  <div style={{ position: "absolute", left: b.left - 24, top: b.top - 24, width: 38, height: 38, borderRadius: 19, background: C.accent, color: C.badgeText, fontFamily: UI, fontWeight: 700, fontSize: 22, display: "grid", placeItems: "center", transform: `scale(${pop})` }}>
                    {i + 1}
                  </div>
                </React.Fragment>
              );
            })
          : null}
      </LightStage>
      <Keys keys={["Win", "Shift", "Q"]} from={KEYS_AT} hold={14} size={72} style={{ left: 0, right: 0, top: 40, justifyContent: "center", zIndex: 70 }} />
      <UseCase label="Two monitors" opacity={interpolate(frame, [4, 14], [0, 1], clamp)} />
    </AbsoluteFill>
  );
};
