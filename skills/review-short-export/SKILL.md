---
name: review-short-export
description: Inspect an actual rendered short for stream/duration/audio-signal problems and timestamped picture evidence. Use when a final MP4 needs technical and visual review before sharing.
---

# Review short export

Review the actual final MP4, the intended narration and asset/source notes. Use
the user's acceptance criteria. Do not turn a technical stream pass into a claim
that speech sounds natural, a demo is genuine or viewers will watch longer.

From this skill directory, create bounded local evidence with Python3.10+,
FFmpeg and FFprobe; no extra Python packages are required:

```bash
python scripts/inspect_export.py finished.mp4 --out output/review --expect-audio
```

Omit `--expect-audio` when silence is intentional. Set `--times 0.5 1 3 5`
for relevant pictures; timestamps must be distinct/increasing and inside the
file, up to12samples. Add closely spaced transition samples for a motion issue.
The helper limits source size to512MiB and duration to180seconds and refuses an
existing output. It records exact hashes, metadata, full-decode status, sampled
audio peak/RMS/nonzero signal and actual selected pictures.

Open those pictures. Check phone-size reading, crop, caption/credit collisions,
what changes between transition samples and the visible action's relation to the
narration. Samples establish those moments, not unseen frames or full motion.
Use fuller playback/sequence inspection when the reported issue needs it.

Read `review.json`. Missing expected audio and an all-zero decoded track are
technical findings. A nonzero track is not proof of intelligibility, correct
words, natural pauses or a good mix; compare the intended recording/transcript
and obtain listening evidence when needed. Check source labels and reuse notes
separately. Return timestamped findings and actual evidence paths, then repair
the specific problem without replacing an accepted output. No upload is performed.
