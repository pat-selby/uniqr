import React from "react";
import { AbsoluteFill, Audio, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Card } from "./components/Card";
import { Code } from "./components/Code";
import { Fade } from "./components/Fade";
import { Icon } from "./components/Icon";
import { Keys } from "./components/Keys";
import { LightStage } from "./components/Laptop";
import { WinBrowser } from "./components/OS";
import { HOTKEY } from "./platform";
import { C, L, UI } from "./theme";

// A 20-second vertical clip for Instagram and other phone feeds, about the
// scam check in v0.2.7. It has no voice, so the captions tell the story and
// it works muted. Everything is drawn large for a phone: one browser window on
// a laptop screen, the code, and the app's card under it.
//
// The fake link is a reserved .example address. The warning is the app's own
// sentence, from brand_warning() in uniqr/linkcheck.py. PayPal appears as text
// only: no logo, no colors.

export const VERTICAL_W = 1080;
export const VERTICAL_H = 1920;
export const VERTICAL_FRAMES = 600;

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

// The beats, in frames at 30 fps.
const SAFE = { from: 0, to: 240 }; // a plain code, copied
const SCAM = { from: 240, to: 480 }; // the borrowed brand name
const END = { from: 480, to: VERTICAL_FRAMES };
const KEYS_AT = 110; // frames into a beat
const CARD_AT = KEYS_AT + 26;

// The laptop screen, and the code's place on it.
const SCREEN = { x: 50, y: 520, w: 980, h: 700 };
const CODE = { left: 560, top: 150, size: 340 }; // inside the browser page

const S = 2.1; // card scale: the app's card, enlarged for a phone

const SAFE_URL = "https://example.com/workshop/signup";
const SCAM_HOST = "paypal.com.account-verify.example";
const SCAM_URL = `https://${SCAM_HOST}/login`;
const SCAM_WARNING = "Mentions PayPal, but the site is account-verify.example, not PayPal's.";

const Caption: React.FC<{ text: string; at: number }> = ({ text, at }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pop = spring({ frame: frame - at, fps, config: { damping: 16 } });
  return (
    <div
      style={{
        position: "absolute",
        left: 70,
        right: 70,
        top: 200,
        textAlign: "center",
        fontFamily: UI,
        fontSize: 84,
        fontWeight: 800,
        lineHeight: 1.08,
        whiteSpace: "pre-line",
        letterSpacing: -1.5,
        color: L.ink,
        opacity: frame >= at ? pop : 0,
        transform: `translateY(${(1 - pop) * 24}px)`,
      }}
    >
      {text}
    </div>
  );
};

// A laptop screen showing one browser window that holds a page and its code.
const Screen: React.FC<{ tab: string; url: string; children: React.ReactNode }> = ({ tab, url, children }) => (
  <>
    <div style={{ position: "absolute", left: SCREEN.x - 18, top: SCREEN.y - 18, width: SCREEN.w + 36, height: SCREEN.h + 36, borderRadius: 30, background: "linear-gradient(180deg,#2a2d33,#1b1d22)", boxShadow: "0 40px 90px rgba(20,24,32,0.28)" }} />
    <div style={{ position: "absolute", left: SCREEN.x - 60, top: SCREEN.y + SCREEN.h + 18, width: SCREEN.w + 120, height: 26, borderRadius: "0 0 20px 20px", background: "linear-gradient(180deg,#d9dce1,#b9bdc4)" }} />
    <div style={{ position: "absolute", left: SCREEN.x, top: SCREEN.y, width: SCREEN.w, height: SCREEN.h, overflow: "hidden", borderRadius: 8, background: "#e9e4dc" }}>
      <WinBrowser x={0} y={0} w={SCREEN.w} h={SCREEN.h} tab={tab} url={url}>
        {children}
      </WinBrowser>
    </div>
  </>
);

const Page: React.FC<{ kicker: string; title: string; body: string; code: string; color: string }> = ({ kicker, title, body, code, color }) => (
  <div style={{ position: "absolute", inset: 0, background: "#ffffff", fontFamily: '"Segoe UI", system-ui, sans-serif', color: "#1b2333" }}>
    <div style={{ position: "absolute", left: 48, top: 70, width: 470 }}>
      <div style={{ fontSize: 24, letterSpacing: 3, fontWeight: 700, color }}>{kicker}</div>
      <div style={{ fontSize: 56, fontWeight: 800, lineHeight: 1.05, marginTop: 14 }}>{title}</div>
      <div style={{ fontSize: 28, color: "#5a6478", marginTop: 22, lineHeight: 1.35 }}>{body}</div>
    </div>
    <div style={{ position: "absolute", left: CODE.left, top: CODE.top }}>
      <Code bcid="qrcode" text={code} width={CODE.size} color="#1b2333" />
    </div>
  </div>
);

// One beat: the screen, the hotkey, and the card that answers it.
const Beat: React.FC<{ screen: React.ReactNode; card: React.ReactNode; caption: string; captionAt: number; ring?: boolean }> = ({ screen, card, caption, captionAt, ring }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const cardIn = spring({ frame: frame - CARD_AT, fps, config: { damping: 15 } });
  const glow = interpolate(frame, [CARD_AT + 20, CARD_AT + 30], [0, 1], clamp);
  return (
    <LightStage>
      {screen}
      <Keys keys={HOTKEY.windows} from={KEYS_AT} hold={40} size={96} style={{ left: 0, right: 0, top: 400, justifyContent: "center", zIndex: 10 }} />
      {frame >= CARD_AT ? (
        <div style={{ position: "absolute", left: 90, top: SCREEN.y + 104 + CODE.top + CODE.size + 24, width: 420 * S, opacity: Math.min(1, cardIn * 1.4), transform: `translateY(${(1 - cardIn) * 30}px)` }}>
          {card}
          {ring ? (
            <div style={{ position: "absolute", left: -4 * S, top: 34 * S, width: 426 * S, height: 74 * S, border: `6px solid ${C.warn}`, borderRadius: 18, opacity: glow, boxShadow: `0 0 40px ${C.warn}99` }} />
          ) : null}
        </div>
      ) : null}
      <Caption text={caption} at={captionAt} />
    </LightStage>
  );
};

const End: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pop = spring({ frame, fps, config: { damping: 15 } });
  const line = (at: number) => interpolate(frame, [at, at + 10], [0, 1], clamp);
  return (
    <LightStage>
      <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 48, fontFamily: UI, textAlign: "center", padding: "0 90px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 30, transform: `scale(${0.9 + 0.1 * pop})`, opacity: pop }}>
          <div style={{ padding: 24, borderRadius: 32, background: L.ink, boxShadow: "0 24px 60px rgba(20,24,32,0.25)" }}>
            <Icon size={120} animate from={4} />
          </div>
          <span style={{ fontSize: 150, fontWeight: 800, letterSpacing: -4, color: L.ink }}>UniQR</span>
        </div>
        <div style={{ fontSize: 58, fontWeight: 700, lineHeight: 1.2, color: L.ink, opacity: line(14) }}>Free and open source for Windows, Mac and Linux.</div>
        <div style={{ fontSize: 64, fontWeight: 800, color: C.accent, opacity: line(34) }}>Link in bio.</div>
      </div>
    </LightStage>
  );
};

export const Vertical: React.FC = () => (
  <AbsoluteFill style={{ background: L.stage }}>
    <Sequence from={SAFE.from} durationInFrames={SAFE.to - SAFE.from}>
      <Fade duration={SAFE.to - SAFE.from} color={L.stage} edge={8}>
        <SafeBeat />
      </Fade>
    </Sequence>
    <Sequence from={SCAM.from} durationInFrames={SCAM.to - SCAM.from}>
      <Fade duration={SCAM.to - SCAM.from} color={L.stage} edge={8}>
        <ScamBeat />
      </Fade>
    </Sequence>
    <Sequence from={END.from} durationInFrames={END.to - END.from}>
      <Fade duration={END.to - END.from} color={L.stage} edge={8}>
        <End />
      </Fade>
    </Sequence>
    <Audio src={staticFile("sfx/pad_bright.wav")} volume={(f) => interpolate(f, [0, 20, VERTICAL_FRAMES - 30, VERTICAL_FRAMES], [0, 0.35, 0.35, 0], clamp)} />
    {[SCAM.from - 6, END.from - 6].map((at) => (
      <Sequence key={at} from={at} durationInFrames={24}>
        <Audio src={staticFile("sfx/whoosh.wav")} volume={0.4} />
      </Sequence>
    ))}
    <Sequence from={SCAM.from + CARD_AT + 20} durationInFrames={60}>
      <Audio src={staticFile("sfx/impact.wav")} volume={0.35} />
    </Sequence>
  </AbsoluteFill>
);

const SafeBeat: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <Beat
      screen={
        <Screen tab="Workshop sign-up" url="example.com/workshop">
          <Page kicker="SATURDAY WORKSHOP" title="Save your seat" body="Scan the code to sign up." code={SAFE_URL} color="#b0552f" />
        </Screen>
      }
      card={
        <Card scale={S} kind="Link" status="Copied" host="example.com" rest="/workshop/signup" buttons={[{ label: "Open", primary: true }, { label: "Dismiss", primary: false }]} style={{ left: 0, top: 0 }} />
      }
      caption={frame < KEYS_AT ? "A QR code\non your laptop?" : "One shortcut.\nLink copied."}
      captionAt={frame < KEYS_AT ? 6 : KEYS_AT}
    />
  );
};

const ScamBeat: React.FC = () => (
  <Beat
    screen={
      <Screen tab="Inbox - Mail" url="mail.example.com/inbox">
        <Page kicker="ACCOUNT NOTICE" title="Your account is on hold" body="Scan to confirm your PayPal details today." code={SCAM_URL} color="#8a5a00" />
      </Screen>
    }
    card={
      <Card
        scale={S}
        kind="Link"
        status="Copied"
        host={SCAM_HOST}
        rest="/login"
        notes={[{ text: SCAM_WARNING, warn: true }]}
        buttons={[{ label: "Open", primary: true }, { label: "Dismiss", primary: false }]}
        style={{ left: 0, top: 0 }}
      />
    }
    caption={"It spots scam tricks\nbefore you click."}
    captionAt={8}
    ring
  />
);
