import React from "react";
import { AbsoluteFill, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame } from "remotion";
import { Stage } from "../components/Desktop";
import { C, UI } from "../theme";
import { SceneProps } from "../timeline";

// "Is it real?": a screen recording of the actual app, if there is one.
//
// Record UniQR on a clean desktop (nothing private on screen), save it as
// public/real.mp4, and this scene appears in the video. Git ignores the file.
// The clip plays muted, from its start, for REAL_SECONDS.

export const REAL_FILE = "real.mp4";
export const REAL_SECONDS = 8;
export const REAL = 110 + REAL_SECONDS * 30;

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

export const Real: React.FC<SceneProps> = ({ t }) => {
  const frame = useCurrentFrame();
  const start = (t.ends[1] ?? 80) + 4;
  const show = interpolate(frame, [start - 10, start + 4], [0, 1], clamp);

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
          <Sequence from={start} layout="none">
            <OffthreadVideo src={staticFile(REAL_FILE)} muted style={{ width: "100%", height: "100%", objectFit: "contain" }} />
          </Sequence>
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
        </div>
      </AbsoluteFill>
    </Stage>
  );
};
