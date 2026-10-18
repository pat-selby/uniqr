import React from "react";
import { Easing, interpolate, useCurrentFrame } from "remotion";

// A mouse pointer that glides between points. `path` is a list of
// [frame, x, y] stops; between stops it eases, and it holds at the ends.

export type Stop = [number, number, number];

export const Cursor: React.FC<{ path: Stop[]; size?: number; visibleFrom?: number }> = ({
  path,
  size = 34,
  visibleFrom = 0,
}) => {
  const frame = useCurrentFrame();
  if (frame < visibleFrom) return null;
  const frames = path.map((p) => p[0]);
  const opts = {
    extrapolateLeft: "clamp" as const,
    extrapolateRight: "clamp" as const,
    easing: Easing.inOut(Easing.cubic),
  };
  const x = path.length > 1 ? interpolate(frame, frames, path.map((p) => p[1]), opts) : path[0][1];
  const y = path.length > 1 ? interpolate(frame, frames, path.map((p) => p[2]), opts) : path[0][2];
  const opacity = interpolate(frame, [visibleFrom, visibleFrom + 6], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <svg
      width={size}
      height={size * 1.5}
      viewBox="0 0 16 24"
      style={{
        position: "absolute",
        left: x,
        top: y,
        opacity,
        filter: "drop-shadow(0 2px 3px rgba(0,0,0,0.5))",
        zIndex: 50,
      }}
    >
      <path
        d="M1 1 L1 19 L5.5 14.8 L8.6 22 L11.4 20.8 L8.4 13.8 L14.5 13.8 Z"
        fill="#ffffff"
        stroke="#000000"
        strokeWidth="1.1"
        strokeLinejoin="round"
      />
    </svg>
  );
};
