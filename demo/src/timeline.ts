import { FPS } from "./theme";
import voiceover from "./voiceover.json";

// Each scene's length and timing come from its voiceover lines, made by
// tools/make_voiceover.py. A line starts, plays for as long as the voice
// speaks, then a short gap. Scenes use the start of each line ("cues") to
// time their animations, so the picture moves with the words.

const LEAD = 10; // frames of quiet before the first line in a scene
const GAP = 9; // frames between lines
const TAIL = 10; // frames after the last line, before the scene fades

export type Clip = { file: string; from: number };

export type Timing = {
  duration: number;
  cues: number[]; // frame each line starts at, in scene time
  ends: number[]; // frame each line's speech ends at
  clips: Clip[];
};

type Spoken = { text: string; file: string; seconds: number; pause: number };
const SCENES = (voiceover as { scenes: Record<string, Spoken[]> }).scenes;

export function timing(scene: string, minimum: number): Timing {
  const spoken = SCENES[scene] ?? [];
  const cues: number[] = [];
  const ends: number[] = [];
  const clips: Clip[] = [];
  let t = LEAD;
  for (const line of spoken) {
    const length = Math.ceil(line.seconds * FPS);
    cues.push(t);
    ends.push(t + length);
    clips.push({ file: line.file, from: t });
    t += length + GAP + line.pause;
  }
  const duration = Math.max(minimum, t + TAIL);
  return { duration, cues, ends, clips };
}

export type SceneProps = { t: Timing };

// A cue, or a fallback frame if the script has fewer lines than expected.
export const cue = (t: Timing, i: number, fallback: number) => t.cues[i] ?? fallback;

// A frame partway through line i: 0 is where it starts, 1 where the voice stops.
export const within = (t: Timing, i: number, part: number, fallback: number) => {
  const start = t.cues[i];
  const end = t.ends[i];
  return start === undefined || end === undefined ? fallback : start + Math.round((end - start) * part);
};
