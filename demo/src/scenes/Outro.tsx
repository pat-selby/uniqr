import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Code } from "../components/Code";
import { Icon } from "../components/Icon";
import { LightStage } from "../components/Laptop";
import { L, MONO, UI } from "../theme";
import { SceneProps, cue, within } from "../timeline";

export const OUTRO = 150;

// The ending: "Try it out." and a real QR code for the site, so anyone who
// already runs UniQR can read it straight off the video.
export const SITE = "pat-selby.github.io/uniqr";
const SITE_URL = `https://${SITE}/`;

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

export const Outro: React.FC<SceneProps> = ({ t }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const mark = cue(t, 0, 6);
  const tryIt = within(t, 1, 0.62, 50); // "Try it out"
  const big = spring({ frame: frame - tryIt, fps, config: { damping: 14 } });
  const code = spring({ frame: frame - tryIt - 8, fps, config: { damping: 15 } });
  const text = interpolate(frame, [tryIt + 16, tryIt + 28], [0, 1], clamp);

  return (
    <LightStage>
      <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", fontFamily: UI }}>
        <div style={{ display: "flex", alignItems: "center", gap: 18, opacity: interpolate(frame, [mark, mark + 10], [0, 1], clamp) }}>
          <div style={{ padding: 12, borderRadius: 16, background: L.ink }}>
            <Icon size={44} animate from={mark} />
          </div>
          <span style={{ fontSize: 56, fontWeight: 800, color: L.ink, letterSpacing: -1 }}>UniQR</span>
        </div>
        <div style={{ fontSize: 150, fontWeight: 800, color: L.ink, letterSpacing: -5, marginTop: 18, opacity: big, transform: `scale(${0.85 + 0.15 * big})` }}>
          Try it out.
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 56, marginTop: 34 }}>
          <div style={{ background: "#fff", padding: 22, borderRadius: 22, boxShadow: "0 22px 50px rgba(20,24,32,0.18)", opacity: code, transform: `scale(${0.85 + 0.15 * code})` }}>
            <Code bcid="qrcode" text={SITE_URL} width={250} color={L.ink} />
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 16, opacity: text, transform: `translateX(${(1 - text) * 20}px)` }}>
            <div style={{ fontFamily: MONO, fontSize: 46, fontWeight: 700, color: L.ink }}>{SITE}</div>
            <div style={{ fontSize: 30, color: L.sub }}>Free and open source · Windows, Mac, Linux</div>
            <div style={{ fontSize: 30, color: L.ink, fontWeight: 600 }}>Got UniQR? Press the hotkey on this code.</div>
          </div>
        </div>
      </div>
    </LightStage>
  );
};
