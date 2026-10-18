import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Code } from "../components/Code";
import { Stage } from "../components/Desktop";
import { C, UI } from "../theme";
import { SceneProps, within } from "../timeline";

export const OPENER = 120;

// The cold open: a wall of real QR codes pops in, then every one gets the
// picker's blue outline and number in a wave, on "Your screen".

const COLS = 6;
const ROWS = 4;
const TILE = 170;
const GAP = 40;
const LEFT = (1920 - (COLS * TILE + (COLS - 1) * GAP)) / 2;
const TOP = (1080 - (ROWS * TILE + (ROWS - 1) * GAP)) / 2;

const TILES = Array.from({ length: COLS * ROWS }, (_, i) => {
  const col = i % COLS;
  const row = Math.floor(i / COLS);
  const x = LEFT + col * (TILE + GAP);
  const y = TOP + row * (TILE + GAP);
  // How far from the middle, so both waves start there and spread out.
  const d = Math.hypot(col - (COLS - 1) / 2, row - (ROWS - 1) / 2);
  return { i, x, y, d };
});

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

export const Opener: React.FC<SceneProps> = ({ t }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const BADGES = within(t, 0, 0.78, 80);
  const push = interpolate(frame, [0, t.duration], [1, 1.1]);

  return (
    <Stage>
      <AbsoluteFill style={{ transform: `scale(${push})` }}>
        {TILES.map(({ i, x, y, d }) => {
          const pop = spring({ frame: frame - 4 - d * 7, fps, config: { damping: 13, stiffness: 140 } });
          const mark = spring({ frame: frame - BADGES - d * 4, fps, config: { damping: 12 } });
          return (
            <div key={i} style={{ position: "absolute", left: x, top: y, width: TILE, height: TILE, transform: `scale(${pop})`, opacity: Math.min(1, pop * 1.5) }}>
              <div style={{ width: TILE, height: TILE, background: "#fff", borderRadius: 14, display: "grid", placeItems: "center", boxShadow: "0 12px 30px rgba(0,0,0,0.45)" }}>
                <Code bcid="qrcode" text={`https://example.com/everywhere/${i + 1}`} width={TILE - 30} />
              </div>
              <div style={{ position: "absolute", inset: 8, border: `4px solid ${C.accent}`, borderRadius: 6, opacity: Math.min(1, mark * 2) }} />
              <div
                style={{
                  position: "absolute",
                  left: -14,
                  top: -14,
                  width: 38,
                  height: 38,
                  borderRadius: 19,
                  background: C.accent,
                  color: C.badgeText,
                  fontFamily: UI,
                  fontWeight: 700,
                  fontSize: 20,
                  display: "grid",
                  placeItems: "center",
                  transform: `scale(${mark})`,
                }}
              >
                {i + 1}
              </div>
            </div>
          );
        })}
      </AbsoluteFill>
      {/* the screen dims around the codes as the picker would */}
      <AbsoluteFill style={{ background: "#000", opacity: interpolate(frame, [BADGES, BADGES + 10], [0, 0.25], clamp), pointerEvents: "none" }} />
    </Stage>
  );
};
