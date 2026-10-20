import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { Card } from "../components/Card";
import { Cursor } from "../components/Cursor";
import { Keys } from "../components/Keys";
import { Laptop } from "../components/Laptop";
import { UseCase } from "../components/OS";
import { Picker } from "../components/Picker";
import { CallScreen, callBoxes } from "../components/Screens";
import { useHotkey, usePlatform } from "../platform";
import { SceneProps, cue, within } from "../timeline";

export const CALL = 120;

// Use case: a team call where a shared slide has three codes. The picker
// numbers them; the 2 key copies the middle one.

const S = 1.5;
const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

export const CallScene: React.FC<SceneProps> = ({ t }) => {
  const frame = useCurrentFrame();
  const CALL_BOXES = callBoxes(usePlatform());
  const hotkey = useHotkey();
  const PICK = cue(t, 1, 60) - 2; // "Each one gets a number"
  const HOVER = PICK + 18;
  const PRESS = within(t, 1, 0.78, PICK + 50); // "Pick one"
  const OUT = PRESS + 12;
  const box = CALL_BOXES[1];

  const overlay = (
    <>
      {frame >= PICK && frame < OUT ? <Picker boxes={CALL_BOXES} from={PICK} /> : null}
      {frame >= HOVER && frame < OUT ? (
        <Card
          scale={S}
          kind="Link"
          host="example.org"
          rest="/q3/backend"
          buttons={[
            { label: "Open", primary: true },
            { label: "Copy", primary: false },
          ]}
          style={{ left: box.left, top: box.top + box.size + 16 * S, zIndex: 45 }}
        />
      ) : null}
      {frame >= OUT ? (
        <Card
          scale={S}
          kind="Link"
          status="Copied"
          host="example.org"
          rest="/q3/backend"
          buttons={[
            { label: "Open", primary: true },
            { label: "Dismiss", primary: false },
          ]}
          style={{ left: box.left, top: box.top + box.size + 14 * S, zIndex: 45, opacity: interpolate(frame, [OUT, OUT + 6], [0, 1], clamp) }}
        />
      ) : null}
      <Cursor visibleFrom={PICK + 4} path={[[PICK + 4, 1500, 900], [HOVER, box.left + box.size * 0.6, box.top + box.size * 0.55]]} size={40} />
    </>
  );

  return (
    <AbsoluteFill>
      <Laptop overlay={overlay}>
        <CallScreen />
      </Laptop>
      <Keys keys={hotkey} from={PICK - 26} hold={6} size={72} style={{ left: 0, right: 0, top: 24, justifyContent: "center", zIndex: 70 }} />
      <Keys keys={["2"]} from={PRESS - 10} hold={14} size={90} style={{ left: 0, right: 0, top: 24, justifyContent: "center", zIndex: 70 }} />
      <UseCase label="Team call" opacity={interpolate(frame, [4, 14], [0, 1], clamp)} />
    </AbsoluteFill>
  );
};
