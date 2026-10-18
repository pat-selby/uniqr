import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { Icon } from "../components/Icon";
import { Stage } from "../components/Desktop";
import { C } from "../theme";
import { SceneProps, Timing, cue } from "../timeline";

export const INTRO = 90;

// The frame the name lands on "That's UniQR", early in the line. The sound
// bed hits its impact here too.
export const reveal = (t: Timing) => {
  const start = cue(t, 0, 8);
  return start + Math.round(((t.ends[0] ?? start + 60) - start) * 0.16);
};

export const Intro: React.FC<SceneProps> = ({ t }) => {
  const frame = useCurrentFrame();
  const name = reveal(t);
  // A flash and a glow on the reveal, fading fast.
  const flash = interpolate(frame, [name - 2, name, name + 14], [0, 0.55, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const glow = interpolate(frame, [name, name + 6, name + 40], [1, 2.4, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const show = (from: number) => ({
    opacity: interpolate(frame, [from, from + 12], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }),
    transform: `translateY(${interpolate(frame, [from, from + 12], [16, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    })}px)`,
  });

  return (
    <Stage>
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 36,
        }}
      >
        <div
          style={{
            padding: 34,
            borderRadius: 40,
            background: C.cardBg,
            border: `2px solid ${C.border}`,
            boxShadow: `0 0 ${120 * glow}px ${C.accent}${glow > 1.2 ? "66" : "33"}`,
          }}
        >
          <Icon size={200} animate from={4} />
        </div>
        <div style={{ fontSize: 140, fontWeight: 700, letterSpacing: -2, ...show(name) }}>
          UniQR
        </div>
        <div style={{ fontSize: 46, color: C.muted, ...show(name + 24) }}>
          Read any QR code on your screen with one keypress.
        </div>
      </div>
      <div style={{ position: "absolute", inset: 0, background: "#dfeeff", opacity: flash }} />
    </Stage>
  );
};
