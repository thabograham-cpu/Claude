# Headless Mode (this cloud session)

There is **no Blender MCP server and no Blender GUI** here. Blender runs headless as the
`bpy` Python module. Whenever a skill says "via MCP", do the same work with the runner below.
This file overrides any MCP-only instruction in the other skills.

```bash
PY=/home/user/blender-shorts/.venv/bin/python
BL=tools/bl.py   # in the thabograham-cpu/claude repo (run from the repo root)
```

| MCP tool in the skills | Headless equivalent |
|---|---|
| `get_scene_info` / scene query | `$PY $BL info scene.blend --out info.json` (JSON: objects, tris, materials, collections, camera; use `--out` because Blender also logs to stdout) |
| `execute_blender_code` | write the bpy code to a `.py` file, then `$PY $BL run step.py --blend scene.blend --save` |
| `get_viewport_screenshot` | `$PY $BL shot scene.blend preview.png` (Workbench, fast), then view the PNG with the Read tool |
| Final / lookdev render | `$PY $BL shot scene.blend out.png --engine eevee` or `--engine cycles --samples 64` |
| Export (FBX/GLB/OBJ) | `bpy.ops.export_scene.fbx(...)` / `bpy.ops.export_scene.gltf(...)` inside a `run` script |
| Poly Haven / Hyper3D / Hunyuan3D | Not available. Build procedurally, or download files the network allows |

## Rules

- **One phase per script.** Each `run` call is a fresh Python process that opens the `.blend`,
  runs the script and (with `--save`) saves. Nothing carries over in memory between calls, so
  always pass `--save` when the scene changes.
- Keep project files in `/home/user/blender-projects/<project>/` (`scene.blend`, `scripts/`, `renders/`, `export/`).
- After camera, materials and lighting phases, take a `shot` and **look at it** with the Read tool,
  just as the skills' screenshot loop requires.
- `shot` adds a temporary camera and sun only if the scene has none; set a real camera
  (`CAM_` prefix) for anything you deliver.
- Don't use `bpy.context.area`, viewport, or UI operators (`view3d.*`, `screen.*`): there is no window.
  Edit-mode ops work with `bpy.ops.object.mode_set`, but prefer `bmesh` and data API calls.
- Cycles runs on CPU only; keep samples low for previews. EEVEE uses software EGL.
- The `.blend`, renders and exports live in this container and are lost when it is reclaimed.
  Hand the user the files (SendUserFile) or commit them somewhere durable.

## Repo toolkit (`tools/`)

| Tool | Use |
|---|---|
| `bl.py` | `info` / `run` / `shot` (see table above; `shot --frame N` renders a timeline frame) |
| `render_range.py` | `FS=1 FE=100 $PY tools/bl.py run tools/render_range.py --blend x.blend` renders an animation range; resumable; run one worker per ~3.5 GB RAM |
| `cast.py` | realistic rigged humans via MPFB (MakeHuman), `cast.human(...)`, `cast.tint_clothes(...)` |
| `contact.py` | contact sheet of PNGs: `$PY tools/contact.py out.png COLS a.png b.png ...` |
| `psx_post.py` / `psx_batch.py` | PS1 look: downscale, 15-bit dither, nearest upscale |
| `asr.py` | word timestamps: `HF_HUB_DISABLE_XET=1 /home/user/blender-shorts/asr/bin/python -I tools/asr.py voice.mp3 words.json` (venv: `pip install faster-whisper`) |
| `render_segment.sh` | `tools/render_segment.sh projects/<name> FIRST LAST [WORKERS]`: one cloud session renders a frame range into `segments/seg_*.mp4` to commit; split long renders across sessions |
| `camera.py` | camera rig (position, look-at, lens, focus as independent channels) + eased moves: dolly, truck, pedestal, pan/tilt, crane, orbit/arc, zoom, dolly zoom, whip pan, track/anticipate, follow (tracking shots), foreground reveal, hold, paths, DoF, rack/follow focus, deterministic handheld, motion blur; `describe()` + `apply()` for shot lists; self-test `$PY tools/camera.py` |
| `shotcraft.py` | shot placement (size->distance, line-of-sight, eye line, low/high/overhead), coverage (OTS, shot-reverse-shot, inserts), PURPOSE presets, shot list export, camera lint + parallax check, sequence lint (180-degree rule, jump cuts, pacing); self-test `$PY tools/shotcraft.py` |
| `phonemes.py` | forced phoneme alignment of dialogue audio + text (wav2vec2 phoneme CTC); runs in `/home/user/blender-shorts/lipsync/bin/python -I`; self-test with no args |
| `lipsync.py` | phoneme -> MPFB viseme lip sync, ARKit expressions, blinks, eyes, nods; speaker-only (`apply`) vs listener (`idle`); planner self-test `python3 tools/lipsync.py`; guide in the `lipsync-facial-animation` skill |
| `acting.py` | character acting: per-frame body/face/eyes from a per-shot spec (intent, preset, look, beats); 2-bone arm IK pose library, 9 emotion presets, accents, filmer/listener behaviours, walk cycle, eye-line lint; self-test `python3 tools/acting.py`; guide in the `character-acting-director` skill |
| `hotelkit.py` | modular hotel kit + the persistent Grand Aurelia (street, facade, lobby, desk, elevator lobby + VIP car, stairwell x9 floors, corridors, suite, pet store); procedural materials, practical + sun/sky lighting, `eevee_quality`, `ORIGIN` set frames, `keep_inside` camera containment, `check_routes`; guide in the `hotel-location-kit` skill |
| `fonts/` | Press Start 2P (OFL) for caption burn-in via ffmpeg `ass=...:fontsdir=tools/fonts` |
