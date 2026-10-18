import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Stage } from "../components/Desktop";
import { Icon } from "../components/Icon";
import { C, MONO, UI } from "../theme";
import { SceneProps, cue, within } from "../timeline";

export const OUTRO = 150;

// The ending: "Try it out." and the one link to go to, the latest release.
export const RELEASES = "github.com/pat-selby/uniqr/releases/latest";

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

export const Outro: React.FC<SceneProps> = ({ t }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const mark = cue(t, 0, 6);
  const tryIt = within(t, 1, 0.45, 50);
  const big = spring({ frame: frame - tryIt, fps, config: { damping: 14 } });
  const link = interpolate(frame, [tryIt + 10, tryIt + 22], [0, 1], clamp);

  return (
    <Stage>
      <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", fontFamily: UI }}>
        <div style={{ display: "flex", alignItems: "center", gap: 22, opacity: interpolate(frame, [mark, mark + 10], [0, 1], clamp) }}>
          <Icon size={70} animate from={mark} />
          <span style={{ fontSize: 64, fontWeight: 700, color: C.cardFg, letterSpacing: -1 }}>UniQR</span>
        </div>
        <div style={{ fontSize: 170, fontWeight: 800, color: C.cardFg, letterSpacing: -5, marginTop: 30, opacity: big, transform: `scale(${0.85 + 0.15 * big})` }}>
          Try it out.
        </div>
        <div
          style={{
            marginTop: 40,
            fontFamily: MONO,
            fontSize: 50,
            color: C.accent,
            background: C.cardBg,
            border: `2px solid ${C.border}`,
            borderRadius: 18,
            padding: "18px 34px",
            opacity: link,
            transform: `translateY(${(1 - link) * 16}px)`,
            boxShadow: `0 0 60px ${C.accent}22`,
          }}
        >
          {RELEASES}
        </div>
      </div>
    </Stage>
  );
};
