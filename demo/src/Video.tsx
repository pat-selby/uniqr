import React from "react";
import { AbsoluteFill, Audio, Sequence, Series, getStaticFiles, staticFile } from "remotion";
import { Fade } from "./components/Fade";
import { CallScene, CALL } from "./scenes/CallScene";
import { ClassScene, CLASS } from "./scenes/ClassScene";
import { Hook, HOOK } from "./scenes/Hook";
import { Monitors, MONITORS } from "./scenes/Monitors";
import { Outro, OUTRO } from "./scenes/Outro";
import { Platforms, PLATFORMS } from "./scenes/Platforms";
import { Real, REAL, REAL_FILE } from "./scenes/Real";
import { Reveal, REVEAL } from "./scenes/Reveal";
import { Scam, SCAM } from "./scenes/Scam";
import { Placed, Soundtrack } from "./Soundtrack";
import { L } from "./theme";
import { SceneProps, timing } from "./timeline";

// Each scene, its name in voiceover/script.json, and its shortest length in
// frames. The voiceover can make a scene longer than this, never shorter.
// The "Is this real?" scene joins only once a real recording is in public/.
const HAS_REAL = getStaticFiles().some((f) => f.name === REAL_FILE);

const SCENES: [React.FC<SceneProps>, string, number][] = [
  [Hook, "hook", HOOK],
  [Reveal, "reveal", REVEAL],
  [Platforms, "platforms", PLATFORMS],
  [ClassScene, "class", CLASS],
  [CallScene, "call", CALL],
  [Monitors, "monitors", MONITORS],
  [Scam, "scam", SCAM],
  ...(HAS_REAL ? [[Real, "real", REAL] as [React.FC<SceneProps>, string, number]] : []),
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
// Without them the video is silent.
const present = new Set(getStaticFiles().map((f) => f.name));

export const Video: React.FC = () => (
  <AbsoluteFill style={{ background: L.stage }}>
    <Series>
      {SCENES.map(([Scene], i) => {
        const t = TIMINGS[i];
        return (
          <Series.Sequence key={i} durationInFrames={t.duration}>
            <Fade duration={t.duration} color={L.stage} edge={8}>
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
