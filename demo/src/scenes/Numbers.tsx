import React from "react";
import { Easing, interpolate, useCurrentFrame } from "remotion";
import { Stage } from "../components/Desktop";
import { C, MONO } from "../theme";
import { SceneProps, cue, within } from "../timeline";

export const NUMBERS = 150;

// Every number here is measured:
//   part one from benchmarks/RESULTS.md (seed 7),
//   part two from the comparison table in cpp/README.md (seed 11).
// They are two separate runs, so they stay on separate screens.

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

export const Numbers: React.FC<SceneProps> = ({ t }) => {
  const frame = useCurrentFrame();
  // Count up on the benchmark line, zero on "Zero", C++ on "rebuilt in C++".
  // The benchmark line counts up and lands on "Zero wrong answers"; the C++
  // line brings the speed bars, which grow on "a median of 5 milliseconds".
  const SPLIT = cue(t, 2, 150) - 4;
  const COUNT = cue(t, 1, 20);
  const ZERO = within(t, 1, 0.7, COUNT + 90);
  const GROW = within(t, 2, 0.45, SPLIT + 30) - SPLIT;
  const first = interpolate(frame, [0, 10, SPLIT - 12, SPLIT], [0, 1, 1, 0], clamp);
  const second = interpolate(frame, [SPLIT, SPLIT + 12], [0, 1], clamp);

  return (
    <Stage>
      {frame < SPLIT ? (
        <Benchmark opacity={first} count={COUNT} zero={ZERO} />
      ) : (
        <Port opacity={second} frame={frame - SPLIT} grow={GROW} />
      )}
    </Stage>
  );
};

const Benchmark: React.FC<{ opacity: number; count: number; zero: number }> = ({ opacity, count, zero }) => {
  const frame = useCurrentFrame();
  const pct = interpolate(frame, [count, count + 42], [0, 96.8], { ...clamp, easing: Easing.out(Easing.cubic) });
  const stats = [
    { big: `${pct.toFixed(1)}%`, label: "decoded", sub: "of 1,064 generated test codes in 7 formats" },
    { big: "0", label: "wrong answers", sub: "a miss is safer than a wrong link" },
    { big: "0", label: "false alarms", sub: "on 48 images with no code" },
  ];
  return (
    <div style={{ position: "absolute", inset: 0, opacity }}>
      <div
        style={{
          position: "absolute",
          top: 200,
          left: 0,
          right: 0,
          textAlign: "center",
          fontSize: 34,
          color: C.muted,
          letterSpacing: 4,
          fontWeight: 600,
        }}
      >
        BENCHMARK LAB
      </div>
      <div
        style={{
          position: "absolute",
          top: 320,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          gap: 70,
        }}
      >
        {stats.map((s, i) => {
          const at = i === 0 ? count - 4 : zero + (i - 1) * 10;
          const show = interpolate(frame, [at, at + 12], [0, 1], clamp);
          return (
            <div
              key={s.label}
              style={{
                width: 500,
                padding: "40px 30px",
                boxSizing: "border-box",
                background: C.cardBg,
                border: `1px solid ${C.border}`,
                borderRadius: 24,
                textAlign: "center",
                opacity: show,
                transform: `translateY(${(1 - show) * 20}px)`,
              }}
            >
              <div style={{ fontSize: 128, fontWeight: 800, color: i === 0 ? C.accent : C.ok }}>
                {s.big}
              </div>
              <div style={{ fontSize: 40, fontWeight: 700, marginTop: 4 }}>{s.label}</div>
              <div style={{ fontSize: 26, color: C.muted, marginTop: 14, lineHeight: 1.35 }}>
                {s.sub}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const Port: React.FC<{ opacity: number; frame: number; grow: number }> = ({ opacity, frame, grow: growAt }) => {
  const MAX = 1000;
  const grow = interpolate(frame, [growAt, growAt + 40], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
  const bars = [
    { name: "Python", ms: 115, color: C.muted },
    { name: "C++", ms: 5, color: C.accent },
  ];
  return (
    <div style={{ position: "absolute", inset: 0, opacity }}>
      <div
        style={{
          position: "absolute",
          top: 200,
          left: 0,
          right: 0,
          textAlign: "center",
          fontSize: 34,
          color: C.muted,
          letterSpacing: 4,
          fontWeight: 600,
        }}
      >
        MEDIAN SCAN TIME, SAME 1,064 CODES
      </div>
      <div style={{ position: "absolute", top: 300, left: 260, width: 1400 }}>
        {bars.map((b) => (
          <div key={b.name} style={{ display: "flex", alignItems: "center", marginBottom: 40 }}>
            <div style={{ width: 180, fontSize: 44, fontWeight: 700 }}>{b.name}</div>
            <div
              style={{
                height: 84,
                width: Math.max(14, (b.ms / 115) * MAX * grow),
                background: b.color,
                borderRadius: 12,
              }}
            />
            <div
              style={{
                fontFamily: MONO,
                fontSize: 52,
                fontWeight: 700,
                marginLeft: 28,
                whiteSpace: "nowrap",
                color: b.color === C.accent ? C.accent : C.cardFg,
                opacity: grow,
              }}
            >
              {b.ms} ms
            </div>
          </div>
        ))}
        <div
          style={{
            marginTop: 40,
            display: "flex",
            gap: 28,
            fontSize: 32,
            color: C.cardFg,
            opacity: interpolate(frame, [12, 26], [0, 1], clamp),
          }}
        >
          <Pill>Python read 1,027. C++ read 1,026.</Pill>
          <Pill>Both: 0 wrong</Pill>
          <Pill>C++ app: one 1.9 MB exe</Pill>
        </div>
      </div>
    </div>
  );
};

const Pill: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div
    style={{
      background: C.cardBg,
      border: `1px solid ${C.border}`,
      borderRadius: 14,
      padding: "14px 24px",
    }}
  >
    {children}
  </div>
);
