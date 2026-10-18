"""Turn voiceover/script.json into one audio clip per line.

The script is a conversation: each line says `who` speaks, and the
`voices` table gives each speaker a voice, speed and pitch.

Writes public/vo/<scene>-<n>.mp3 and src/voiceover.json, which holds each
line's text and length so the video can place the clips and time its
animations to them.

Needs edge-tts and mutagen:  pip install edge-tts mutagen
Run from the demo folder:    python tools/make_voiceover.py

edge-tts sends the script text to Microsoft's online speech service.
"""

import asyncio
import json
from pathlib import Path

import edge_tts
from mutagen.mp3 import MP3

DEMO = Path(__file__).resolve().parent.parent
SCRIPT = DEMO / "voiceover" / "script.json"
OUT_AUDIO = DEMO / "public" / "vo"
OUT_TIMING = DEMO / "src" / "voiceover.json"


async def speak(text: str, path: Path, voice: str, rate: str, pitch: str) -> float:
    """Save the clip and return when the speech ends, in seconds.

    The file itself runs on with silence, so its length would leave gaps. The
    service reports each word's start and length (in 100 ns ticks), and the
    last word's end is when the voice actually stops.
    """
    talk = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, boundary="WordBoundary")
    end = 0
    with path.open("wb") as audio:
        async for chunk in talk.stream():
            if chunk["type"] == "audio":
                audio.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                end = max(end, chunk["offset"] + chunk["duration"])
    spoken = end / 10_000_000
    return min(spoken + 0.12, MP3(str(path)).info.length) if spoken else MP3(str(path)).info.length


async def speak_retrying(*args) -> float:
    """The free service drops a request now and then. Try a few times."""
    for attempt in range(4):
        try:
            return await speak(*args)
        except edge_tts.exceptions.NoAudioReceived:
            if attempt == 3:
                raise
            await asyncio.sleep(1 + attempt)
    raise AssertionError("unreachable")


async def main() -> None:
    script = json.loads(SCRIPT.read_text(encoding="utf-8"))
    OUT_AUDIO.mkdir(parents=True, exist_ok=True)
    timing: dict[str, list[dict]] = {}
    for scene, lines in script["scenes"].items():
        timing[scene] = []
        for n, line in enumerate(lines, start=1):
            name = f"{scene}-{n}.mp3"
            voice = script["voices"][line["who"]]
            seconds = await speak_retrying(
                line.get("say", line["text"]),
                OUT_AUDIO / name,
                voice["voice"],
                voice["rate"],
                voice["pitch"],
            )
            timing[scene].append(
                {"text": line["text"], "file": name, "seconds": round(seconds, 3), "pause": line.get("pause", 0)}
            )
            print(f"{name:12} {line['who']} {seconds:5.2f}s  {line['text']}")
    OUT_TIMING.write_text(json.dumps({"voices": script["voices"], "scenes": timing}, indent=2) + "\n", encoding="utf-8")
    total = sum(line["seconds"] for lines in timing.values() for line in lines)
    print(f"wrote {OUT_TIMING.relative_to(DEMO)}, {total:.1f}s of speech")


if __name__ == "__main__":
    asyncio.run(main())
