import React from "react";
import { Audio, Sequence, getStaticFiles, interpolate, staticFile } from "remotion";
import { reveal } from "./scenes/Intro";
import { within, type Timing } from "./timeline";

// The sound bed under the voice, placed on the story's beats. The pieces come
// from tools/make_music.py; without them this plays nothing.
//
//   the livestream  dark drone and a heartbeat: the phone is dead
//   the turn        a riser into "That's UniQR", then an impact and a flash
//   use cases       a brighter progression, a whoosh into each new scene
//   the trap        back to the drone and the heartbeat for the poster
//   the proof       bright again, a soft hit on "Zero wrong answers"
//   the end         a last hit on "Try it out", then a fade
//
// Everything dips while the voice speaks, so the words stay on top.

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

const VOLUME = {
  dark: 0.3,
  bright: 0.24,
  pulse: 0.4,
  riser: 0.45,
  impact: 0.6,
  whoosh: 0.22,
};
const DUCK = 0.5; // how far the music dips under the voice
const RISER = 75; // frames of the riser to play: the last two and a half seconds

export const Soundtrack: React.FC<{ scenes: Placed[]; total: number }> = ({ scenes, total }) => {
  const files = new Set(getStaticFiles().map((f) => f.name));
  if (!files.has("sfx/pad_dark.wav")) return null;

  const at = (name: string) => scenes.find((s) => s.name === name)!;
  const talk = at("talk");
  const intro = at("title");
  const trap = at("trap");
  const more = at("more");
  const proof = at("proof");
  const outro = at("outro");
  const abs = (s: Placed, i: number, fallback = 0) => s.start + (s.t.cues[i] ?? fallback);

  const hit = intro.start + reveal(intro.t);
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

  const dark: Span[] = [
    [0, hit + 20, 20, 40],
    [trap.start - 6, more.start + 20, 30, 30],
  ];
  const bright: Span[] = [
    [hit - 2, trap.start + 10, 20, 30],
    [more.start - 5, total, 30, 60],
  ];
  const pulse: Span[] = [
    [abs(talk, 0), abs(talk, 2) + 10, 20, 25],
    [abs(trap, 0) + 10, abs(trap, 2) + 25, 20, 25],
  ];
  const whooshes = scenes
    .filter((s) => !["opener", "title"].includes(s.name))
    .map((s) => s.start - 14);
  const proofLine = proof.t.cues[1] ?? 40;
  const zero = proof.start + proofLine + Math.round(((proof.t.ends[1] ?? proofLine + 150) - proofLine) * 0.7);
  const last = outro.start + within(outro.t, 1, 0.45, 50) - 2;

  return (
    <>
      <Audio src={staticFile("sfx/pad_dark.wav")} volume={(f) => VOLUME.dark * level(f, dark) * duck(f)} />
      <Audio src={staticFile("sfx/pulse.wav")} volume={(f) => VOLUME.pulse * level(f, pulse) * duck(f)} />
      <Sequence from={hit - 2}>
        <Audio
          src={staticFile("sfx/pad_bright.wav")}
          volume={(f) => VOLUME.bright * level(f + hit - 2, bright) * duck(f + hit - 2)}
        />
      </Sequence>
      <Sequence from={hit - RISER} durationInFrames={RISER + 2}>
        <Audio src={staticFile("sfx/riser.wav")} startFrom={120 - RISER} volume={VOLUME.riser} />
      </Sequence>
      {[
        [hit - 1, VOLUME.impact],
        [zero, VOLUME.impact * 0.45],
        [last - 1, VOLUME.impact * 0.9],
      ].map(([from, volume]) => (
        <Sequence key={from} from={from}>
          <Audio src={staticFile("sfx/impact.wav")} volume={volume} />
        </Sequence>
      ))}
      {whooshes.map((from) => (
        <Sequence key={from} from={from} durationInFrames={30}>
          <Audio src={staticFile("sfx/whoosh.wav")} volume={VOLUME.whoosh} />
        </Sequence>
      ))}
    </>
  );
};
