import React from "react";
import { AbsoluteFill, Audio, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Card } from "./components/Card";
import { Code } from "./components/Code";
import { Icon } from "./components/Icon";
import { Keys } from "./components/Keys";
import { LightStage } from "./components/Laptop";
import { InSquare, WinBrowser } from "./components/OS";
import { PhoneCam } from "./components/PhoneCam";
import { Monitors } from "./scenes/Monitors";
import { Platforms } from "./scenes/Platforms";
import { HOTKEY } from "./platform";
import { C, HEIGHT, L, UI, WIDTH } from "./theme";
import { timing } from "./timeline";

// A square, 34-second story for a first LinkedIn post: "I kept reaching for my
// phone to scan my own laptop, so I built UniQR." No voice, so the captions
// carry it and it works muted. Every scene is drawn, not recorded, so each
// carries an "Illustration" tag. No brand names anywhere: the warning uses the
// @ trick on reserved .example addresses, in the app's own words from
// describe_link() in uniqr/actions.py.

export const STORY = 1080;
export const STORY_FRAMES = 1020;

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

// The beats, in frames at 30 fps.
const HOOK = { from: 0, to: 120 };
const BUILT = { from: 120, to: 360 };
const CHECK = { from: 360, to: 600 };
const SYSTEMS = { from: 600, to: 810 };
const CLOSE = { from: 810, to: STORY_FRAMES };

// The laptop screen, and the page and code inside its browser window.
const SCREEN = { x: 40, y: 300, w: 1000, h: 600 };
const BAR = 104; // the browser's tab row and address bar
const CODE = { left: 640, top: 70, size: 300 };
const CODE_BOTTOM = SCREEN.y + BAR + CODE.top + CODE.size; // on the video frame
const S = 1.8; // the app's card, enlarged for a phone
// The card hangs under its code, lined up with the code's right edge, as the
// app places it. Cards grow to the left, so they're anchored on the right.
const CARD_RIGHT = STORY - (SCREEN.x + CODE.left + CODE.size);
const UNDER_CODE = { right: 0, left: "auto", top: 0, transformOrigin: "top right" } as const;
const KEYS_TOP = SCREEN.y + 12; // over the browser's bars, clear of the page and the code

const CLASS_URL = "https://example.edu/attend/cs201-week6";
const SCAM_HOST = "login-verify.example";
const SCAM_URL = `https://yourbank.example@${SCAM_HOST}/`;
const SCAM_WARNING = `Text before the @ is ignored. This really goes to ${SCAM_HOST}.`;
const SITE = "pat-selby.github.io/uniqr";

export const Caption: React.FC<{ text: string; at?: number }> = ({ text, at = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pop = spring({ frame: frame - at, fps, config: { damping: 16 } });
  return (
    <div
      style={{
        position: "absolute",
        left: 60,
        right: 60,
        top: 70,
        height: 190,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        textAlign: "center",
        whiteSpace: "pre-line",
        fontFamily: UI,
        fontSize: 66,
        fontWeight: 800,
        lineHeight: 1.1,
        letterSpacing: -1.2,
        color: L.ink,
        opacity: frame >= at ? pop : 0,
        transform: `translateY(${(1 - pop) * 20}px)`,
      }}
    >
      {text}
    </div>
  );
};

// Marks a drawn scene, so no one takes it for a screen recording.
export const Illustration: React.FC = () => (
  <div style={{ position: "absolute", left: 40, bottom: 34, padding: "8px 16px", borderRadius: 10, background: "rgba(21,23,28,0.78)", color: "#ffffff", fontFamily: UI, fontSize: 24, fontWeight: 600, letterSpacing: 0.3, zIndex: 80 }}>
    Illustration
  </div>
);

// A laptop screen showing one browser window.
export const Screen: React.FC<{ tab: string; url: string; children: React.ReactNode }> = ({ tab, url, children }) => (
  <>
    <div style={{ position: "absolute", left: SCREEN.x - 16, top: SCREEN.y - 16, width: SCREEN.w + 32, height: SCREEN.h + 32, borderRadius: 28, background: "linear-gradient(180deg,#2a2d33,#1b1d22)", boxShadow: "0 36px 80px rgba(20,24,32,0.26)" }} />
    <div style={{ position: "absolute", left: SCREEN.x - 50, top: SCREEN.y + SCREEN.h + 16, width: SCREEN.w + 100, height: 24, borderRadius: "0 0 18px 18px", background: "linear-gradient(180deg,#d9dce1,#b9bdc4)" }} />
    <div style={{ position: "absolute", left: SCREEN.x, top: SCREEN.y, width: SCREEN.w, height: SCREEN.h, overflow: "hidden", borderRadius: 6 }}>
      <WinBrowser x={0} y={0} w={SCREEN.w} h={SCREEN.h} tab={tab} url={url}>
        {children}
      </WinBrowser>
    </div>
  </>
);

const Page: React.FC<{ kicker: string; title: string; body: string; code: string; color: string; children?: React.ReactNode }> = ({ kicker, title, body, code, color, children }) => (
  <div style={{ position: "absolute", inset: 0, background: "#ffffff", fontFamily: '"Segoe UI", system-ui, sans-serif', color: "#1b2333" }}>
    <div style={{ position: "absolute", left: 50, top: 70, width: 540 }}>
      <div style={{ fontSize: 24, letterSpacing: 3, fontWeight: 700, color }}>{kicker}</div>
      <div style={{ fontSize: 58, fontWeight: 800, lineHeight: 1.04, marginTop: 14 }}>{title}</div>
      <div style={{ fontSize: 28, color: "#5a6478", marginTop: 20, lineHeight: 1.35 }}>{body}</div>
    </div>
    <div style={{ position: "absolute", left: CODE.left, top: CODE.top }}>
      <Code bcid="qrcode" text={code} width={CODE.size} color="#1b2333" />
    </div>
    {children}
  </div>
);

const ClassPage: React.FC<{ pasted?: number }> = ({ pasted = 0 }) => (
  <Screen tab="CS 201: Week 6 (live)" url="example.edu/courses/cs201/live">
    <Page kicker="CS 201 · WEEK 6" title="Attendance check" body="Scan the code before 10:15." code={CLASS_URL} color="#b0552f">
      {/* The class chat's message box, where the copied link gets pasted. */}
      <div style={{ position: "absolute", left: 50, top: 330, width: 520, height: 64, borderRadius: 12, border: "2px solid #d5d8de", display: "flex", alignItems: "center", padding: "0 18px", fontSize: 24, color: pasted > 0 ? "#1b2333" : "#9aa1ad", boxSizing: "border-box", overflow: "hidden", whiteSpace: "nowrap" }}>
        {pasted > 0 ? CLASS_URL.slice(0, Math.round(CLASS_URL.length * pasted)) : "Message the class"}
      </div>
    </Page>
  </Screen>
);

const CardAt: React.FC<{ at: number; children: React.ReactNode; ring?: number }> = ({ at, children, ring }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pop = spring({ frame: frame - at, fps, config: { damping: 15 } });
  const glow = ring === undefined ? 0 : interpolate(frame, [at + 24, at + 34], [0, 1], clamp);
  if (frame < at) return null;
  return (
    <div style={{ position: "absolute", right: CARD_RIGHT, top: CODE_BOTTOM + 14, width: 420 * S, opacity: Math.min(1, pop * 1.4), transform: `translateY(${(1 - pop) * 24}px)`, zIndex: 20 }}>
      {children}
      {ring !== undefined ? (
        <div style={{ position: "absolute", right: -4 * S, top: 34 * S, width: 426 * S, height: ring * S, border: `6px solid ${C.warn}`, borderRadius: 16, opacity: glow, boxShadow: `0 0 36px ${C.warn}99` }} />
      ) : null}
    </div>
  );
};

const HotKeys: React.FC<{ at: number; keys?: string[] }> = ({ at, keys = HOTKEY.windows }) => (
  <Keys keys={keys} from={at} hold={34} size={92} style={{ left: 0, right: 0, top: KEYS_TOP, justifyContent: "center", zIndex: 30 }} />
);

// 1. The problem: a phone held up to a laptop.
const Hook: React.FC = () => {
  const frame = useCurrentFrame();
  const show = interpolate(frame, [16, 46], [0, 1], { ...clamp, easing: (x) => 1 - Math.pow(1 - x, 3) });
  return (
    <LightStage>
      <ClassPage />
      {/* The phone is placed for the wide frame; move it onto this one. */}
      <div style={{ position: "absolute", left: -560, top: 140 }}>
        <PhoneCam show={show} away={0} />
      </div>
      <Caption text={"Why am I using my phone\nto scan my laptop?"} at={4} />
      <Illustration />
    </LightStage>
  );
};

// 2. The fix: one shortcut, the card, then the link pasted where it's needed.
const Built: React.FC = () => {
  const frame = useCurrentFrame();
  const paste = interpolate(frame, [170, 182], [0, 1], clamp);
  return (
    <LightStage>
      <ClassPage pasted={paste} />
      <HotKeys at={20} />
      <CardAt at={52}>
        <Card scale={S} kind="Link" status="Copied" host="example.edu" rest="/attend/cs201-week6" buttons={[{ label: "Open", primary: true }, { label: "Dismiss", primary: false }]} style={UNDER_CODE} />
      </CardAt>
      <Keys keys={["Ctrl", "V"]} from={150} hold={20} size={80} style={{ left: 0, right: 0, top: KEYS_TOP, justifyContent: "center", zIndex: 30 }} />
      <Caption text={"So I built UniQR.\nOne shortcut."} at={6} />
      <Illustration />
    </LightStage>
  );
};

// 3. The check: a code whose link hides where it goes.
const Check: React.FC = () => (
  <LightStage>
    <Screen tab="Inbox - Mail" url="mail.example.com/inbox">
      <Page kicker="ACCOUNT ALERT" title="Confirm your login" body="Scan the code to keep your account open." code={SCAM_URL} color="#8a5a00" />
    </Screen>
    <HotKeys at={30} />
    <CardAt at={62} ring={58}>
      <Card scale={S} kind="Link" status="Copied" host={SCAM_HOST} notes={[{ text: SCAM_WARNING, warn: true }]} buttons={[{ label: "Open", primary: true }, { label: "Dismiss", primary: false }]} style={UNDER_CODE} />
    </CardAt>
    <Caption text={"Check the link\nbefore opening it."} at={6} />
    <Illustration />
  </LightStage>
);

// 4. Every system, and every monitor: the wide video's scenes, shown whole.
const WIDE_SCALE = STORY / WIDTH;
const Wide: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{ position: "absolute", left: 0, top: 300, width: WIDTH, height: HEIGHT, transform: `scale(${WIDE_SCALE})`, transformOrigin: "0 0" }}>
    <InSquare.Provider value={true}>{children}</InSquare.Provider>
  </div>
);
const Systems: React.FC = () => (
  <LightStage>
    <Sequence from={-14} durationInFrames={140} layout="none">
      <Wide>
        <Platforms t={timing("platforms", 150)} />
      </Wide>
    </Sequence>
    <Sequence from={126} layout="none">
      <Sequence from={-30} layout="none">
        <Wide>
          <Monitors t={timing("monitors", 120)} />
        </Wide>
      </Sequence>
    </Sequence>
    <Caption text={"Windows, Mac and Linux."} at={6} />
    <Illustration />
  </LightStage>
);

// 5. Back to the app, then where to get it.
const Close: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const end = spring({ frame: frame - 90, fps, config: { damping: 15 } });
  return (
    <LightStage>
      {frame < 96 ? (
        <>
          <ClassPage />
          <HotKeys at={6} />
          <CardAt at={30}>
            <Card scale={S} kind="Link" status="Copied" host="example.edu" rest="/attend/cs201-week6" buttons={[{ label: "Open", primary: true }, { label: "Dismiss", primary: false }]} style={UNDER_CODE} />
          </CardAt>
          <Illustration />
        </>
      ) : (
        <div style={{ position: "absolute", left: 0, right: 0, top: 300, bottom: 60, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 34, fontFamily: UI, opacity: end, transform: `scale(${0.94 + 0.06 * end})` }}>
          <div style={{ display: "flex", alignItems: "center", gap: 26 }}>
            <div style={{ padding: 20, borderRadius: 26, background: L.ink }}>
              <Icon size={92} animate from={92} />
            </div>
            <span style={{ fontSize: 118, fontWeight: 800, letterSpacing: -3, color: L.ink }}>UniQR</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 30 }}>
            <div style={{ padding: 14, background: "#ffffff", borderRadius: 14, boxShadow: "0 12px 30px rgba(20,24,32,0.12)" }}>
              <Code bcid="qrcode" text={`https://${SITE}/`} width={210} color={L.ink} />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <span style={{ fontSize: 44, fontWeight: 800, color: C.accent }}>{SITE}</span>
              <span style={{ fontSize: 30, color: L.sub }}>Free and open source.</span>
            </div>
          </div>
        </div>
      )}
      <Caption text={"Still reaching for your phone?\nTry UniQR."} at={6} />
    </LightStage>
  );
};

const BEATS: [React.FC, { from: number; to: number }][] = [
  [Hook, HOOK],
  [Built, BUILT],
  [Check, CHECK],
  [Systems, SYSTEMS],
  [Close, CLOSE],
];

const FadeIn: React.FC<{ length: number; children: React.ReactNode }> = ({ length, children }) => {
  const frame = useCurrentFrame();
  const o = interpolate(frame, [0, 8, length - 8, length], [0, 1, 1, 0], clamp);
  return <AbsoluteFill style={{ opacity: o }}>{children}</AbsoluteFill>;
};

export const Story: React.FC = () => (
  <AbsoluteFill style={{ background: L.stage }}>
    {BEATS.map(([Beat, b]) => (
      <Sequence key={b.from} from={b.from} durationInFrames={b.to - b.from}>
        <FadeIn length={b.to - b.from}>
          <Beat />
        </FadeIn>
      </Sequence>
    ))}
    <Audio src={staticFile("sfx/pad_bright.wav")} volume={(f) => interpolate(f, [0, 20, STORY_FRAMES - 40, STORY_FRAMES], [0, 0.25, 0.25, 0], clamp)} />
    {BEATS.slice(1).map(([, b]) => (
      <Sequence key={b.from} from={b.from - 6} durationInFrames={24}>
        <Audio src={staticFile("sfx/whoosh.wav")} volume={0.3} />
      </Sequence>
    ))}
  </AbsoluteFill>
);

// The post's cover image: one frame, the laptop and its code.
export const Cover: React.FC = () => (
  <LightStage>
    <ClassPage />
    <Caption text={"Your laptop\ncan scan that."} at={-60} />
    <Illustration />
  </LightStage>
);
