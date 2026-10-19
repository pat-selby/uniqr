import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Icon } from "../components/Icon";
import { Keys } from "../components/Keys";
import { Laptop, LightStage } from "../components/Laptop";
import { PhoneCam } from "../components/PhoneCam";
import { ScamScreen } from "../components/Screens";
import { L } from "../theme";
import { SceneProps, Timing, cue, within } from "../timeline";

export const REVEAL = 120;

// "Too many." / "Keep the phone down. There's a faster way." The phone drops,
// and UniQR's name and hotkey take the screen. The sound bed hits here.
export const revealAt = (t: Timing) => within(t, 1, 0.72, 70);

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

export const Reveal: React.FC<SceneProps> = ({ t }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const drop = interpolate(frame, [cue(t, 1, 40), cue(t, 1, 40) + 16], [0, 1], clamp);
  const at = revealAt(t);
  const title = spring({ frame: frame - at, fps, config: { damping: 15 } });
  const laptopOut = interpolate(frame, [at - 8, at + 6], [1, 0], clamp);

  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ opacity: laptopOut }}>
        <Laptop>
          <ScamScreen />
        </Laptop>
        <PhoneCam show={1} away={drop} />
      </AbsoluteFill>
      {frame >= at - 8 ? (
        <AbsoluteFill style={{ opacity: Math.min(1, title * 1.4) }}>
          <LightStage>
            <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 34 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 34, transform: `scale(${0.9 + 0.1 * title})` }}>
                <div style={{ padding: 26, borderRadius: 34, background: L.ink, boxShadow: "0 24px 60px rgba(20,24,32,0.25)" }}>
                  <Icon size={130} animate from={at} />
                </div>
                <span style={{ fontSize: 170, fontWeight: 800, letterSpacing: -5, color: L.ink }}>UniQR</span>
              </div>
              <div style={{ fontSize: 44, color: L.sub }}>Read any QR code on your screen with one keypress.</div>
            </div>
          </LightStage>
          <Keys keys={["Win", "Shift", "Q"]} from={at + 8} hold={60} size={84} style={{ left: 0, right: 0, top: 800, justifyContent: "center" }} />
        </AbsoluteFill>
      ) : null}
    </AbsoluteFill>
  );
};
