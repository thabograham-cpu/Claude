Use the ponytail skill (full level) for every coding task in this repo, unless I say "stop ponytail" or "normal mode".

## Blender work
- 94 Blender skills are in `.claude/skills/` (start with `blender-director`). There is no Blender MCP: Blender runs headless via `bpy`; follow `.claude/skills/references/headless-mode.md`.
- Shared tools are in `tools/`; projects live in `projects/<name>/` (scripts, audio, shot lists). Keep `.blend` files and rendered frames out of git: scenes are rebuilt from their scripts.
- Cameras: use `tools/camera.py` (rig, moves, DoF/rack focus, paths) and `tools/shotcraft.py` (placement, coverage, shot lists, lint); guide in the `camera-cinematography` skill. Write and review a shot list before every render.
- Locations: hotel stories use the persistent Grand Aurelia from `tools/hotelkit.py` (skill `hotel-location-kit`): one connected world (street, lobby, elevators, stairwell, corridors, suite); cameras go through `keep_inside`, routes through `check_routes`.
- Acting: every character in every shot gets an intention and a performance via `tools/acting.py` (skill `character-acting-director`): breathing, weight shift, eye lines, anticipation/follow-through, gestures, emotion presets. Nobody poses for the lens.
- Talking characters: phoneme lip sync + facial performance with `tools/phonemes.py` and `tools/lipsync.py` (skill `lipsync-facial-animation`). Only the speaking character lip-syncs; narration moves no mouths.
- Which video pipeline: realistic or PSX 3D shorts with characters -> Blender (`blender-director` + `tools/`); 2D stick-figure explainers -> `growkaz-stickman`; animated wildlife/nature explainers -> `wildlife-explainer`; React/motion-graphics or caption-heavy edits -> `remotion`; AI-generated footage -> Higgsfield / ElevenLabs video. Reuse `tools/asr.py` for word timings and the Blender captions unless the chosen pipeline has its own.
