"""Phoneme-driven lip sync + facial performance for MPFB characters (headless bpy).

Pipeline:  dialogue audio + text --tools/phonemes.py--> timed phonemes  --plan()--> per-frame face channels
           --apply()--> shape-key + bone keyframes on ONE speaking character; listeners only get idle face life.

Mouth: each phoneme maps to one of MPFB's 22 Microsoft visemes (real sculpted shape keys on the basemesh,
copied onto teeth/tongue/eyes/brows by MPFB's MHCLO interpolation, so teeth never detach). Visemes are blended
with a Cohen-Massaro style dominance model: every phone has a Gaussian dominance around its centre, closures
(M B P, F V) dominate their neighbours so lips really meet, invisible consonants (H K G) borrow the next vowel's
shape. Visual speech leads audio by LEAD seconds. Mouth returns to rest in silence. No randomness, no loops,
no volume-driven jaw: loudness only scales vowel openness inside a capped range.
Face life: ARKit face units for expressions (emotion presets), stress-timed brow accents, deterministic blinks,
eye bones aimed at a look target with small saccades, neck nods on stressed syllables.

    import lipsync as LS
    LS.prepare(rig)                                      # once per character: loads viseme + face-unit shape keys
    track = LS.plan(phones_json, emotion="angry", fps=24, start=2.5)   # pure python, testable
    LS.apply(rig, track, look_at=other_head_point_or_object)
    LS.idle(listener_rig, f0, f1, emotion="neutral", look_at=speaker_rig)  # blinks/eyes only - mouth stays shut
"""
import math, zlib

LEAD = 0.05          # mouth shapes lead the audio (s)
RAMP = 0.08          # silence <-> speech ramp (s)
MAX_KEY = 0.9        # no single shape key beyond this
MAX_MOUTH = 1.0      # sum of mouth (viseme) weights at any frame

# ARPAbet -> Microsoft viseme shape key (MPFB visemes01). Diphthongs glide between two shapes.
VIS = {
    "AE": "aa_ah_ax_01", "AH": "aa_ah_ax_01", "AA": "aa_02", "AO": "ao_03", "EH": "ey_eh_uh_04", "UH": "ey_eh_uh_04",
    "ER": "er_05", "IH": "y_iy_ih_ix_06", "IY": "y_iy_ih_ix_06", "Y": "y_iy_ih_ix_06", "W": "w_uw_07", "UW": "w_uw_07",
    "OW": "ow_08", "HH": "h_12", "R": "r_13", "L": "l_14", "S": "s_z_15", "Z": "s_z_15", "SH": "sh_ch_jh_zh_16",
    "CH": "sh_ch_jh_zh_16", "JH": "sh_ch_jh_zh_16", "ZH": "sh_ch_jh_zh_16", "TH": "th_dh_17", "DH": "th_dh_17",
    "F": "f_v_18", "V": "f_v_18", "D": "d_t_n_19", "T": "d_t_n_19", "N": "d_t_n_19", "K": "k_g_ng_20",
    "G": "k_g_ng_20", "NG": "k_g_ng_20", "P": "p_b_m_21", "B": "p_b_m_21", "M": "p_b_m_21",
}
GLIDE = {"AY": ("aa_02", "y_iy_ih_ix_06"), "AW": ("aa_02", "w_uw_07"), "OY": ("ao_03", "y_iy_ih_ix_06"),
         "EY": ("ey_eh_uh_04", "y_iy_ih_ix_06"), "OW": ("ow_08", "w_uw_07")}
# The groups asked for, for reports and tests
GROUPS = {
    "rest": ["sil_00"], "MBP": ["p_b_m_21"], "A/AH": ["aa_ah_ax_01", "aa_02"], "E/EE": ["ey_eh_uh_04", "y_iy_ih_ix_06", "er_05"],
    "O/OO": ["ao_03", "ow_08", "w_uw_07"], "FV": ["f_v_18"], "L/tongue": ["l_14", "d_t_n_19", "th_dh_17", "r_13", "k_g_ng_20"],
    "wide": ["s_z_15", "y_iy_ih_ix_06"], "narrow": ["sh_ch_jh_zh_16", "w_uw_07"],
}
VISEMES = sorted({v for v in VIS.values()} | {"sil_00", "aw_09", "oy_10", "ay_11"})
# per-viseme peak weight and dominance (how strongly it wins over neighbours); closures must hit, H/K/G borrow
SHAPE = {  # key: (peak, dominance, min width s)
    "p_b_m_21": (0.95, 6.0, 0.035), "f_v_18": (0.85, 4.0, 0.035), "sh_ch_jh_zh_16": (0.75, 2.5, 0.04),
    "w_uw_07": (0.8, 2.5, 0.045), "ow_08": (0.75, 1.5, 0.05), "ao_03": (0.75, 1.2, 0.05), "aa_02": (0.8, 1.2, 0.05),
    "aa_ah_ax_01": (0.7, 1.0, 0.045), "ey_eh_uh_04": (0.7, 1.0, 0.045), "y_iy_ih_ix_06": (0.7, 1.2, 0.045),
    "er_05": (0.65, 1.2, 0.045), "r_13": (0.55, 1.2, 0.04), "l_14": (0.6, 1.0, 0.035), "s_z_15": (0.6, 1.4, 0.035),
    "th_dh_17": (0.6, 1.4, 0.035), "d_t_n_19": (0.45, 0.8, 0.03), "k_g_ng_20": (0.4, 0.4, 0.03), "h_12": (0.3, 0.2, 0.03),
}
OPEN = {"aa_02", "aa_ah_ax_01", "ao_03", "ey_eh_uh_04", "ow_08", "er_05"}   # vowels whose openness loudness may scale
# secondary lip/cheek units driven by the visemes (ARKit face units), small and capped
SECONDARY = {
    "p_b_m_21": {"mouthPressLeft": 0.25, "mouthPressRight": 0.25, "mouthClose": 0.15},
    "f_v_18": {"mouthRollLower": 0.3, "mouthUpperUpLeft": 0.1, "mouthUpperUpRight": 0.1},
    "w_uw_07": {"mouthPucker": 0.35, "mouthFunnel": 0.15}, "ow_08": {"mouthFunnel": 0.3},
    "sh_ch_jh_zh_16": {"mouthFunnel": 0.35},
    "y_iy_ih_ix_06": {"mouthStretchLeft": 0.2, "mouthStretchRight": 0.2, "cheekSquintLeft": 0.12, "cheekSquintRight": 0.12},
    "s_z_15": {"mouthStretchLeft": 0.2, "mouthStretchRight": 0.2},
}
# Emotions: base expression (ARKit face units), mouth gain, head motion style, brow accent style
EMOTION = {
    "neutral":   dict(face={}, gain=1.0, nod=2.5, tilt=0.0, accent={"browInnerUp": 0.25, "browOuterUpLeft": 0.15, "browOuterUpRight": 0.15}),
    "angry":     dict(face={"browDownLeft": 0.75, "browDownRight": 0.75, "noseSneerLeft": 0.35, "noseSneerRight": 0.35,
                            "eyeSquintLeft": 0.3, "eyeSquintRight": 0.3, "mouthFrownLeft": 0.25, "mouthFrownRight": 0.25,
                            "mouthUpperUpLeft": 0.15, "mouthUpperUpRight": 0.15, "jawForward": 0.1},
                      gain=1.15, nod=5.0, tilt=0.0, accent={"browDownLeft": 0.2, "browDownRight": 0.2, "noseSneerLeft": 0.15, "noseSneerRight": 0.15}),
    "sarcastic": dict(face={"mouthSmileLeft": 0.5, "mouthSmileRight": 0.22, "mouthDimpleLeft": 0.3, "cheekSquintLeft": 0.3,
                            "mouthPressLeft": 0.15, "mouthPressRight": 0.15, "browOuterUpLeft": 0.55, "browOuterUpRight": 0.2,
                            "browDownRight": 0.15, "eyeSquintLeft": 0.15, "eyeSquintRight": 0.25, "mouthLeft": 0.1},
                      gain=0.8, nod=1.5, tilt=5.0, accent={"browOuterUpLeft": 0.25, "browInnerUp": 0.15}, eyeroll=True),
    "happy":     dict(face={"mouthSmileLeft": 0.55, "mouthSmileRight": 0.55, "cheekSquintLeft": 0.35, "cheekSquintRight": 0.35,
                            "eyeSquintLeft": 0.2, "eyeSquintRight": 0.2}, gain=1.0, nod=3.0, tilt=2.0,
                      accent={"browInnerUp": 0.2, "browOuterUpLeft": 0.2, "browOuterUpRight": 0.2}),
    "sad":       dict(face={"browInnerUp": 0.6, "mouthFrownLeft": 0.4, "mouthFrownRight": 0.4, "mouthShrugLower": 0.2},
                      gain=0.75, nod=1.5, tilt=3.0, accent={"browInnerUp": 0.15}),
    "shocked":   dict(face={"browInnerUp": 0.7, "browOuterUpLeft": 0.6, "browOuterUpRight": 0.6, "eyeWideLeft": 0.6, "eyeWideRight": 0.6},
                      gain=1.1, nod=1.0, tilt=0.0, accent={"browInnerUp": 0.2}),
}
BLINK = ("eyeBlinkLeft", "eyeBlinkRight")
CLOSURES = ("p_b_m_21", "f_v_18")
REST = {"mouthClose": 0.15}   # MPFB rest pose has parted lips: seal them when not speaking (press/p_b_m at low weight don't)
LIP_RAISE = ("mouthUpperUpLeft", "mouthUpperUpRight", "noseSneerLeft", "noseSneerRight")  # would pull a closure apart


# ---------------------------------------------------------------- pure-python planning
def _hash01(*parts):
    return (zlib.crc32("|".join(map(str, parts)).encode()) % 10007) / 10007


def _smooth(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)


def _units(phones):
    """Phones -> viseme units (s, e, key, stress). Diphthongs split 50/50 into their glide shapes."""
    out = []
    for ph in phones:
        p, s, e, st = ph["p"], ph["s"], ph["e"], ph.get("stress", -1)
        if p in GLIDE:
            a, b = GLIDE[p]; m = (s + e) / 2
            out += [(s, m, a, st), (m, e, b, st)]
        else:
            out.append((s, e, VIS[p], st))
    return out


def speech_envelope(t, phones, silences):
    """1 while speaking, smooth 0 in silence (between phones more than 120 ms apart, before and after)."""
    if not phones: return 0.0
    if t < phones[0]["s"] - LEAD - RAMP or t > phones[-1]["e"] + RAMP: return 0.0
    v = min(_smooth((t - (phones[0]["s"] - LEAD - RAMP)) / RAMP), _smooth((phones[-1]["e"] + RAMP - t) / RAMP))
    for a, b in silences:
        if b - a < 0.12 or a <= phones[0]["s"] or b >= phones[-1]["e"]: continue
        if a < t < b - LEAD:
            v = min(v, 1 - min(_smooth((t - a) / RAMP), _smooth((b - LEAD - t) / RAMP)))
    return v


def mouth_at(t, units, env, loud=1.0, gain=1.0):
    """Viseme weights at time t (dominance blend, closures win, capped)."""
    if env <= 0: return {}
    num, den = {}, 1e-6
    for s, e, key, _ in units:
        peak, dom, wmin = SHAPE.get(key, (0.6, 1.0, 0.04))
        if key in CLOSURES:                                         # lips must still be shut when the sound starts
            c = (s + e - LEAD) / 2; w = max(wmin, (e - s) * 0.55)
        else:
            c = (s + e) / 2 - LEAD; w = max(wmin, (e - s) * 0.55)
        if abs(t - c) > 4 * w: continue
        d = dom * math.exp(-((t - c) / w) ** 2)
        num[key] = num.get(key, 0.0) + d * peak; den += d
    out = {}
    for k, v in num.items():
        w = v / den * env
        if k in OPEN: w *= min(1.2, gain * (0.8 + 0.3 * loud))     # loudness/emotion only scale vowel openness
        if k in ("h_12", "k_g_ng_20"): continue                     # invisible consonants: neighbours show through
        if w > 0.01: out[k] = min(MAX_KEY, w)
    tot = sum(out.values())
    if tot > MAX_MOUTH: out = {k: v * MAX_MOUTH / tot for k, v in out.items()}
    return out


def plan(ph, emotion="neutral", fps=24, start=0.0, name="char", look=None):
    """Per-frame face channels for one spoken line. ph: phonemes.py JSON (dict). start: line start (s) on the
    timeline. Returns {"f0", "f1", "keys": {shape_key: [values per frame]}, "nod": [deg], "tilt": [deg],
    "blinks": [frames], "accents": [frames]}. Pure python and deterministic."""
    E = EMOTION[emotion]; phones, sil = ph["phones"], ph["silences"]; units = _units(phones)
    rms = ph.get("rms", []); hi = max(rms) if rms else 1.0
    f0 = int(math.floor(start * fps)) + 1; f1 = f0 + int(math.ceil(ph["duration"] * fps))
    names = sorted(set(VISEMES) | {k for d in SECONDARY.values() for k in d} | set(E["face"]) | set(E["accent"]) | set(BLINK) | set(REST))
    keys = {k: [] for k in names}; nod, tilt, roll = [], [], []
    stressed = [((p["s"] + p["e"]) / 2, p["e"] - p["s"]) for p in phones if p.get("stress") == 1]
    accents = sorted({int(round((c - LEAD) * fps)) for c, _ in stressed})
    for f in range(f0, f1 + 1):
        t = (f - f0) / fps
        env = speech_envelope(t, phones, sil)
        loud = (rms[min(len(rms) - 1, int(t * 100))] / hi) if rms else 1.0
        m = mouth_at(t, units, env, loud, E["gain"])
        frame = {k: 0.0 for k in names}
        frame.update(m)
        for k, a in REST.items(): frame[k] = frame.get(k, 0) + a * (1 - env)
        for vk, sec in SECONDARY.items():
            if vk in m:
                for k, a in sec.items(): frame[k] = frame.get(k, 0) + a * m[vk] / SHAPE[vk][0]
        # expression: ramps in over 0.25 s from the line start, out over 0.4 s after it
        ex = min(_smooth(t / 0.25), _smooth((ph["duration"] + 0.4 - t) / 0.4))
        for k, a in E["face"].items(): frame[k] = frame.get(k, 0) + a * ex
        # brow/face accents on stressed syllables: up in 70 ms, down in 250 ms
        acc = 0.0; head = 0.0
        for c, d in stressed:
            u = t - (c - LEAD - 0.07)
            if 0 <= u < 0.32: acc = max(acc, _smooth(u / 0.07) * (1 - _smooth((u - 0.07) / 0.25)))
            v = t - (c - LEAD - 0.12)                                # neck dips just before the stressed vowel
            if 0 <= v < 0.45: head = max(head, math.sin(math.pi * v / 0.45))
        for k, a in E["accent"].items(): frame[k] = frame.get(k, 0) + a * acc
        clo = m.get("p_b_m_21", 0.0) / SHAPE["p_b_m_21"][0]
        for k in LIP_RAISE:
            if k in frame: frame[k] *= 1 - clo
        roll.append(0.0)
        if E.get("eyeroll"):                                         # sarcasm: eyes roll up after the line
            r = t - (ph["duration"] - 0.25)
            if 0 <= r < 0.7:
                up = math.sin(math.pi * r / 0.7)
                frame["eyeLookUpLeft"] = frame["eyeLookUpRight"] = 0.6 * up
                roll[-1] = up
                keys.setdefault("eyeLookUpLeft", [0.0] * (f - f0)); keys.setdefault("eyeLookUpRight", [0.0] * (f - f0))
        for k in list(frame):
            frame[k] = min(MAX_KEY, frame[k])
            keys.setdefault(k, [0.0] * (f - f0)).append(frame[k])
        nod.append(E["nod"] * head * env); tilt.append(E["tilt"] * ex)
    return {"f0": f0, "f1": f1, "keys": keys, "nod": nod, "tilt": tilt, "roll": roll, "accents": [f0 + a for a in accents],
            "emotion": emotion, "name": name}


def blink_frames(name, f0, f1, fps=24, phrase_starts=()):
    """Deterministic blink starts: every 2.2-4.8 s (hashed from the name), plus one at phrase starts."""
    out, t = [], 0.8 + 1.5 * _hash01(name, "first")
    while f0 + t * fps < f1:
        out.append(int(f0 + t * fps)); t += 2.2 + 2.6 * _hash01(name, len(out))
    for p in phrase_starts:
        if all(abs(p - b) > fps * 0.8 for b in out): out.append(p)
    return sorted(b for b in out if f0 <= b <= f1 - 6)


def blink_curve(frames, f0, f1):
    """eyeBlink weight per frame: close in 2 frames, hold 1, open in 4."""
    shape = [0.55, 1.0, 1.0, 0.7, 0.4, 0.15]
    out = [0.0] * (f1 - f0 + 1)
    for b in frames:
        for i, v in enumerate(shape):
            if 0 <= b - f0 + i < len(out): out[b - f0 + i] = max(out[b - f0 + i], v)
    return out


# ---------------------------------------------------------------- Blender side
def _bpy():
    import bpy
    return bpy


def body_of(rig):
    return next(o for o in rig.children if o.type == "MESH" and o.name.lower().endswith(".body"))


def prepare(rig):
    """Load the 22 visemes + 52 ARKit face units onto the character's basemesh, copy them to teeth, tongue,
    eyes, brows, lashes (MHCLO interpolation) and drive every copy from the basemesh key. Idempotent."""
    bpy = _bpy()
    from bl_ext.user_default.mpfb.services.faceservice import FaceService
    body = body_of(rig)
    kb = body.data.shape_keys.key_blocks if body.data.shape_keys else {}
    if "p_b_m_21" not in kb:
        FaceService.load_targets(body, load_microsoft_visemes=True, load_arkit_faceunits=True)
        FaceService.interpolate_targets(body)
    src = body.data.shape_keys
    for ch in rig.children_recursive:
        if ch == body or ch.type != "MESH" or not ch.data.shape_keys: continue
        for k in ch.data.shape_keys.key_blocks:
            if k.name == "Basis" or k.name not in src.key_blocks: continue
            fc = k.driver_add("value"); dr = fc.driver; dr.type = "AVERAGE"
            if not dr.variables:
                v = dr.variables.new(); v.targets[0].id_type = "KEY"; v.targets[0].id = src
                v.targets[0].data_path = f'key_blocks["{k.name}"].value'
    for k in src.key_blocks:
        if k.name != "Basis": k.slider_max = 1.0
    return body


def _key_values(body, chans, f0):
    """Write per-frame values for shape keys as keyframes (linear between frames: we sample every frame)."""
    sk = body.data.shape_keys
    if not sk.animation_data: sk.animation_data_create()
    if not sk.animation_data.action:
        sk.animation_data.action = _bpy().data.actions.new(f"{body.name}_face")
    for name, vals in chans.items():
        if name not in sk.key_blocks: continue
        kb = sk.key_blocks[name]
        for i, v in enumerate(vals):
            kb.value = v; kb.keyframe_insert("value", frame=f0 + i)


def _key_bone(rig, bone, f0, vals, axis):
    pb = rig.pose.bones[bone]; pb.rotation_mode = "XYZ"
    for i, deg in enumerate(vals):
        r = list(pb.rotation_euler); r[axis] = math.radians(deg); pb.rotation_euler = r
        pb.keyframe_insert("rotation_euler", index=axis, frame=f0 + i)


def look_rig(rig):
    """Eye bones damped-track an empty in front of the face (created once). Returns the empty."""
    bpy = _bpy(); name = f"EMPTY_Look_{rig.name}"
    if name in bpy.data.objects: return bpy.data.objects[name]
    e = bpy.data.objects.new(name, None); bpy.context.scene.collection.objects.link(e)
    bpy.context.view_layer.update()
    h = rig.matrix_world @ rig.pose.bones["head"].head
    fwd = (rig.matrix_world.to_3x3() @ __import__("mathutils").Vector((0, -1, 0))).normalized()
    e.location = h + fwd * 2.0 + __import__("mathutils").Vector((0, 0, 0.08))
    for b in ("eye.L", "eye.R"):
        c = rig.pose.bones[b].constraints.new("DAMPED_TRACK"); c.target = e; c.track_axis = "TRACK_Y"; c.influence = 0.85
    return e


def key_look(rig, f0, f1, target, fps=24):
    """Eyes hold on target (object/bone point/fixed point) with small deterministic saccades every 0.6-1.6 s."""
    from mathutils import Vector
    bpy = _bpy(); e = look_rig(rig); sc = bpy.context.scene
    t, k = f0, 0
    while t <= f1:
        sc.frame_set(t)
        p = target.matrix_world.translation.copy() if hasattr(target, "matrix_world") else Vector(target)
        if hasattr(target, "pose") and "head" in target.pose.bones:
            p = target.matrix_world @ target.pose.bones["head"].head
        j = Vector(((_hash01(rig.name, k, "x") - 0.5) * 0.06, 0, (_hash01(rig.name, k, "z") - 0.5) * 0.04))
        e.location = p + j; e.keyframe_insert("location", frame=t)
        e.keyframe_insert("location", frame=min(f1, t + 2))             # saccades are fast: snap, then hold
        t += int(fps * (0.6 + _hash01(rig.name, k) * 1.0)); k += 1
    for fc in (e.animation_data.action.fcurves if hasattr(e.animation_data.action, "fcurves") else []):
        for kp in fc.keyframe_points: kp.interpolation = "CONSTANT"


def apply(rig, track, look_at=None):
    """Key one spoken line onto the SPEAKING character: mouth, expression, accents, blinks, nods, eyes."""
    bpy = _bpy(); body = prepare(rig); f0, f1 = track["f0"], track["f1"]
    chans = dict(track["keys"])
    bl = blink_curve(blink_frames(rig.name, f0, f1, phrase_starts=[f0]), f0, f1)
    for k in BLINK: chans[k] = [max(a, b) for a, b in zip(chans.get(k, [0.0] * len(bl)), bl)]
    _key_values(body, chans, f0)
    _key_bone(rig, "neck03", f0, [-n for n in track["nod"]], 0)    # nod = pitch forward
    _key_bone(rig, "neck02", f0, track["tilt"], 1)                  # sarcasm/head tilt = roll
    if look_at is not None: key_look(rig, f0, f1, look_at)
    if any(track.get("roll", [])):                                  # eye roll: lift the eye target (eyeballs follow)
        from mathutils import Vector
        e = look_rig(rig); sc = bpy.context.scene
        for i, u in enumerate(track["roll"]):
            if u <= 0 and (i == 0 or track["roll"][i - 1] <= 0): continue
            sc.frame_set(f0 + i); base = e.location.copy()
            e.location = base + Vector((0, 0, 1.4 * u)); e.keyframe_insert("location", frame=f0 + i); e.location = base
    return body


def idle(rig, f0, f1, emotion="neutral", look_at=None, intensity=0.6):
    """A LISTENER: no visemes, mouth relaxed shut; expression at reduced intensity, blinks, eyes, tiny nods."""
    bpy = _bpy(); body = prepare(rig); E = EMOTION[emotion]; n = f1 - f0 + 1
    chans = {k: [a * intensity] * n for k, a in E["face"].items()}
    for k, a in REST.items(): chans[k] = [v + a for v in chans.get(k, [0.0] * n)]
    for v in VISEMES: chans.setdefault(v, [0.0] * n)                 # make sure no lip sync leaks onto a listener
    bl = blink_curve(blink_frames(rig.name, f0, f1), f0, f1)
    for k in BLINK: chans[k] = bl
    _key_values(body, chans, f0)
    _key_bone(rig, "neck03", f0, [0.8 * math.sin(2 * math.pi * i / (n + 1)) for i in range(n)], 0)
    if look_at is not None: key_look(rig, f0, f1, look_at)
    return body


# ---------------------------------------------------------------- self-check (pure python)
def _selftest():
    P = lambda p, s, e, st=-1: {"p": p, "s": s, "e": e, "stress": st}
    ph = {"duration": 1.6, "silences": [[0.0, 0.2], [0.75, 1.05], [1.45, 1.6]], "rms": [0.2] * 160,
          "phones": [P("M", 0.2, 0.3), P("AA", 0.3, 0.5, 1), P("P", 0.5, 0.56), P("IY", 0.56, 0.75),
                     P("F", 1.05, 1.14), P("UW", 1.14, 1.3, 1), P("L", 1.3, 1.45)]}
    tr = plan(ph, "neutral", fps=100, start=0.0)
    K = tr["keys"]; at = lambda k, t: K[k][int(round(t * 100))]
    assert at("p_b_m_21", 0.25 - LEAD) > 0.75, at("p_b_m_21", 0.25 - LEAD)          # lips close on M
    assert at("aa_02", 0.4 - LEAD) > 0.5 and at("p_b_m_21", 0.4 - LEAD) < 0.2       # open on AA
    assert at("p_b_m_21", 0.53 - LEAD) > 0.6                                          # short P still closes
    assert at("p_b_m_21", 0.2) > 0.6 and at("p_b_m_21", 0.5) > 0.6                   # still shut at the sound onset
    assert at("mouthClose", 0.9) > 0.12 and at("mouthClose", 0.4) < 0.03            # lips sealed only in silence
    ang = plan(ph, "angry", fps=100)["keys"]
    assert ang["mouthUpperUpLeft"][int(round((0.25 - LEAD) * 100))] < 0.03 < ang["mouthUpperUpLeft"][40]  # no lip raise on M
    assert at("f_v_18", 1.095 - LEAD) > 0.6 and at("w_uw_07", 1.22 - LEAD) > 0.45
    assert all(v < 0.02 for k in VISEMES if k in K for v in [at(k, 0.9)]), "mouth rests in the silence"
    assert all(at(k, 0.05) == 0 for k in VISEMES if k in K)
    assert all(max(v) <= MAX_KEY + 1e-9 for v in K.values())
    assert all(sum(K[k][i] for k in VISEMES if k in K) <= MAX_MOUTH + 1e-6 for i in range(len(K["aa_02"])))
    # smooth: no frame-to-frame jump above 0.35 on any viseme at 100 fps
    assert all(abs(a - b) < 0.35 for k in VISEMES if k in K for a, b in zip(K[k], K[k][1:])), "jerky"
    angry = plan(ph, "angry", fps=100)["keys"]; sar = plan(ph, "sarcastic", fps=100)["keys"]
    assert angry["browDownLeft"][40] > 0.5 and sar["mouthSmileLeft"][40] > sar.get("mouthSmileRight", [0] * 200)[40]
    assert plan(ph, "neutral", fps=24) == plan(ph, "neutral", fps=24)                 # deterministic
    b = blink_frames("CLK", 1, 480); assert b == blink_frames("CLK", 1, 480) and all(40 < y - x for x, y in zip(b, b[1:]))
    print("lipsync.py self-test OK")


if __name__ == "__main__":
    _selftest()
