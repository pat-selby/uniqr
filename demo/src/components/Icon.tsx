import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

// The tray icon from uniqr/icon.py, on the same 8 x 8 grid: three corner
// squares and a few dots in the empty corner. `animate` builds it piece by
// piece, starting at frame `from`.

const FINDERS: [number, number][] = [
  [0.25, 0.25],
  [4.75, 0.25],
  [0.25, 4.75],
];
const DOTS: [number, number][] = [
  [5, 5],
  [6.25, 5],
  [5, 6.25],
  [6.25, 6.25],
  [5.6, 5.6],
];

export const Icon: React.FC<{
  size: number;
  color?: string;
  animate?: boolean;
  from?: number;
}> = ({ size, color = "#ffffff", animate = false, from = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pop = (delay: number) =>
    animate
      ? spring({ frame: frame - from - delay, fps, config: { damping: 14, stiffness: 160 } })
      : 1;

  return (
    <svg width={size} height={size} viewBox="0 0 8 8">
      <defs>
        <mask id="finder-hole">
          <rect x="0" y="0" width="3" height="3" fill="white" />
          <rect x="0.75" y="0.75" width="1.5" height="1.5" fill="black" />
        </mask>
      </defs>
      {FINDERS.map(([x, y], i) => {
        const s = pop(i * 5);
        return (
          <g
            key={i}
            transform={`translate(${x + 1.5} ${y + 1.5}) scale(${s}) translate(-1.5 -1.5)`}
            opacity={interpolate(s, [0, 0.3], [0, 1], { extrapolateRight: "clamp" })}
          >
            <rect width="3" height="3" fill={color} mask="url(#finder-hole)" />
          </g>
        );
      })}
      {DOTS.map(([x, y], i) => {
        const s = pop(16 + i * 3);
        return (
          <rect
            key={i}
            x={x + 0.4 - 0.4 * s}
            y={y + 0.4 - 0.4 * s}
            width={0.8 * s}
            height={0.8 * s}
            fill={color}
          />
        );
      })}
    </svg>
  );
};
