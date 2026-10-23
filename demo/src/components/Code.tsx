import React, { useMemo } from "react";
import bwipjs from "bwip-js/browser";

// A real, scannable code drawn by bwip-js. Every code in the video holds a
// made-up example.com style address, so scanning a paused frame is safe.

export type Symbology =
  | "qrcode"
  | "microqrcode"
  | "rectangularmicroqrcode"
  | "datamatrix"
  | "azteccode"
  | "pdf417"
  | "maxicode";

export const Code: React.FC<{
  bcid: Symbology;
  text: string;
  width: number;
  color?: string;
  options?: Record<string, unknown>;
  style?: React.CSSProperties;
}> = ({ bcid, text, width, color, options, style }) => {
  const src = useMemo(() => {
    const svg = bwipjs.toSVG({
      bcid,
      text,
      scale: 4,
      ...(color ? { barcolor: color.replace("#", "") } : {}),
      ...options,
    } as Parameters<typeof bwipjs.toSVG>[0]);
    return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
  }, [bcid, text, color, options]);

  return <img src={src} style={{ width, display: "block", ...style }} />;
};
