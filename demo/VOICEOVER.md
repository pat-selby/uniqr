# Voiceover

A conversation between two neural text-to-speech voices from Microsoft,
through the open-source `edge-tts` package: Ava (A) runs into the problems and
Andrew (B) answers with UniQR. Each line is its own clip, and the video times
itself to them: a scene lasts as long as its lines, and the key moments land
on the words. The keys go down on "Win, Shift, Q", the picker opens on "Each
one gets a number", and the warning lights up on "Look closer".

## Change a line

1. Edit [voiceover/script.json](voiceover/script.json). `who` is the speaker,
   `text` is the line, `say` is how the voice reads it (for numbers and
   symbols), and `pause` adds frames of silence after it.
2. Make the clips again:

   ```bash
   pip install edge-tts mutagen
   python tools/make_voiceover.py
   ```

   It writes `public/vo/*.mp3` (ignored by git, since the script can always
   make them again) and `src/voiceover.json` with each line's length.
3. Render. Scenes stretch or shrink to fit.

`make_voiceover.py` sends the script text to Microsoft's online speech service.
Nothing else leaves the machine.

## Change a voice

Each speaker has a `voice`, `rate` and `pitch` under `voices` in
`script.json`. Some that work well:

| Voice | Feel |
|---|---|
| `en-US-AvaMultilingualNeural` | expressive, friendly (A) |
| `en-US-AndrewMultilingualNeural` | warm, confident (B) |
| `en-US-EmmaMultilingualNeural` | cheerful, clear |
| `en-US-ChristopherNeural` | steady, authoritative |

`python -m edge_tts --list-voices` lists them all.
