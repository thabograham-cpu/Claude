---
name: camera-cinematography
description: Cinematic camera work in headless Blender - framing, lenses, camera tracking, dolly/pan/tilt/crane/orbit moves, optical zoom and dolly zoom, depth of field and rack focus, camera paths, handheld shake, motion blur, and rule-based shot placement and shot-sequence checks (180-degree rule, jump cuts). Use for any camera setup, camera animation or shot list in Blender.
license: MIT
metadata:
  author: https://github.com/arjun988 (extended for headless bpy)
  version: "2.0.0"
  domain: blender
  role: specialist
  triggers: camera, cinematography, lens, framing, composition, shot, dolly, pan, tilt, crane, orbit, zoom, dolly zoom, vertigo, focal length, depth of field, rack focus, focus pull, camera path, tracking shot, handheld, whip pan, shot list, coverage, 180 degree rule
  related-skills: rendering, lighting, animation, compositing, lookdev
---

# Camera Cinematography

Intentional framing. Lens language. Motivated camera moves. **No Blender MCP here:** everything runs headless
through `tools/camera.py` (rig + moves) and `tools/shotcraft.py` (placement + sequence checks). Both have self-tests:
`$PY tools/camera.py`, `$PY tools/shotcraft.py` (`PY=/home/user/blender-shorts/.venv/bin/python`).

## Workflow
```
Shot intent -> shot size + lens -> shotcraft.place (line of sight) -> aim_point (eye line)
  -> camera.rig -> move / track / focus -> check start AND end frames -> lint the sequence
```

## 1. Place the camera (`tools/shotcraft.py`)
```python
import shotcraft as SC
dist = SC.distance_for("cu", lens=40)                      # size -> distance from lens (vertical sensor 24 mm)
pos, info = SC.place(head, front, dist, angle_deg=35, height=0.05, ignore={"Hero", *child_names})
aim = SC.aim_point(head, "cu", pos, 40)                   # eyes on the upper third
```
- Shot sizes (visible height at subject): ecu 0.30 m, cu 0.55, mcu 0.85, med 1.30, full 2.30, wide 4.2.
- `place()` ray-casts from the subject toward the camera: pulls in before walls/props, and swings around the
  subject (15..90 degrees) if that would lose more than 25% of the distance. Pass the subject's own objects in `ignore`.
- Narrow spaces (stairwells, corridors): shoot along the space (from behind / down the corridor), not across it.

## 2. Rig + moves (`tools/camera.py`)
```python
import camera as C
r = C.rig("Shot12", pos, aim, lens=40)          # CAM_Shot12 + EMPTY_CamTarget_Shot12 + EMPTY_CamFocus_Shot12
C.dolly(r, 1, 48, 0.6)         # push in 0.6 m along the view (negative = pull out)
C.pan(r, 1, 48, 25)            # pan left 25 deg (tilt= for up/down); camera stays put, aim swings
C.crane(r, 1, 48, 1.2)         # raise camera, aim fixed -> reveal
C.orbit(r, 1, 96, 40)          # circle the aim point
C.move(r, 1, 48, (1, 0, 0))    # truck/pedestal: camera and aim together
C.zoom(r, 1, 24, 35, 85)       # optical zoom (mm)
C.dolly_zoom(r, 1, 48, 85)     # vertigo: subject size locked while background stretches
C.whip_pan(r, 40, 44, 80); C.motion_blur(True)
C.track(r, hero_rig, 1, 96, bone="head", smooth=0.6)   # aim + focus follow a moving subject (lazy operator lag)
C.path(r, [(0,-5,1.6), (3,-3,2), (4,0,1.6)], 1, 96)  # camera rides a curve (replaces keyed position)
C.dof(r, 2.0, focus=hero_rig, bone="head")              # depth of field on the subject
C.rack_focus(r, 40, 52, hero_rig, other_rig, bone_a="head", bone_b="head")
C.handheld(r, 0.6)             # 0.2 subtle .. 1.5 shaky
```
Moves key every frame from the rig's state at their first frame with eased timing (`ease="inout"|"in"|"out"|"linear"`).
Different channels combine (camera position / aim / lens / focus); don't overlap two moves on the same channel.

## 3. Moves in a shot list
`camera.apply(rig, spec, f0, f1, subjects)` reads a dict per shot:
`{"move": "dolly_in"|"dolly_out"|"pan_left"|"pan_right"|"tilt_up"|"tilt_down"|"orbit"|"crane_up"|"crane_down"|"zoom_in"|"zoom_out"|"dolly_zoom"|"whip_pan"|"follow", "amount": n, "subject": "NAME", "fstop": 2.0, "focus": "NAME", "rack_to": "NAME", "rack_at": 0.6, "handheld": 0.5}`
(`subjects` maps names to `(object, bone)`). See `projects/complainer/shots.py` `MOVES`.

## 4. Check the sequence
`SC.lint(records)` flags: shots under 0.7 s, jump cuts (same subject/size/angle within 25 deg), 4 same sizes in a row,
180-degree line crossings between principals, and shot sizes that fight the beat (reaction -> CU, story object ->
insert, first visit to a location -> wide). Advisory: fix or consciously ignore. Always look at the **end frame** of a
moving shot too.

## Lens guide
| Feel | Focal | Notes |
|------|-------|-------|
| Establishing | 18-24 mm | Watch edge stretch |
| Story / medium | 28-40 mm | Natural |
| Close-up / hero | 40-85 mm | Compression flatters faces |
| Tele drama / surveillance | 100 mm+ | Flat space |

## Move language
| Move | Emotion |
|------|---------|
| Slow dolly in | Focus, dread, realisation |
| Dolly zoom | Shock, the floor drops away |
| Crane up | Reveal scale or quantity |
| Rack focus | Shift of attention between two characters / object |
| Pan / follow | Keep with action; lead room in the direction of travel |
| Whip pan | Energy, comic timing, transition |
| Handheld | Panic, live-stream / documentary feel |
| Locked off | Calm, deadpan, product |

## Constraints
MUST: name cameras/targets via `camera.rig`; match aspect (vertical shorts: `sensor_fit` VERTICAL); check start and end
frames; give the subject lead room; keep DoF shallow only where it helps the story.
MUST NOT: animate FOV wildly without motive; cross the 180-degree line by accident; rack focus without a reason to look
elsewhere; leave a moving shot unchecked at its last frame.

Cost: DoF and motion blur add roughly 10-30% render time on CPU - enable per shot.

## Reference Guide
| Topic | Reference |
|-------|-----------|
| Lens and composition | `references/lens-and-composition.md` |
| Camera move library | `references/camera-move-library.md` |
| DoF guide | `references/dof-guide.md` |
| Headless runner | `../references/headless-mode.md` |
