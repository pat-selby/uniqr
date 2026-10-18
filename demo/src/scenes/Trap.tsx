import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { Card } from "../components/Card";
import { Code } from "../components/Code";
import { Keys } from "../components/Keys";
import { UseCase, WinDesktop, WinWindow } from "../components/OS";
import { C } from "../theme";
import { SceneProps, cue, within } from "../timeline";

export const TRAP = 120;

// Use case: a "win a free pass" poster whose code hides the @ trick. The link
// reads like one site, but everything before the @ is ignored, and the card
// shows where it really goes. The warning is the app's own text, from
// describe_link() in uniqr/actions.py.

const S = 1.5;
const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

const WIN = { x: 250, y: 36, w: 1420, h: 920 };
const CODE = { left: WIN.x + 1 + 860, top: WIN.y + 49 + 210, size: 300 };
const HOST = "prize-claim.example.net";

export const Trap: React.FC<SceneProps> = ({ t }) => {
  const frame = useCurrentFrame();
  const KEYS_AT = within(t, 0, 0.75, 40);
  const CARD_IN = KEYS_AT + 26;
  const LOOK = cue(t, 1, 80);
  const zoom = interpolate(frame, [LOOK - 4, LOOK + 26], [1, 1.45], {
    ...clamp,
    easing: Easing.inOut(Easing.cubic),
  });
  const ring = interpolate(frame, [LOOK + 20, LOOK + 30], [0, 1], clamp);

  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ transform: `scale(${zoom})`, transformOrigin: `${CODE.left + 300}px ${CODE.top + 470}px` }}>
        <WinDesktop active={0}>
          <WinWindow {...WIN} title="free-pass-poster.jpg - Image Viewer" icon="#0f6cbd">
            <Poster />
          </WinWindow>
          {frame >= CARD_IN ? (
            <div style={{ position: "absolute", left: CODE.left, top: CODE.top + CODE.size + 14 * S, width: 420 * S, zIndex: 30, opacity: interpolate(frame, [CARD_IN, CARD_IN + 6], [0, 1], clamp) }}>
              <Card
                scale={S}
                kind="Link"
                status="Copied"
                host={HOST}
                rest="/login"
                notes={[{ text: `Text before the @ is ignored. This really goes to ${HOST}.`, warn: true }]}
                buttons={[
                  { label: "Open", primary: true },
                  { label: "Dismiss", primary: false },
                ]}
                style={{ left: 0, top: 0 }}
              />
              {/* A highlight around the host and the warning, for "look closer". */}
              <div
                style={{
                  position: "absolute",
                  left: -4 * S,
                  top: 34 * S,
                  width: 426 * S,
                  height: 90 * S,
                  border: `4px solid ${C.warn}`,
                  borderRadius: 12,
                  opacity: ring,
                  boxShadow: `0 0 30px ${C.warn}88`,
                }}
              />
            </div>
          ) : null}
        </WinDesktop>
      </AbsoluteFill>
      <Keys keys={["Win", "Shift", "Q"]} from={KEYS_AT - 10} hold={20} size={80} style={{ left: 0, right: 0, top: 120, justifyContent: "center", zIndex: 70 }} />
      <UseCase label="A poster with a trap" opacity={interpolate(frame, [4, 14, LOOK - 8, LOOK], [0, 1, 1, 0], clamp)} />
    </AbsoluteFill>
  );
};

// A made-up giveaway poster. The code really holds the @ trick, pointed at
// reserved example names.
const Poster: React.FC = () => (
  <div
    style={{
      position: "absolute",
      inset: 0,
      background: "#0e0e12",
      display: "grid",
      placeItems: "center",
    }}
  >
    <div
      style={{
        position: "absolute",
        left: 40,
        top: 30,
        right: 40,
        bottom: 30,
        borderRadius: 10,
        background: "linear-gradient(135deg, #ff7a45 0%, #ff3d7f 55%, #7a4fd6 100%)",
        color: "#fff",
      }}
    >
      <div style={{ position: "absolute", left: 80, top: 120, width: 640 }}>
        <div style={{ fontSize: 28, letterSpacing: 5, fontWeight: 800, opacity: 0.9 }}>GIVEAWAY</div>
        <div style={{ fontSize: 96, fontWeight: 900, lineHeight: 1, marginTop: 16 }}>WIN A FREE PASS!</div>
        <div style={{ fontSize: 32, marginTop: 28, opacity: 0.92 }}>All-access to Harbor Dev Summit.</div>
        <div style={{ display: "inline-block", marginTop: 40, fontSize: 30, fontWeight: 800, background: "#fff", color: "#ff3d7f", padding: "14px 30px", borderRadius: 40 }}>
          Scan to enter →
        </div>
      </div>
      <div
        style={{
          position: "absolute",
          left: CODE.left - WIN.x - 1 - 40 - 20,
          top: CODE.top - WIN.y - 49 - 30 - 20,
          background: "#fff",
          padding: 20,
          borderRadius: 16,
        }}
      >
        <Code bcid="qrcode" text={`https://freepass.example@${HOST}/login`} width={CODE.size} />
      </div>
    </div>
  </div>
);
