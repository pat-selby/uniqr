# UniQR demo video

A 100-second pitch for UniQR, sized for a LinkedIn post or a hackathon page,
written as code with [Remotion](https://www.remotion.dev). Remotion draws each
frame as a React web page and stitches the frames into a video.

It opens on a wall of QR codes and ends on "Try it out." with the
latest-release link. In between, two voices talk it through over use cases on
Windows and Mac screens: a conference livestream when your phone is dead, a video call with three codes,
a PDF ticket on a Mac, and a giveaway poster hiding the @ trick. Then a fast
run of features (two screens at once, a page full of codes, styled codes,
a taken hotkey, start at login, privacy), the benchmark, and where to get it. There are no captions; a small "use case"
tag names each scene.

Nothing in it is a recording of a real screen. The desktops are drawn from
plain shapes in the style of Windows 11 and macOS, with no logos. Every link is
an example.com style address, and the card and the picker are rebuilt in HTML
with the app's own colors and text. The codes are real: `python scan.py` on a
rendered frame reads the same text the card shows.

## Run it

You need Node.js 18 or newer.

```bash
cd demo
npm install
npm run studio    # opens a live preview in the browser
npm run render          # writes out/uniqr-demo.mp4 (1920x1080)
npm run render:square   # writes out/uniqr-demo-square.mp4 (1080x1080)
```

The square cut is for the LinkedIn feed. It is the same video, seen through a
"camera" that pans to where the action is and pulls back when a scene needs
the full width (`src/Square.tsx`). Bands above and below carry the name, the
use case and the link.

Rendered videos go in `out/`, which git ignores. Share them as uploads or
release files, not commits.

## Your own recording

The "Is it real?" scene plays a real screen recording of UniQR, and only
appears once there is one. Record the app on a clean desktop with nothing
private on screen, save it as `public/real.mp4` (git ignores it), and render
again. It plays muted, for `REAL_FRAMES` frames, set in
`src/scenes/Real.tsx` to match the clip.

## Landing page

`site/index.html` is a one-page site for UniQR: the video, the use cases, a
"try the card" box that applies the app's link rules to anything you paste,
the features, the numbers, and download links. It plays a lighter copy of the
video (`npm run render:web`, about 2 MB), published next to it as
`uniqr-demo.mp4`, with `out/poster.jpg` as the poster frame.

## Voiceover

The conversation is in [voiceover/script.json](voiceover/script.json): two
speakers, one clip per line, and the video times itself to the clips. To change a line or
the voice, see [VOICEOVER.md](VOICEOVER.md). Without the clips the video is
silent.

## Sound bed

Every sound besides the voice is synthesized by `tools/make_music.py` from sine
waves and noise, so there is nothing to license: a dark drone and a heartbeat
while the phone is dead, a riser and an impact for the reveal, a brighter
progression once UniQR arrives, the drone again for the trap poster, and
whooshes between scenes. `src/Soundtrack.tsx` places
each piece on a story beat and dips it whenever the voice speaks.

```bash
pip install numpy scipy
python tools/make_music.py    # writes public/sfx/, which git ignores
```

## Where things come from

| In the video | Source |
|---|---|
| Card and picker colors, sizes, text | `uniqr/overlay.py` |
| Warning text | `describe_link()` in `uniqr/actions.py` |
| The icon | `uniqr/icon.py` |
| Setup steps, first-run card, hotkey fallbacks | `INSTALL.md`, `app.py`, `uniqr/hotkeys.py` |
| 96.8% of 1,064 codes, 0 wrong, 0 false alarms | `benchmarks/RESULTS.md` (seed 7) |
| Python vs C++: 1,027 and 1,026 read, 115 ms and 5 ms, 1.9 MB | `cpp/README.md` (seed 11) |

The two benchmark runs used different seeds, so the video shows them on
separate screens.

The seven codes in the ticket scene's format strip are real codes drawn by
bwip-js. In an earlier full-size layout, `python scan.py` read six of them off a
rendered frame and missed the MaxiCode.

## Files

```
src/theme.ts          the app's palette and fonts
src/components/       card, picker, icon, codes, keycaps, pointer, OS screens
src/scenes/           one file per scene, in the order they play
src/timeline.ts       scene lengths, captions and cue frames from the voiceover
src/voiceover.json    each line's text and length, made by tools/make_voiceover.py
src/Video.tsx         puts the scenes in a row and plays each voice clip
src/Soundtrack.tsx    the sound bed, placed on the story beats
voiceover/script.json the narration
tools/                make_voiceover.py, make_music.py
```
