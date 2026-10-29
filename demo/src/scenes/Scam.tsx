import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { Card } from "../components/Card";
import { Keys } from "../components/Keys";
import { Laptop } from "../components/Laptop";
import { UseCase } from "../components/OS";
import { SCAM_HOST, ScamScreen, scamCode } from "../components/Screens";
import { useHotkey, usePlatform } from "../platform";
import { C } from "../theme";
import { SceneProps, cue, within } from "../timeline";

export const SCAM = 120;

// Use case: a "your package is on hold" email whose code hides the @ trick.
// The warning is the app's own text, from describe_link() in uniqr/actions.py.

const S = 1.5;
const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

export const Scam: React.FC<SceneProps> = ({ t }) => {
  const frame = useCurrentFrame();
  const SCAM_CODE = scamCode(usePlatform());
  const AIM = scamCode("windows"); // see ClassScene: keeps the zoom inside the screen
  const hotkey = useHotkey();
  const KEYS_AT = within(t, 0, 0.8, 60);
  const CARD_IN = KEYS_AT + 26;
  const LOOK = cue(t, 1, 100); // "Look at the card"
  const zoom = interpolate(frame, [LOOK - 4, LOOK + 26], [1, 1.6], { ...clamp, easing: Easing.inOut(Easing.cubic) });
  const ring = interpolate(frame, [LOOK + 22, LOOK + 32], [0, 1], clamp);

  const overlay =
    frame >= CARD_IN ? (
      <div style={{ position: "absolute", left: SCAM_CODE.left, top: SCAM_CODE.top + SCAM_CODE.size + 14 * S, width: 420 * S, opacity: interpolate(frame, [CARD_IN, CARD_IN + 6], [0, 1], clamp) }}>
        <Card
          scale={S}
          kind="Link"
          status="Copied"
          host={SCAM_HOST}
          rest="/fee"
          notes={[{ text: `Text before the @ is ignored. This really goes to ${SCAM_HOST}.`, warn: true }]}
          buttons={[
            { label: "Open", primary: true },
            { label: "Dismiss", primary: false },
          ]}
          style={{ left: 0, top: 0 }}
        />
        <div style={{ position: "absolute", left: -4 * S, top: 34 * S, width: 426 * S, height: 90 * S, border: `4px solid ${C.warn}`, borderRadius: 12, opacity: ring, boxShadow: `0 0 30px ${C.warn}88` }} />
      </div>
    ) : null;

  return (
    <AbsoluteFill>
      <Laptop zoom={zoom} focus={{ x: AIM.left + 300, y: AIM.top + AIM.size + 110 }} overlay={overlay}>
        <ScamScreen />
      </Laptop>
      <Keys keys={hotkey} from={KEYS_AT - 10} hold={18} size={84} style={{ left: 0, right: 0, top: 24, justifyContent: "center", zIndex: 70 }} />
      <UseCase label="A scam email" opacity={interpolate(frame, [4, 14, LOOK - 6, LOOK + 4], [0, 1, 1, 0], clamp)} />
    </AbsoluteFill>
  );
};
