---
name: character-acting-director
description: Directs believable body and face acting for MPFB/MakeHuman characters in headless Blender, so nobody stands stiff or poses for the camera. Covers idle life (breathing, weight shifts, micro-motion), head turns and eye contact toward other characters, blinks, anticipation and follow-through on every pose change, arm gestures and hand shapes (2-bone arm IK to body landmarks), walking and turning, listening, background reactions, phone-filming friends, and nine emotion presets (arrogance, annoyance, disbelief, embarrassment, anger, confusion, sarcasm, exhaustion, surprise) coordinated across posture, head, shoulders, eyes, brows, hands and face. Use for any character performance, blocking, reaction, gesture, idle, walk or per-shot acting direction in Blender.
license: MIT
metadata:
  version: "1.0.0"
  domain: blender
  role: specialist
  triggers: acting, character performance, stiff characters, idle animation, breathing, weight shift, gesture, hand pose, anticipation, follow-through, overlapping action, reaction, listening, eye contact, eye line, head turn, walk cycle, emotion preset, body language, background characters, blocking, intention
  related-skills: lipsync-facial-animation, camera-cinematography, animation, rigging
---

# Character acting director (headless)

Every character is a physical actor with an **intention** in every shot. Nobody holds a pose for the lens.
The style is grounded, slightly stylised adult 3D comedy (reference: *Do Your Job.mp4*). That means small, readable moves, not children's-cartoon exaggeration.

| Piece | Where |
|---|---|
| Acting engine: `plan` (pure Python, deterministic) and `perform` (Blender) | `tools/acting.py` |
| Face units for each emotion; lip sync for speakers | `tools/lipsync.py` (`EMOTION`) |
| Worked example: three characters at a desk, plus a gallery of the nine presets | `projects/actingtest/` |
| Production use: per-shot direction for a whole short | `projects/complainer/direction.py` → `scene.py` → `acting.md` |

Self-test: `python3 tools/acting.py`.

## What the reference does (and what was missing)
- **Eye lines.** People look at each other, at props and at phones; nobody looks at the camera.
  - Drivers talk to the attendant past the lens.
  - The mechanic reads the receipt.
- **Gestures.**
  - They come from the shoulder: open-palm "Excuse me?" and a point with "You?!".
  - Hands touch the face: forehead rubs, a hand at the brow in the smoke.
  - Weight on one hip: "I'm not paying".
  - People lean on the counter.
- **Background characters** stay alive but quiet.
- **Our first version** had keyed holds, 2-pose walks, no eye lines and characters facing the camera. That is the stiffness this skill removes.

## How a performance is built
`perform(rig, spec, f0, f1, rigs, poser)` keys every body bone, finger, face unit and the eye target, every frame:

1. **Base pose track.** Every pose change has:
   - **Anticipation:** it pulls back first, by 10% × energy.
   - **Follow-through:** an under-damped spring overshoots by about 3–10% and settles.
   - **Overlap:** the body leads, the head and forearm follow 1 frame later, and the hand 2 frames later.

   A beat's time is when the move **lands**, so you put it on the word.
2. **Additive layer** (degrees in body space), on top of the pose:
   - **Breathing:** chest and shoulders. Its rate and depth come from the preset.
   - **Weight shift:** contrapposto. The hips go over one foot and that hip hikes, the shoulders counter-tilt, and the free knee bends. Leg compensation keeps the feet planted.
   - **Micro-motion:** slow sines with hashed phases.
   - **Preset posture.**
   - **Head turn toward the look target.** The head follows with a 0.12 s lag; past 45° the torso helps.
   - **Averted-gaze windows.**
   - **Listener nods.**
   - **One-shot accents.**
   - **Spoken nods and tilts** from `lipsync.plan`.
   - **Walk cycle:** a procedural cycle whose phase comes from the distance actually travelled.
3. **Hands.** Each finger joint is curled to a `HANDS` shape (relaxed, open, fist, point, grip), blended over about 5 frames.
   - Poses that hold a prop force `grip`.
   - Otherwise the preset decides, for example fists when angry.
4. **Face.** The preset's ARKit units are scaled by role, then combined:
   - The lip seal (rest) is added, unless the preset opens the jaw.
   - Blinks: a hashed rhythm, one at each reaction, and one at each change of look target.
5. **Eyes.** `eye.L/R` damped-track `EMPTY_Look_<rig>`, which is keyed on the target with saccades every 0.9 s. Averted gaze rotates the eye line. The eyes jump first and the head follows: that is the natural order.

## A spec: one character, one shot
```python
dict(name="CLK", intent="process it: fourteen bags, nine floors, no elevator",  # ALWAYS write the intention
     preset="neutral", role="listener", pose="stand",
     look=[(0, "INF"), (0.35, (-1.6, 0.4, 0.7)), (0.75, "INF")],    # cast name | "self:phone" | point | "camera" (only if intended)
     beats=[(0.15, "react", "disbelief"), (0.85, "accent", "shake"), (1.2, "pose", "palms_up"), (1.6, "hands", "fist")],
     avert=0.0, camera_ok=False, climb=False)
```
- **role:**
  - `primary`: full amplitude.
  - `listener`: small nods, slight lean in, eyes on the speaker.
  - `background`: 60% amplitude, subtle reactions.
- **Times** are seconds from the shot start. A `react` cross-fades presets (0.2 s for sudden ones, 0.6 s for others) and starts with a "take".
- **`acting.filmer(name, subject, duration, react=[(t, "laugh")])`** builds a friend filming:
  - eyes on the screen;
  - glances over the phone at the subject;
  - re-grips and tilts the phone;
  - laughs or nods at the subject's big moments.

## Emotion presets (`PRESETS`; aliases accepted, e.g. "anger", "sarcasm")
| Preset | Posture | Head and eyes | Hands | Rhythm | Face (`lipsync.EMOTION`) |
|---|---|---|---|---|---|
| arrogant | chest up, shoulders back, strong hip shift | chin up, dismissive glances away | relaxed, hand on hip | lazy (energy 0.85) | half smirk, heavy lids, one brow |
| annoyed | shoulders up a little | head down and tilted, glances aside | relaxed / arms crossed | impatient shifts, sighs every 6 s | brows down, pressed lips |
| disbelief | head pulled back, chin tucked, frozen | eyes locked, slow head shakes | open, palms out | breath held, almost no shifting | brows up, eyes wide, jaw dropped a little |
| embarrassed | shoulders up and forward | head down and away, gaze averts 60% of the time | rub the back of the neck | fidgety | tight smile, inner brows up, eyes down |
| angry | chest forward, head jutting, shoulders up | eyes locked | fists | fast, deep breath, sharp moves (1.3) | brows down, sneer, frown |
| confused | — | head tilt (9°), looks up to think | hand at chin | normal | one brow up, one down, mouth to one side |
| sarcastic | slight lean back | head tilt, eye roll | palm-up offhand | easy | asymmetric smirk, eye roll |
| exhausted | slump, shoulders dropped forward | head low, eyes drop | hanging | slow (0.6), heavy breathing, sighs | heavy lids, inner brows up, mouth slightly open |
| surprised | chest up, shoulders up | head back | open | quick take (1.0) | brows up, eyes wide, jaw open |

Tune a preset in one place. Never key faces or postures by hand.

## Library
**Poses** (`POSES`, with 2-bone arm IK to body landmarks, so they fit every body):
- `stand` (relaxed, not the A-pose)
- `hands_hips`, `hand_hip_L`
- `arms_crossed`
- `palms_up`, `palm_up_R`
- `point_fwd_R`, `point_up_R`, `snap_R`
- `rub_neck_R`, `forehead_R`, `chin_R`
- `fists_low`
- `phone_film`, `phone_selfie_R`, `phone_check_R`

Project poses still work through `poser(rig, name)`; the Complainer uses the storyboard library.

**Accents** (`ACCENTS`): `nod`, `shake`, `shrug`, `sigh`, `laugh`, `take`, `scoff`, `lean_in`, `adjust_phone`, `beat` (word emphasis; added automatically on stressed syllables when speaking).

**Hands** (`HANDS`): relaxed, open, fist, point, grip.

## Workflow for a production scene
1. **Direction table first.** For each shot, give each character in it a `d(shot, who, intent, preset, look, beats)` entry (see `projects/complainer/direction.py`).
   - Put the beats on narration word times (`audio/words.json`).
   - Give every character an arc across the film.
2. **Stage for eye lines, not for the lens.** A character talking to someone faces them.
   - Cover the exchange with `ots` / `side` angles (shot–reverse-shot).
   - When the partner is off screen in a front close-up, look at a point just off the lens, never at the lens.
3. **Show the reaction before the consequence.** Cut to the listener's disbelief or take before you show the physical result. In the Complainer, the clerk's disbelief comes before the stairs.
4. **Build.** The build places everyone first (object keys only), then calls `perform` per character per shot.
   - Read `EYELINE LINT` (eye line within 10° of the lens).
   - Review `acting.md` (intention, preset, role, look, beats per shot) next to the shot list.
5. **Preview before the full render.**
   - Render stills on the beats: the land frame of a pose and a reaction peak.
   - For new presets, render the preset gallery (`MODE=gallery` in `projects/actingtest/actingtest.py`).
6. **Speakers.** Call `lipsync.apply(rig, track, body=False)` *after* `perform`, so the mouth wins. Pass the tracks to `perform(speech=...)` so spoken nods and word beats join the body.

## Checks
- **Gallery** (`projects/actingtest/gallery`): each preset reads from the silhouette alone at medium-shot size.
- **IK contact poses:**
  - a hand on the hip touches the hip;
  - a hand at the neck sits behind the neck, not across the face;
  - a hand at the chin is under the chin.

  Landmark offsets assume the MPFB default rig (head bone head = skull base, chin ≈ head − 0.17 z, + 0.1 forward).
- **The test scene:**
  - no one is frozen, even when they're not speaking;
  - eye lines meet;
  - each move has anticipation and settles;
  - friends keep filming;
  - the background stays subtle.

## Constraints
MUST:
- an intention for every character in every shot;
- eyes and head on a motivated target;
- anticipation before every pose change;
- breathing and weight shift on everyone;
- presets rather than hand-keyed faces;
- reaction before consequence;
- preview stills before a full render;
- `.blend` files rebuilt from an empty file.

MUST NOT:
- look into the lens unless the spec says `camera_ok`;
- hold a pose without idle life;
- move in sync like twins (all timing is hashed per character);
- use cartoon squash-and-stretch or rotations over 35° from presets;
- run a walk cycle on someone who isn't moving;
- lip sync anyone but the speaker.
