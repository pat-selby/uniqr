import React, { useMemo } from "react";
import bwipjs from "bwip-js/browser";

// A real QR code drawn in the styles marketing codes use (README, "the harder
// ones it also handles"): dots, rounded blocks with a logo in the middle, light
// on dark, colors on a colored background, a gradient, or tilted. bwip-js gives
// the module grid; this draws it.

export type QRStyle = "plain" | "dark" | "dots" | "logo" | "color" | "gradient" | "tilted";

const QUIET = 3;

const LOOK: Record<QRStyle, { fg: string; bg: string; finder: number }> = {
  plain: { fg: "#111826", bg: "#ffffff", finder: 0 },
  dark: { fg: "#e8eefc", bg: "#0b1220", finder: 0 },
  dots: { fg: "#111826", bg: "#ffffff", finder: 3.5 },
  logo: { fg: "#3b1f6e", bg: "#ffffff", finder: 1.6 },
  color: { fg: "#0f5a4f", bg: "#fbe7a1", finder: 1.6 },
  gradient: { fg: "url(#qr-gradient)", bg: "#ffffff", finder: 1.6 },
  tilted: { fg: "#111826", bg: "#ffffff", finder: 0 },
};

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
  const { fg, bg, finder } = LOOK[style];
  const inFinder = (x: number, y: number) =>
    (x < 7 && y < 7) || (x >= n - 7 && y < 7) || (x < 7 && y >= n - 7);
  const logo = style === "logo" ? { from: Math.floor(n / 2) - 3, to: Math.floor(n / 2) + 3 } : null;
  const inLogo = (x: number, y: number) => !!logo && x >= logo.from && x <= logo.to && y >= logo.from && y <= logo.to;
  const round = style === "logo" || style === "color" || style === "gradient";

  const modules: React.ReactNode[] = [];
  for (let y = 0; y < n; y++) {
    for (let x = 0; x < n; x++) {
      if (!grid.pixs[y * n + x] || inFinder(x, y) || inLogo(x, y)) continue;
      const cx = x + QUIET;
      const cy = y + QUIET;
      if (style === "dots") {
        modules.push(<circle key={`${x},${y}`} cx={cx + 0.5} cy={cy + 0.5} r={0.42} fill={fg} />);
      } else if (round) {
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
    return (
      <g key={`${fx},${fy}`}>
        <rect x={x + 0.5} y={y + 0.5} width={6} height={6} rx={finder * 0.86} fill="none" stroke={fg} strokeWidth={1} />
        <rect x={x + 2} y={y + 2} width={3} height={3} rx={finder * 0.43} fill={fg} />
      </g>
    );
  });

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${total} ${total}`}
      style={{ display: "block", borderRadius: size * 0.06, transform: style === "tilted" ? "rotate(-16deg)" : undefined }}
    >
      <defs>
        <linearGradient id="qr-gradient" gradientUnits="userSpaceOnUse" x1={0} y1={0} x2={total} y2={total}>
          <stop offset="0" stopColor="#6d28d9" />
          <stop offset="1" stopColor="#e2541b" />
        </linearGradient>
      </defs>
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
          <circle cx={(logo.from + logo.to) / 2 + QUIET + 0.5} cy={(logo.from + logo.to) / 2 + QUIET + 0.5} r={1.6} fill="#ffffff" />
        </g>
      ) : null}
    </svg>
  );
};
