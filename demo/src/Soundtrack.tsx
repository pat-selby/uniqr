import React from "react";
import { Audio, Sequence, getStaticFiles, interpolate, staticFile } from "remotion";
import { revealAt } from "./scenes/Reveal";
import { within, type Timing } from "./timeline";

// The sound bed under the voices, placed on the story's beats. The pieces come
// from tools/make_music.py; without them this plays nothing.
//
//   the hook        a soft heartbeat while the phone keeps coming out
//   the turn        a riser into "UniQR", then one clean hit
//   the use cases   a bright, quiet progression, and a whoosh into each scene
//   the end         a last hit on "Try it out", then a fade
//
// Everything dips while anyone speaks, and every whoosh ends before a line
// starts, so nothing sits on top of the words.

export type Placed = { name: string; start: number; t: Timing };

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

// [start, end, fade in, fade out], in frames from the start of the video.
type Span = [number, number, number, number];

function level(f: number, spans: Span[]): number {
  let best = 0;
  for (const [a, b, i, o] of spans) {
    const up = Math.min(a + i, (a + b) / 2);
    const down = Math.max(b - o, up + 1);
    if (b <= up) continue;
    best = Math.max(best, interpolate(f, [a, up, down, Math.max(b, down + 1)], [0, 1, 1, 0], clamp));
  }
  return best;
}

const VOLUME = { bright: 0.2, pulse: 0.3, riser: 0.35, impact: 0.55, whoosh: 0.16 };
const DUCK = 0.45; // the music drops to this share of its level under a voice
const RISER = 60; // frames of the riser: its last two seconds
const WHOOSH = 18; // frames; whoosh.wav is 0.6 s

export const Soundtrack: React.FC<{ scenes: Placed[]; total: number }> = ({ scenes, total }) => {
  const files = new Set(getStaticFiles().map((f) => f.name));
  if (!files.has("sfx/pad_bright.wav")) return null;

  const at = (name: string) => scenes.find((s) => s.name === name)!;
  const hook = at("hook");
  const reveal = at("reveal");
  const outro = at("outro");
  const hit = reveal.start + revealAt(reveal.t);
  const last = outro.start + within(outro.t, 1, 0.62, 50) - 2;

  const speech: [number, number][] = scenes.flatMap((s) =>
    s.t.cues.map((c, i) => [s.start + c, s.start + s.t.ends[i]] as [number, number]),
  );
  const duck = (f: number) => {
    let talking = 0;
    for (const [a, b] of speech) {
      if (f < a - 8 || f > b + 10) continue;
      talking = Math.max(talking, interpolate(f, [a - 8, a, b, b + 10], [0, 1, 1, 0], clamp));
    }
    return 1 - (1 - DUCK) * talking;
  };

  const bright: Span[] = [[hit - 4, total, 20, 50]];
  const pulse: Span[] = [[hook.start, hit, 15, 20]];
  // Into each scene after the title, ending before the scene's first line.
  const whooshes = scenes
    .filter((s) => !["hook", "reveal"].includes(s.name))
    .map((s) => s.start - WHOOSH + 2);

  return (
    <>
      <Audio src={staticFile("sfx/pulse.wav")} volume={(f) => VOLUME.pulse * level(f, pulse) * duck(f)} />
      <Sequence from={hit - 4}>
        <Audio src={staticFile("sfx/pad_bright.wav")} volume={(f) => VOLUME.bright * level(f + hit - 4, bright) * duck(f + hit - 4)} />
      </Sequence>
      <Sequence from={hit - RISER} durationInFrames={RISER + 2}>
        <Audio src={staticFile("sfx/riser.wav")} startFrom={120 - RISER} volume={(f) => VOLUME.riser * duck(f + hit - RISER)} />
      </Sequence>
      {[hit - 1, last].map((from) => (
        <Sequence key={from} from={from}>
          <Audio src={staticFile("sfx/impact.wav")} volume={VOLUME.impact} />
        </Sequence>
      ))}
      {whooshes.map((from) => (
        <Sequence key={from} from={from} durationInFrames={WHOOSH}>
          <Audio src={staticFile("sfx/whoosh.wav")} volume={VOLUME.whoosh} />
        </Sequence>
      ))}
    </>
  );
};
