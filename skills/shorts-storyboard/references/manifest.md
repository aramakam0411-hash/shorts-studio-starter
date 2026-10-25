# Starter renderer manifest

Use `assets/short.json` from this skill root for a complete renderable example.

| Field | Requirements |
| --- | --- |
| fps | Integer 12 to30; default24 |
| scenes | 1 to30 scenes, total at most180seconds |
| scenes[].title | 1 to100characters |
| scenes[].seconds | 1 to60seconds, exact frame boundary at chosen fps |
| scenes[].steps | 1 to4 labels, at most24characters each |
| scenes[].credit | Short visible credit; at most two rendered lines |
| scenes[].media | Optional `{"kind":"image" or "video","path":"relative-file"}` |
| captions | Optional records with `start`, `end`, `text` |

Assets must be inside the manifest's directory. Video inserts loop to fill a
scene and omit their original sound. State that behavior if it could mislead.
Caption intervals must lie inside the film and fit at most three rendered lines.
Narration/music are separate renderer inputs; narration must cover the full
timeline. Image/layout, pronunciation, comprehension and reuse rights need
review beyond structural validity.
