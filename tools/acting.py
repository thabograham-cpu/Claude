"""Character acting for MPFB rigs in headless Blender: actors that breathe, shift their weight, look at each
other, anticipate and follow through, gesture, listen, react and walk - with emotion presets coordinated
across posture, head, shoulders, hands, eyes, brows and face. Style: grounded, slightly stylised adult comedy.

Two halves, like lipsync.py:
  plan(spec, n, fps, aims, speeds, turns)   pure python, deterministic -> per-frame pose blend, offsets, face, eyes
  perform(rig, spec, f0, f1, rigs, poser)   Blender: poses (2-bone arm IK), look targets, keys bones/face/eyes
A spec is one character's direction for one shot (times in seconds from the shot start):
  dict(name="CLK", intent="get them upstairs without a scene", preset="annoyed", role="primary",
       pose="stand", look=[(0, "INF"), (1.4, "cart")],
       beats=[(0.8, "react", "disbelief"), (1.6, "pose", "palms_up"), (2.4, "accent", "shake")])
  role: primary (full), listener (nods, attention), background (60% amplitude, subtle reactions).
  beats: react <preset> | pose <pose> (time = when the move LANDS) | accent <name> | hands <shape>.
Axes: the rig's armature space - the character faces -Y, +X is the character's LEFT, +Z is up. Offsets are
(pitch, roll, yaw) degrees about X, Y, Z: pitch + = forward/down, roll + = top tilts to the character's left,
yaw + = turns to the character's left. Bone keys ending in '*' are given for .L and mirrored to .R.
Self-test: python3 tools/acting.py
"""
import math, zlib

# ---------------------------------------------------------------- presets
PRESETS = {
    "neutral":     dict(face="neutral", body={}, breath=(0.24, 1.0), shift=(5.5, 1.0), energy=1.0, avert=(0.1, 14, 6), hands="relaxed", take=0.0),
    "arrogant":    dict(face="arrogant", body={"spine02": (-3, 0, 0), "spine01": (-3, 0, 0), "neck02": (-2, 0, 0), "head": (-6, 3, 0),
                                                "clavicle*": (0, 1.5, 4)},
                        breath=(0.2, 0.9), shift=(6.5, 1.8), energy=0.85, avert=(0.3, 20, -6), hands="relaxed", take=0.2),
    "annoyed":     dict(face="annoyed", body={"head": (3, -2, 0), "neck02": (2, 0, 0), "clavicle*": (0, -2, 0)},
                        breath=(0.3, 1.2), shift=(3.0, 1.0), energy=1.1, avert=(0.2, -14, 4), hands="relaxed", take=0.25, sigh=6.0),
    "disbelief":   dict(face="disbelief", body={"neck02": (-3, 0, 0), "neck03": (-2, 0, 0), "head": (4, 0, 0), "spine02": (-2, 0, 0),
                                                 "clavicle*": (0, -2, 1)},
                        breath=(0.15, 0.5), shift=(9.0, 0.4), energy=0.8, avert=(0.0, 0, 0), hands="open", take=0.7, shake=3.5),
    "embarrassed": dict(face="embarrassed", body={"spine02": (3, 0, 0), "neck02": (4, 0, 0), "head": (8, -3, -10), "clavicle*": (0, -4, -4)},
                        breath=(0.3, 0.9), shift=(3.5, 0.8), energy=0.9, avert=(0.6, -20, 14), hands="relaxed", take=0.3),
    "angry":       dict(face="angry", body={"spine03": (3, 0, 0), "spine02": (3, 0, 0), "neck01": (4, 0, 0), "head": (-4, 0, 0),
                                             "clavicle*": (0, -3, -3)},
                        breath=(0.38, 1.8), shift=(4.0, 0.6), energy=1.3, avert=(0.0, 0, 0), hands="fist", take=0.5),
    "confused":    dict(face="confused", body={"head": (2, 9, 4), "neck02": (0, 3, 0)},
                        breath=(0.24, 1.0), shift=(4.5, 1.0), energy=0.95, avert=(0.35, 15, -10), hands="open", take=0.3),
    "sarcastic":   dict(face="sarcastic", body={"head": (-3, 6, 0), "spine01": (-1, 0, 0)},
                        breath=(0.22, 1.0), shift=(5.0, 1.4), energy=0.9, avert=(0.25, 14, -12), hands="open", take=0.2),
    "exhausted":   dict(face="exhausted", body={"spine04": (3, 0, 0), "spine03": (4, 0, 0), "spine02": (3, 0, 0), "neck01": (2, 0, 0),
                                                 "head": (3, 0, 0), "clavicle*": (0, 5, -4)},
                        breath=(0.32, 2.4), shift=(7.0, 1.2), energy=0.6, avert=(0.35, 0, 8), hands="relaxed", take=0.15, sigh=5.0),
    "surprised":   dict(face="surprised", body={"spine02": (-3, 0, 0), "neck02": (-3, 0, 0), "head": (-3, 0, 0), "clavicle*": (0, -5, 1)},
                        breath=(0.35, 1.4), shift=(8.0, 0.3), energy=1.2, avert=(0.0, 0, 0), hands="open", take=1.0),
}
ALIAS = {"arrogance": "arrogant", "annoyance": "annoyed", "anger": "angry", "confusion": "confused", "sarcasm": "sarcastic",
         "exhaustion": "exhausted", "surprise": "surprised", "embarrassment": "embarrassed", "calm": "neutral"}
ROLE = {"primary": 1.0, "listener": 0.85, "background": 0.6}

# one-shot accents: name -> (seconds, fn(u in 0..1) -> {bone: (pitch, roll, yaw)})
def _bump(u): return math.sin(math.pi * min(1.0, max(0.0, u))) ** 2
def _hold(u, a=0.25): return min(1.0, u / a, (1 - u) / a) if 0 < u < 1 else 0.0


ACCENTS = {
    "nod":   (0.45, lambda u: {"neck03": (4 * _bump(u), 0, 0), "head": (3 * _bump(u), 0, 0)}),
    "shake": (0.9, lambda u: {"head": (0, 0, 6 * math.sin(4 * math.pi * u) * (1 - u)), "neck03": (0, 0, 2 * math.sin(4 * math.pi * u) * (1 - u))}),
    "shrug": (0.8, lambda u: {"clavicle*": (0, -8 * _bump(u), 0), "head": (0, 4 * _bump(u), 0)}),
    "sigh":  (1.6, lambda u: (lambda a, b: {"spine02": (-2.5 * a + 3 * b, 0, 0), "spine01": (-2 * a + 2 * b, 0, 0),
                                            "clavicle*": (0, -4 * a + 3 * b, 0), "head": (-1.5 * a + 3 * b, 0, 0)})(
                  _bump(u / 0.35 / 2) if u < 0.35 else 0.0, _bump((u - 0.35) / 0.65) if u >= 0.35 else 0.0)),
    "laugh": (1.0, lambda u: {"clavicle*": (0, -3 * abs(math.sin(8 * math.pi * u)) * _hold(u), 0),
                              "spine01": (-2 * _hold(u), 0, 0), "head": (-5 * _hold(u), 2 * _hold(u), 0)}),
    "take":  (0.6, lambda u: (lambda k: {"neck02": (-4 * k, 0, 0), "head": (-3 * k, 0, 0), "clavicle*": (0, -4 * k, 0),
                                         "spine02": (-2 * k, 0, 0)})(
                  -0.4 * _bump(u / 0.12) if u < 0.12 else math.exp(-(u - 0.12) * 4) * math.sin(min(1, (u - 0.12) / 0.15) * math.pi / 2))),
    "scoff": (0.5, lambda u: {"head": (-4 * _bump(u), 3 * _bump(u), 0), "clavicle*": (0, -1.5 * _bump(u), 0)}),
    "lean_in": (1.4, lambda u: {"spine03": (4 * _hold(u), 0, 0), "spine02": (3 * _hold(u), 0, 0), "head": (-2 * _hold(u), 0, 0)}),
    "adjust_phone": (0.9, lambda u: {"lowerarm01.R": (-6 * _bump(u), 0, 0), "wrist.R": (0, 12 * math.sin(2 * math.pi * u) * _bump(u), 0),
                                     "head": (2 * _bump(u), 3 * _bump(u), 0)}),
    "phone_tap": (0.5, lambda u: {"wrist.R": (-5 * _bump(u * 2) - 5 * _bump(u * 2 - 1), 0, 0), "head": (2 * _bump(u), 0, 0)}),
    "beat":  (0.35, lambda u: {"lowerarm01*": (-4 * _bump(u), 0, 0), "head": (1.5 * _bump(u), 0, 0)}),   # emphasis on a stressed word
}

# hand shapes: finger -> curl degrees per joint (local X). f1 = thumb ... f5 = pinky
HANDS = {
    "relaxed": {"f1": (0, 8, 8), "f2": (12, 18, 10), "f3": (16, 22, 12), "f4": (20, 26, 14), "f5": (24, 28, 16)},
    "open":    {"f1": (-4, 0, 0), "f2": (2, 3, 2), "f3": (2, 3, 2), "f4": (3, 4, 2), "f5": (4, 5, 3)},
    "fist":    {"f1": (10, 30, 30), "f2": (70, 95, 60), "f3": (75, 95, 60), "f4": (78, 95, 60), "f5": (80, 95, 60)},
    "point":   {"f1": (10, 25, 25), "f2": (2, 3, 2), "f3": (75, 95, 60), "f4": (78, 95, 60), "f5": (80, 95, 60)},
    "grip":    {"f1": (10, 20, 20), "f2": (45, 55, 35), "f3": (48, 55, 35), "f4": (50, 55, 35), "f5": (52, 55, 35)},
    "cup":     {"f1": (6, 12, 12), "f2": (26, 32, 22), "f3": (28, 34, 22), "f4": (30, 36, 24), "f5": (32, 38, 26)},   # an object on the palm
}
FINGER_BONES = {f"f{k}": [f"finger{k}-{j}" for j in (1, 2, 3)] for k in range(1, 6)}

# reusable poses. arm.X: hand (wrist) target for 2-bone IK at a landmark bone head + offset (m, armature space),
# pole = where the elbow points, twist = forearm roll (deg), wrist = hand direction. hand.X = HANDS shape.
_STAND = dict(at="upperarm01.L", off=(0.04, -0.06, -0.43), pole=(0.3, 1, 0))
_STAND_R = dict(at="upperarm01.R", off=(-0.04, -0.06, -0.43), pole=(-0.3, 1, 0))
POSES = {
    "stand":       {"arm*": _STAND},
    "hands_hips":  {"arm*": dict(at="upperleg01.L", off=(0.09, 0.03, 0.11), pole=(1, 0.6, 0), wrist=(0.1, 0.4, -1)), "hand*": "open"},
    "hand_hip_L":  {"arm.L": dict(at="upperleg01.L", off=(0.09, 0.03, 0.11), pole=(1, 0.6, 0), wrist=(0.1, 0.4, -1)), "hand.L": "open",
                    "arm.R": _STAND_R},
    "arms_crossed": {"arm.L": dict(at="spine01", off=(-0.12, -0.19, -0.08), pole=(1, 0.2, -1)),
                     "arm.R": dict(at="spine01", off=(0.12, -0.15, -0.04), pole=(-1, 0.2, -1)), "hand*": "relaxed"},
    "palms_up":    {"arm*": dict(at="root", off=(0.27, -0.3, 0.14), pole=(0.6, 0.6, -1), twist=-55), "hand*": "open"},
    "palm_up_R":   {"arm.L": _STAND, "arm.R": dict(at="root", off=(-0.2, -0.36, 0.16), pole=(-0.5, 0.6, -1), twist=55), "hand.R": "open"},
    "point_fwd_R": {"arm.L": _STAND, "arm.R": dict(at="upperarm01.R", off=(-0.06, -0.45, 0.0), pole=(-0.3, 0, -1)), "hand.R": "point"},
    "point_up_R":  {"arm.L": _STAND, "arm.R": dict(at="upperarm01.R", off=(-0.1, -0.14, 0.42), pole=(-1, 0, -0.2)), "hand.R": "point"},
    "point_side_R": {"arm.L": _STAND, "arm.R": dict(at="upperarm01.R", off=(-0.42, -0.16, 0.08), pole=(0, 1, -0.4)), "hand.R": "point"},
    "snap_R":      {"arm.L": _STAND, "arm.R": dict(at="upperarm01.R", off=(-0.12, -0.36, -0.12), pole=(-0.6, 0.2, -1)), "hand.R": "point"},
    "rub_neck_R":  {"arm.L": _STAND, "arm.R": dict(at="neck02", off=(-0.11, 0.06, -0.01), pole=(-1, -0.6, 0.3), wrist=(0.8, 0.4, 0.3)),
                    "hand.R": "relaxed"},
    "forehead_R":  {"arm.L": _STAND, "arm.R": dict(at="head", off=(-0.1, -0.15, 0.04), pole=(-1, -0.2, -0.6), wrist=(0.55, 0.15, 0.8)),
                    "hand.R": "open"},
    "chin_R":      {"arm.L": dict(at="spine03", off=(-0.03, -0.18, 0.02), pole=(1, 0.3, -1)), "hand.L": "relaxed",
                    "arm.R": dict(at="head", off=(-0.02, -0.1, -0.175), pole=(-0.4, -0.2, -1), wrist=(0.1, 0.1, 1)), "hand.R": "fist"},
    "fists_low":   {"arm*": dict(at="upperarm01.L", off=(0.07, -0.1, -0.41), pole=(0.6, 1, 0)), "hand*": "fist"},
    "phone_film":  {"arm.R": dict(at="head", off=(-0.05, -0.34, -0.12), pole=(-0.7, 0.3, -1)), "hand.R": "grip",
                    "arm.L": dict(at="head", off=(0.02, -0.33, -0.17), pole=(0.7, 0.3, -1)), "hand.L": "grip"},
    "phone_selfie_R": {"arm.L": _STAND, "arm.R": dict(at="head", off=(-0.12, -0.42, -0.02), pole=(-0.5, 0.2, -1)), "hand.R": "grip"},
    "phone_check_R":  {"arm.L": _STAND, "arm.R": dict(at="spine01", off=(-0.06, -0.3, -0.1), pole=(-0.4, 0.6, -1)), "hand.R": "grip"},
    "carry_two":   {"arm*": dict(at="upperleg01.L", off=(0.17, -0.02, 0.0), pole=(1, 0.3, 0), wrist=(0.15, 0.0, -1)), "hand*": "grip"},
    "show_box_R":  {"arm.L": _STAND, "arm.R": dict(at="spine01", off=(-0.04, -0.34, 0.02), pole=(-0.6, 0.4, -1), wrist=(0.25, -0.6, 0.2)),
                    "hand.R": "cup"},
    "sit_read":    {"aim": {"spine03": (0, 0.12, 1), "upperleg01.L": (0.06, -1, 0.02), "upperleg01.R": (-0.06, -1, 0.02),
                            "lowerleg01.L": (0.02, -0.08, -1), "lowerleg01.R": (-0.02, -0.08, -1), "head": (0, -0.35, 1)},
                    "arm*": dict(at="spine01", off=(0.11, -0.3, -0.14), pole=(0.8, 0.2, -1)), "hand*": "grip"},   # seated, holding a magazine
    "pocket_R":    {"arm.L": _STAND, "arm.R": dict(at="upperleg01.R", off=(-0.06, -0.09, -0.02), pole=(-0.6, 1, 0)), "hand.R": "relaxed"},
}
# poses not in POSES (project libraries) get hands from their name
_GRIP = ("selfie", "film", "phone", "show_box", "pay", "slide", "carry", "push")


def resolve(preset): return ALIAS.get(preset, preset)


def hand_for(pose, side, preset_hand="relaxed"):
    spec = POSES.get(pose)
    if spec is not None:
        return spec.get(f"hand.{side}", spec.get("hand*", preset_hand))
    if pose.startswith(("film", "carry", "push")): return "grip"
    if any(k in pose for k in _GRIP) and side == "R": return "grip"
    if "point" in pose or "snap" in pose: return "point" if side == "R" else preset_hand
    return preset_hand


def holds_prop(pose, side):
    return hand_for(pose, side) == "grip"


# chains: base-pose transitions start in the body and arrive later at the head and hands (overlapping action)
def chain_of(bone):
    if bone.startswith(("neck", "head")): return "head", 1
    if bone.startswith(("lowerarm",)): return "fore" + bone[-1], 1
    if bone.startswith(("wrist", "finger", "metacarpal")): return "hand" + bone[-1], 2
    if bone.startswith(("clavicle", "shoulder", "upperarm")): return "arm" + bone[-1], 0
    return "core", 0


CHAINS = ("core", "head", "armL", "armR", "foreL", "foreR", "handL", "handR")
LAG = {"core": 0, "head": 1, "armL": 0, "armR": 0, "foreL": 1, "foreR": 1, "handL": 2, "handR": 2}


# ---------------------------------------------------------------- pure helpers
def _h(*p):
    return (zlib.crc32("|".join(map(str, p)).encode()) & 0xFFFFFFFF) / 2 ** 32


def _smooth(x):
    x = min(1.0, max(0.0, x)); return x * x * x * (x * (x * 6 - 15) + 10)


def mirror(d):
    """{'clavicle*': v} -> {'clavicle.L': v, 'clavicle.R': (p, -r, -y)}"""
    out = {}
    for k, v in d.items():
        if k.endswith("*"):
            out[k[:-1] + ".L"] = v; out[k[:-1] + ".R"] = (v[0], -v[1], -v[2])
        else:
            out[k] = v
    return out


def _add(acc, d, k=1.0):
    for b, v in mirror(d).items():
        a = acc.get(b, (0.0, 0.0, 0.0)); acc[b] = (a[0] + k * v[0], a[1] + k * v[1], a[2] + k * v[2])


def transition(u_frames, dur, ant, zeta):
    """Base-pose blend factor for a move whose anticipation starts at u_frames=0, hits its peak at dur frames.
    Anticipation pulls back by -ant first (sin^2, 35% of dur), then an under-damped spring overshoots by
    exp(-pi*zeta/sqrt(1-zeta^2)) and settles: follow-through with continuous velocity."""
    a = 0.35 * dur
    if u_frames <= 0: return 0.0
    if u_frames < a: return -ant * math.sin(math.pi * u_frames / a) ** 2
    t = u_frames - a; td = dur - a                                     # the spring peaks at t = td
    wd = math.pi / max(1.0, td); w = wd / math.sqrt(1 - zeta ** 2)
    return 1 - math.exp(-zeta * w * t) * (math.cos(wd * t) + zeta / math.sqrt(1 - zeta ** 2) * math.sin(wd * t))


def timeline(spec, kind, fps):
    """[(frame, value)] for beats of one kind, sorted."""
    return sorted((int(round(t * fps)), v) for t, k, v in spec.get("beats", []) if k == kind)


def pose_track(spec, n, fps):
    """Per frame: {chain: (pose_from, pose_to, s)} with anticipation + overshoot + chain lag."""
    E = PRESETS[resolve(spec.get("preset", "neutral"))]["energy"]
    dur = max(5, round(0.45 * fps / E)); ant = 0.1 * E; zeta = min(0.85, max(0.55, 0.75 - 0.15 * (E - 1)))
    T = round(1.35 * dur); segs = []; cur = spec.get("pose", "stand")
    for f, p in timeline(spec, "pose", fps):
        if p != cur: segs.append((f - T, cur, p)); cur = p                  # anticipation starts T early: the hit lands on f
    out = []
    for i in range(n):
        row = {}
        for c in CHAINS:
            j = i - LAG[c]; frm = to = spec.get("pose", "stand"); s = 1.0
            for fs, a, b in segs:
                if j >= fs: frm, to, s = a, b, transition(j - fs, T, ant, zeta)
            row[c] = (frm, to, s)
        out.append(row)
    return out


def pose_at(spec, f, fps):
    cur = spec.get("pose", "stand")
    for g, p in timeline(spec, "pose", fps):
        if g <= f: cur = p
    return cur


def look_schedule(spec, n, fps):
    """Look target per frame (name/tuple, or None = straight ahead)."""
    lk = sorted((int(round(t * fps)), v) for t, v in spec.get("look", []))
    out, cur = [], None
    for i in range(n):
        while lk and lk[0][0] <= i: cur = lk.pop(0)[1]
        out.append(cur)
    return out


def preset_weights(spec, n, fps):
    """Per frame {preset: weight} (cross-fades at react beats: sudden presets in 0.2 s, others 0.6 s)."""
    cur = {resolve(spec.get("preset", "neutral")): 1.0}; out = []
    reacts = [(f, resolve(p)) for f, p in timeline(spec, "react", fps)]
    hist = [(0, dict(cur), dict(cur), 1)]
    for f, p in reacts:
        ramp = max(2, round((0.2 if PRESETS[p]["take"] >= 0.7 else 0.6) * fps))
        hist.append((f, None, {p: 1.0}, ramp))
    for i in range(n):
        w = {}
        start = hist[0][2]
        for f, _, tgt, ramp in hist[1:]:
            if i < f: break
            k = _smooth((i - f) / ramp)
            start = {q: start.get(q, 0) * (1 - k) + tgt.get(q, 0) * k for q in set(start) | set(tgt)}
        out.append({q: v for q, v in start.items() if v > 1e-4})
    return out


def blend(weights, key, idx=None):
    v = 0.0
    for p, w in weights.items():
        x = PRESETS[p][key]; v += w * (x[idx] if idx is not None else x)
    return v


# ---------------------------------------------------------------- the planner
def plan(spec, n, fps=24, aims=None, speeds=None, turns=None, speech=None):
    """Per-frame acting for one character in one shot. aims: [(yaw, pitch)] of the look target per frame
    (degrees, body space; None = ahead). speeds: m/s per frame (walking). turns: facing change deg/s.
    speech: [(i0, track)] lipsync plans whose nods/tilts/accents belong to this character.
    Returns {"base", "add", "root", "fingers", "face", "eyes", "blinks", "weights"}."""
    name = spec["name"]; amp = ROLE[spec.get("role", "primary")]
    base = pose_track(spec, n, fps); W = preset_weights(spec, n, fps)
    aims = aims or [None] * n; speeds = speeds or [0.0] * n; turns = turns or [0.0] * n
    accents = [(f, v) for f, v in timeline(spec, "accent", fps)]
    for f, p in timeline(spec, "react", fps):                         # every reaction starts with a take
        if PRESETS[resolve(p)]["take"] > 0: accents.append((f, ("take", PRESETS[resolve(p)]["take"])))
    for i0, tr in speech or []:
        accents += [(i0 + a - tr["f0"], ("beat", 0.8)) for a in tr["accents"]]
    hand_over = timeline(spec, "hands", fps)
    out = {k: [] for k in ("base", "add", "root", "fingers", "face", "eyes", "weights")}
    br_phase = _h(name, "br") * 2 * math.pi; walk_phase = 0.0; walk_w = 0.0
    head = [0.0, 0.0]; fing_prev = None
    shift_sched = []; t, k = _h(name, "s0") * 2.0, 0
    while t < n / fps + 10:
        shift_sched.append((t, 1 if k % 2 == 0 else -1)); t += 0.7 + _h(name, "s", k) * 0.6; k += 1   # scaled by period below
    for i in range(n):
        t = i / fps; w = W[i]
        add = {}
        _ = [_add(add, PRESETS[p]["body"], wt * amp) for p, wt in w.items()]
        # breathing: chest and shoulders rise, head barely moves
        rate, depth = blend(w, "breath", 0), blend(w, "breath", 1) * (0.8 + 0.2 * amp)
        br_phase += 2 * math.pi * rate / fps; b = math.sin(br_phase)
        _add(add, {"spine02": (-0.7 * depth * b, 0, 0), "spine01": (-0.5 * depth * b, 0, 0), "clavicle*": (0, -0.7 * depth * b, 0),
                   "neck01": (0.6 * depth * b, 0, 0)})
        # weight shift (contrapposto): hips over one foot, hip hikes, shoulders counter-tilt, feet stay planted
        period, sa = blend(w, "shift", 0), blend(w, "shift", 1) * amp
        sw = 0.0
        for (ts, side), (tn, _) in zip(shift_sched, shift_sched[1:]):
            ts *= period; tn *= period
            if t >= ts: sw = side * _smooth((t - ts) / 0.9) + (-side) * (1 - _smooth((t - ts) / 0.9)) if t < ts + 0.9 else side
        sw *= sa * (1 - walk_w)
        x = 0.025 * sw; roll = -2.0 * sw                                  # weight on L (+X): L hip up = -roll
        leg = math.degrees(math.asin(max(-0.3, min(0.3, x / 0.82)))) - roll
        free = "R" if sw > 0 else "L"
        _add(add, {"spine05": (0, 1.6 * sw, 0), "spine03": (0, 1.4 * sw, 0), "neck02": (0, -1.0 * sw, 0),
                   "upperleg01.L": (0, leg, 0), "upperleg01.R": (0, leg, 0),
                   f"upperleg01.{free}": (-3 * abs(sw), 0, 0), f"lowerleg01.{free}": (6 * abs(sw), 0, 0)})
        rootrot = (0.0, roll, 0.0); root = [x, 0.0, -0.004 * abs(sw)]
        # micro motion so nobody is a statue (two slow sines per axis, hashed phases)
        mm = lambda a, s: a * (math.sin(2 * math.pi * 0.11 * t + _h(name, s) * 6) + 0.5 * math.sin(2 * math.pi * 0.27 * t + _h(name, s, 2) * 6))
        _add(add, {"head": (mm(0.8, "hp"), mm(0.6, "hr"), mm(1.0, "hy")), "spine03": (mm(0.4, "sp"), 0, mm(0.5, "sy"))}, amp)
        # look: head follows the target with lag; eyes jump first (saccade)
        av = spec.get("avert", blend(w, "avert", 0)); aw = 0.0
        win = int(t / 2.6); u = t - win * 2.6
        if _h(name, "av", win) < av and 0.6 < u < 0.6 + 1.0 + _h(name, "al", win): aw = min(_smooth((u - 0.6) / 0.15), _smooth((1.6 + _h(name, "al", win) - u) / 0.15))
        ay = aw * blend(w, "avert", 1); ap = aw * blend(w, "avert", 2)
        ty, tp = aims[i] if aims[i] else (0.0, 0.0)
        ty = max(-80.0, min(80.0, ty)) * 0.75 + 0.5 * ay; tp = max(-35.0, min(35.0, tp)) * 0.6 + 0.5 * ap
        E = blend(w, "energy"); k_ = 1 - math.exp(-1 / (fps * 0.12 / E))
        head[0] += (ty - head[0]) * k_; head[1] += (tp - head[1]) * k_
        hy, hp = head; torso = max(0.0, abs(hy) - 45) * (1 if hy > 0 else -1)
        hy -= torso
        _add(add, {"neck01": (0.15 * hp, 0, 0.15 * hy), "neck02": (0.2 * hp, 0, 0.2 * hy), "neck03": (0.25 * hp, 0, 0.25 * hy),
                   "head": (0.4 * hp, 0, 0.4 * hy), "spine03": (0, 0, 0.4 * torso), "spine02": (0, 0, 0.35 * torso), "spine01": (0, 0, 0.25 * torso)})
        tr_ = max(-30.0, min(30.0, turns[i] * 0.3))                       # head leads a turn of the whole body
        _add(add, {"neck03": (0, 0, 0.4 * tr_), "head": (0, 0, 0.6 * tr_)})
        # listening: small nods, attention
        if spec.get("role") == "listener":
            nb = int(t / 2.8); v = t - nb * 2.8 - 0.8 * _h(name, "ln", nb)
            if 0 < v < 0.45: _add(add, ACCENTS["nod"][1](v / 0.45), 0.6)
            _add(add, {"spine03": (1.5, 0, 0)})
        # disbelief shake / sighs on their own clock
        for p, wt in w.items():
            if PRESETS[p].get("shake") and wt > 0.5:
                c = t % PRESETS[p]["shake"]
                if c < 1.1: _add(add, ACCENTS["shake"][1](c / 1.1), wt * 0.7)
            if PRESETS[p].get("sigh") and wt > 0.5:
                c = (t + 1.3 * _h(name, "sg")) % PRESETS[p]["sigh"]
                if c < 1.6: _add(add, ACCENTS["sigh"][1](c / 1.6), wt * amp)
        # one-shot accents
        for f, a in accents:
            nm, g = (a if isinstance(a, tuple) else (a, 1.0))
            d, fn = ACCENTS[nm]; u = (i - f) / (d * fps)
            if 0 <= u <= 1: _add(add, fn(u), g * amp)
        for i0, tr in speech or []:                                     # spoken nods and tilts from lipsync.plan
            j = i - i0
            if 0 <= j < len(tr["nod"]): _add(add, {"neck03": (tr["nod"][j], 0, 0), "neck02": (0, tr["tilt"][j], 0)})
        # walking: legs, pelvis bob, hip/shoulder counter-rotation, free arms swing (phase from real distance)
        sp = speeds[i]; climb = spec.get("climb", False)
        walk_w += ((1.0 if sp > 0.08 else 0.0) - walk_w) * (1 - math.exp(-1 / (fps * 0.15)))
        stride = 0.3 if climb else 0.62
        walk_phase += math.pi * sp / fps / stride
        if walk_w > 1e-3:
            s, c = math.sin(walk_phase), math.cos(walk_phase); A = (30 if climb else 21) * walk_w
            knee = (55 if climb else 35) * walk_w
            fr = pose_at(spec, i, fps)
            sw_l = 0.2 if holds_prop(fr, "L") else 1.0; sw_r = 0.2 if holds_prop(fr, "R") else 1.0
            _add(add, {"upperleg01.L": (-A * s, 0, 0), "upperleg01.R": (A * s, 0, 0),
                       "lowerleg01.L": (knee * max(0.0, c) ** 1.5 + 4 * walk_w, 0, 0), "lowerleg01.R": (knee * max(0.0, -c) ** 1.5 + 4 * walk_w, 0, 0),
                       "foot.L": (-8 * walk_w * math.sin(walk_phase + 0.6), 0, 0), "foot.R": (8 * walk_w * math.sin(walk_phase + 0.6), 0, 0),
                       "spine05": (0, 0, -4 * s * walk_w), "spine03": (0, 0, 3 * s * walk_w), "spine02": (0, 0, 2.5 * s * walk_w),
                       "neck02": (0, 0, -1.5 * s * walk_w), "spine04": ((6 if climb else 1.5) * walk_w, 0, 0),
                       "upperarm01.L": (12 * s * walk_w * sw_l, 0, 0), "upperarm01.R": (-12 * s * walk_w * sw_r, 0, 0),
                       "lowerarm01.L": (-5 * walk_w * sw_l * (1 + s) / 2, 0, 0), "lowerarm01.R": (-5 * walk_w * sw_r * (1 - s) / 2, 0, 0)})
            root[2] += -0.022 * abs(s) * walk_w + (0.0 if not climb else 0.0)
            root[0] += 0.012 * c * walk_w
        # hands: pose shape, else preset/beat override; blended over ~5 frames
        hs = {}; main = PRESETS[max(w, key=w.get)]["hands"]
        for side in ("L", "R"):
            ph = hand_for(base[i]["hand" + side][1], side, main)
            for f, v in hand_over:
                if f <= i and ph != "grip": ph = v
            hs[side] = ph
        tgt = {}
        for side, shape in hs.items():
            for fk, curls in HANDS[shape].items():
                for b, cdeg in zip(FINGER_BONES[fk], curls): tgt[f"{b}.{side}"] = cdeg
        fing = tgt if fing_prev is None else {b: fing_prev[b] + (v - fing_prev[b]) * 0.35 for b, v in tgt.items()}
        fing_prev = fing
        # face: blended preset units (scaled by role), heavy lids, rest seal unless the preset opens the jaw
        face = {}
        for p, wt in w.items():
            from_ls = _face(PRESETS[p]["face"])
            for kk, vv in from_ls[0].items(): face[kk] = face.get(kk, 0) + vv * wt * (0.6 + 0.4 * amp)
            for kk, vv in from_ls[1].items(): face[kk] = face.get(kk, 0) + vv * wt
        out["base"].append(base[i]); out["add"].append(add); out["root"].append((tuple(root), rootrot))
        out["fingers"].append(fing); out["face"].append(face); out["eyes"].append((aims[i] is not None, ay, ap)); out["weights"].append(w)
    # blinks: hashed rhythm + at reactions + when the eyes jump to a new target
    sched = look_schedule(spec, n, fps)
    extra = [f for f, _ in timeline(spec, "react", fps)] + [i for i in range(1, n) if sched[i] != sched[i - 1]]
    out["blinks"] = _blinks(name, n, fps, extra)
    return out


def _face(name):
    """(units, rest) for a lipsync EMOTION name - imported lazily so this file stays standalone."""
    try:
        import lipsync
    except ImportError:
        return {}, {}
    E = lipsync.EMOTION.get(name, lipsync.EMOTION["neutral"])
    return E["face"], E.get("rest", lipsync.REST)


def _blinks(name, n, fps, extra):
    out, t, k = [], 0.4 + _h(name, "b0") * 1.5, 0
    while t * fps < n:
        out.append(int(t * fps)); t += 2.2 + 2.6 * _h(name, "b", k); k += 1
    for f in extra:
        if all(abs(f - b) > fps * 0.5 for b in out): out.append(f)
    return sorted(b for b in out if 0 <= b < n)


# ---------------------------------------------------------------- Blender side
class PoseCache:
    """Resolves pose names on one rig into per-bone basis quaternions, parent-space frames (for armature-space
    offsets) and landmarks. poser(rig, name) handles project poses not in POSES."""

    def __init__(self, rig, poser=None):
        self.rig, self.poser, self.c = rig, poser, {}

    def get(self, name):
        if name not in self.c: self.c[name] = self._make(name)
        return self.c[name]

    def _make(self, name):
        import bpy
        from mathutils import Matrix
        rig = self.rig
        for pb in rig.pose.bones: pb.matrix_basis = Matrix()
        bpy.context.view_layer.update()
        if name in POSES:
            spec = POSES[name]
            for b, d in spec.get("aim", {}).items(): _aim(rig, b, d)
            for side in ("L", "R"):
                arm = spec.get(f"arm.{side}") or spec.get("arm*")
                if arm is None: continue
                if side == "R" and f"arm.{side}" not in spec: arm = _mirror_arm(arm)
                _ik(rig, side, arm)
        elif self.poser:
            self.poser(rig, name)
        else:
            raise KeyError(f"unknown pose {name!r}")
        bpy.context.view_layer.update()
        snap = {}
        for pb in rig.pose.bones:
            q = pb.matrix_basis.to_quaternion(); A = (pb.matrix.to_quaternion() @ q.inverted()).normalized()
            snap[pb.name] = (q, A, pb.matrix_basis.to_translation())
        lm = {pb.name: (pb.head.copy(), pb.tail.copy()) for pb in rig.pose.bones}
        for pb in rig.pose.bones: pb.matrix_basis = Matrix()
        return {"q": snap, "lm": lm}


def _aim(rig, bone, d):
    import bpy
    from mathutils import Matrix, Vector
    bpy.context.view_layer.update()
    pb = rig.pose.bones[bone]; cur = (pb.tail - pb.head).normalized()
    q = cur.rotation_difference(Vector(d).normalized()); h = pb.matrix.translation.copy()
    pb.matrix = Matrix.Translation(h) @ q.to_matrix().to_4x4() @ Matrix.Translation(-h) @ pb.matrix
    bpy.context.view_layer.update()


def _mirror_arm(a):
    m = dict(a)
    m["at"] = a["at"].replace(".L", ".R")
    for k in ("off", "pole", "wrist"):
        if k in a: m[k] = (-a[k][0], a[k][1], a[k][2])
    if "twist" in a: m["twist"] = -a["twist"]
    return m


def ik_elbow(S, T, a, b, pole):
    """2-bone IK in plain tuples: shoulder S, wrist target T, bone lengths a, b, pole direction -> elbow E."""
    d = [T[i] - S[i] for i in range(3)]; L = math.sqrt(sum(x * x for x in d)) or 1e-6
    u = [x / L for x in d]; L = min(L, (a + b) * 0.999); L = max(L, abs(a - b) + 1e-4)
    pd = sum(pole[i] * u[i] for i in range(3)); v = [pole[i] - pd * u[i] for i in range(3)]
    vn = math.sqrt(sum(x * x for x in v)) or 1e-6; v = [x / vn for x in v]
    ca = max(-1.0, min(1.0, (a * a + L * L - b * b) / (2 * a * L))); sa = math.sqrt(1 - ca * ca)
    return [S[i] + a * (ca * u[i] + sa * v[i]) for i in range(3)], [S[i] + L * u[i] for i in range(3)]


def _ik(rig, side, arm):
    import bpy
    from mathutils import Vector, Matrix
    bpy.context.view_layer.update(); pb = rig.pose.bones
    S = pb[f"upperarm01.{side}"].head.copy(); el = pb[f"lowerarm01.{side}"].head; wr = pb[f"wrist.{side}"].head
    a = (el - S).length; b = (wr - el).length
    T = pb[arm["at"]].head + Vector(arm["off"])
    E, T2 = ik_elbow(tuple(S), tuple(T), a, b, arm["pole"])
    _aim(rig, f"upperarm01.{side}", Vector(E) - S)
    _aim(rig, f"lowerarm01.{side}", Vector(T2) - Vector(E))
    if arm.get("twist"):
        t = pb[f"lowerarm02.{side}"]; t.rotation_mode = "XYZ"; t.rotation_euler[1] += math.radians(arm["twist"])
        bpy.context.view_layer.update()
    if arm.get("wrist"): _aim(rig, f"wrist.{side}", arm["wrist"])


def _world_at(ob, f):
    """Object matrix at frame f from its own location/rotation fcurves (no frame_set)."""
    from mathutils import Matrix, Euler, Vector
    import camera
    loc, rot = list(ob.location), list(ob.rotation_euler)
    for fc in camera._fcurves(ob):
        if fc.data_path == "location": loc[fc.array_index] = fc.evaluate(f)
        if fc.data_path == "rotation_euler": rot[fc.array_index] = fc.evaluate(f)
    return Matrix.Translation(Vector(loc)) @ Euler(rot).to_matrix().to_4x4()


def _eyes_point(rig):
    b = rig.data.bones
    return (b["eye.L"].head_local + b["eye.R"].head_local) / 2


def target_point(rig, tgt, f, rigs, cache, spec, fps, i):
    """World point a target name refers to at frame f: another cast rig's eyes, 'self:<bone>' (own hand/phone),
    'camera' (only when the scene asks for it), an object name, or an (x, y, z) tuple."""
    import bpy
    from mathutils import Vector
    if tgt is None: return None
    if isinstance(tgt, (tuple, list)): return Vector(tgt)
    if tgt in rigs: return _world_at(rigs[tgt], f) @ _eyes_point(rigs[tgt])
    if tgt.startswith("self:"):
        bone = tgt[5:].replace("phone", "wrist.R"); lm = cache.get(pose_at(spec, i, fps))["lm"][bone]
        return _world_at(rig, f) @ lm[1]
    if tgt == "camera": return bpy.context.scene.camera.matrix_world.translation.copy()
    ob = bpy.data.objects[tgt]
    return _world_at(ob, f).translation if ob.animation_data else ob.matrix_world.translation.copy()


def perform(rig, spec, f0, f1, rigs, poser=None, cache=None, speech=None, fps=24):
    """Key one character's acting for frames f0..f1: bones (pose blend + offsets), fingers, face, blinks, eyes.
    speech: [lipsync tracks] spoken by this character in the span (apply them with lipsync.apply(body=False)
    AFTER this call so the mouth wins). Returns the plan (for checks and shot lists)."""
    import bpy, lipsync
    from mathutils import Vector, Quaternion, Euler, Matrix
    cache = cache or PoseCache(rig, poser); n = f1 - f0 + 1
    for p in {spec.get("pose", "stand")} | {v for _, k, v in spec.get("beats", []) if k == "pose"}: cache.get(p)
    sched = look_schedule(spec, n, fps); eye_rest = _eyes_point(rig)
    aims, pts, speeds, turns = [], [], [], []
    for i in range(n):
        f = f0 + i; M = _world_at(rig, f); Mi = M.inverted()
        P = target_point(rig, sched[i], f, rigs, cache, spec, fps, i); pts.append(P)
        if P is None: aims.append(None)
        else:
            d = Mi @ P - eye_rest
            aims.append((math.degrees(math.atan2(d.x, -d.y)), math.degrees(math.atan2(-d.z, math.hypot(d.x, d.y)))))
        a, b = _world_at(rig, f - 1), _world_at(rig, f + 1)
        speeds.append((b.translation - a.translation).xy.length * fps / 2)
        turns.append(math.degrees(b.to_euler().z - a.to_euler().z) * fps / 2)
    pl = plan(spec, n, fps, aims, speeds, turns, [(t["f0"] - f0, t) for t in (speech or [])])
    # bones
    body_bones = [pb for pb in rig.pose.bones if not pb.name.startswith(("finger", "metacarpal", "eye", "toe"))
                  and pb.name in cache.get(spec.get("pose", "stand"))["q"] and chain_of(pb.name)]
    body_bones = [pb for pb in body_bones if pb.parent is None or pb.name.split(".")[0] in _BODY]
    prev = {}
    for i in range(n):
        f = f0 + i; row = pl["base"][i]; add = pl["add"][i]; (rloc, rrot) = pl["root"][i]
        for pb in body_bones:
            c, _ = chain_of(pb.name); a, b, s = row[c]
            qa, Aa, la = cache.get(a)["q"][pb.name]; qb, Ab, lb = cache.get(b)["q"][pb.name]
            dq = qa.inverted() @ qb; ang, ax = dq.angle, dq.axis
            q = qa @ Quaternion(ax, ang * s) if ang > 1e-6 else qa.copy()
            A = Ab if s > 0.5 else Aa
            o = add.get(pb.name)
            if pb.name == "root": o = tuple((o or (0, 0, 0))[k] + (0, rrot[1], 0)[k] for k in range(3))
            if o:
                R = Euler((math.radians(o[0]), math.radians(o[1]), math.radians(o[2])), "XYZ").to_quaternion()
                q = A.inverted() @ R @ A @ q
            pb.rotation_mode = "XYZ"; e = q.to_euler("XYZ", prev.get(pb.name, Euler())); prev[pb.name] = e
            pb.rotation_euler = e; pb.keyframe_insert("rotation_euler", frame=f)
            if pb.name == "root":
                pb.location = la.lerp(lb, min(1, max(0, s))) + A.inverted() @ Vector(rloc); pb.keyframe_insert("location", frame=f)
        for bn, curl in pl["fingers"][i].items():
            pb = rig.pose.bones.get(bn)
            if pb is None: continue
            pb.rotation_mode = "XYZ"; pb.rotation_euler = (math.radians(curl), 0, 0); pb.keyframe_insert("rotation_euler", frame=f)
    # face (blinks merged with heavy lids), eyes
    body = lipsync.prepare(rig); names = sorted({k for fr in pl["face"] for k in fr} | set(lipsync.BLINK) | set(lipsync.VISEMES))
    bl = lipsync.blink_curve([f0 + b for b in pl["blinks"]], f0, f1)
    chans = {k: [min(1.0, fr.get(k, 0.0)) for fr in pl["face"]] for k in names}
    for k in lipsync.BLINK: chans[k] = [max(a, b) for a, b in zip(chans[k], bl)]
    lipsync._key_values(body, chans, f0)
    e = lipsync.look_rig(rig); hd = 0
    for i in range(n):
        f = f0 + i; M = _world_at(rig, f); has, ay, ap = pl["eyes"][i]
        eye = M @ eye_rest
        P = pts[i] if pts[i] is not None else M @ (eye_rest + Vector((0, -2.0, 0)))
        d = P - eye
        if ay or ap:                                                        # averted gaze: rotate the eye line in body space
            Rb = M.to_quaternion(); db = Rb.inverted() @ d
            db = Euler((math.radians(ap), 0, math.radians(ay)), "XYZ").to_matrix() @ db; d = Rb @ db
        j = int(i / (fps * 0.9)); jit = Vector(((_h(rig.name, "sx", j) - 0.5) * 0.05, 0, (_h(rig.name, "sz", j) - 0.5) * 0.035))
        e.location = eye + d + jit; e.keyframe_insert("location", frame=f)
    return pl


_BODY = {"root", "pelvis", "spine05", "spine04", "spine03", "spine02", "spine01", "neck01", "neck02", "neck03", "head",
         "clavicle", "shoulder01", "upperarm01", "upperarm02", "lowerarm01", "lowerarm02", "wrist",
         "upperleg01", "upperleg02", "lowerleg01", "lowerleg02", "foot"}


def eyeline_lint(rigs, specs, f0, f1, step=6):
    """Warn when a character's eye line points into the lens (< 10 deg) unless its spec says camera_ok.
    Eye lines to another character are motivated (over-the-shoulder grammar puts them just off the lens)."""
    import bpy
    sc = bpy.context.scene; out = []
    for name, spec in specs.items():
        if spec.get("camera_ok") or f"EMPTY_Look_{name}" not in bpy.data.objects: continue
        rig = rigs[name]; e = bpy.data.objects[f"EMPTY_Look_{name}"]; sched = look_schedule(spec, f1 - f0 + 1, sc.render.fps)
        for f in range(f0, f1 + 1, step):
            if isinstance(sched[f - f0], str) and sched[f - f0] in rigs: continue
            sc.frame_set(f); cam = sc.camera.matrix_world.translation
            eye = rig.matrix_world @ _eyes_point(rig); a = (e.matrix_world.translation - eye); c = cam - eye
            if a.length and c.length and math.degrees(a.angle(c)) < 10:
                out.append(f"{name} looks into the lens at frame {f}"); break
    return out


def foot_ik(rig, f0, f1, plants, lift=0.14, ankle=0.08):
    """Plant the feet on given footholds (stairs, kerbs) with IK: plants = [(frame, "L"|"R", world (x, y, z))] =
    when each foot lands where. Between two plants of a foot the ankle swings in a lifted arc; IK chains
    (lowerleg02 -> upperleg01) reach the ankle targets, knees aim at poles in front of the rig. Influence is
    keyed 1 inside f0..f1 only, so the acting layer's leg cycle runs everywhere else."""
    import bpy
    from mathutils import Vector
    sc = bpy.context.scene; out = {}
    for side in ("L", "R"):
        tgt = bpy.data.objects.get(f"IK_{rig.name}_{side}") or bpy.data.objects.new(f"IK_{rig.name}_{side}", None)
        pole = bpy.data.objects.get(f"POLE_{rig.name}_{side}") or bpy.data.objects.new(f"POLE_{rig.name}_{side}", None)
        for o in (tgt, pole):
            if o.name not in sc.collection.objects: sc.collection.objects.link(o)
        pole.parent = rig; pole.location = (0.12 if side == "L" else -0.12, -0.8, 0.55)
        pb = rig.pose.bones[f"lowerleg02.{side}"]
        c = pb.constraints.get("FOOT_IK") or pb.constraints.new("IK"); c.name = "FOOT_IK"
        c.target = tgt; c.pole_target = pole; c.chain_count = 4; c.pole_angle = math.radians(-90); c.use_tail = True
        for f, v in ((f0 - 1, 0.0), (f0, 1.0), (f1, 1.0), (f1 + 1, 0.0)):
            c.influence = v; c.keyframe_insert("influence", frame=f)
        P = sorted((f, Vector(p) + Vector((0, 0, ankle))) for f, sd, p in plants if sd == side)
        for f in range(f0, f1 + 1):
            prev = max((q for q in P if q[0] <= f), default=P[0], key=lambda q: q[0])
            nxt = min((q for q in P if q[0] > f), default=None, key=lambda q: q[0])
            if nxt is None or f <= prev[0]: pos = prev[1]
            else:
                swing0 = max(prev[0], nxt[0] - 10)                       # the foot leaves ~10 frames before it lands
                u = 0.0 if f < swing0 else (f - swing0) / max(1, nxt[0] - swing0)
                u = u * u * (3 - 2 * u); pos = prev[1].lerp(nxt[1], u) + Vector((0, 0, lift * math.sin(math.pi * u)))
            tgt.location = pos; tgt.keyframe_insert("location", frame=f)
        out[side] = tgt
    return out


# ---------------------------------------------------------------- reusable behaviours
def filmer(name, subject, dur, seed=0, react=None, role="background"):
    """A friend filming the subject: eyes on the phone screen, glances over it at the subject, re-grips and
    tilts the phone, laughs at the subject's big moments. react: [(t, accent)]."""
    look, beats, t, k = [(0.0, "self:phone")], [], 0.3 + _h(name, seed, "f") * 0.6, 0
    while t < dur - 0.4:
        if _h(name, seed, "g", k) < 0.55:
            look += [(t, subject), (t + 0.7 + 0.6 * _h(name, seed, "d", k), "self:phone")]
        else:
            beats.append((t, "accent", "adjust_phone"))
        t += 1.3 + 1.1 * _h(name, seed, "n", k); k += 1
    beats += [(rt, "accent", a) for rt, a in (react or [])]
    return dict(name=name, role=role, look=sorted(look, key=lambda x: x[0]), beats=beats, intent=f"get {subject}'s best moment on camera")


# ---------------------------------------------------------------- self-test (pure python)
def _selftest():
    fps = 24
    # transition: anticipation goes negative, overshoot bounded, settles at 1
    tr = [transition(u, 14, 0.1, 0.7) for u in range(0, 60)]
    assert min(tr[:6]) < -0.05 and 1.02 < max(tr) < 1.12 and abs(tr[-1] - 1) < 0.01, (min(tr), max(tr), tr[-1])
    assert all(abs(a - b) < 0.3 for a, b in zip(tr, tr[1:])), "transition jumps"
    # IK reaches and respects bone lengths
    E, T = ik_elbow((0, 0, 0), (0.3, -0.2, -0.2), 0.25, 0.25, (0, 1, 0))
    la = math.dist((0, 0, 0), E); lb = math.dist(E, T)
    assert abs(la - 0.25) < 1e-6 and abs(lb - 0.25) < 1e-6 and E[1] > -0.1, (la, lb, E)
    assert mirror({"clavicle*": (1, 2, 3)}) == {"clavicle.L": (1, 2, 3), "clavicle.R": (1, -2, -3)}
    spec = dict(name="CLK", preset="neutral", pose="stand", look=[(0, "INF")],
                beats=[(1.0, "pose", "palms_up"), (1.5, "react", "disbelief"), (2.5, "accent", "nod")])
    n = 4 * fps; aims = [(30.0, 5.0)] * n
    p = plan(spec, n, fps, aims); assert p == plan(spec, n, fps, aims), "deterministic"
    # pose lands near 1.0 s: by then the arm chain is near the new pose and was pulled back before it
    s_arm = [r["armR"][2] for r in p["base"]]
    assert p["base"][fps]["armR"][1] == "palms_up" and 0.9 < s_arm[fps] < 1.15 and min(s_arm) < -0.02
    # hands lag the arms (overlapping action)
    assert p["base"][fps - 6]["handR"][2] < p["base"][fps - 6]["armR"][2]
    # preset cross-fade
    assert p["weights"][0] == {"neutral": 1.0} and abs(p["weights"][-1].get("disbelief", 0) - 1) < 1e-6
    # head turns toward the target with lag, ends near 75% of 30 deg
    hy = [sum(v[2] for k, v in a.items() if k in ("neck01", "neck02", "neck03", "head")) for a in p["add"]]
    assert hy[1] < hy[12] < hy[40] and 18 < hy[40] < 26, hy[40]
    # breathing and weight shift keep moving; no offset is huge
    sp = [a.get("spine02", (0, 0, 0))[0] for a in p["add"][:fps * 2]]; assert max(sp) - min(sp) > 0.5
    assert all(abs(c) < 35 for a in p["add"] for v in a.values() for c in v)
    # every preset plans without error and differs from neutral
    for pr in PRESETS:
        q = plan(dict(name="X", preset=pr), fps, fps); assert len(q["add"]) == fps
    for a in ALIAS: assert resolve(a) in PRESETS
    # walking: legs move only when moving
    w = plan(dict(name="W", pose="stand"), 2 * fps, fps, speeds=[1.0] * fps + [0.0] * fps)
    lg = [a.get("upperleg01.L", (0, 0, 0))[0] for a in w["add"]]
    assert max(map(abs, lg[10:24])) > 8 and max(map(abs, lg[-6:])) < 4
    assert hand_for("selfie", "R") == "grip" and hand_for("point_up_R", "R") == "point" and hand_for("stand", "L", "fist") == "fist"
    f = filmer("F1", "INF", 6.0); assert f["look"][0][1] == "self:phone" and any(b[2] == "adjust_phone" for b in f["beats"])
    print("acting.py self-test OK")


if __name__ == "__main__":
    _selftest()
