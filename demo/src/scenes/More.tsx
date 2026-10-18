import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Card } from "../components/Card";
import { Code } from "../components/Code";
import { UseCase, WinBrowser, WinDesktop } from "../components/OS";
import { Picker } from "../components/Picker";
import { Stage } from "../components/Desktop";
import { StyledQR, QRStyle } from "../components/StyledQR";
import { C, HEIGHT, MONO, UI, WIDTH } from "../theme";
import { SceneProps, cue, within } from "../timeline";

export const MORE = 400;

// "What else?": a quick run of real features, one beat per line.
//   two screens        a scan covers the whole desktop, every monitor at once
//   a page of codes    the picker numbers every code it finds
//   styled codes       dots, rounded blocks, a logo, dark mode
//   your hotkey        a taken key falls back on Windows; or pick your own
//   start at login     the first-run question, and the tray menu's toggle
//   privacy            nothing is captured until the key; no history

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

export const More: React.FC<SceneProps> = ({ t }) => {
  const frame = useCurrentFrame();
  const beats = [0, cue(t, 2, 80), cue(t, 3, 160), cue(t, 4, 230), cue(t, 6, 330)];
  const PRIVATE = within(t, 7, 0.42, 380);
  const beat = beats.filter((b) => frame >= b).length - 1;
  const local = frame - beats[beat];
  const fadeIn = interpolate(local, [0, 6], [0, 1], clamp);
  const labels = ["Every screen at once", "A page full of codes", "Styled codes", "Your hotkey", "Start at login"];

  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ opacity: fadeIn }}>
        {beat === 0 ? <TwoScreens from={cue(t, 1, 30) + 6} /> : null}
        {beat === 1 ? <SearchPage from={within(t, 2, 0.45, 120)} /> : null}
        {beat === 2 ? <Styled start={beats[2]} /> : null}
        {beat === 3 ? (
          <HotkeyBeat
            taken={within(t, 4, 0.72, 250)}
            next={within(t, 5, 0.2, 280)}
            card={within(t, 5, 0.42, 295)}
            own={within(t, 5, 0.74, 310)}
          />
        ) : null}
        {beat === 4 ? <Login start={beats[4]} yes={cue(t, 7, 370) + 4} /> : null}
      </AbsoluteFill>
      {frame >= PRIVATE ? <Privacy from={PRIVATE} /> : null}
      <UseCase kicker="FEATURE" label={frame >= PRIVATE ? "Private by design" : labels[beat]} opacity={fadeIn} />
    </AbsoluteFill>
  );
};

// -- two screens --------------------------------------------------------------

const MON = [
  { x: 70, y: 150, w: 870, h: 490 },
  { x: 980, y: 150, w: 870, h: 490 },
];
const MON_CODE = [
  { left: MON[0].x + 560, top: MON[0].y + 120, size: 220, url: "https://example.com/screen-one" },
  { left: MON[1].x + 560, top: MON[1].y + 190, size: 200, url: "https://example.org/screen-two" },
];

const TwoScreens: React.FC<{ from: number }> = ({ from }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const dim = interpolate(frame, [from, from + 8], [0, 0.62], clamp);
  const pad = 10;
  return (
    <Stage>
      {MON.map((m, i) => (
        <React.Fragment key={i}>
          <div style={{ position: "absolute", left: m.x - 14, top: m.y - 14, width: m.w + 28, height: m.h + 28, borderRadius: 18, background: "#05070c", boxShadow: "0 30px 70px rgba(0,0,0,0.6)" }} />
          <div style={{ position: "absolute", left: m.x + m.w / 2 - 40, top: m.y + m.h + 14, width: 80, height: 90, background: "#1a1f2b" }} />
          <div style={{ position: "absolute", left: m.x + m.w / 2 - 150, top: m.y + m.h + 100, width: 300, height: 16, borderRadius: 8, background: "#1a1f2b" }} />
          <div style={{ position: "absolute", left: m.x, top: m.y, width: m.w, height: m.h, overflow: "hidden", borderRadius: 6, background: i === 0 ? "#f6f2ea" : "linear-gradient(135deg,#13294f,#0a1424)" }}>
            <div style={{ position: "absolute", left: 50, top: 70, width: 460, color: i === 0 ? "#2a2116" : "#fff", fontFamily: UI }}>
              <div style={{ fontSize: 22, letterSpacing: 3, fontWeight: 700, opacity: 0.7 }}>{i === 0 ? "MONITOR 1" : "MONITOR 2"}</div>
              <div style={{ fontSize: 44, fontWeight: 800, marginTop: 10, lineHeight: 1.1 }}>{i === 0 ? "Workshop sign-up" : "Live demo repo"}</div>
            </div>
          </div>
          <div style={{ position: "absolute", left: MON_CODE[i].left - 14, top: MON_CODE[i].top - 14, padding: 14, background: "#fff", borderRadius: 8 }}>
            <Code bcid="qrcode" text={MON_CODE[i].url} width={MON_CODE[i].size} />
          </div>
        </React.Fragment>
      ))}
      {/* the picker: one overlay over the whole desktop, both monitors */}
      <svg width={WIDTH} height={HEIGHT} style={{ position: "absolute" }}>
        <defs>
          <mask id="two-screens">
            {MON.map((m, i) => (
              <rect key={i} x={m.x} y={m.y} width={m.w} height={m.h} fill="white" />
            ))}
            {MON_CODE.map((c, i) => (
              <rect key={i} x={c.left - pad} y={c.top - pad} width={c.size + 2 * pad} height={c.size + 2 * pad} fill="black" />
            ))}
          </mask>
        </defs>
        <rect width={WIDTH} height={HEIGHT} fill="black" opacity={dim} mask="url(#two-screens)" />
      </svg>
      {frame >= from
        ? MON_CODE.map((c, i) => {
            const pop = spring({ frame: frame - from - 2 - i * 6, fps, config: { damping: 12 } });
            return (
              <React.Fragment key={i}>
                <div style={{ position: "absolute", left: c.left - 3, top: c.top - 3, width: c.size + 6, height: c.size + 6, boxSizing: "border-box", border: `4px solid ${C.accent}`, opacity: Math.min(1, pop * 2) }} />
                <div style={{ position: "absolute", left: c.left - 30, top: c.top - 30, width: 40, height: 40, borderRadius: 20, background: C.accent, color: C.badgeText, fontFamily: UI, fontWeight: 700, fontSize: 24, display: "grid", placeItems: "center", transform: `scale(${pop})` }}>
                  {i + 1}
                </div>
              </React.Fragment>
            );
          })
        : null}
    </Stage>
  );
};

// -- a page full of codes ----------------------------------------------------

const RESULTS = ["Menu", "Wi-Fi", "Event", "Survey", "Coupon", "Ticket", "Playlist", "Map"];
const GRID = { x: 170, y: 250, w: 380, h: 330, gap: 22, code: 190 };
const cell = (i: number) => ({
  x: GRID.x + (i % 4) * (GRID.w + GRID.gap),
  y: GRID.y + Math.floor(i / 4) * (GRID.h + GRID.gap),
});
const codeBox = (i: number) => {
  const c = cell(i);
  return { left: c.x + (GRID.w - GRID.code) / 2, top: c.y + 34, size: GRID.code };
};

const SearchPage: React.FC<{ from: number }> = ({ from }) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill>
      <WinDesktop active={1}>
        <WinBrowser x={90} y={30} w={1740} h={930} tab="qr code ideas - Search" url="example.com/search?q=qr+code+ideas&tab=images">
          <div style={{ position: "absolute", inset: 0, background: "#fff", fontFamily: UI }}>
            <div style={{ position: "absolute", left: 80, top: 24, width: 700, height: 52, borderRadius: 26, border: "1px solid #dadce0", display: "flex", alignItems: "center", padding: "0 24px", fontSize: 22, color: "#222", boxShadow: "0 1px 6px rgba(32,33,36,0.18)" }}>
              qr code ideas
            </div>
            <div style={{ position: "absolute", left: 100, top: 92, display: "flex", gap: 36, fontSize: 19, color: "#5f6368" }}>
              {["All", "Images", "Videos", "News"].map((tab) => (
                <span key={tab} style={tab === "Images" ? { color: "#1a73e8", fontWeight: 600, borderBottom: "3px solid #1a73e8", paddingBottom: 8 } : {}}>{tab}</span>
              ))}
            </div>
          </div>
        </WinBrowser>
        {RESULTS.map((name, i) => {
          const c = cell(i);
          const b = codeBox(i);
          return (
            <React.Fragment key={name}>
              <div style={{ position: "absolute", left: c.x, top: c.y, width: GRID.w, height: GRID.h, borderRadius: 14, background: ["#fdf3e7", "#eef4ff", "#f3eefe", "#eefaf3"][i % 4] }} />
              <div style={{ position: "absolute", left: b.left, top: b.top }}>
                <Code bcid="qrcode" text={`https://example.com/ideas/${name.toLowerCase()}`} width={b.size} />
              </div>
              <div style={{ position: "absolute", left: c.x + 20, top: c.y + GRID.h - 70, fontFamily: UI, fontSize: 21, color: "#202124", fontWeight: 600 }}>{name} QR code</div>
              <div style={{ position: "absolute", left: c.x + 20, top: c.y + GRID.h - 40, fontFamily: UI, fontSize: 17, color: "#5f6368" }}>example.com</div>
            </React.Fragment>
          );
        })}
      </WinDesktop>
      {frame >= from ? <Picker boxes={RESULTS.map((_, i) => codeBox(i))} from={from} /> : null}
    </AbsoluteFill>
  );
};

// -- styled codes -------------------------------------------------------------

const STYLES: { style: QRStyle; label: string; url: string }[] = [
  { style: "dots", label: "Dots", url: "https://example.com/styled/dots" },
  { style: "rounded", label: "Rounded", url: "https://example.com/styled/rounded" },
  { style: "logo", label: "Logo in the middle", url: "https://example.com/styled/logo" },
  { style: "dark", label: "Dark mode", url: "https://example.com/styled/dark" },
];

const Styled: React.FC<{ start: number }> = ({ start }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <Stage>
      <div style={{ position: "absolute", inset: 0, display: "flex", justifyContent: "center", alignItems: "center", gap: 46, fontFamily: UI }}>
        {STYLES.map((s, i) => {
          const pop = spring({ frame: frame - start - i * 5, fps, config: { damping: 13 } });
          const read = interpolate(frame, [start + 22 + i * 7, start + 30 + i * 7], [0, 1], clamp);
          return (
            <div key={s.style} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 20, opacity: pop, transform: `translateY(${(1 - pop) * 30}px)` }}>
              <div style={{ padding: s.style === "dark" ? 0 : 18, background: s.style === "dark" ? "transparent" : "#fff", borderRadius: 22, boxShadow: "0 20px 50px rgba(0,0,0,0.45)", border: s.style === "dark" ? `1px solid ${C.border}` : "none" }}>
                <StyledQR text={s.url} style={s.style} size={s.style === "dark" ? 316 : 280} />
              </div>
              <div style={{ color: C.cardFg, fontSize: 30, fontWeight: 700 }}>{s.label}</div>
              <div style={{ opacity: read, color: C.ok, fontSize: 24, fontWeight: 700, background: "rgba(63,178,127,0.12)", border: `1px solid ${C.ok}`, borderRadius: 20, padding: "6px 18px" }}>✓ Read</div>
            </div>
          );
        })}
      </div>
    </Stage>
  );
};

// -- your hotkey --------------------------------------------------------------

// From uniqr/hotkeys.py and INSTALL.md: on Windows a taken Win+Shift+Q falls
// back to Ctrl+Alt+Q, then Ctrl+Shift+9, and the startup card names the key it
// took. --hotkey sets your own.

const Cap: React.FC<{ label: string; dim?: boolean; accent?: boolean }> = ({ label, dim, accent }) => (
  <span
    style={{
      minWidth: 70,
      height: 70,
      padding: "0 20px",
      boxSizing: "border-box",
      display: "inline-flex",
      alignItems: "center",
      justifyContent: "center",
      borderRadius: 12,
      background: accent ? C.accent : "#f2f5fb",
      color: accent ? C.badgeText : "#1a2233",
      fontSize: 30,
      fontWeight: 700,
      fontFamily: UI,
      boxShadow: accent ? `0 0 30px ${C.accent}66` : "0 7px 0 #9aa6bd",
      opacity: dim ? 0.35 : 1,
    }}
  >
    {label}
  </span>
);

const Combo: React.FC<{ keys: string[]; dim?: boolean; accent?: boolean }> = ({ keys, dim, accent }) => (
  <span style={{ display: "inline-flex", alignItems: "center", gap: 12 }}>
    {keys.map((k, i) => (
      <React.Fragment key={k}>
        {i > 0 ? <span style={{ color: "#c9d3e8", fontSize: 30 }}>+</span> : null}
        <Cap label={k} dim={dim} accent={accent} />
      </React.Fragment>
    ))}
  </span>
);

const HotkeyBeat: React.FC<{ taken: number; next: number; card: number; own: number }> = ({ taken, next, card, own }) => {
  const frame = useCurrentFrame();
  const show = (at: number) => interpolate(frame, [at, at + 8], [0, 1], clamp);
  return (
    <WinDesktop active={-1}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 210, display: "flex", flexDirection: "column", alignItems: "center", gap: 60 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 34 }}>
          <span style={{ position: "relative" }}>
            <Combo keys={["Win", "Shift", "Q"]} dim={frame >= taken} />
            <span style={{ position: "absolute", top: -34, right: -30, background: C.warn, color: C.badgeText, fontFamily: UI, fontSize: 22, fontWeight: 800, padding: "5px 14px", borderRadius: 8, opacity: show(taken), transform: `scale(${0.7 + 0.3 * show(taken)})` }}>
              TAKEN
            </span>
          </span>
          <span style={{ opacity: show(next), display: "inline-flex", alignItems: "center", gap: 34 }}>
            <span style={{ color: "#fff", fontSize: 50 }}>→</span>
            <Combo keys={["Ctrl", "Alt", "Q"]} accent />
          </span>
        </div>
        <div style={{ opacity: show(own), transform: `translateY(${(1 - show(own)) * 14}px)`, display: "flex", alignItems: "center", gap: 22, fontFamily: UI, color: "#fff", fontSize: 30 }}>
          Or your own:
          <span style={{ fontFamily: MONO, fontSize: 32, background: C.cardBg, border: `1px solid ${C.border}`, borderRadius: 14, padding: "14px 24px", color: C.cardFg }}>
            UniQR.exe --hotkey <span style={{ color: C.accent }}>ctrl+alt+k</span>
          </span>
        </div>
      </div>
      {/* the startup card, which names the hotkey UniQR took */}
      <div style={{ position: "absolute", left: 1200, top: 820, opacity: show(card) }}>
        <Card scale={1.6} title="UniQR is running. Press Ctrl+Alt+Q to scan." style={{ position: "relative" }} />
      </div>
    </WinDesktop>
  );
};

// -- start at login -----------------------------------------------------------

const MENU = ["Scan now (Win+Shift+Q)", "Start at login", "Check for updates now", "Check for updates automatically", "Report a problem", "", "Exit UniQR"];

const Login: React.FC<{ start: number; yes: number }> = ({ start, yes }) => {
  const frame = useCurrentFrame();
  const S = 1.6;
  const answered = frame >= yes + 12;
  const menu = interpolate(frame, [yes + 16, yes + 24], [0, 1], clamp);
  return (
    <WinDesktop active={-1}>
      {/* the first-run card, near the bottom-right corner where the app puts it */}
      <div style={{ position: "absolute", left: 1150, top: 330 }}>
        {!answered ? (
          <Card
            scale={S}
            title="UniQR is running. Press Win+Shift+Q to scan."
            notes={[{ text: "Start UniQR automatically when you log in?", warn: false }]}
            buttons={[
              { label: "Yes, start at login", primary: true },
              { label: "Not now", primary: false },
            ]}
            hot={frame >= yes ? 0 : undefined}
            style={{ position: "relative", opacity: interpolate(frame, [start, start + 8], [0, 1], clamp) }}
          />
        ) : (
          <Card scale={S} title="UniQR will start when you log in." style={{ position: "relative" }} />
        )}
      </div>
      {/* the tray menu, with its tick */}
      <div
        style={{
          position: "absolute",
          right: 150,
          bottom: 90,
          width: 470,
          padding: "8px 6px",
          borderRadius: 10,
          background: "#2b2b2b",
          border: "1px solid #3d3d3d",
          boxShadow: "0 16px 40px rgba(0,0,0,0.5)",
          fontFamily: '"Segoe UI", sans-serif',
          color: "#f0f0f0",
          fontSize: 22,
          opacity: menu,
          transform: `translateY(${(1 - menu) * 16}px)`,
        }}
      >
        {MENU.map((item, i) =>
          item ? (
            <div key={item} style={{ display: "flex", alignItems: "center", gap: 14, padding: "10px 16px", borderRadius: 6, background: i === 1 ? "#3a3a3a" : "transparent" }}>
              <span style={{ width: 22, color: C.accent, fontWeight: 700 }}>{i === 1 ? "✓" : ""}</span>
              {item}
            </div>
          ) : (
            <div key={i} style={{ height: 1, background: "#444", margin: "6px 10px" }} />
          ),
        )}
      </div>
    </WinDesktop>
  );
};

// -- privacy -----------------------------------------------------------------

const Privacy: React.FC<{ from: number }> = ({ from }) => {
  const frame = useCurrentFrame();
  const show = interpolate(frame, [from, from + 10], [0, 1], clamp);
  const lines = ["Nothing is captured until you press the key.", "No scan history.", "Your scans stay on your machine."];
  return (
    <AbsoluteFill style={{ background: `rgba(6, 10, 20, ${0.78 * show})`, display: "grid", placeItems: "center", zIndex: 50 }}>
      <div style={{ opacity: show, transform: `scale(${0.94 + 0.06 * show})`, display: "flex", alignItems: "center", gap: 56, fontFamily: UI, color: C.cardFg }}>
        <div style={{ width: 200, height: 200, borderRadius: 40, background: C.cardBg, border: `2px solid ${C.border}`, display: "grid", placeItems: "center", boxShadow: `0 0 90px ${C.accent}44` }}>
          <svg width={110} height={130} viewBox="0 0 22 26">
            <path d="M5 11V7a6 6 0 0 1 12 0v4" fill="none" stroke={C.accent} strokeWidth="2.4" strokeLinecap="round" />
            <rect x="2" y="11" width="18" height="13" rx="3" fill={C.accent} />
            <circle cx="11" cy="17" r="2" fill={C.badgeText} />
          </svg>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
          {lines.map((line, i) => (
            <div key={line} style={{ fontSize: 44, fontWeight: i === 2 ? 800 : 600, opacity: interpolate(frame, [from + 4 + i * 8, from + 12 + i * 8], [0, 1], clamp) }}>
              {line}
            </div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};
