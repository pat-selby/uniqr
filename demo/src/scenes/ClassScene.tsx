import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { Card } from "../components/Card";
import { Keys } from "../components/Keys";
import { Laptop } from "../components/Laptop";
import { UseCase } from "../components/OS";
import { CLASS_CODE, ClassScreen } from "../components/Screens";
import { SceneProps, cue, within } from "../timeline";

export const CLASS = 120;

// Use case: an online class. The attendance code is on the professor's slide.

const S = 1.5;
const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

export const ClassScene: React.FC<SceneProps> = ({ t }) => {
  const frame = useCurrentFrame();
  const KEYS_AT = cue(t, 1, 50) - 2; // "Windows key, Shift, Q" opens the line
  const CARD_IN = within(t, 1, 0.62, 80); // "It's copied"
  const zoom = interpolate(frame, [CARD_IN, CARD_IN + 24], [1, 1.55], { ...clamp, easing: Easing.inOut(Easing.cubic) });
  const card = (
    <Card
      scale={S}
      kind="Link"
      status="Copied"
      host="example.edu"
      rest="/attend/cs201-week6"
      buttons={[
        { label: "Open", primary: true },
        { label: "Dismiss", primary: false },
      ]}
      style={{ left: CLASS_CODE.left, top: CLASS_CODE.top + CLASS_CODE.size + 14 * S, opacity: interpolate(frame, [CARD_IN - 6, CARD_IN], [0, 1], clamp) }}
    />
  );

  return (
    <AbsoluteFill>
      <Laptop zoom={zoom} focus={{ x: CLASS_CODE.left + 200, y: CLASS_CODE.top + CLASS_CODE.size + 60 }} overlay={frame >= CARD_IN - 6 ? card : null}>
        <ClassScreen />
      </Laptop>
      <Keys keys={["Win", "Shift", "Q"]} from={KEYS_AT} hold={18} size={84} style={{ left: 0, right: 0, top: 24, justifyContent: "center", zIndex: 70 }} />
      <UseCase label="Online class" opacity={interpolate(frame, [4, 14, CARD_IN, CARD_IN + 10], [0, 1, 1, 0], clamp)} />
    </AbsoluteFill>
  );
};
