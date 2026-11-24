Use the ponytail skill (full level) for every coding task in this repo, unless I say "stop ponytail" or "normal mode".

## Blender work
- 94 Blender skills are in `.claude/skills/` (start with `blender-director`). There is no Blender MCP: Blender runs headless via `bpy`; follow `.claude/skills/references/headless-mode.md`.
- Shared tools are in `tools/`; projects live in `projects/<name>/` (scripts, audio, shot lists). Keep `.blend` files and rendered frames out of git: scenes are rebuilt from their scripts.
- Cameras: use `tools/camera.py` (rig, moves, DoF/rack focus, paths) and `tools/shotcraft.py` (placement, sequence lint); guide in the `camera-cinematography` skill.
- Which video pipeline: realistic or PSX 3D shorts with characters -> Blender (`blender-director` + `tools/`); 2D stick-figure explainers -> `growkaz-stickman`; animated wildlife/nature explainers -> `wildlife-explainer`; React/motion-graphics or caption-heavy edits -> `remotion`; AI-generated footage -> Higgsfield / ElevenLabs video. Reuse `tools/asr.py` for word timings and the Blender captions unless the chosen pipeline has its own.
