import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { Icon } from "./components/Icon";
import { InSquare } from "./components/OS";
import { C, HEIGHT, MONO, UI, WIDTH } from "./theme";
import { cue, within } from "./timeline";
import { RELEASES } from "./scenes/Outro";
import { PLACED, Video } from "./Video";

// The same video in a square, for the LinkedIn feed. A "camera" shows a slice
// of the wide frame, panned to where the action is, and pulls back when a
// scene needs the full width. Bands above and below carry the name and link.

export const SQUARE = 1080;

// One camera position: `scale` is how much of the wide frame shows (0.75
// shows 1440 of its 1920 pixels), and `x` is the centre of that slice.
type Shot = { at: number; scale: number; x: number };

const WIDE = 0.75;
const FULL = SQUARE / WIDTH; // the whole width: 0.5625

function shots(): Shot[] {
  const at = (name: string) => PLACED.find((s) => s.name === name)!;
  const opener = at("opener");
  const talk = at("talk");
  const title = at("title");
  const call = at("call");
  const ticket = at("ticket");
  const trap = at("trap");
  const more = at("more");
  const real = PLACED.find((s) => s.name === "real");
  const proof = at("proof");
  const outro = at("outro");
  const seven = ticket.start + within(ticket.t, 1, 0.5, 100);
  return [
    // the cold open: the whole wall of codes
    { at: opener.start, scale: FULL, x: WIDTH / 2 },
    { at: talk.start - 6, scale: FULL, x: WIDTH / 2 },
    // the livestream: the dead phone on the left and the code on the right
    { at: talk.start + 6, scale: WIDE, x: 760 },
    { at: title.start - 8, scale: WIDE, x: 760 },
    { at: title.start + 4, scale: WIDE, x: WIDTH / 2 },
    // the call: centred on the middle code, which gets picked
    { at: call.start - 6, scale: WIDE, x: WIDTH / 2 },
    { at: call.start + 6, scale: WIDE, x: 820 },
    // the ticket: on the barcode and its card, then all seven formats
    { at: ticket.start - 6, scale: WIDE, x: 820 },
    { at: ticket.start + 6, scale: WIDE, x: 960 },
    { at: seven - 4, scale: WIDE, x: 960 },
    { at: seven + 10, scale: FULL, x: WIDTH / 2 },
    // the poster: on the code, then right with the zoom onto the warning
    { at: trap.start - 6, scale: FULL, x: WIDTH / 2 },
    { at: trap.start + 6, scale: WIDE, x: 1010 },
    { at: trap.start + cue(trap.t, 1, 80) - 4, scale: WIDE, x: 1010 },
    { at: trap.start + cue(trap.t, 1, 80) + 26, scale: WIDE, x: 1200 },
    // the features: the two screens and the page of codes need the full width
    { at: more.start - 6, scale: WIDE, x: 1200 },
    { at: more.start + 6, scale: FULL, x: WIDTH / 2 },
    // the real recording, if there is one, and the proof: pull back
    ...(real ? [{ at: real.start, scale: FULL, x: WIDTH / 2 }] : []),
    { at: proof.start - 6, scale: FULL, x: WIDTH / 2 },
    { at: proof.start + 6, scale: 0.62, x: WIDTH / 2 },
    { at: outro.start - 6, scale: 0.62, x: WIDTH / 2 },
    { at: outro.start + 6, scale: 0.62, x: WIDTH / 2 },
  ];
}

const SHOTS = shots();

// What the bottom band says: the use case or feature while one plays, else
// the link.
const BAND: Record<string, [string, string]> = {
  talk: ["USE CASE", "Conference livestream"],
  call: ["USE CASE", "Video call"],
  ticket: ["USE CASE", "Ticket in a PDF, on a Mac"],
  trap: ["USE CASE", "A poster with a trap"],
  more: ["FEATURES", "Two screens · pages of codes · styled codes · private"],
  real: ["PROOF", "The real app, recorded"],
};
function useCaseAt(frame: number): [string, string] | null {
  const scene = [...PLACED].reverse().find((s) => frame >= s.start);
  return scene ? BAND[scene.name] ?? null : null;
}
// The outro shows the link large, so the band stays empty there.
const inOutro = (frame: number) => frame >= (PLACED.find((s) => s.name === "outro")?.start ?? Infinity);

function camera(frame: number): { scale: number; x: number } {
  const frames = SHOTS.map((s) => s.at);
  const opts = {
    extrapolateLeft: "clamp" as const,
    extrapolateRight: "clamp" as const,
    easing: Easing.inOut(Easing.cubic),
  };
  return {
    scale: interpolate(frame, frames, SHOTS.map((s) => s.scale), opts),
    x: interpolate(frame, frames, SHOTS.map((s) => s.x), opts),
  };
}

export const Square: React.FC = () => {
  const frame = useCurrentFrame();
  const { scale, x } = camera(frame);
  const shown = HEIGHT * scale; // height of the picture in the square
  const band = (SQUARE - shown) / 2;
  // Keep the slice inside the wide frame.
  const half = SQUARE / scale / 2;
  const cx = Math.min(Math.max(x, half), WIDTH - half);
  const useCase = useCaseAt(frame);

  return (
    <AbsoluteFill style={{ background: C.stage }}>
      <div
        style={{
          position: "absolute",
          left: 0,
          top: band,
          width: WIDTH,
          height: HEIGHT,
          transformOrigin: "0 0",
          transform: `translateX(${SQUARE / 2 - cx * scale}px) scale(${scale})`,
        }}
      >
        <InSquare.Provider value={true}>
          <Video />
        </InSquare.Provider>
      </div>
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: band,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 18,
          background: C.stage,
          fontFamily: UI,
          color: C.cardFg,
          overflow: "hidden",
        }}
      >
        <Icon size={46} />
        <span style={{ fontSize: 46, fontWeight: 800, letterSpacing: -1 }}>UniQR</span>
        <span style={{ fontSize: 28, color: C.muted, marginLeft: 8 }}>read any QR code on your screen</span>
      </div>
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          height: band,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: C.stage,
          fontFamily: MONO,
          fontSize: 32,
          color: C.accent,
          overflow: "hidden",
        }}
      >
        {useCase ? (
          <span style={{ fontFamily: UI, color: C.cardFg, fontSize: 32, fontWeight: 600, display: "flex", gap: 16, alignItems: "center" }}>
            <span style={{ color: C.accent, fontWeight: 800, letterSpacing: 3, fontSize: 22 }}>{useCase[0]}</span>
            {useCase[1]}
          </span>
        ) : inOutro(frame) ? null : (
          RELEASES
        )}
      </div>
    </AbsoluteFill>
  );
};
