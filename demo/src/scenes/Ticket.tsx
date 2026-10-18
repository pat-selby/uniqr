import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Card } from "../components/Card";
import { Code, Symbology } from "../components/Code";
import { Keys } from "../components/Keys";
import { MacDesktop, MacWindow, UseCase } from "../components/OS";
import { C, UI } from "../theme";
import { SceneProps, cue, within } from "../timeline";

export const TICKET = 120;

// Use case: an event ticket in a PDF on a Mac. The code is a PDF417, not a QR
// code, and what it holds is not a link, so the card copies it and nothing
// more. Then all seven kinds of code UniQR reads.

const S = 1.5;
const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

const WIN = { x: 330, y: 80, w: 1260, h: 600 };
const PAGE = { x: WIN.x + 1 + 130, y: WIN.y + 57 + 40, w: 1000, h: 480 };
const CODE = { left: PAGE.x + 240, top: PAGE.y + 330, width: 520 };
const CODE_H = Math.round((CODE.width * 108) / 480); // bwip-js draws PDF417 at 480 x 108 here

const FORMATS: { name: string; bcid: Symbology; text: string; width: number; options?: Record<string, unknown> }[] = [
  { name: "QR", bcid: "qrcode", text: "https://example.com/qr", width: 130 },
  { name: "Micro QR", bcid: "microqrcode", text: "example.com/m", width: 110 },
  { name: "rMQR", bcid: "rectangularmicroqrcode", text: "https://example.com/rmqr", width: 250, options: { version: "R13x59" } },
  { name: "Data Matrix", bcid: "datamatrix", text: "https://example.com/dm", width: 125 },
  { name: "Aztec", bcid: "azteccode", text: "https://example.com/aztec", width: 130 },
  { name: "PDF417", bcid: "pdf417", text: "https://example.com/pdf417", width: 250 },
  { name: "MaxiCode", bcid: "maxicode", text: "https://example.com/maxi", width: 140 },
];

export const Ticket: React.FC<SceneProps> = ({ t }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const KEYS_AT = cue(t, 1, 50) - 2;
  const CARD_IN = KEYS_AT + 34;
  const SEVEN = within(t, 1, 0.5, 100);
  const seven = interpolate(frame, [SEVEN, SEVEN + 10], [0, 1], clamp);

  return (
    <AbsoluteFill>
      <MacDesktop app="Viewer">
        <MacWindow {...WIN} title="harbor-summit-ticket.pdf">
          <TicketPage />
        </MacWindow>
        {frame >= CARD_IN ? (
          <Card
            scale={S}
            kind="Text"
            status="Copied · PDF417"
            body="HDS26-DAYPASS-HALLB-0042"
            notes={[{ text: "Not a web link, so UniQR won't open it.", warn: false }]}
            buttons={[{ label: "Dismiss", primary: false }]}
            style={{
              left: CODE.left,
              top: CODE.top + CODE_H + 14 * S,
              zIndex: 30,
              opacity: interpolate(frame, [CARD_IN, CARD_IN + 6], [0, 1], clamp),
            }}
          />
        ) : null}
      </MacDesktop>
      {seven > 0 ? (
        <AbsoluteFill style={{ background: `rgba(8, 10, 24, ${0.55 * seven})`, zIndex: 55, display: "grid", placeItems: "center" }}>
          <div
            style={{
              opacity: seven,
              transform: `translateY(${(1 - seven) * 30}px)`,
              background: "rgba(17, 24, 38, 0.92)",
              border: `1px solid ${C.border}`,
              borderRadius: 28,
              padding: "40px 50px",
              display: "flex",
              gap: 30,
              alignItems: "flex-end",
              fontFamily: UI,
            }}
          >
            {FORMATS.map((f, i) => {
              const pop = spring({ frame: frame - SEVEN - i * 3, fps, config: { damping: 14 } });
              return (
                <div key={f.name} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 14, opacity: pop, transform: `scale(${0.8 + 0.2 * pop})` }}>
                  <div style={{ background: "#fff", borderRadius: 14, padding: 16, height: 150, display: "grid", placeItems: "center" }}>
                    <Code bcid={f.bcid} text={f.text} width={f.width} options={f.options} />
                  </div>
                  <div style={{ color: C.cardFg, fontSize: 24, fontWeight: 600 }}>{f.name}</div>
                </div>
              );
            })}
          </div>
        </AbsoluteFill>
      ) : null}
      <Keys keys={["Cmd", "Shift", "8"]} from={KEYS_AT} hold={22} size={80} style={{ left: 0, right: 0, top: 110, justifyContent: "center", zIndex: 70 }} />
      <UseCase label="Ticket in a PDF, on a Mac" opacity={interpolate(frame, [4, 14, SEVEN - 8, SEVEN], [0, 1, 1, 0], clamp)} />
    </AbsoluteFill>
  );
};

// A made-up day pass.
const TicketPage: React.FC = () => (
  <div style={{ position: "absolute", inset: 0, background: "#8a8f99" }}>
    <div
      style={{
        position: "absolute",
        left: PAGE.x - WIN.x - 1,
        top: PAGE.y - WIN.y - 57,
        width: PAGE.w,
        height: PAGE.h,
        background: "#fff",
        borderRadius: 6,
        overflow: "hidden",
        boxShadow: "0 6px 20px rgba(0,0,0,0.25)",
        color: "#1a2233",
      }}
    >
      <div style={{ height: 120, background: "linear-gradient(90deg,#1d4fbf,#7a4fd6)", color: "#fff", padding: "26px 40px", boxSizing: "border-box" }}>
        <div style={{ fontSize: 22, letterSpacing: 4, fontWeight: 700, opacity: 0.85 }}>ADMIT ONE</div>
        <div style={{ fontSize: 44, fontWeight: 800 }}>Harbor Dev Summit 2026</div>
      </div>
      <div style={{ display: "flex", gap: 80, padding: "30px 40px", fontSize: 24 }}>
        {[
          ["Attendee", "Alex Rivera"],
          ["Pass", "Day pass"],
          ["Room", "Hall B"],
        ].map(([k, v]) => (
          <div key={k}>
            <div style={{ color: "#6b7590", fontSize: 18, letterSpacing: 2 }}>{k.toUpperCase()}</div>
            <div style={{ fontWeight: 700, marginTop: 4 }}>{v}</div>
          </div>
        ))}
      </div>
      <div style={{ position: "absolute", left: CODE.left - PAGE.x, top: CODE.top - PAGE.y }}>
        <Code bcid="pdf417" text="HDS26-DAYPASS-HALLB-0042" width={CODE.width} />
      </div>
    </div>
  </div>
);
