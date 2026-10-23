import React from "react";

// A phone held up to the laptop with its camera open: the long way to scan a
// code that is already on your screen. `show` brings it up, `away` drops it.

export const PhoneCam: React.FC<{ show: number; away: number }> = ({ show, away }) => (
  <div
    style={{
      position: "absolute",
      left: 1380,
      top: 360,
      opacity: show * (1 - away),
      transform: `translate(${(1 - show) * 60}px, ${(1 - show) * 260 + away * 520}px) rotate(${7 + away * 12}deg)`,
      zIndex: 50,
    }}
  >
    <div
      style={{
        width: 250,
        height: 500,
        borderRadius: 42,
        background: "#111216",
        border: "7px solid #2b2e35",
        boxShadow: "0 40px 80px rgba(20,24,32,0.45)",
        display: "grid",
        placeItems: "center",
        position: "relative",
      }}
    >
      <div style={{ position: "absolute", top: 16, width: 70, height: 14, borderRadius: 7, background: "#000" }} />
      <svg width={160} height={160} viewBox="0 0 120 120">
        {["M8 34V8h26", "M86 8h26v26", "M112 86v26H86", "M34 112H8V86"].map((d) => (
          <path key={d} d={d} fill="none" stroke="#ffffff" strokeWidth={6} strokeLinecap="round" />
        ))}
        <rect x="38" y="38" width="44" height="44" rx="4" fill="none" stroke="#c9cdd5" strokeWidth={4} strokeDasharray="6 6" />
      </svg>
      <div style={{ position: "absolute", bottom: 40, width: 64, height: 64, borderRadius: 32, border: "5px solid #fff" }} />
    </div>
  </div>
);
