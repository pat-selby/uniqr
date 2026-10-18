import React from "react";
import { AbsoluteFill, Audio, Sequence, Series, getStaticFiles, staticFile } from "remotion";
import { Fade } from "./components/Fade";
import { Call, CALL } from "./scenes/Call";
import { Intro, INTRO } from "./scenes/Intro";
import { More, MORE } from "./scenes/More";
import { Numbers, NUMBERS } from "./scenes/Numbers";
import { Opener, OPENER } from "./scenes/Opener";
import { Outro, OUTRO } from "./scenes/Outro";
import { Real, REAL, REAL_FILE } from "./scenes/Real";
import { Talk, TALK } from "./scenes/Talk";
import { Ticket, TICKET } from "./scenes/Ticket";
import { Trap, TRAP } from "./scenes/Trap";
import { Placed, Soundtrack } from "./Soundtrack";
import { SceneProps, timing } from "./timeline";

// Each scene, its name in voiceover/script.json, and its shortest length in
// frames. The voiceover can make a scene longer than this, never shorter.
// The "Is it real?" scene joins only once a real recording is in public/.
const HAS_REAL = getStaticFiles().some((f) => f.name === REAL_FILE);

const SCENES: [React.FC<SceneProps>, string, number][] = [
  [Opener, "opener", OPENER],
  [Talk, "talk", TALK],
  [Intro, "title", INTRO],
  [Call, "call", CALL],
  [Ticket, "ticket", TICKET],
  [Trap, "trap", TRAP],
  [More, "more", MORE],
  ...(HAS_REAL ? [[Real, "real", REAL] as [React.FC<SceneProps>, string, number]] : []),
  [Numbers, "proof", NUMBERS],
  [Outro, "outro", OUTRO],
];

const TIMINGS = SCENES.map(([, name, minimum]) => timing(name, minimum));

export const TOTAL = TIMINGS.reduce((sum, t) => sum + t.duration, 0);

// Where each scene starts in the whole video, for the sound bed.
export const PLACED: Placed[] = SCENES.map(([, name], i) => ({
  name,
  start: TIMINGS.slice(0, i).reduce((sum, t) => sum + t.duration, 0),
  t: TIMINGS[i],
}));

// The voice clips live in public/vo; tools/make_voiceover.py makes them.
// Without them the video is silent and the captions carry it.
const present = new Set(getStaticFiles().map((f) => f.name));

export const Video: React.FC = () => (
  <AbsoluteFill style={{ background: "#000" }}>
    <Series>
      {SCENES.map(([Scene], i) => {
        const t = TIMINGS[i];
        return (
          <Series.Sequence key={i} durationInFrames={t.duration}>
            <Fade duration={t.duration}>
              <Scene t={t} />
            </Fade>
            {t.clips
              .filter((clip) => present.has(`vo/${clip.file}`))
              .map((clip) => (
                <Sequence key={clip.file} from={clip.from}>
                  <Audio src={staticFile(`vo/${clip.file}`)} />
                </Sequence>
              ))}
          </Series.Sequence>
        );
      })}
    </Series>
    <Soundtrack scenes={PLACED} total={TOTAL} />
  </AbsoluteFill>
);
