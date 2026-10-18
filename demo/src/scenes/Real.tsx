import React from "react";
import { AbsoluteFill, Freeze, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame } from "remotion";
import { Stage } from "../components/Desktop";
import { Keys } from "../components/Keys";
import { C, UI } from "../theme";
import { SceneProps } from "../timeline";

// "Is it real?": a screen recording of the actual app, if there is one.
//
// Record UniQR on a clean desktop (nothing private on screen), save it as
// public/real.mp4, and this scene appears in the video. Git ignores the file.
// The clip plays muted, from its start, for REAL_FRAMES. The current clip is
// three pieces of one recording: the keypress and the numbered codes, the
// click on Open, and the site it opened (OPENED is where that starts).

export const REAL_FILE = "real.mp4";
export const REAL_FRAMES = 229;
export const REAL = 110 + REAL_FRAMES;
const PRESS = 14; // clip frame where the hotkey goes down
const OPENED = 175;

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

export const Real: React.FC<SceneProps> = ({ t }) => {
  const frame = useCurrentFrame();
  const start = (t.ends[1] ?? 80) + 4;
  // The frame is up from the start, paused on the clip's first frame, and plays
  // once the voice says "Here's the actual app".
  const show = interpolate(frame, [4, 16], [0, 1], clamp);

  return (
    <Stage>
      <AbsoluteFill style={{ display: "grid", placeItems: "center" }}>
        <div
          style={{
            width: 1600,
            height: 900,
            borderRadius: 22,
            overflow: "hidden",
            border: `2px solid ${C.border}`,
            boxShadow: `0 40px 100px rgba(0,0,0,0.6), 0 0 80px ${C.accent}22`,
            background: "#000",
            opacity: show,
            transform: `scale(${0.94 + 0.06 * show})`,
            position: "relative",
          }}
        >
          {frame < start ? (
            <Freeze frame={0}>
              <OffthreadVideo src={staticFile(REAL_FILE)} muted style={{ width: "100%", height: "100%", objectFit: "contain" }} />
            </Freeze>
          ) : (
            <Sequence from={start} layout="none">
              <OffthreadVideo src={staticFile(REAL_FILE)} muted style={{ width: "100%", height: "100%", objectFit: "contain" }} />
            </Sequence>
          )}
          <div
            style={{
              position: "absolute",
              top: 20,
              left: 20,
              display: "flex",
              alignItems: "center",
              gap: 10,
              background: "rgba(11,18,32,0.85)",
              borderRadius: 12,
              padding: "8px 16px",
              fontFamily: UI,
              color: C.cardFg,
              fontSize: 22,
              fontWeight: 700,
            }}
          >
            <span style={{ width: 14, height: 14, borderRadius: 7, background: "#e5383b" }} />
            Real recording, not an animation
          </div>
          {frame >= start + OPENED ? (
            <div
              style={{
                position: "absolute",
                bottom: 24,
                left: "50%",
                transform: "translateX(-50%)",
                background: C.accent,
                color: C.badgeText,
                fontFamily: UI,
                fontSize: 28,
                fontWeight: 800,
                borderRadius: 14,
                padding: "12px 24px",
                boxShadow: "0 10px 30px rgba(0,0,0,0.4)",
                opacity: interpolate(frame, [start + OPENED, start + OPENED + 6], [0, 1], clamp),
              }}
            >
              Clicked Open. The real site loaded.
            </div>
          ) : null}
        </div>
      </AbsoluteFill>
      <Keys keys={["Win", "Shift", "Q"]} from={start + PRESS - 12} hold={16} size={72} style={{ left: 0, right: 0, top: 30, justifyContent: "center", zIndex: 70 }} />
    </Stage>
  );
};
