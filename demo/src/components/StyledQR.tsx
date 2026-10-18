import React, { useMemo } from "react";
import bwipjs from "bwip-js/browser";

// A real QR code drawn in the styles marketing codes use: dots, rounded
// blocks, a logo in the middle, or light on dark. bwip-js gives the module
// grid; this draws it. The benchmark covers each of these styles.

export type QRStyle = "dots" | "rounded" | "logo" | "dark";

const QUIET = 3;

export const StyledQR: React.FC<{ text: string; style: QRStyle; size: number }> = ({ text, style, size }) => {
  const grid = useMemo(() => {
    const [sym] = bwipjs.raw({ bcid: "qrcode", text, eclevel: style === "logo" ? "H" : "M" } as Parameters<typeof bwipjs.raw>[0]) as unknown as {
      pixs: number[];
      pixx: number;
    }[];
    return sym;
  }, [text, style]);

  const n = grid.pixx;
  const total = n + QUIET * 2;
  const dark = style === "dark";
  const fg = dark ? "#e8eefc" : style === "logo" ? "#3b1f6e" : "#111826";
  const bg = dark ? "#0b1220" : "#ffffff";
  const inFinder = (x: number, y: number) =>
    (x < 7 && y < 7) || (x >= n - 7 && y < 7) || (x < 7 && y >= n - 7);
  const logo = style === "logo" ? { from: Math.floor(n / 2) - 3, to: Math.floor(n / 2) + 3 } : null;
  const inLogo = (x: number, y: number) => !!logo && x >= logo.from && x <= logo.to && y >= logo.from && y <= logo.to;

  const modules: React.ReactNode[] = [];
  for (let y = 0; y < n; y++) {
    for (let x = 0; x < n; x++) {
      if (!grid.pixs[y * n + x] || inFinder(x, y) || inLogo(x, y)) continue;
      const cx = x + QUIET;
      const cy = y + QUIET;
      if (style === "dots") {
        modules.push(<circle key={`${x},${y}`} cx={cx + 0.5} cy={cy + 0.5} r={0.42} fill={fg} />);
      } else if (style === "rounded" || style === "logo") {
        modules.push(<rect key={`${x},${y}`} x={cx + 0.05} y={cy + 0.05} width={0.9} height={0.9} rx={0.32} fill={fg} />);
      } else {
        modules.push(<rect key={`${x},${y}`} x={cx} y={cy} width={1.02} height={1.02} fill={fg} />);
      }
    }
  }

  const finders = [
    [0, 0],
    [n - 7, 0],
    [0, n - 7],
  ].map(([fx, fy]) => {
    const x = fx + QUIET;
    const y = fy + QUIET;
    const round = style === "dark" ? 0 : style === "dots" ? 3.5 : 1.6;
    return (
      <g key={`${fx},${fy}`}>
        <rect x={x + 0.5} y={y + 0.5} width={6} height={6} rx={round * 0.86} fill="none" stroke={fg} strokeWidth={1} />
        <rect x={x + 2} y={y + 2} width={3} height={3} rx={round * 0.43} fill={fg} />
      </g>
    );
  });

  return (
    <svg width={size} height={size} viewBox={`0 0 ${total} ${total}`} style={{ display: "block", borderRadius: size * 0.06 }}>
      <rect width={total} height={total} fill={bg} />
      {modules}
      {finders}
      {logo ? (
        <g>
          <rect
            x={logo.from + QUIET + 0.3}
            y={logo.from + QUIET + 0.3}
            width={logo.to - logo.from + 0.4}
            height={logo.to - logo.from + 0.4}
            rx={1.4}
            fill="#ff7a45"
          />
          <text
            x={(logo.from + logo.to) / 2 + QUIET + 0.5}
            y={(logo.from + logo.to) / 2 + QUIET + 1.9}
            textAnchor="middle"
            fontSize={4.4}
            fontWeight={800}
            fill="#fff"
            fontFamily="Segoe UI, Arial, sans-serif"
          >
            ☕
          </text>
        </g>
      ) : null}
    </svg>
  );
};
