import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { Icon } from "./components/Icon";
import { InSquare } from "./components/OS";
import { SITE } from "./scenes/Outro";
import { C, HEIGHT, L, MONO, UI, WIDTH } from "./theme";
import { PLACED, Video } from "./Video";

// The same video in a square, for the LinkedIn feed. Every scene keeps its
// subject in the middle, so the wide frame is shown at one steady size, with
// bands above and below for the name, the use case, and the link.

export const SQUARE = 1080;
const SCALE = 0.7; // shows 1543 of the frame's 1920 pixels: the whole laptop
const WIDE_SCALE = 0.56; // the three laptops side by side need the full width
const WIDE_SCENES = ["platforms", "monitors"];

// What the bottom band says: the use case while one plays, else the link.
const BAND: Record<string, [string, string]> = {
  platforms: ["RUNS ON", "Windows, Mac and Linux"],
  class: ["USE CASE", "Online class"],
  call: ["USE CASE", "Team call"],
  monitors: ["WORKS ON", "Every monitor at once"],
  scam: ["USE CASE", "A scam email"],
  real: ["PROOF", "Real recording, on Windows"],
};
function bandAt(frame: number): [string, string] | null {
  const scene = [...PLACED].reverse().find((s) => frame >= s.start);
  return scene ? BAND[scene.name] ?? null : null;
}
const outroStart = PLACED.find((s) => s.name === "outro")?.start ?? Infinity;

export const Square: React.FC = () => {
  const frame = useCurrentFrame();
  const band = bandAt(frame);
  // The switch lands on a scene change, while the picture is faded out.
  const scene = [...PLACED].reverse().find((s) => frame >= s.start)?.name ?? "";
  const scale = WIDE_SCENES.includes(scene) ? WIDE_SCALE : SCALE;
  const BAND_H = (SQUARE - HEIGHT * scale) / 2;

  return (
    <AbsoluteFill style={{ background: L.stage }}>
      <div
        style={{
          position: "absolute",
          left: SQUARE / 2 - (WIDTH * scale) / 2,
          top: BAND_H,
          width: WIDTH,
          height: HEIGHT,
          transformOrigin: "0 0",
          transform: `scale(${scale})`,
        }}
      >
        <InSquare.Provider value={true}>
          <Video />
        </InSquare.Provider>
      </div>
      <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: BAND_H, display: "flex", alignItems: "center", justifyContent: "center", gap: 16, background: L.stage, fontFamily: UI, color: L.ink }}>
        <div style={{ padding: 8, borderRadius: 10, background: L.ink, display: "grid" }}>
          <Icon size={34} />
        </div>
        <span style={{ fontSize: 44, fontWeight: 800, letterSpacing: -1 }}>UniQR</span>
        <span style={{ fontSize: 26, color: L.sub, marginLeft: 6 }}>read any QR code on your screen</span>
      </div>
      <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: BAND_H, display: "flex", alignItems: "center", justifyContent: "center", background: L.stage, fontFamily: UI, fontSize: 30 }}>
        {band ? (
          <span style={{ color: L.ink, fontWeight: 600, display: "flex", gap: 14, alignItems: "center" }}>
            <span style={{ color: C.accent, fontWeight: 800, letterSpacing: 3, fontSize: 20 }}>{band[0]}</span>
            {band[1]}
          </span>
        ) : frame >= outroStart ? null : (
          <span style={{ fontFamily: MONO, color: L.sub }}>{SITE}</span>
        )}
      </div>
    </AbsoluteFill>
  );
};
