import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

// Fades a whole scene in from black and out again at its end.
export const Fade: React.FC<{ duration: number; edge?: number; children: React.ReactNode }> = ({
  duration,
  edge = 10,
  children,
}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, edge, duration - edge, duration], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return <AbsoluteFill style={{ opacity, background: "#000" }}>{children}</AbsoluteFill>;
};
