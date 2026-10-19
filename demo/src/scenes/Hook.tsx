import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { Laptop } from "../components/Laptop";
import { PhoneCam } from "../components/PhoneCam";
import { CallScreen, ClassScreen, ScamScreen } from "../components/Screens";
import { SceneProps, cue } from "../timeline";

export const HOOK = 150;

// The hook: three everyday moments flash by on the laptop, a class, a call,
// an email, each with a QR code, and each time the phone comes up to scan it.

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

export const Hook: React.FC<SceneProps> = ({ t }) => {
  const frame = useCurrentFrame();
  const start = cue(t, 0, 6);
  const span = Math.max(40, Math.round(((t.ends[0] ?? start + 150) - start) / 3));
  const which = Math.min(2, Math.floor(Math.max(0, frame - start) / span));
  const local = frame - start - which * span;
  // The phone comes up for each moment and dips between them.
  const lift = interpolate(local, [4, 16, span - 8, span], [0, 1, 1, which === 2 ? 1 : 0.55], clamp);
  const flash = interpolate(local, [0, 5], [0.5, 0], clamp);

  return (
    <AbsoluteFill>
      <Laptop>
        {which === 0 ? <ClassScreen /> : which === 1 ? <CallScreen /> : <ScamScreen />}
        <AbsoluteFill style={{ background: "#fff", opacity: frame > start ? flash : 0 }} />
      </Laptop>
      <PhoneCam show={lift} away={0} />
    </AbsoluteFill>
  );
};
