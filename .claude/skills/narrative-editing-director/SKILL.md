---
name: narrative-editing-director
description: Turns narration into an edited short, the way Do Your Job.mp4 is cut. It splits the voiceover into story beats and gives every beat a performed visual action, a reaction, a camera choice and sound. It mixes establishing, action, dialogue, reaction, insert, reveal and point-of-view shots and comedic pauses with motivated cuts and camera moves. It holds jokes long enough to land, syncs actions and effects to words, and adds procedural sound effects and ambience under the narration, plus reference-style captions (white sentence-case Montserrat, thin outline, kept off faces, Shorts-safe). Use for any narrated short, beat sheet, shot pacing, edit review, sound design pass or caption styling.
license: MIT
metadata:
  version: "1.0.0"
  domain: video
  role: specialist
  triggers: edit, editing, beat sheet, story beats, pacing, cut, montage, reaction shot, establishing shot, insert, POV, comedic pause, timing, sound effects, sfx, foley, ambience, room tone, captions, subtitles, YouTube Shorts, vertical video
  related-skills: camera-cinematography, character-acting-director, lipsync-facial-animation, hotel-location-kit
---

# Narrative editing director

**Never show a character while the narration describes an action. Show the action happening.**
Every beat answers four questions: what do we **watch happen**, who **reacts**, **how** do we see it, and what do we **hear**?

| Tool | Does |
|---|---|
| `tools/edit.py` | `segment(words)` → beats with suggested functions; `lint(sheet, shots, words)`; `compile_cues(sheet, words)` → sfx cues; `markdown(sheet)` |
| `tools/sfx.py` | Procedural effects and ambience beds, mixed under the narration with ducking (`render`) |
| `tools/captions.py` | Reference-style captions → ASS, kept off faces, inside the Shorts safe area |
| Worked example | `projects/complainer/beats.py` (63 beats) → `beats.md`, `cues.json`, `beds.json`; `finish.py` mixes and captions |

All three tools self-test with `python3 tools/<name>.py`.

## What the reference does (measured)
- **A new picture every 1.5–3 s, but few hard cuts.**
  - The camera travels through beats: it dollies with the car from "drove up" into "threw a hundred-dollar".
  - Setups change on 4–5 frame dissolves or cuts on action. That's why cut detectors find only about 18 cuts in 122 s.
- **Every narrated action is performed and shown:**
  - the bill is thrown, then a hand picks it up;
  - the pump nozzles are shown, panning to the green DIESEL label;
  - the sunglasses come down.
- **Quotes are played** by the character in a tighter shot. The listener gets their own reaction shot.
- **Jokes land, then the picture holds** about 1 s on the reaction, often while the next line starts (an L-cut).
- **Sound.** A bed sits about 9–14 dB under the narration (−16 dBFS). Effects peak around −17 to −22 dBFS, mostly in the pauses.
- **Captions:**
  - white Montserrat ExtraBold, 1–3 words, sentence case as spoken;
  - a thin dark outline and soft shadow;
  - about 4.3% of the frame height per line, centred at 74% of the height;
  - at most 2 lines of about 14 characters;
  - placed under faces, never on them.

## Workflow
1. **Beats.**
   - Run `edit.segment(words)` on the word timings (`tools/asr.py`, or forced alignment).
   - Breaks fall at `. ? !` always, and at `, ; :` or pauses over 0.3 s once a clause has 3 or more words. A one-word tail joins its clause.
   - Each beat gets a suggested function: establish / action / dialogue / reaction / insert / reveal / pov / pause / transition.
2. **The director's pass** (`beats.py`). For every beat, write:
   - **visual**: an action with a verb that we watch happen. "INF snaps his fingers at the clerk on 'bags'", not "INF is shown".
   - **reaction**: who responds, and how, in their own shot or in the background.
   - **camera**: shot type and move. Use the `camera-cinematography` vocabulary, POV via `pov:<rig>:<bone>`, or `cam_at` for buildings.
   - **sfx**: `(at, kind, args)`, where `at` = seconds or `"word:bags[+0.1]"`. Mark `sync=True` when the sound *is* the visible action.
   - **shots**: the shot ids that cover the beat. Set `joke=True` on punchlines.
3. **Shot list from the beats.**
   - **Establishing:** at each new location. Use the exterior or a reveal, at least once per location.
   - **Action shots:** for verbs.
   - **Dialogue shots:** for quotes. Use over-the-shoulder or profile, so the eye line goes to the listener, never to the lens.
   - **Reaction shots:** after the line they react to.
   - **Inserts:** for objects the story turns on (the box, the bill, the trolley).
   - **POV:** when a character's view is the point (his phone's selfie view; the clerk seeing 14 bags).
   - **Comedic pauses:** hold the shot through the narration gap and past the next line's first word.
4. **Lint** (`edit.lint`):
   - every visual is an action, not a display;
   - jokes and reactions get at least min(0.8 s, the gap) before the cut;
   - no shot under 0.6 s;
   - no static shot over 3 s without a move or new action;
   - median shot length 1.4–3.2 s;
   - no three static shots of the same size in a row;
   - no loud effect inside a spoken word unless it's synced to the action.
5. **Sound** (`sfx.render`).
   - Ambience beds per location (street, lobby, elevator, stairs, room, corridor) cross-fade at cuts.
   - **Effects:** steps on the right surface (marble, carpet or concrete), luggage wheels, elevator ding and doors, door, finger snap, phone tap, ping and shutter, cardboard, bag thud, exhausted breath, whoosh. Each gets a room reverb for its space.
   - **Ducking:** effects duck 6 dB and the bed 4 dB under words (adaptive speech mask).
   - Finish at −14 LUFS (`loudnorm`).
6. **Captions** (`captions.build(words, faces, fps, fix)`).
   - Merges ASR splits: "five -star", "$4 ,000", "a .m.".
   - Fixes misheard words ({"lean": "lien"}).
   - Captions run from just before the first word until the next caption, holding 0.6 s into pauses.
   - Face boxes per frame come from the scene build (`faces.json`, head projected through the shot camera). A caption stays at 74%; if a face is there it moves up to 64%, and to the top band (30%) only if both are covered. The reference keeps captions low, over a close-up's chest.
  - Size: Montserrat ExtraBold 118 at 1080x1920, outline 4.2, shadow 2.4: letter height matched to the reference crop at the same scale (64 and then 88 both read too small).
   - Safe area: x 9–82%, y 12–80%.
7. **Review a draft.** Render the cut at draft size (`RES=270x480 SAMPLES=6`), then `finish.py`. Watch for beats that don't play, jokes that don't land, effects that are too loud or too quiet, and captions on faces. Fix, then render at full quality.

## Rules
- **Sync.**
  - Cut on words or on action: a pose lands on the stressed word, and the cut comes mid-gesture.
  - Effects that *are* the action (snap, ding, doors, thud) sit on the frame where it happens.
  - Footsteps follow the walk; wheels follow the trolley.
- **New information** every 1.5–3 s: a cut, a camera move, a new action or a reveal. Don't cut every second just to cut.
- **Sound serves the story.**
  - The bed is felt, not noticed.
  - Effects never cover a word's consonants; loud ones go in pauses.
  - No music bed unless asked: the narration is the score.
- **Captions.**
  - White, sentence case, as spoken. No all-caps, no thick outlines, no bouncing.
  - Never cover a face. Never sit under the Shorts UI (bottom 20%) or the right-side buttons.

## Limits (shortcuts)
- **Effects are synthesised.** They're clean and deterministic, but not recorded foley. Swap in recorded files through `cue_audio` if a story needs realism; ElevenLabs or Higgsfield sound-effect search are options.
- **Shots join with hard cuts.** Reference-style 4-frame dissolves need render handles: render a few extra frames per shot, then use ffmpeg `xfade`.
