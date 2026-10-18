"""Make the sound bed: every sound in the video besides the voice.

All of it is synthesized here from sine waves and noise, so there is nothing
to license. The video decides where each piece plays and how loud (see
src/Soundtrack.tsx); this script only makes the pieces.

    pad_dark    a low A minor drone, for the problem and the safety twist
    pad_bright  a slow A minor, F, C, G progression with soft plucks, for UniQR
    pulse       a low heartbeat, for tension
    riser       four seconds of rising noise and tone, into the reveal
    impact      a deep hit with a tail, for the reveal and the last word
    whoosh      a short air sweep, between scenes

Needs numpy and scipy:  pip install numpy scipy
Run from the demo folder:  python tools/make_music.py
"""

import wave
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfilt

RATE = 32000
OUT = Path(__file__).resolve().parent.parent / "public" / "sfx"
RNG = np.random.default_rng(7)


def note(name: str) -> float:
    """Frequency of a note like "A2" or "C#3"."""
    steps = {"C": -9, "C#": -8, "D": -7, "D#": -6, "E": -5, "F": -4, "F#": -3,
             "G": -2, "G#": -1, "A": 0, "A#": 1, "B": 2}
    letter, octave = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((steps[letter] + 12 * (octave - 4)) / 12)


def times(seconds: float) -> np.ndarray:
    return np.arange(int(seconds * RATE)) / RATE


def lowpass(x: np.ndarray, hz: float, order: int = 2) -> np.ndarray:
    return sosfilt(butter(order, hz, "low", fs=RATE, output="sos"), x)


def bandpass(x: np.ndarray, lo: float, hi: float) -> np.ndarray:
    return sosfilt(butter(2, [lo, hi], "band", fs=RATE, output="sos"), x)


def warm(freq: float, t: np.ndarray, harmonics: int = 5) -> np.ndarray:
    """A soft, slightly detuned tone: three voices, harmonics falling away."""
    out = np.zeros_like(t)
    for cents in (-7, 0, 7):
        f = freq * 2 ** (cents / 1200)
        phase = RNG.uniform(0, 2 * np.pi)
        for k in range(1, harmonics + 1):
            out += np.sin(2 * np.pi * f * k * t + phase * k) / k**1.6
    return out


def fade(x: np.ndarray, fade_in: float, fade_out: float) -> np.ndarray:
    env = np.ones_like(x)
    a, b = int(fade_in * RATE), int(fade_out * RATE)
    if a:
        env[:a] = np.linspace(0, 1, a)
    if b:
        env[-b:] = np.minimum(env[-b:], np.linspace(1, 0, b))
    return x * env


def tail(x: np.ndarray, seconds: float = 2.5, feedback: float = 0.55) -> np.ndarray:
    """A cheap reverb: a few spread-out echoes that fade, then smoothed."""
    out = np.concatenate([x, np.zeros(int(seconds * RATE))])
    dry = out.copy()
    for delay_ms, gain in ((37, 0.6), (53, 0.5), (79, 0.45), (113, 0.4), (167, 0.35)):
        d = int(delay_ms / 1000 * RATE)
        echo = np.zeros_like(out)
        for k in range(1, 12):
            if k * d >= len(out):
                break
            echo[k * d:] += dry[: len(out) - k * d] * (gain * feedback ** (k - 1))
        out += echo * 0.35
    return lowpass(out, 5000)


def save(name: str, x: np.ndarray, peak: float = 0.9) -> None:
    x = x / (np.abs(x).max() or 1) * peak
    OUT.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUT / f"{name}.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print(f"{name:11} {len(x) / RATE:6.1f}s")


def pad_dark(seconds: float = 180) -> np.ndarray:
    t = times(seconds)
    x = sum(warm(note(n), t, 6) * a for n, a in (("A1", 1.0), ("E2", 0.6), ("A2", 0.5), ("C3", 0.35)))
    # A slow swell and a filter that breathes, so the drone never sits still.
    swell = 0.75 + 0.25 * np.sin(2 * np.pi * t / 11)
    x = lowpass(x * swell, 700) + 0.4 * lowpass(x, 260)
    return fade(x, 3, 3)


CHORDS = [
    ("A2", "C4", "E4", "A4"),  # A minor
    ("F2", "C4", "F4", "A4"),  # F
    ("C3", "E4", "G4", "C5"),  # C
    ("G2", "D4", "G4", "B4"),  # G
]


def pad_bright(seconds: float = 180, bar: float = 4.0) -> np.ndarray:
    t = times(seconds)
    x = np.zeros_like(t)
    arp = np.zeros_like(t)
    n_bars = int(np.ceil(seconds / bar))
    for i in range(n_bars):
        chord = CHORDS[i % len(CHORDS)]
        start, end = int(i * bar * RATE), min(len(t), int((i + 1) * bar * RATE) + int(0.6 * RATE))
        seg = t[start:end] - t[start]
        env = np.minimum(1, seg / 0.8) * np.minimum(1, np.maximum(0, (seg[-1] - seg)) / 0.6 + 0.0)
        tone = sum(warm(note(n), seg, 4) * (1.2 if j == 0 else 0.55) for j, n in enumerate(chord))
        x[start:end] += tone * env
        # Eighth-note plucks over the chord, up and down, quietly.
        step = bar / 8
        order = [1, 2, 3, 2, 1, 2, 3, 2]
        for k, idx in enumerate(order):
            s0 = start + int(k * step * RATE)
            if s0 >= len(t):
                break
            pl = t[s0: min(len(t), s0 + int(0.9 * RATE))] - t[s0]
            f = note(chord[idx]) * 2
            pluck = (np.sin(2 * np.pi * f * pl) + 0.3 * np.sin(4 * np.pi * f * pl)) * np.exp(-pl * 6)
            arp[s0: s0 + len(pl)] += pluck
    x = lowpass(x, 2400) + 0.22 * lowpass(arp, 4000)
    return fade(x, 2, 3)


def pulse(seconds: float = 180, bpm: float = 66) -> np.ndarray:
    t = times(seconds)
    x = np.zeros_like(t)
    beat = 60 / bpm
    hit_t = times(0.35)
    f = 70 * np.exp(-hit_t * 4) + 38
    hit = np.sin(2 * np.pi * np.cumsum(f) / RATE) * np.exp(-hit_t * 11)
    for b in np.arange(0, seconds - 0.5, beat):
        for offset, gain in ((0.0, 1.0), (0.22, 0.6)):  # lub, dub
            s = int((b + offset) * RATE)
            x[s: s + len(hit)] += hit[: len(x) - s] * gain
    return lowpass(x, 180)


def riser(seconds: float = 4.0) -> np.ndarray:
    t = times(seconds)
    p = t / seconds
    noise = RNG.standard_normal(len(t))
    # Noise brightening from a low hiss to a bright rush, in chunks.
    out = np.zeros_like(t)
    chunk = RATE // 20
    for s in range(0, len(t), chunk):
        c = min(1.0, s / len(t))
        lo, hi = 200 + 1500 * c**2, 900 + 9000 * c**2
        out[s: s + chunk] = bandpass(noise[max(0, s - chunk): s + chunk], lo, min(hi, RATE / 2 - 100))[-len(out[s: s + chunk]):]
    glide = np.sin(2 * np.pi * np.cumsum(110 * 2 ** (p * 3)) / RATE)
    x = out * p**2.2 + 0.35 * glide * p**1.6
    return fade(x, 0.05, 0.03)


def impact(seconds: float = 1.2) -> np.ndarray:
    t = times(seconds)
    f = 90 * np.exp(-t * 3) + 32
    boom = np.sin(2 * np.pi * np.cumsum(f) / RATE) * np.exp(-t * 2.6)
    crack = lowpass(RNG.standard_normal(len(t)), 2500) * np.exp(-t * 18) * 0.5
    return tail(boom + crack, 3.0)


def whoosh(seconds: float = 0.9) -> np.ndarray:
    t = times(seconds)
    p = t / seconds
    noise = RNG.standard_normal(len(t))
    out = np.zeros_like(t)
    chunk = RATE // 50
    for s in range(0, len(t), chunk):
        c = np.sin(np.pi * min(1.0, s / len(t)))
        lo, hi = 300 + 900 * c, 1200 + 5000 * c
        out[s: s + chunk] = bandpass(noise[max(0, s - chunk): s + chunk], lo, hi)[-len(out[s: s + chunk]):]
    return out * np.sin(np.pi * p) ** 2


if __name__ == "__main__":
    save("pad_dark", pad_dark())
    save("pad_bright", pad_bright())
    save("pulse", pulse())
    save("riser", riser())
    save("impact", impact())
    save("whoosh", whoosh(), peak=0.7)
