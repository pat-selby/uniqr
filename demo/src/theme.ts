// The palette from uniqr/overlay.py (the C++ app in cpp/src/win/win.hpp uses
// the same values), so the video's card and picker match the real ones.
export const C = {
  accent: "#4ea1ff",
  accentHover: "#7ab8ff",
  badgeText: "#0b1220",
  cardBg: "#111826",
  cardFg: "#e8eefc",
  muted: "#8fa3c8",
  border: "#2a3752",
  raised: "#1c2740",
  buttonBg: "#1f2a40",
  buttonHover: "#2c3a58",
  ok: "#3fb27f",
  warn: "#e0a33e",
  tipBg: "#0b1220",
  // Video-only: the stage behind the scenes that are not a desktop.
  stage: "#0b1220",
};

// The light look: a soft off-white stage with dark type. UniQR's own blue
// stays on its card and badges only.
export const L = {
  stage: "#f1f2f4",
  stageEdge: "#e2e4e9",
  ink: "#15171c",
  sub: "#5c6370",
  line: "#d5d8de",
};

// The fonts the app asks for on Windows, with the macOS and Linux ones after.
export const UI = '"Segoe UI", "SF Pro Text", "DejaVu Sans", system-ui, sans-serif';
export const MONO = 'Consolas, Menlo, "DejaVu Sans Mono", monospace';

// Tk sizes are in points. At 96 dpi a point is 4/3 of a pixel.
export const pt = (points: number) => (points * 4) / 3;

export const FPS = 30;
export const WIDTH = 1920;
export const HEIGHT = 1080;
