import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

// Fades a whole scene in from a plain color and out again at its end.
export const Fade: React.FC<{ duration: number; edge?: number; color?: string; children: React.ReactNode }> = ({
  duration,
  edge = 10,
  color = "#000",
  children,
}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, edge, duration - edge, duration], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill style={{ background: color }}>
      <AbsoluteFill style={{ opacity }}>{children}</AbsoluteFill>
    </AbsoluteFill>
  );
};
