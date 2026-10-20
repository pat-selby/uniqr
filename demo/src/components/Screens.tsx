import React from "react";
import { Code } from "./Code";
import { Platform, usePlatform } from "../platform";
import { AppWindow, Browser, Desktop, FRAME } from "./OS";

// Three everyday moments with a QR code on a laptop screen, each in a window
// that fills a 1920 x 1080 screen on this cut's system. Made-up content,
// reserved example addresses. classCode(), callBoxes() and scamCode() say
// where each code sits, in screen pixels, so cards and the picker can be
// placed on it. The page inside each window is the same on every system;
// only the window's corner and title bar move.

const FONT = '"Segoe UI", system-ui, sans-serif';

// -- an online class ------------------------------------------------------------

// The video player, inside the browser page; the code, inside the player.
const PLAYER = { x: 36, y: 28, w: 1340, h: 754 };
const IN_PLAYER = { left: 880, top: 190, size: 320 };
export const classCode = (os: Platform) => {
  const f = FRAME[os];
  return { left: f.full.x + PLAYER.x + IN_PLAYER.left, top: f.full.y + f.browserBar + PLAYER.y + IN_PLAYER.top, size: IN_PLAYER.size };
};
export const CLASS_URL = "https://example.edu/attend/cs201-week6";

export const ClassScreen: React.FC = () => (
  <Desktop active={1} app="Safari" full>
    <Browser {...FRAME[usePlatform()].full} tab="CS 201: Week 6 (live)" url="example.edu/courses/cs201/live">
      <div style={{ position: "absolute", inset: 0, background: "#f6f7f9", fontFamily: FONT }}>
        <div
          style={{
            position: "absolute",
            left: PLAYER.x,
            top: PLAYER.y,
            width: PLAYER.w,
            height: PLAYER.h,
            borderRadius: 14,
            overflow: "hidden",
            background: "#ffffff",
            boxShadow: "0 2px 10px rgba(0,0,0,0.1)",
          }}
        >
          <div style={{ position: "absolute", left: 90, top: 150, width: 680, color: "#1b2333" }}>
            <div style={{ fontSize: 30, letterSpacing: 4, fontWeight: 700, color: "#b0552f" }}>CS 201 · WEEK 6</div>
            <div style={{ fontSize: 86, fontWeight: 800, lineHeight: 1.04, marginTop: 18 }}>Attendance check</div>
            <div style={{ fontSize: 34, color: "#5a6478", marginTop: 26 }}>Scan the code before 10:15.</div>
          </div>
          <div style={{ position: "absolute", left: IN_PLAYER.left, top: IN_PLAYER.top }}>
            <Code bcid="qrcode" text={CLASS_URL} width={IN_PLAYER.size} color="#1b2333" />
          </div>
          <div style={{ position: "absolute", left: 24, bottom: 24, width: 240, height: 150, borderRadius: 12, background: "linear-gradient(160deg,#c9b8a6,#9c8672)", display: "grid", placeItems: "center" }}>
            <div style={{ width: 70, height: 70, borderRadius: 35, background: "#efe4d8" }} />
          </div>
          <div style={{ position: "absolute", right: 20, top: 18, background: "#d6453d", color: "#fff", fontSize: 20, fontWeight: 800, padding: "4px 12px", borderRadius: 6 }}>LIVE</div>
        </div>
        <div style={{ position: "absolute", left: PLAYER.x + PLAYER.w + 28, top: 28, right: 28, bottom: 28, background: "#ffffff", borderRadius: 14, padding: 24, color: "#3a4256", fontSize: 22, display: "flex", flexDirection: "column", gap: 18, boxShadow: "0 2px 10px rgba(0,0,0,0.08)" }}>
          <div style={{ fontWeight: 700, color: "#1b2333", fontSize: 24 }}>Class chat</div>
          {[
            ["Dana", "is the code on the slide?"],
            ["Omar", "yep, scan it now"],
            ["Lee", "my phone is in my bag..."],
          ].map(([who, msg]) => (
            <div key={who}>
              <b style={{ color: "#b0552f" }}>{who} </b>
              {msg}
            </div>
          ))}
        </div>
      </div>
    </Browser>
  </Desktop>
);

// -- a team call ----------------------------------------------------------------

// The shared slide, inside the call window; the codes, inside the slide.
const SLIDE = { x: 24, y: 22, w: 1520, h: 855 };
const CALL_SIZE = 230;
const CALL_TOP = 360;
export const CALL_ITEMS = [
  { label: "Design", url: "https://example.com/q3/design" },
  { label: "Backend", url: "https://example.org/q3/backend" },
  { label: "Data", url: "https://example.net/q3/data" },
];
const IN_SLIDE = [0.2, 0.5, 0.8].map((k) => Math.round(SLIDE.w * k - CALL_SIZE / 2));
export const callBoxes = (os: Platform) => {
  const f = FRAME[os];
  return IN_SLIDE.map((left) => ({
    left: f.full.x + SLIDE.x + left,
    top: f.full.y + f.appBar + SLIDE.y + CALL_TOP,
    size: CALL_SIZE,
  }));
};

export const CallScreen: React.FC = () => (
  <Desktop active={3} app="Meetings" full>
    <AppWindow {...FRAME[usePlatform()].full} title="Team sync" icon="#6264a7">
      <div style={{ position: "absolute", inset: 0, background: "#26262c", fontFamily: FONT }}>
        <div style={{ position: "absolute", left: SLIDE.x, top: SLIDE.y, width: SLIDE.w, height: SLIDE.h, background: "#fbfaf7", borderRadius: 8, color: "#1a2233" }}>
          <div style={{ textAlign: "center", paddingTop: 90 }}>
            <div style={{ fontSize: 28, letterSpacing: 4, fontWeight: 700, color: "#6264a7" }}>Q3 PLANNING</div>
            <div style={{ fontSize: 70, fontWeight: 800, marginTop: 12 }}>Pick your workstream</div>
          </div>
          {CALL_ITEMS.map((item, i) => (
            <div key={item.url} style={{ position: "absolute", left: IN_SLIDE[i], top: CALL_TOP, width: CALL_SIZE, textAlign: "center" }}>
              <Code bcid="qrcode" text={item.url} width={CALL_SIZE} color="#1a2233" />
              <div style={{ fontSize: 32, fontWeight: 700, marginTop: 70 }}>{item.label}</div>
            </div>
          ))}
        </div>
        <div style={{ position: "absolute", right: 24, top: 22, width: 330, display: "flex", flexDirection: "column", gap: 18 }}>
          {[
            ["MK", "#c96f4a"],
            ["JR", "#5b8a72"],
            ["You", "#6264a7"],
          ].map(([who, color]) => (
            <div key={who} style={{ height: 200, borderRadius: 12, background: "#34343c", display: "grid", placeItems: "center" }}>
              <div style={{ width: 92, height: 92, borderRadius: 46, background: color, color: "#fff", fontSize: 32, fontWeight: 700, display: "grid", placeItems: "center" }}>{who}</div>
            </div>
          ))}
        </div>
      </div>
    </AppWindow>
  </Desktop>
);

// -- a scam email ---------------------------------------------------------------

// The reading pane, inside the mail window; the code, inside the pane.
const PANE = { x: 760 };
const IN_PANE = { left: 70, top: 330, size: 300 };
export const scamCode = (os: Platform) => {
  const f = FRAME[os];
  return { left: f.full.x + PANE.x + IN_PANE.left, top: f.full.y + f.appBar + IN_PANE.top, size: IN_PANE.size };
};
// The @ trick: everything before the @ is ignored, so this goes to the host
// after it. Both names are reserved examples.
export const SCAM_HOST = "pay-redelivery.example.net";
export const SCAM_URL = `https://parcel.example@${SCAM_HOST}/fee`;

export const ScamScreen: React.FC = () => (
  <Desktop active={2} app="Mail" full>
    <AppWindow {...FRAME[usePlatform()].full} title="Inbox - Mail" icon="#0f6cbd">
      <div style={{ position: "absolute", inset: 0, background: "#ffffff", fontFamily: FONT, color: "#1b2333" }}>
        <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: 260, background: "#f3f4f6", padding: "28px 24px", boxSizing: "border-box", fontSize: 24, display: "flex", flexDirection: "column", gap: 22 }}>
          <b>Inbox <span style={{ color: "#0f6cbd" }}>3</span></b>
          <span style={{ color: "#5a6478" }}>Sent</span>
          <span style={{ color: "#5a6478" }}>Drafts</span>
          <span style={{ color: "#5a6478" }}>Archive</span>
        </div>
        <div style={{ position: "absolute", left: 260, top: 0, bottom: 0, width: 480, borderRight: "1px solid #e3e6eb" }}>
          {[
            ["Parcel Service", "Your package is on hold", true],
            ["Ana", "Lunch on Friday?", false],
            ["Course updates", "Week 6 slides are up", false],
          ].map(([from, subject, selected]) => (
            <div key={String(subject)} style={{ padding: "22px 26px", borderBottom: "1px solid #eef0f3", background: selected ? "#e8f1fb" : "#fff", fontSize: 22 }}>
              <div style={{ fontWeight: 700 }}>{from}</div>
              <div style={{ color: "#5a6478", marginTop: 4 }}>{subject}</div>
            </div>
          ))}
        </div>
        <div style={{ position: "absolute", left: PANE.x, top: 0, right: 0, bottom: 0, padding: "40px 70px", boxSizing: "border-box" }}>
          <div style={{ fontSize: 44, fontWeight: 700 }}>Your package is on hold</div>
          <div style={{ fontSize: 22, color: "#5a6478", marginTop: 12 }}>Parcel Service &lt;alerts@parcel-notice.example&gt;</div>
          <div style={{ fontSize: 26, lineHeight: 1.5, marginTop: 36, maxWidth: 900 }}>
            We tried to deliver your package today. To schedule a new delivery, scan the code below and pay the redelivery fee.
          </div>
          <div style={{ position: "absolute", left: IN_PANE.left, top: IN_PANE.top }}>
            <Code bcid="qrcode" text={SCAM_URL} width={IN_PANE.size} color="#1b2333" />
          </div>
        </div>
      </div>
    </AppWindow>
  </Desktop>
);
