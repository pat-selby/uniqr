import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { C, UI } from "../theme";

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
              <span style={{ color: C.cardFg, fontSize: size * 0.5, opacity: 0.7 }}>+</span>
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
                background: down ? C.accent : "#f2f5fb",
                color: down ? C.badgeText : "#1a2233",
                fontSize: size * 0.42,
                fontWeight: 700,
                boxShadow: down
                  ? `0 ${size * 0.03}px 0 #2b6fc0, 0 0 ${size * 0.5}px ${C.accent}66`
                  : `0 ${size * 0.1}px 0 #9aa6bd`,
                transform: `translateY(${down ? size * 0.07 : 0}px)`,
              }}
            >
              {k}
            </span>
          </React.Fragment>
        );
      })}
    </div>
  );
};
