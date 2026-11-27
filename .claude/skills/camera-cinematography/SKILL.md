---
name: camera-cinematography
description: Cinematic camera direction in headless Blender, operated like a real virtual camera in a persistent 3D world. Covers framing, lenses, coverage (over-the-shoulder, shot-reverse-shot, reaction close-ups, inserts, low, high and overhead angles), physical moves (dolly, truck, pedestal, crane, arc and orbit, forward, backward and lateral tracking, anticipation, foreground reveals), pan and tilt, optical focal-length changes, depth of field and rack focus, subtle handheld, intentional static holds, motion blur, shot lists before rendering, and camera, sequence and parallax lint. Use for any camera setup, camera animation, coverage plan or shot list in Blender. Also called the cinematic camera director.
license: MIT
metadata:
  author: https://github.com/arjun988 (extended for headless bpy)
  version: "3.0.0"
  domain: blender
  role: specialist
  triggers: camera, cinematography, cinematic camera director, lens, framing, composition, shot, coverage, dolly, truck, pedestal, pan, tilt, crane, orbit, arc, zoom, focal length, tracking shot, follow, anticipate, reveal, foreground reveal, over the shoulder, OTS, shot reverse shot, reaction shot, insert, low angle, high angle, overhead, depth of field, rack focus, focus pull, handheld, static hold, whip pan, parallax, shot list, 180 degree rule
  related-skills: rendering, lighting, animation, compositing, lookdev
---

# Camera Cinematography (cinematic camera director)

The camera behaves like an operator inside one persistent 3D world. It never works by enlarging rendered frames.
Everything runs headless through two files:
- `tools/camera.py`: rigs and moves.
- `tools/shotcraft.py`: placement, coverage, direction, lint and shot lists.

Both have self-tests: run `$PY tools/camera.py` and `$PY tools/shotcraft.py`, with `PY=/home/user/blender-shorts/.venv/bin/python`.
The worked example is `projects/camera-demo/coverage.py` (12 shots in the hotel lobby). Build it with `bash projects/camera-demo/build.sh coverage`.

## Visual reference: "Do Your Job" (measured, 122 s, 9:16)
- **Cutting:** 9 cuts a minute, median shot 4.7 s.
  - Shots are long and the camera re-frames inside them.
  - Transitions follow an object into the next subject: the falling bill, then a crane up to the driver.
  - Some transitions are whip-pans with motion blur.
- **Camera movement:**
  - The camera moves in 80% of frames, mostly slow physical drift and push.
  - Fast moves are kept for transitions and action.
  - Every move shows parallax (0.3–0.6 px of residual motion), so there are no digital push-ins or crop zooms.
- **Dialogue:**
  - Close or medium coverage, often over a shoulder, with a foreground windshield or door out of focus.
  - The camera mostly holds, with a whisper of handheld shake.
- **Depth of field:** shallow throughout. Focus is on the speaker; foreground and background melt.
- **Angles:** chosen for the beat. Examples:
  - low on the driver in the car;
  - high or overhead for the intersection;
  - an insert for the card reader;
  - a reaction close-up for "Did I ask?".

## Workflow (the order matters)
```
beat + narrative purpose -> PURPOSE preset (size, angle, move)  -> coverage framing (place_angle / ots / reverse_pair / insert_shot)
  -> camera.rig (position + look-at target + focus empty, all independent) -> one move per channel
  -> describe() rows -> shotlist() + camera_lint() + lint()   <- REVIEW BEFORE RENDERING
  -> check start, middle and end frames -> render (render_range.py) -> finish
```

## 1. The rig: four independent channels
```python
import camera as C
r = C.rig("Shot12", pos, aim, lens=40)   # CAM_Shot12 (Track To) + EMPTY_CamTarget_Shot12 + EMPTY_CamFocus_Shot12
```

| Channel | Animated by | Notes |
|---|---|---|
| Camera position | `dolly`, `truck`, `pedestal`, `crane`, `orbit`/arc, `follow`, `reveal`, `path`, `move` | physical travel, which gives parallax |
| Look-at target | `pan` (and tilt), `track`, anticipation (`lead=`), `whip_pan`, `move` | the camera stays put; the aim swings |
| Focal length | `zoom`, `dolly_zoom` | optical; keep it within ×1.35 a shot unless the zoom is the point |
| Focus distance | `dof`, `rack_focus`, `follow_focus`, `track`/`follow` | the focus empty, independent of the aim |

Moves on different channels combine freely (for example a dolly plus a small lens change plus a rack). Two moves on the same channel must not overlap in time.

## 2. Moves
All moves are eased with smootherstep by default (`ease="inout"`): zero velocity *and* acceleration at both ends, so there are no jolts on start or stop. Use `ease="in"` to accelerate into a cut or whip, `"out"` to land from one, and never `"linear"` except for a constant-speed follow.

```python
C.dolly(r, 1, 48, 0.6)                    # push in 0.6 m along the view (negative = pull out)
C.truck(r, 1, 72, 3.2)                    # lateral slide on the camera's own right axis (negative = left)
C.pedestal(r, 1, 48, 0.4)                 # camera and aim rise together
C.crane(r, 1, 48, 1.2)                    # camera rises, aim fixed -> the view tilts down to follow
C.pan(r, 1, 48, 25); C.pan(r, 1, 48, 0, tilt=9)   # horizontal pan / vertical tilt (camera fixed)
C.orbit(r, 1, 96, 40)                     # circle the aim point
C.orbit(r, 1, 84, 16, rise=0.3, radius=-0.4)      # arc: orbit while rising and pushing in
C.zoom(r, 10, 72, 35, 41)                 # optical focal-length change (mm), its own channel
C.follow(r, hero, 1, 96, bone="head", lag=0.8)    # tracking shot: camera TRAVELS with the subject at its f0 offset
#   camera in front = backward (leading) tracking, behind = forward tracking, beside = parallel; lead=12 anticipates
C.track(r, hero, 1, 48, bone="head", smooth=0.7, lead=14)  # camera fixed, aim leads where he is going (anticipation)
C.reveal(r, 1, 72, pillar, clerk, bone="head")    # foreground reveal: slides exactly far enough to clear the occluder
C.hold(r, 1, 48)                          # intentional static hold: every channel locked (focus=False leaves focus free)
C.handheld(r, 0.12, f0=1, f1=48)          # subtle operator drift, limited to one shot, soft 6-frame ramps
C.whip_pan(r, 40, 46, 70); C.motion_blur(True)
C.path(r, [(0,-5,1.6), (3,-3,2), (4,0,1.6)], 1, 96)  # camera rides a curve
C.dof(r, 2.0, focus=hero, bone="head"); C.rack_focus(r, 40, 56, bill, clerk, bone_b="head")
C.follow_focus(r, hero, 1, 96, bone="head")       # focus rides a walker while the camera holds
```
`handheld` strength: 0.08–0.15 is the dialogue whisper (the reference), 0.3–0.6 documentary, 1.0+ panic.

**Deterministic:** moves key every frame from scene state; noise phases come from object names (CRC32). There is no randomness and no wall-clock dependence, so the same script gives the same camera every build. Rebuild from scratch: run the build script on an empty file (`build.sh` deletes the `.blend` first), never on top of a saved build, or the set and cast are duplicated.

## 3. Coverage framings (`tools/shotcraft.py`)
```python
import shotcraft as SC
pos, info = SC.place(head, front, SC.distance_for("cu", 55), 20, 0.02, ignore=names)   # eye level, line-of-sight safe
pos, info = SC.place_angle(pt, front, dist, vertical="low")    # eye | low (power) | high (small, vulnerable) | overhead (geography)
(p1, a1, l1), (p2, a2, l2) = SC.reverse_pair(inf_head, clk_head, "mcu", side=1)   # shot / reverse shot, same side of the line
pos, aim, lens = SC.ots(subject_head, other_head, "mcu")       # one over-the-shoulder; lens chosen to frame the size
pos, centre, info = SC.insert_shot(prop_points, 50, vertical="high")                # object insert
aim = SC.aim_point(head, "cu", pos, 55)                       # eyes on the upper third
```
- **Shot sizes** (visible height at the subject): ecu 0.30 m, cu 0.55, mcu 0.85, med 1.30, full 2.30, wide 4.2, insert 0.6.
- **Line of sight:** `place()` ray-casts. Pass the subject's own meshes, and any props they hold, in `ignore`.
  - **Assert `info["clear"] >= 0.75`.** A blocked placement otherwise parks the camera inside someone.
- **Dialogue:** `reverse_pair` keeps both cameras on one side of the A–B line, so eye-lines match across the cut. Hold both shots.
- **Reaction close-up:** a 50–60 mm lens, a hold, handheld of 0.1 or less, and f/2. No move competes with the face.
- **Narrow spaces** (stairwells, corridors): shoot along the space, not across it.

## 4. Direction: when the camera moves
`SC.choose(purpose)` returns the default design for each beat, and any key can be overridden.

| Purpose | Size / angle | Camera |
|---|---|---|
| establish | wide, high | slow arc (parallax on foreground pillars) |
| dialogue | mcu, OTS | **hold** + handheld 0.12 |
| reaction | cu | **hold** + handheld 0.1 |
| realise | cu | slow push (0.25 m) after a short delay |
| action | med | `follow` (tracking) |
| anticipate | wide | aim leads the subject (`lead`) |
| reveal | wide | `reveal` past a foreground object |
| insert | insert, high | hold (optionally rack to who reacts) |
| power / vulnerable | med, low / high | hold |
| geography | wide, overhead | hold |
| transition | — | whip pan + motion blur |

Rules:
- **Don't move by default.** Dialogue and reactions hold; movement is spent on action, reveals, realisations and transitions. `camera_lint` flags more than 70% of shots moving, and three identical moves in a row.
- **Dolly, don't zoom.** A lens change of more than ×1.35 inside a shot is flagged. Physical travel gives parallax between foreground, middle ground and background; a zoom and a frame crop don't.
- **Physical action:** choose the angle that shows cause and effect (hand → object → reaction). Insert the story object.
- Give lead room in the direction of travel, and cut or whip on motion.

## 5. Shot list and checks, before rendering
```python
rows.append(dict(id=k, f0=f0, f1=f1, type="OTS mcu", subject="INF", purpose="dialogue: his demand",
                 **C.describe(r, f0, f1, "INF")))                          # camera start/end, lens, f-stop, focus, moves
rows[-1]["parallax"] = SC.parallax(r.cam, f0, f1)                         # only for shots where the camera travels
SC.shotlist(rows, "shotlist.md", fps=24)                                  # markdown: time, type, subject, camera, lens, move, focus, purpose
for w in SC.camera_lint(rows) + SC.lint(records): print(w)
```
- **`parallax()`** puts two points on one camera ray (1.5 m and 15 m away) and measures how far apart they end up on screen.
  - Pans, tilts, zooms and crops leave them together (0).
  - Real travel separates them; above 0.02 reads as a physical move.
- **`lint()`** flags:
  - shots under 0.7 s;
  - jump cuts;
  - four same-size shots in a row;
  - 180° line crossings;
  - shot sizes that fight the beat.
- Look at the start, middle and end frame of every moving shot before a full render.

`projects/complainer/scene.py` writes `shotlist.md` and prints `CAMERA LINT` on every build.
`camera.apply(rig, spec, f0, f1, subjects)` runs a shot-list dict:
`{"move": "hold"|"push"|"pull"|"dolly_in"|"dolly_out"|"truck_left"|"truck_right"|"pedestal_up"|"pedestal_down"|"pan_left"|"pan_right"|"tilt_up"|"tilt_down"|"orbit"|"arc"|"crane_up"|"crane_down"|"zoom_in"|"zoom_out"|"dolly_zoom"|"whip_pan"|"track"|"anticipate"|"follow"|"reveal", "amount": n, "subject": "NAME", "occluder": obj, "lead": 12, "delay": 0.2, "ease": "inout", "fstop": 2.0, "focus": "NAME", "follow_focus": "NAME", "rack_to": "NAME", "rack_at": 0.6, "handheld": 0.12}`.
No `move` means an intentional hold.

## Lens guide (vertical 9:16, sensor fit VERTICAL)
| Feel | Focal | Notes |
|------|-------|-------|
| Establishing / geography | 18-24 mm | watch edge stretch; keep verticals straight |
| Story / medium / tracking | 28-35 mm | natural; good for moving with people |
| Dialogue OTS / close-up | 40-60 mm | compression flatters faces; f/2-2.8 |
| Insert / macro detail | 50-85 mm | f/1.8-2.8; rack to the person who reacts |

## Constraints
MUST:
- one rig per shot via `camera.rig`;
- a narrative purpose for every shot;
- a shot list reviewed before rendering;
- clear placements;
- start, middle and end frames checked;
- motion blur on for whips and action.

MUST NOT:
- scale or crop rendered frames to fake a move;
- pan or zoom every shot;
- use linear eases on starts and stops;
- zoom more than ×1.35 without a motive;
- cross the 180° line by accident;
- rack focus without a reason to look elsewhere.

Cost: DoF and motion blur add roughly 10–30% render time on CPU.

## Reference Guide
| Topic | Where |
|-------|-------|
| Worked coverage scene (all techniques, with shot list) | `projects/camera-demo/coverage.py` |
| Technique-by-technique demo | `projects/camera-demo/demo.py` |
| Headless runner | `../references/headless-mode.md` |
