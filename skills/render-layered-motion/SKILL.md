---
name: render-layered-motion
description: Render an original local HTML animation into a vertical MP4 with deterministic frames, optional supplied audio and a receipt. Use for layered explainer scenes with an explicit window.frame(seconds) function.
---

# Render layered motion

Copy this whole skill folder. Its script and example work without another
repository folder. Requires Python 3.10+, Playwright, an installed Chromium and
FFmpeg/FFprobe. Use the user's existing environment; install dependencies only
under their environment policy. No model, cloud account or paid service is needed.

Use an original or authorized local HTML scene. Read its code before executing
it; blocking network requests is not a sandbox for hostile browser code. The
scene must define `window.frame(seconds)` and render the same image when a time
is visited again. Pause CSS/Web Animations or drive their state explicitly; do
not depend on wall-clock timers. Keep required local assets in the scene folder.
Requests outside that folder and HTTP(S) requests are refused by this helper.

The included example is an editable six-second silent illustration, not a real
agent operation. It scales its original scene to the selected vertical viewport.
Change its subject, imagery and copy for the actual story. For narrated work,
author the scene and meaningful action times to the real supplied recording.
Use design-explainer-motion if available, or work from the user's own brief.

```bash
python scripts/render_html.py assets/layered-demo.html --out output/study --seconds 6
```

For an existing Chrome/Chromium installation, add `--chromium /path/to/chrome`.
For narration, add `--audio /path/to/recording.wav`. Audio must match the requested
film duration within one video frame; shorter/longer recordings are rejected.
No speech speed change or phrase timing is inferred. Silence is deliberate when
no audio is supplied. Supply any music mixed into your own authorized audio.

Supported widths 360/720/1080 retain 9:16 framing, with 12/24/30 fps. Duration must
be 0.25–120 seconds and end on a whole frame, with at most 3600 frames. Output must
be a new directory. On a failed run inspect any retained partial output before
retrying into another directory; never overwrite an accepted export.

Inspect `video.mp4`, `receipt.json` and the opening/middle/ending pictures.
The helper checks frame-seek determinism, full decode, stream/frame count and
unchanged inputs. Use review-short-export if available to sample more of the
actual MP4, then assess visual continuity, readable phone-size text, timing and
sound where you can hear it. A technical pass does not establish natural speech
or a compelling explanation. Return the actual output and relevant findings;
account connection, scheduling and publishing remain separate user scope.
