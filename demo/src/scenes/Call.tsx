import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { Card } from "../components/Card";
import { Code } from "../components/Code";
import { Cursor } from "../components/Cursor";
import { Keys } from "../components/Keys";
import { UseCase, WinDesktop, WinWindow } from "../components/OS";
import { Picker } from "../components/Picker";
import { SceneProps, cue, within } from "../timeline";

export const CALL = 120;

// Use case: a video call where someone shares a slide with three codes.

const S = 1.5;
const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

const WIN = { x: 90, y: 30, w: 1740, h: 930 };
const SLIDE = { x: WIN.x + 24, y: WIN.y + 48 + 20, w: 1360, h: 765 };
const SIZE = 210;
const TOP = SLIDE.y + 330;
const LEFTS = [0.2, 0.5, 0.8].map((k) => Math.round(SLIDE.x + SLIDE.w * k - SIZE / 2));
const ITEMS = [
  { label: "Register", url: "https://example.com/hack/register" },
  { label: "Starter repo", url: "https://example.org/hack/starter" },
  { label: "Team chat", url: "https://example.net/hack/chat" },
];

export const Call: React.FC<SceneProps> = ({ t }) => {
  const frame = useCurrentFrame();
  const PICK = cue(t, 1, 60) - 4;
  const HOVER = PICK + 22;
  const PRESS = within(t, 1, 0.62, PICK + 50);
  const OUT = PRESS + 12;
  const box = (i: number) => ({ left: LEFTS[i], top: TOP, size: SIZE });

  return (
    <AbsoluteFill>
      <WinDesktop active={3}>
        <WinWindow {...WIN} title="Meeting: Hackathon kickoff" icon="#6264a7">
          <Meeting />
        </WinWindow>
      </WinDesktop>
      {frame >= PICK && frame < OUT ? <Picker boxes={[0, 1, 2].map(box)} from={PICK} /> : null}
      {frame >= HOVER && frame < OUT ? (
        <Card
          scale={S}
          kind="Link"
          host="example.org"
          rest="/hack/starter"
          buttons={[
            { label: "Open", primary: true },
            { label: "Copy", primary: false },
          ]}
          style={{ left: LEFTS[1], top: TOP + SIZE + 16 * S, zIndex: 45 }}
        />
      ) : null}
      {frame >= OUT ? (
        <Card
          scale={S}
          kind="Link"
          status="Copied"
          host="example.org"
          rest="/hack/starter"
          buttons={[
            { label: "Open", primary: true },
            { label: "Dismiss", primary: false },
          ]}
          style={{ left: LEFTS[1], top: TOP + SIZE + 14 * S, zIndex: 45, opacity: interpolate(frame, [OUT, OUT + 6], [0, 1], clamp) }}
        />
      ) : null}
      <Cursor
        visibleFrom={PICK + 4}
        path={[
          [PICK + 4, 1500, 860],
          [HOVER, LEFTS[1] + SIZE * 0.6, TOP + SIZE * 0.55],
        ]}
      />
      <Keys keys={["Win", "Shift", "Q"]} from={PICK - 26} hold={8} size={72} style={{ left: 0, right: 0, top: 120, justifyContent: "center", zIndex: 70 }} />
      <Keys keys={["2"]} from={PRESS - 10} hold={14} size={96} style={{ left: 0, right: 0, top: 120, justifyContent: "center", zIndex: 70 }} />
      <UseCase label="Video call" opacity={interpolate(frame, [4, 14, PICK - 8, PICK], [0, 1, 1, 0], clamp)} />
    </AbsoluteFill>
  );
};

// A made-up meeting: the shared slide, three people on the right, controls below.
const Meeting: React.FC = () => (
  <div style={{ position: "absolute", inset: 0, background: "#1f1f24" }}>
    <div
      style={{
        position: "absolute",
        left: SLIDE.x - WIN.x - 1,
        top: SLIDE.y - WIN.y - 49,
        width: SLIDE.w,
        height: SLIDE.h,
        background: "#fbfaf7",
        borderRadius: 8,
        color: "#1a2233",
      }}
    >
      <div style={{ textAlign: "center", paddingTop: 70 }}>
        <div style={{ fontSize: 24, letterSpacing: 4, fontWeight: 700, color: "#6264a7" }}>48-HOUR HACKATHON</div>
        <div style={{ fontSize: 60, fontWeight: 800, marginTop: 10 }}>Before you start building</div>
      </div>
      {ITEMS.map((item, i) => (
        <div key={item.url} style={{ position: "absolute", left: LEFTS[i] - SLIDE.x, top: TOP - SLIDE.y, width: SIZE, textAlign: "center" }}>
          <Code bcid="qrcode" text={item.url} width={SIZE} color="#1a2233" />
          <div style={{ fontSize: 28, fontWeight: 700, marginTop: 60 }}>{item.label}</div>
        </div>
      ))}
    </div>
    <div style={{ position: "absolute", right: 24, top: 20, width: 300, display: "flex", flexDirection: "column", gap: 16 }}>
      {[
        ["JM", "#2f7cf6"],
        ["AK", "#e05a8a"],
        ["You", "#3fb27f"],
      ].map(([who, color]) => (
        <div key={who} style={{ height: 180, borderRadius: 12, background: "#2c2c33", display: "grid", placeItems: "center", position: "relative" }}>
          <div style={{ width: 84, height: 84, borderRadius: 42, background: color, color: "#fff", fontSize: 30, fontWeight: 700, display: "grid", placeItems: "center" }}>{who}</div>
        </div>
      ))}
    </div>
    <div style={{ position: "absolute", left: 0, right: 0, bottom: 18, display: "flex", justifyContent: "center", gap: 16 }}>
      {["#3a3a44", "#3a3a44", "#3a3a44", "#c4314b"].map((c, i) => (
        <div key={i} style={{ width: i === 3 ? 110 : 64, height: 52, borderRadius: 10, background: c }} />
      ))}
    </div>
  </div>
);
