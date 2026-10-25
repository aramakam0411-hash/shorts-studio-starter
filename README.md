# Shorts Studio Starter

A small local Python renderer for vertical videos: staged motion, readable
captions, optional image/video inserts, narration, quiet background music and
MP4 export. Runs on a CPU. No model key, cloud account or auto-publisher.

## Render the included example

Install Python 3.10+, [FFmpeg and FFprobe](https://ffmpeg.org/download.html),
and Pillow in a virtual environment:

```bash
python -m venv .venv
# Activate the environment using your shell's standard command.
python -m pip install -r requirements.txt
python render.py examples/short.json --out output/demo --width 720
```

See the [actual rendered example](examples/preview.mp4), its [receipt](examples/preview-receipt.json)
and [source ledger](examples/sources.json). The sample explains file hashes using
[Python hashlib](https://docs.python.org/3/library/hashlib.html).

This creates `short.mp4` and an exact-input/output hash receipt. The included
24-second motion example is deliberately **silent**. It is a starting template,
not a finished voiced film. Output folders must be new, so rerunning cannot
silently replace an accepted export. Widths 360, 720 and 1080 keep 9:16 framing.
On systems without a detected font, pass `--font path/to/font.ttf`.

## Your voice, your clips

```bash
python render.py examples/short.json --out output/narrated \
  --audio path/to/your-narration.wav --music path/to/licensed-music.mp3
```

Narration must cover the full scene timeline; shorter recordings are rejected
before output. Adjust scene durations to your actual voice. Narration is
normalized; optional music loops quietly underneath. Listen to your final mix.
The renderer is not a voice generator, speech transcriber or automatic lip sync.

Each scene has `title`, `seconds`, 1 to 4 short `steps`, and a `credit`. The
original flow objects build in order, move into place, change focus and settle.
To add a real image or video, place it beside the manifest and add:

```json
"media": {"kind": "video", "path": "my-demo.mp4"}
```

Use `"kind": "image"` for a still. Inserts crop to fit the upper demonstration
area; clips loop when shorter than their scene. Their original audio is excluded
so you can control the voice/music mix. Preview that crop and disclose a loop
where it could mislead. Keep filenames relative to the manifest folder and use
your own or appropriately licensed material. Asset hashes go into the receipt.

Captions are explicit intervals, not automatically guessed from scene length:

```json
"captions": [{"start": 0.5, "end": 3.5, "text": "Show the useful action."}]
```

Keep captions concise and timed to the actual recording. Source credits remain
visible near the lower edge. Review the result at phone size and move your
important text if a platform's interface covers it. This kit does not claim a
universal platform safe area, broadcast audio certification or measured retention.

## Connect the content workflow

[AIOS Content Starter](https://github.com/aramakam0411-hash/aios-content-starter)
exports the same `short.json` format plus narration, storyboard and source ledger.
Copy its output folder here and render that manifest. Tasks and code are separate
so your existing assistant can write a better visual plan without a hosted service.

## Verify and extend

```bash
python -m unittest discover -s tests -v
```

Integration tests render and decode actual media, exercise captions/image/clip
inserts and narration/music, and check failure cases. The style is intentionally
small and editable: extend `frame()` for your own original motion and layouts.
No scraper, download command, scheduling, model inference or automatic posting.
Original source is MIT; fonts, inputs and FFmpeg keep their own licences.
