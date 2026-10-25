---
name: render-vertical-video
description: Render a supplied shorts manifest locally into a vertical MP4 with staged flow motion, optional images/clips, timed captions, narration and music. Use for actual CPU rendering rather than storyboard advice.
---

# Render vertical video

Use the bundled helper from this skill directory. It is self-contained when
copied alone. Requirements: Python3.10+, Pillow, FFmpeg and FFprobe. Install
`requirements.txt` in the user's chosen environment if Pillow is missing; do
not change a global environment or download a model for this render.

```bash
python scripts/render_short.py assets/short.json --out output/demo --width 720
```

This example is deliberately silent. For a voiced film, pass the user's
recording with `--audio narration.wav`, and optional authorised music with
`--music music.mp3`. `--font font.ttf` selects a local font if none is detected.
The output folder must be new. A failed render is not an accepted earlier export.

The helper supports360/720/1080 widths in9:16, staged flow nodes, moving focus,
image/video inserts and explicit timed captions. It does not invent custom
character animation, transcribe speech, generate a voice, verify content rights
or publish. Clip inserts loop and their original sound is omitted. Inspect the
crop and loop before using them as evidence of a real task.

Match scene/caption timings to the actual narration. Do not shorten a recording
or silently remove speech to make a template fit. Shorter-than-film narration is
rejected; revise the timeline or recording deliberately.

Inspect `short.mp4` and `receipt.json`, not just the command exit. The helper
checks final stream presence, duration and decode. Still inspect actual pictures
and sound evidence for the property the user cares about. Report silence, missing
inputs and unverified perceptual quality honestly. Return the actual MP4 path
and what was checked; leave scheduling and uploads to the user's existing flow.
