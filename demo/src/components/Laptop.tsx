import React from "react";
import { AbsoluteFill } from "remotion";
import { HEIGHT, L, UI, WIDTH } from "../theme";

// A laptop on a light stage. Whatever is passed in is drawn as a full
// 1920 x 1080 screen and fitted into the laptop's display, so every scene
// keeps working in screen pixels. `zoom` and `focus` (in screen pixels) move
// the camera in, for example onto UniQR's card.

export const SCREEN_W = 1340;
export const SCREEN_SCALE = SCREEN_W / WIDTH;
const SCREEN_H = HEIGHT * SCREEN_SCALE;
const BEZEL = 18;
const TOP = 70;
const LEFT = (WIDTH - SCREEN_W) / 2;

// Where a screen pixel lands in the video frame, before any zoom.
export const toFrame = (x: number, y: number) => ({
  x: LEFT + x * SCREEN_SCALE,
  y: TOP + y * SCREEN_SCALE,
});

export const LightStage: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AbsoluteFill
    style={{
      background: `radial-gradient(ellipse at 50% 40%, #ffffff 0%, ${L.stage} 55%, ${L.stageEdge} 100%)`,
      fontFamily: UI,
      color: L.ink,
    }}
  >
    {children}
  </AbsoluteFill>
);

export const Laptop: React.FC<{
  children: React.ReactNode;
  zoom?: number;
  focus?: { x: number; y: number };
  overlay?: React.ReactNode; // drawn over the screen, in screen pixels (e.g. the picker)
}> = ({ children, zoom = 1, focus, overlay }) => {
  const f = focus ? toFrame(focus.x, focus.y) : { x: WIDTH / 2, y: HEIGHT / 2 };
  return (
    <LightStage>
      <AbsoluteFill style={{ transform: `scale(${zoom})`, transformOrigin: `${f.x}px ${f.y}px` }}>
        {/* soft shadow on the desk */}
        <div
          style={{
            position: "absolute",
            left: LEFT - 40,
            top: TOP + SCREEN_H + 40,
            width: SCREEN_W + 80,
            height: 60,
            borderRadius: "50%",
            background: "radial-gradient(ellipse, rgba(20,24,32,0.28) 0%, transparent 70%)",
          }}
        />
        {/* the lid */}
        <div
          style={{
            position: "absolute",
            left: LEFT - BEZEL,
            top: TOP - BEZEL,
            width: SCREEN_W + BEZEL * 2,
            height: SCREEN_H + BEZEL * 2,
            borderRadius: 26,
            background: "linear-gradient(180deg, #2a2d33 0%, #1b1d22 100%)",
            boxShadow: "0 30px 70px rgba(20,24,32,0.25), inset 0 0 0 1px rgba(255,255,255,0.06)",
          }}
        />
        {/* the screen */}
        <div
          style={{
            position: "absolute",
            left: LEFT,
            top: TOP,
            width: SCREEN_W,
            height: SCREEN_H,
            overflow: "hidden",
            borderRadius: 6,
            background: "#000",
          }}
        >
          <div style={{ position: "absolute", left: 0, top: 0, width: WIDTH, height: HEIGHT, transform: `scale(${SCREEN_SCALE})`, transformOrigin: "0 0" }}>
            <AbsoluteFill>{children}</AbsoluteFill>
            {overlay ? <AbsoluteFill>{overlay}</AbsoluteFill> : null}
          </div>
        </div>
        {/* the base */}
        <div
          style={{
            position: "absolute",
            left: LEFT - 110,
            top: TOP + SCREEN_H + BEZEL,
            width: SCREEN_W + 220,
            height: 30,
            borderRadius: "0 0 22px 22px",
            background: "linear-gradient(180deg, #d9dce1 0%, #b9bdc4 100%)",
            boxShadow: "0 8px 18px rgba(20,24,32,0.18)",
          }}
        >
          <div style={{ position: "absolute", left: "50%", top: 0, width: 200, height: 10, transform: "translateX(-50%)", borderRadius: "0 0 10px 10px", background: "#a9adb5" }} />
        </div>
      </AbsoluteFill>
    </LightStage>
  );
};
