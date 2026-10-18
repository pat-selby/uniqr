import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { C, HEIGHT, UI, WIDTH, pt } from "../theme";

// The picker from uniqr/overlay.py: the whole screen dimmed, each code left
// bright with a margin, an outline and a numbered badge, and the hint line.

const DIM = 0.38; // the screen keeps 38% of its brightness
export type Box = { left: number; top: number; size: number };

export const Picker: React.FC<{ boxes: Box[]; from: number; scale?: number }> = ({
  boxes,
  from,
  scale: S = 1.5,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pad = 10 * S;
  const dim = interpolate(frame, [from, from + 8], [0, 1 - DIM], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const n = boxes.length;

  return (
    <AbsoluteFill style={{ zIndex: 40 }}>
      <svg width={WIDTH} height={HEIGHT} style={{ position: "absolute" }}>
        <defs>
          <mask id="picker-holes">
            <rect width={WIDTH} height={HEIGHT} fill="white" />
            {boxes.map((b, i) => (
              <rect key={i} x={b.left - pad} y={b.top - pad} width={b.size + 2 * pad} height={b.size + 2 * pad} fill="black" />
            ))}
          </mask>
        </defs>
        <rect width={WIDTH} height={HEIGHT} fill="black" opacity={dim} mask="url(#picker-holes)" />
      </svg>
      {boxes.map((b, i) => {
        const pop = spring({ frame: frame - from - 2 - i * 5, fps, config: { damping: 12 } });
        const r = 15 * S;
        return (
          <React.Fragment key={i}>
            <div
              style={{
                position: "absolute",
                left: b.left - 1.5 * S,
                top: b.top - 1.5 * S,
                width: b.size + 3 * S,
                height: b.size + 3 * S,
                boxSizing: "border-box",
                border: `${3 * S}px solid ${C.accent}`,
                opacity: Math.min(1, pop * 2),
              }}
            />
            <div
              style={{
                position: "absolute",
                left: b.left - 6 * S - r,
                top: b.top - 6 * S - r,
                width: 2 * r,
                height: 2 * r,
                borderRadius: r,
                background: C.accent,
                color: C.badgeText,
                fontFamily: UI,
                fontWeight: 700,
                fontSize: pt(12) * S,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                transform: `scale(${pop})`,
              }}
            >
              {i + 1}
            </div>
          </React.Fragment>
        );
      })}
      <div
        style={{
          position: "absolute",
          top: 28 * S - pt(12) * S * 0.7,
          left: 0,
          right: 0,
          textAlign: "center",
          color: C.cardFg,
          fontFamily: UI,
          fontSize: pt(12) * S,
          whiteSpace: "pre",
          opacity: interpolate(frame, [from + 4, from + 12], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        {`${n} QR codes found  -  hover to inspect, press 1-${Math.min(n, 9)} to copy, Esc to cancel`}
      </div>
    </AbsoluteFill>
  );
};
