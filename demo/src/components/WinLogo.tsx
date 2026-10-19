import React from "react";

// The Windows key, drawn as the Windows logo: four blue squares. Same drawing
// as docs/windows-key.svg in the app (PR 33). Key caps show this, never "Win".
export const WinLogo: React.FC<{ size: number }> = ({ size }) => (
  <svg width={size} height={size} viewBox="0 0 88 88" role="img" aria-label="Windows key">
    <g fill="#0078D4">
      <rect width="41" height="41" />
      <rect x="47" width="41" height="41" />
      <rect y="47" width="41" height="41" />
      <rect x="47" y="47" width="41" height="41" />
    </g>
  </svg>
);

// A key cap's face: the logo for the Windows key, the name for anything else.
export const KeyFace: React.FC<{ k: string; size: number }> = ({ k, size }) =>
  k === "Win" ? <WinLogo size={size} /> : <>{k}</>;
