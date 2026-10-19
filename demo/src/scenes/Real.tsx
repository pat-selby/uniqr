import React from "react";
import { AbsoluteFill, Freeze, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame } from "remotion";
import { Keys } from "../components/Keys";
import { Laptop } from "../components/Laptop";
import { UseCase } from "../components/OS";
import { C, UI } from "../theme";
import { SceneProps, cue } from "../timeline";

// "Is this real?": a screen recording of the actual app, if there is one.
//
// Record UniQR on a clean desktop (nothing private on screen), save it as
// public/real.mp4, and this scene appears in the video. Git ignores the file.
// The clip plays muted, for REAL_FRAMES. The current clip is three pieces of
// one recording: the keypress and the numbered codes, the click on Open, and
// the site it opened (OPENED is where that starts).

export const REAL_FILE = "real.mp4";
export const REAL_FRAMES = 229;
export const REAL = 60 + REAL_FRAMES;
const PRESS = 14; // clip frame where the hotkey goes down
const OPENED = 175;

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

export const Real: React.FC<SceneProps> = ({ t }) => {
  const frame = useCurrentFrame();
  // Paused on the first frame for "Is this real?", playing from the answer.
  const start = cue(t, 1, 50);
  const video = { width: "100%", height: "100%", objectFit: "cover" as const };

  return (
    <AbsoluteFill>
      <Laptop>
        {frame < start ? (
          <Freeze frame={0}>
            <OffthreadVideo src={staticFile(REAL_FILE)} muted style={video} />
          </Freeze>
        ) : (
          <Sequence from={start} layout="none">
            <OffthreadVideo src={staticFile(REAL_FILE)} muted style={video} />
          </Sequence>
        )}
      </Laptop>
      <Keys keys={["Win", "Shift", "Q"]} from={start + PRESS - 12} hold={16} size={72} style={{ left: 0, right: 0, top: 24, justifyContent: "center", zIndex: 70 }} />
      {frame >= start + OPENED ? (
        <div
          style={{
            position: "absolute",
            bottom: 70,
            left: "50%",
            transform: "translateX(-50%)",
            background: C.accent,
            color: C.badgeText,
            fontFamily: UI,
            fontSize: 30,
            fontWeight: 800,
            borderRadius: 14,
            padding: "12px 26px",
            whiteSpace: "nowrap",
            boxShadow: "0 10px 30px rgba(20,24,32,0.25)",
            opacity: interpolate(frame, [start + OPENED, start + OPENED + 6], [0, 1], clamp),
          }}
        >
          Clicked Open. The real site loaded.
        </div>
      ) : null}
      <UseCase kicker="PROOF" label="Real recording, on Windows" opacity={interpolate(frame, [4, 14], [0, 1], clamp)} />
    </AbsoluteFill>
  );
};
