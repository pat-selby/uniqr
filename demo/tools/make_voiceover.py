"""Turn voiceover/script.json into one audio clip per line.

The script is a conversation: each line says `who` speaks, and the
`voices` table gives each speaker a voice, speed and pitch.

Writes public/vo/<scene>-<n>.mp3 and src/voiceover.json, which holds each
line's text and length so the video can place the clips and time its
animations to them. A line's `os` table gives what it says in the Mac or
Linux cut instead; those clips are <scene>-<n>-<os>.mp3.

A clip whose words and voice haven't changed since the last run is kept as
it is, so adding a line doesn't change how the others sound or line up.

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


def previous_clips(voices: dict) -> dict[str, dict]:
    """The last run's clips by file name, with the voice each was made in.

    Older runs didn't record who said a line; for those, a clip counts as
    made in today's voice only if no voice has changed since.
    """
    if not OUT_TIMING.exists():
        return {}
    old = json.loads(OUT_TIMING.read_text(encoding="utf-8"))
    clips = {}
    for lines in old["scenes"].values():
        for line in lines:
            who = line.get("who")
            for made in [line, *line.get("os", {}).values()]:
                if who:
                    voice = old["voices"].get(who)
                else:
                    voice = "unchanged" if old["voices"] == voices else None
                clips[made["file"]] = {**made, "voice": voice}
    return clips


async def clip(old: dict[str, dict], name: str, say: str, who: str, voice: dict) -> float:
    """Make one clip, or keep last run's if its words and voice are the same."""
    before = old.get(name)
    same_voice = before is not None and before["voice"] in (voice, "unchanged")
    if same_voice and (OUT_AUDIO / name).exists() and before.get("say", before["text"]) == say:
        return before["seconds"]
    return await speak_retrying(say, OUT_AUDIO / name, voice["voice"], voice["rate"], voice["pitch"])


async def main() -> None:
    script = json.loads(SCRIPT.read_text(encoding="utf-8"))
    OUT_AUDIO.mkdir(parents=True, exist_ok=True)
    old = previous_clips(script["voices"])
    timing: dict[str, list[dict]] = {}
    for scene, lines in script["scenes"].items():
        timing[scene] = []
        for n, line in enumerate(lines, start=1):
            name = f"{scene}-{n}.mp3"
            who = line["who"]
            voice = script["voices"][who]
            say = line.get("say", line["text"])
            seconds = await clip(old, name, say, who, voice)
            entry = {"who": who, "text": line["text"], "file": name, "seconds": round(seconds, 3), "pause": line.get("pause", 0)}
            print(f"{name:16} {who} {seconds:5.2f}s  {line['text']}")
            for system, text in line.get("os", {}).items():
                other = f"{scene}-{n}-{system}.mp3"
                length = await clip(old, other, text, who, voice)
                entry.setdefault("os", {})[system] = {"text": text, "file": other, "seconds": round(length, 3)}
                print(f"{other:16} {who} {length:5.2f}s  {text}")
            timing[scene].append(entry)
    OUT_TIMING.write_text(json.dumps({"voices": script["voices"], "scenes": timing}, indent=2) + "\n", encoding="utf-8")
    total = sum(line["seconds"] for lines in timing.values() for line in lines)
    print(f"wrote {OUT_TIMING.relative_to(DEMO)}, {total:.1f}s of speech")


if __name__ == "__main__":
    asyncio.run(main())
