import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { Card } from "../components/Card";
import { Code } from "../components/Code";
import { Keys } from "../components/Keys";
import { UseCase, WinBrowser, WinDesktop } from "../components/OS";
import { SceneProps, cue, within } from "../timeline";

export const TALK = 150;

// Use case: a conference livestream on a Windows laptop. The speaker's last
// slide is a QR code, and the viewer's phone is dead.

const S = 1.5;
const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

const BROWSER = { x: 110, y: 36, w: 1700, h: 920 };
const CONTENT = { x: BROWSER.x + 1, y: BROWSER.y + 104 };
const PLAYER = { x: CONTENT.x + 36, y: CONTENT.y + 28, w: 1180, h: 664 };
const CODE = { left: PLAYER.x + 790, top: PLAYER.y + 150, size: 300 };

export const Talk: React.FC<SceneProps> = ({ t }) => {
  const frame = useCurrentFrame();
  // "Win, Shift, Q" is the end of the second line; the card follows the keys.
  const KEYS_AT = within(t, 1, 0.35, 140);
  const CARD_IN = KEYS_AT + 26;
  const ZOOM_AT = cue(t, 3, 220);
  const zoom = interpolate(frame, [ZOOM_AT - 6, ZOOM_AT + 26], [1, 1.5], {
    ...clamp,
    easing: Easing.inOut(Easing.cubic),
  });
  const phone = interpolate(frame, [cue(t, 0, 6) + 30, cue(t, 0, 6) + 42, KEYS_AT - 10, KEYS_AT], [0, 1, 1, 0], clamp);

  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ transform: `scale(${zoom})`, transformOrigin: `${CODE.left + 150}px ${CODE.top + 330}px` }}>
        <WinDesktop active={1}>
          <WinBrowser {...BROWSER} tab="Live: Harbor Dev Summit" url="example.com/live/keynote">
            <Page />
          </WinBrowser>
          {frame >= CARD_IN ? (
            <Card
              scale={S}
              kind="Link"
              status="Copied"
              host="example.com"
              rest="/talks/keynote-slides"
              buttons={[
                { label: "Open", primary: true },
                { label: "Dismiss", primary: false },
              ]}
              style={{
                left: CODE.left,
                top: CODE.top + CODE.size + 14 * S,
                opacity: interpolate(frame, [CARD_IN, CARD_IN + 6], [0, 1], clamp),
                zIndex: 30,
              }}
            />
          ) : null}
        </WinDesktop>
      </AbsoluteFill>
      <DeadPhone opacity={phone} />
      <Keys keys={["Win", "Shift", "Q"]} from={KEYS_AT - 10} hold={26} size={80} style={{ left: 0, right: 0, top: 120, justifyContent: "center" }} />
      <UseCase label="Conference livestream" opacity={interpolate(frame, [4, 14, ZOOM_AT - 10, ZOOM_AT], [0, 1, 1, 0], clamp)} />
    </AbsoluteFill>
  );
};

// A made-up livestream page: the talk on the left, the chat on the right.
const Page: React.FC = () => (
  <div style={{ position: "absolute", inset: 0, background: "#0f1115" }}>
    <div
      style={{
        position: "absolute",
        left: PLAYER.x - CONTENT.x,
        top: PLAYER.y - CONTENT.y,
        width: PLAYER.w,
        height: PLAYER.h,
        borderRadius: 12,
        overflow: "hidden",
        background: "linear-gradient(135deg, #102a54 0%, #0a1830 100%)",
      }}
    >
      <div style={{ position: "absolute", left: 70, top: 120, color: "#fff", width: 640 }}>
        <div style={{ fontSize: 26, letterSpacing: 4, color: "#7fb4ff", fontWeight: 700 }}>THANKS FOR COMING</div>
        <div style={{ fontSize: 64, fontWeight: 800, lineHeight: 1.08, marginTop: 18 }}>Slides and demo code</div>
        <div style={{ fontSize: 30, color: "#b8c7e6", marginTop: 24 }}>Scan the code. Questions after the break.</div>
      </div>
      <div
        style={{
          position: "absolute",
          left: CODE.left - PLAYER.x - 22,
          top: CODE.top - PLAYER.y - 22,
          background: "#fff",
          padding: 22,
          borderRadius: 16,
        }}
      >
        <Code bcid="qrcode" text="https://example.com/talks/keynote-slides" width={CODE.size} />
      </div>
      {/* the speaker's camera, in the corner of the stream */}
      <div style={{ position: "absolute", left: 24, bottom: 24, width: 230, height: 140, borderRadius: 10, background: "linear-gradient(160deg,#3a4a66,#1c2433)", display: "grid", placeItems: "center" }}>
        <div style={{ width: 64, height: 64, borderRadius: 32, background: "#8fa3c8" }} />
      </div>
      <div style={{ position: "absolute", right: 22, top: 20, background: "#e5383b", color: "#fff", fontWeight: 800, fontSize: 18, padding: "4px 12px", borderRadius: 6 }}>LIVE</div>
    </div>
    <div style={{ position: "absolute", left: PLAYER.x - CONTENT.x, top: PLAYER.y - CONTENT.y + PLAYER.h + 20, color: "#e8eefc", fontSize: 30, fontWeight: 700 }}>
      Keynote: Small tools, big wins
    </div>
    <div
      style={{
        position: "absolute",
        left: PLAYER.x - CONTENT.x + PLAYER.w + 28,
        top: PLAYER.y - CONTENT.y,
        right: 28,
        bottom: 28,
        background: "#171a21",
        borderRadius: 12,
        padding: 22,
        color: "#c9d1e3",
        fontSize: 20,
        display: "flex",
        flexDirection: "column",
        gap: 18,
      }}
    >
      <div style={{ fontWeight: 700, color: "#fff", fontSize: 22 }}>Live chat</div>
      {[
        ["Sam", "Great talk!"],
        ["Priya", "Where are the slides?"],
        ["Leo", "QR on screen now"],
        ["Mia", "my phone is upstairs..."],
      ].map(([who, msg]) => (
        <div key={who}>
          <span style={{ color: "#7fb4ff", fontWeight: 700 }}>{who} </span>
          {msg}
        </div>
      ))}
    </div>
  </div>
);

// A phone with an empty battery, for "my phone is dead".
const DeadPhone: React.FC<{ opacity: number }> = ({ opacity }) => (
  <div
    style={{
      position: "absolute",
      left: 70,
      top: 380,
      opacity,
      transform: `translateX(${(1 - opacity) * -40}px) rotate(-8deg)`,
      zIndex: 50,
    }}
  >
    <div
      style={{
        width: 170,
        height: 330,
        borderRadius: 30,
        background: "#0c0d10",
        border: "6px solid #2a2d35",
        boxShadow: "0 24px 60px rgba(0,0,0,0.6)",
        display: "grid",
        placeItems: "center",
      }}
    >
      <svg width={84} height={44} viewBox="0 0 84 44">
        <rect x="3" y="3" width="70" height="38" rx="7" fill="none" stroke="#e5383b" strokeWidth="5" />
        <rect x="76" y="14" width="6" height="16" rx="2" fill="#e5383b" />
        <rect x="9" y="9" width="7" height="26" rx="2" fill="#e5383b" />
      </svg>
    </div>
  </div>
);
