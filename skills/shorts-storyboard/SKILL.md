---
name: shorts-storyboard
description: Turn narration and a viewer payoff into a timed vertical-video storyboard with meaningful motion, demo inserts and readable captions. Use before rendering an explainer, tool walkthrough or resource Reel.
---

# Shorts storyboard

Name the useful thing the viewer will understand or do. Open with the relevant
action, evidence or question; move background context to where it helps. Preserve
the user's subject and tone. A source-reported story need not become a tutorial.

Use the actual recording to place speech, actions and pauses when available.
Otherwise mark timing provisional and estimate a calm read. Do not squeeze a
long narration into a preset duration or present guessed captions as aligned.

Plan a recognizable object across each explanation: show its input, change,
detail and settled result. Decide where real interface footage adds evidence.
Keep original illustrations distinct from actual tool runs. A zoom or transition
should direct attention to something the words explain.

Write `short.json` using [the renderer field reference](references/manifest.md).
[The example manifest](assets/short.json) is directly renderable. Resolve these
paths relative to this skill directory. The bundled starter renderer implements
a staged flow layout and optional demo insert; richer action notes are a plan,
not a claim that its template already implements custom 3D or character animation.

Place captions at explicit spoken intervals with a readable hold. Keep credit
labels short and source URLs in a separate source ledger. Use the user's chosen
voice and assets; request only a missing input that blocks the intended result.

Return the manifest, narration/asset requirements and any custom motion still
needed. When the user asks to render, use their available renderer or the
standalone render-vertical-video skill. This planning skill needs no other skill
installed and never schedules a post or sends resource DMs.
