import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { L, UI } from "../theme";
import { KeyFace } from "./WinLogo";

// A row of keycaps that appear at `from` and press down one after another,
// to show the hotkey being pressed. This is a video annotation, not app UI.

export const Keys: React.FC<{
  keys: string[];
  from: number;
  hold?: number; // frames to stay up after the last key goes down
  size?: number;
  style?: React.CSSProperties;
}> = ({ keys, from, hold = 30, size = 64, style }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const local = frame - from;
  const enter = spring({ frame: local, fps, config: { damping: 16 } });
  const end = 10 + keys.length * 5 + hold;
  const exit = interpolate(local, [end, end + 8], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  if (local < 0 || exit <= 0) return null;

  return (
    <div
      style={{
        position: "absolute",
        display: "flex",
        alignItems: "center",
        gap: size * 0.28,
        opacity: Math.min(enter, exit),
        transform: `translateY(${(1 - enter) * 30}px)`,
        fontFamily: UI,
        ...style,
      }}
    >
      {keys.map((k, i) => {
        const down = local >= 10 + i * 5;
        return (
          <React.Fragment key={k}>
            {i > 0 ? (
              <span style={{ color: L.sub, fontSize: size * 0.5, opacity: 0.7 }}>+</span>
            ) : null}
            <span
              style={{
                minWidth: size,
                height: size,
                padding: `0 ${size * 0.3}px`,
                boxSizing: "border-box",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                borderRadius: size * 0.18,
                background: down ? L.ink : "#ffffff",
                color: down ? "#ffffff" : L.ink,
                fontSize: size * 0.42,
                fontWeight: 700,
                boxShadow: down
                  ? `0 ${size * 0.03}px 0 #000000, 0 ${size * 0.2}px ${size * 0.5}px rgba(20,24,32,0.25)`
                  : `0 ${size * 0.1}px 0 #c3c8d2`,
                transform: `translateY(${down ? size * 0.07 : 0}px)`,
              }}
            >
              <KeyFace k={k} size={size * 0.42} />
            </span>
          </React.Fragment>
        );
      })}
    </div>
  );
};
