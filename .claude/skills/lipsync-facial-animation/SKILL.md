---
name: lipsync-facial-animation
description: Phoneme-driven lip sync and facial performance for MPFB/MakeHuman characters in headless Blender. Covers forced phoneme alignment from real dialogue audio, viseme blending with co-articulation (M B P closures, F V, O OO, E EE, A AH, L and tongue sounds, wide and narrow mouths), resting mouths in silence, speaker-only lip sync (narration never moves every mouth), emotion expressions from 52 ARKit face units, stress-timed brows and nods, deterministic blinks, eye direction and eye rolls. Use for any talking character, dialogue scene, facial expression, blink or eye-line work in Blender.
license: MIT
metadata:
  version: "1.0.0"
  domain: blender
  role: specialist
  triggers: lip sync, lipsync, visemes, phonemes, mouth shapes, talking, dialogue animation, facial animation, facial expression, blink, eye direction, eye line, head nod, rhubarb, forced alignment, shape keys, blendshapes, ARKit
  related-skills: camera-cinematography, animation, rigging, character-artist
---

# Lip sync and facial performance (headless)

Mouths move by **phoneme**, never by volume, random opening or loops. The pipeline has two stages and two tools:

| Stage | Tool | Runs in |
|---|---|---|
| audio + text -> timed phonemes | `tools/phonemes.py` (forced alignment) | `/home/user/blender-shorts/lipsync/bin/python -I` (torch, transformers, g2p_en) |
| phonemes -> face keyframes | `tools/lipsync.py` (`plan`, `apply`, `idle`) | Blender `bpy` venv |

Both have self-tests: `python3 tools/lipsync.py` (the planner is pure Python) and `$LIPPY -I tools/phonemes.py`.
The worked example is `projects/facetest/` (11.6 s; neutral, angry and sarcastic lines; two characters).

## Why this solution (compatibility review)
| Option | Verdict here |
|---|---|
| **Rhubarb Lip Sync** | Its binary (GitHub releases) and source (codeload) are blocked by this environment's network (403). It is also audio-only recognition, which is worse than alignment when the text is known. Not used. |
| **Montreal Forced Aligner / Gentle** | They need Kaldi through conda or Docker; not installable here. Not used. |
| **wav2vec2 phoneme CTC + forced alignment** (`facebook/wav2vec2-lv-60-espeak-cv-ft`, from Hugging Face) | **Chosen.** Reachable through PyPI and Hugging Face; aligns the *known text's* phonemes to the audio at 20 ms resolution; deterministic. |
| Whisper word timestamps only | Used for transcripts (`tools/asr.py`), but too coarse for M/B/P closures. |
| **MPFB viseme morph targets** (22 Microsoft visemes) + **ARKit face units** (52) | **Chosen.** Real sculpted blendshapes for the MakeHuman basemesh, already installed (`visemes01`, `faceunits01` packs). |
| Skeletal facial rig (`jaw`, `oris*`, `levator*`) | The bones exist, but driving the mouth with them double-counts the jaw that is already in the visemes. Used only for **eyes** (`eye.L/R`) and the **neck** (nods and tilt). |

**Teeth stay attached:** `FaceService.interpolate_targets` copies every face shape key onto the teeth, tongue, eyes, brows and lashes through their MHCLO binding. `prepare()` then drives each copy from the basemesh key, so the lower teeth ride the jaw drop.

## 1. Phonemes from the actual audio
```bash
LIPPY=/home/user/blender-shorts/lipsync/bin/python
HF_HUB_DISABLE_XET=1 $LIPPY -I tools/phonemes.py audio/line.mp3 "Exactly what is said." audio/line.phones.json
```
- **Output:** `phones` [{p (ARPAbet), s, e, stress, w}], `words`, `silences`, and `rms` at 100 Hz.
- **Text:** one clip per line of one speaker. The text must match the audio; fix the transcript first with `tools/asr.py`.
- **Install** (once per container; about 5 GB):
  ```bash
  python3 -m venv /home/user/blender-shorts/lipsync && /home/user/blender-shorts/lipsync/bin/pip install torch transformers g2p_en
  ```
  The model (1.2 GB) downloads on first use.
- **NLTK data:** g2p_en needs NLTK's `cmudict` and `averaged_perceptron_tagger(_eng)` in `~/nltk_data`. NLTK refuses to download through the proxy, so fetch the zips with curl from `raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/...` and unzip them.

## 2. Plan and apply in Blender
```python
import lipsync as LS
LS.prepare(rig)                                     # once: load visemes + face units, copy to teeth/eyes, drivers
tr = LS.plan(json.load(open(ph)), "angry", fps=24, start=3.75, name="INF")   # pure python, deterministic
LS.apply(RIGS["INF"], tr, look_at=RIGS["CLK"])     # speaker: mouth, expression, accents, blinks, nods, eyes
LS.idle(RIGS["CLK"], f0, f1, "neutral", look_at=RIGS["INF"])  # listener: NO visemes, blinks/eyes/expression only
```
**Speaker only.** Lip sync is applied to the line's `speaker` and to nobody else.
- Narration lines use a speaker that is not on screen (for example `NARRATOR`), so they animate no mouth.
- A quoted line delivered by the narrator but *performed* by an on-screen character gets that character as speaker for just that span, as in the reference.

Keep dialogue in a file like `projects/facetest/dialogue.json`, one entry per line:
`{speaker, emotion, start, audio, phones, text, listener_emotion}`.

## 3. What the mouth does
- **Phoneme to viseme** (MPFB shape key):

| Group | Phonemes | Viseme shape keys |
|---|---|---|
| Rest | silence | `sil_00` (all visemes at 0) |
| M B P | M, B, P | `p_b_m_21` (+ `mouthPress`) |
| A / AH | AE, AH, AX, AA | `aa_ah_ax_01`, `aa_02` |
| E / EE | EH, UH, EY, IH, IY, Y, ER | `ey_eh_uh_04`, `y_iy_ih_ix_06`, `er_05` |
| O / OO | AO, OW, W, UW | `ao_03`, `ow_08`, `w_uw_07` (+ `mouthPucker`, `mouthFunnel`) |
| F V | F, V | `f_v_18` (+ `mouthRollLower`) |
| L and tongue | L, D, T, N, TH, DH, R, K, G, NG | `l_14`, `d_t_n_19`, `th_dh_17`, `r_13`, `k_g_ng_20` |
| Wide | S, Z, IY | `s_z_15`, `y_iy_ih_ix_06` (+ `mouthStretch`) |
| Narrow | SH, CH, JH, ZH, W, UW | `sh_ch_jh_zh_16`, `w_uw_07` |

  Diphthongs glide between two shapes: AY = AA→EE, AW = AA→OO, OY = AO→EE, EY = EH→EE, OW = OW→OO.
- **Co-articulation:** a Cohen–Massaro dominance blend.
  - Each phone is a Gaussian centred on its timing.
  - Closures dominate (M B P ×6, F V ×4), so lips meet even on 40 ms consonants.
  - H, K and G are "invisible": neighbouring vowels show through.
- **Visual lead:** shapes lead the audio by `LEAD` = 50 ms. Closures (M B P, F V) lead by only half that, so the lips are still shut when the sound starts. A 40 ms M with the full lead closes and reopens before the audio frame (found in the face test).
- **Silence:** a pause of 120 ms or more ramps the mouth to rest over `RAMP` = 80 ms. Mouths close between phrases and after lines.
- **Rest seal:** the MPFB rest pose has slightly parted lips. `REST` keys `mouthClose` 0.15 in silence (speakers and listeners). `mouthPress` and a low `p_b_m_21` did *not* seal them in render tests.
- **Closures win over expression:** lip-raising units (`mouthUpperUp*`, `noseSneer*`, used by the angry preset) fade out in proportion to `p_b_m_21`, or the lips can't meet.
- **Limits:**
  - each key ≤ 0.9;
  - sum of visemes ≤ 1.0;
  - loudness and emotion scale only vowel *openness*, within 0.8–1.2×;
  - no jaw-bone rotation, so there is no excessive jaw and no lip or teeth clipping.

  Secondary lip and cheek units (press, pucker, funnel, stretch, cheek squint) are capped small.

## 4. Face life
- **Emotion presets** (`EMOTION`, ARKit units): neutral, angry, sarcastic (an asymmetric smirk, one brow up, an eye roll at the end), happy, sad, shocked.
  - They ramp in over 0.25 s and out over 0.4 s.
  - Add a preset rather than keying faces by hand.
- **Stress accents:** a brow pulse on stressed vowels (ARPAbet stress 1), and a neck nod that starts just before the vowel. Angry nods hard (5°); sarcasm adds a 5° head tilt.
- **Blinks:**
  - every 2.2–4.8 s, hashed from the character name, plus one at each line start;
  - close in 2 frames, hold 1, open in 4.
- **Eyes:** eye bones damped-track `EMPTY_Look_<rig>`, which is keyed on the other character's head with small saccades every 0.6–1.6 s. The eye roll lifts that target.
- **Listeners:** `idle()` gives an expression at 60%, blinks, eyes on the speaker and a slow breathing nod. All visemes are keyed to 0.

## 5. Check before integrating
1. `timing.json`: for every frame, the speaker, the phoneme heard and the top visemes.
2. Render close-ups. Look at one still per group (rest, MBP, AA, EE, OO, FV, L, wide, narrow), cropped to the mouth.
3. Watch `FaceTest_debug.mp4` (labels burned in) frame by frame:
   - lips meet on every M, B and P;
   - F and V tuck the lower lip;
   - the mouth is shut in pauses;
   - the listener's mouth never moves.
   - Key values alone can mislead: a frame keyed at `p_b_m_21` 0.85 still rendered open while the angry lip-raise was on. Always check the render.
4. Then wire it into a production scene: build its `dialogue.json` from the shot list and quotes, and call `apply` / `idle` per line.

## Constraints
MUST:
- phonemes from the real audio and its text;
- one speaker per line;
- listeners through `idle()`;
- rest in silence;
- preview close-ups before a full render;
- rebuild `.blend` files from an empty file.

MUST NOT:
- drive mouths from volume alone;
- random or looping mouth motion;
- lip sync on every visible character during narration;
- jaw-bone rotation on top of visemes;
- push viseme keys above 0.9.
