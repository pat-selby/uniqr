import React from "react";
import { C, MONO, UI, pt } from "../theme";

// A copy of _build_card() in uniqr/overlay.py, drawn in HTML. Sizes are the
// real ones in pixels; `scale` enlarges the whole card, like display scaling.

export type Note = { text: string; warn: boolean };
export type Button = { label: string; primary: boolean };

export type CardProps = {
  kind?: string; // the small badge, e.g. "Link" or "Wi-Fi"
  status?: string; // e.g. "Copied"; shown with a check mark
  host?: string; // for a web link: where it really goes
  rest?: string; // the path, dimmed
  body?: string; // for anything that is not a web link
  title?: string; // a card with no payload, e.g. "No QR code found on screen"
  notes?: Note[];
  buttons?: Button[];
  hot?: number; // index of the button under the pointer
  scale?: number;
  style?: React.CSSProperties;
};

const WRAP = 380;

export const Card: React.FC<CardProps> = ({
  kind,
  status,
  host,
  rest,
  body,
  title,
  notes = [],
  buttons = [],
  hot,
  scale = 1,
  style,
}) => {
  return (
    <div
      style={{
        position: "absolute",
        transform: `scale(${scale})`,
        transformOrigin: "top left",
        background: C.border,
        padding: 1,
        borderRadius: 8,
        boxShadow: "0 12px 32px rgba(0,0,0,0.45)",
        ...style,
      }}
    >
      <div
        style={{
          background: C.cardBg,
          padding: "15px 18px",
          borderRadius: 7,
          fontFamily: UI,
          color: C.cardFg,
          maxWidth: WRAP + 36,
          boxSizing: "border-box",
        }}
      >
        {title !== undefined ? (
          <div style={{ fontSize: pt(10), fontWeight: 700 }}>{title}</div>
        ) : (
          <>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 8,
              }}
            >
              <span
                style={{
                  background: C.raised,
                  color: C.muted,
                  fontSize: pt(7),
                  fontWeight: 700,
                  padding: "2px 8px",
                  letterSpacing: 0.3,
                }}
              >
                {(kind ?? "Link").toUpperCase()}
              </span>
              {status ? (
                <span
                  style={{
                    color: C.ok,
                    fontSize: pt(9),
                    fontWeight: 700,
                    marginLeft: 24,
                  }}
                >
                  ✓ {status}
                </span>
              ) : null}
            </div>
            {host !== undefined ? (
              <>
                <div
                  style={{
                    fontFamily: MONO,
                    fontSize: pt(12),
                    fontWeight: 700,
                    maxWidth: WRAP,
                    overflowWrap: "anywhere",
                  }}
                >
                  {host}
                </div>
                {rest && rest !== "/" ? (
                  <div
                    style={{
                      fontFamily: MONO,
                      fontSize: pt(9),
                      color: C.muted,
                      marginTop: 2,
                    }}
                  >
                    {rest}
                  </div>
                ) : null}
              </>
            ) : (
              <div style={{ fontSize: pt(10), maxWidth: WRAP, overflowWrap: "anywhere" }}>
                {body}
              </div>
            )}
          </>
        )}
        {notes.map((n) => (
          <div
            key={n.text}
            style={{
              color: n.warn ? C.warn : C.muted,
              fontSize: pt(9),
              marginTop: 6,
              maxWidth: WRAP,
              lineHeight: 1.3,
            }}
          >
            {n.warn ? "⚠ " : ""}
            {n.text}
          </div>
        ))}
        {buttons.length ? (
          <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
            {buttons.map((b, i) => {
              const isHot = hot === i;
              const bg = b.primary
                ? isHot
                  ? C.accentHover
                  : C.accent
                : isHot
                  ? C.buttonHover
                  : C.buttonBg;
              return (
                <span
                  key={b.label}
                  style={{
                    background: bg,
                    color: b.primary ? C.badgeText : C.cardFg,
                    fontSize: pt(9),
                    fontWeight: 700,
                    padding: "6px 16px",
                  }}
                >
                  {b.label}
                </span>
              );
            })}
          </div>
        ) : null}
      </div>
    </div>
  );
};
