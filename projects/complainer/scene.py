"""The Complainer, animated: shots.py staged on one timeline in the demo's EEVEE look (9:16, 24 fps).
Build:  END_S=20 $PY tools/bl.py run projects/complainer/scene.py --blend projects/complainer/scene.blend --save
Render: render_range.py workers on scene.blend -> frames/f_####.png; then python3 finish.py (labels, voice, captions).
Each shot keys its own cast/props at its first frame and gets its own camera rig (bound by a timeline marker)."""
import os, sys, math, runpy
import bpy
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sb = runpy.run_path(os.path.join(HERE, "storyboard.py"), run_name="storyboard_lib")  # sets, cast, poses, shot_camera
import look, camera as C, shotcraft as SC, acting as A, direction, hotelkit as HK  # storyboard put HERE and tools/ on sys.path

S, RIGS, OBJ, POSES, pose, ORIGIN = (sb[k] for k in ("S", "RIGS", "OBJ", "POSES", "pose", "ORIGIN"))
FPS, END_S = 24, float(os.environ.get("END_S", 20))
sc = bpy.context.scene
sc.render.fps = FPS; sc.frame_start, sc.frame_end = 1, round(END_S * FPS)
look.eevee(sb, os.path.join(HERE, "frames", "f_"))
bpy.data.objects["TXT_stamp"].hide_render = True; bpy.data.objects["TXT_tag"].data.body = ""
for n in ("open_case", "roach_box", "roach"): OBJ[n].location = (0, -200, 0)

WALK = {"selfie_walk": "selfie", "film_walk": "film", "carry_climb": "carry_climb"}  # walkers: arms pose + acting walk cycle
STEP = 8  # location keys every 8 frames (stairs need the step height)
SPEED = {"carry_climb": 0.45}  # m/s along the facing; walkers default 0.9
HANDHELD = ("selfie", "film", "phone")  # poses that hold a phone in the right hand
poser = lambda rig, p: pose(rig.name, rig, p)  # storyboard pose library; tools/acting.py POSES take precedence
CACHES = {n: A.PoseCache(r, poser) for n, r in RIGS.items()}


def key_place(name, f, loc, face):
    """Place/face a rig at frame f (object keys only: tools/acting.py keys every bone per frame)."""
    r = RIGS[name]; r.location = Vector(loc); r.rotation_euler = (0, 0, math.radians(face))
    r.keyframe_insert("location", frame=f); r.keyframe_insert("rotation_euler", frame=f)


def spec_for(s, name, f0, f1):
    """tools/acting.py spec for one character in one shot, from direction.py (defaults if a shot has none)."""
    x, y, face, p = s["chars"][name]; o = ORIGIN[s["set"]]
    dr = dict(direction.DIR.get(s["id"], {}).get(name, {}))
    if "filmer" in dr:
        sp = A.filmer(name, dr.pop("filmer"), (f1 - f0 + 1) / FPS, seed=s["id"], react=dr.pop("react"), role=dr.pop("role"))
        sp.update(dr)
    else:
        sp = dict(dr)
    sp["name"] = name; sp.setdefault("pose", WALK.get(p, p)); sp.setdefault("preset", "neutral")
    sp.setdefault("role", "primary" if s["cam"][1] == name else "listener"); sp.setdefault("intent", "(no direction yet)")
    if p == "carry_climb": sp["climb"] = True
    ahead = Matrix.Rotation(math.radians(face), 3, "Z") @ Vector((0, -2.0, 0))

    def where(v):  # set-local points -> world; cast not in this shot -> a point ahead of the actor
        if isinstance(v, tuple): return (v[0] + o[0], v[1] + o[1], v[2] + o[2])
        if v in RIGS and v not in s["chars"]: return (o[0] + x + ahead.x, o[1] + y + ahead.y, o[2] + 1.6)
        return v
    sp["look"] = [(t, where(v)) for t, v in sp.get("look", [])] or (
        [(0, s["cam"][1])] if s["cam"][1] in s["chars"] and s["cam"][1] != name else [])
    return sp


def key_vis(ob, f, visible):  # hide_viewport too: hidden props must not block shotcraft's line-of-sight rays
    ob.hide_render = ob.hide_viewport = not visible
    ob.keyframe_insert("hide_render", frame=f); ob.keyframe_insert("hide_viewport", frame=f)


def stand_z(set_, y):
    return 0.6 * max(0.0, y) + 0.18 if set_ == "stairs" else 0.0  # stair k: y = 0.3k, top = 0.18(k+1)


# phones ride each filmer's right wrist; the small box rides the influencer's
PHONES = {}
for name in ("INF", "F1", "F2"):
    ph = OBJ["phone"] if name == "INF" else OBJ["phone"].copy()
    if name != "INF": sc.collection.objects.link(ph)
    PHONES[name] = ph
for ob, name in [(PHONES[n], n) for n in PHONES] + [(OBJ["small_box"], "INF")]:
    ob.location = (0, 0, 0)
    c = ob.constraints.new("COPY_LOCATION"); c.target = RIGS[name]; c.subtarget = "wrist.R"; c.head_tail = 1.0
    c = ob.constraints.new("COPY_ROTATION"); c.target = RIGS[name]; c.subtarget = "wrist.R"

# 14 bags strapped to the clerk for the stairs (rig-local: beside him and stacked on his back)
BAGS = []
for k, (sx, by, z) in enumerate(((0.48, 0, 0.55), (-0.48, 0, 0.55), (0, 0.32, 1.05), (0, 0.32, 1.45), (0, 0.32, 1.85))):
    b = sb["box"]((0, 0, 0), (0.45, 0.25, 0.4), sb["CASE_COLS"][k], f"SM_Bag{k}")
    b.parent = RIGS["CLK"]; b.matrix_parent_inverse = Matrix(); b.location = (sx, by, z)  # +Y local = behind him
    BAGS.append(b)

cams, rows = [], []
for s in S:
    if s["t0"] >= END_S: break
    assert s["set"], f"shot {s['id']}: card shots are not built yet"
    f0, f1 = round(s["t0"] * FPS) + 1, min(round(s["t1"] * FPS), sc.frame_end)
    o, set_ = ORIGIN[s["set"]], s["set"]
    walking = any(p in WALK for *_, p in s["chars"].values())
    for name in RIGS:
        if name not in s["chars"]:
            key_place(name, f0, (0, -100, 0), 0); continue
        x, y, face, p = s["chars"][name]
        walks = walking and (p in WALK or p.startswith(HANDHELD))  # the entourage walks with him
        if walks and set_ == "lobby": face = 180  # shortcut: lobby walkers always head in toward the desk (+Y)
        fwd = Matrix.Rotation(math.radians(face), 3, "Z") @ Vector((0, -1, 0))
        travel = fwd * SPEED.get(p, 0.9) * (f1 - f0) / FPS if walks else Vector()
        start = Vector((o[0] + x, o[1] + y, 0)) - travel / 2
        frames = list(range(f0, f1, STEP)) + [f1] if walks else [f0, f1]
        for f in frames:
            pos = start + travel * ((f - f0) / max(1, f1 - f0))
            pos.z = o[2] + stand_z(set_, pos.y - o[1])
            key_place(name, f, pos, face)
        pose(name, RIGS[name], WALK.get(p, p))  # static pose for camera framing; acting keys come after placement
    for name, ph in PHONES.items():
        key_vis(ph, f0, name in s["chars"] and s["chars"][name][3].startswith(HANDHELD))
    key_vis(OBJ["small_box"], f0, s["props"].get("small_box") == "INF")
    vip = sb["HOTEL"]["elevators"]["vip"]; HK.key_doors(vip, f0, 1.0)              # VIP doors: open, closing on elevator shots
    if "VIP doors close" in s["note"] or "doors close on them" in s["note"]:
        HK.key_doors(vip, f0 + (f1 - f0) // 3, 1.0); HK.key_doors(vip, f1, 0.0)
    for b in BAGS: key_vis(b, f0, s["props"].get("bags_on") == "CLK")
    cx, cy = s["props"].get("cart", (-2.2, 3.6)) if set_ == "lobby" else (0, -200)
    OBJ["cart"].location = (o[0] + cx, o[1] + cy, o[2]); OBJ["cart"].keyframe_insert("location", frame=f0)

    # camera: the storyboard's placement + move, framed on the shot's first frame
    sc.frame_set(f0); bpy.context.view_layer.update()
    rg, cpos, aim, hd, info = sb["shot_camera"](s, f0, f1)
    subj = s["cam"][1]
    if walking and not s.get("move") and s["cam"][2] != "ots" and subj in s["chars"]:
        sc.frame_set(f1); end = RIGS[subj].location.copy(); sc.frame_set(f0)
        C.move(rg, f0, f1, end - RIGS[subj].location, ease="linear")  # truck with the walker: framing holds
    if subj in RIGS and not (s.get("move") or {}).get("fstop"):
        C.dof(rg, 2.8, RIGS[subj], "head")
    m = sc.timeline_markers.new(rg.cam.name, frame=f0); m.camera = rg.cam
    cams.append((s["id"], f0, f1, info))
    rows.append(dict(id=s["id"], f0=f0, f1=f1, type=f"{s['cam'][0]} {s['cam'][2]}", subject=subj, purpose=s["note"],
                     **C.describe(rg, f0, f1, subj if rg.cam.data.dof.use_dof else None)))
    print("SHOT", s["id"], f0, f1, info)

# acting: every character in every shot gets its direction (intention, preset, eyes, beats) - see direction.py
acted, notes = [], []
for s in S:
    if s["t0"] >= END_S: break
    f0, f1 = round(s["t0"] * FPS) + 1, min(round(s["t1"] * FPS), sc.frame_end)
    specs = {n: spec_for(s, n, f0, f1) for n in s["chars"]}
    for n, sp in specs.items():
        A.perform(RIGS[n], sp, f0, f1, RIGS, poser, cache=CACHES[n], fps=FPS)
        acted.append((s["id"], n, sp))
    notes += [f"shot {s['id']}: {w}" for w in A.eyeline_lint(RIGS, specs, f0, f1)]
with open(os.path.join(HERE, "acting.md"), "w") as fh:
    fh.write("# Acting direction (built from direction.py)\n\n| shot | who | intention | preset | role | look | beats |\n|---|---|---|---|---|---|---|\n")
    for sid, n, sp in acted:
        lk = ", ".join(f"{t:.1f}s {v if isinstance(v, str) else 'point'}" for t, v in sp["look"])
        bt = "; ".join(f"{t:.2f}s {k} {v}" for t, k, v in sorted(sp.get("beats", [])))
        fh.write(f"| {sid} | {n} | {sp['intent']} | {sp['preset']} | {sp['role']} | {lk} | {bt} |\n")
for w in notes: print("EYELINE LINT:", w)

# cast: linear walk paths, smooth limbs; props and visibility snap at the cuts
for ob in list(RIGS.values()) + [OBJ["cart"], OBJ["small_box"], *PHONES.values(), *BAGS]:
    is_rig = ob in RIGS.values()
    for fc in C._fcurves(ob):
        for kp in fc.keyframe_points:
            kp.interpolation = ("LINEAR" if fc.data_path == "location" else "BEZIER") if is_rig else "CONSTANT"
sc.camera = min(sc.timeline_markers, key=lambda m: m.frame).camera
SC.shotlist(rows, os.path.join(HERE, "shotlist.md"), FPS)  # review this before rendering
for w in SC.camera_lint(rows): print("CAMERA LINT:", w)
sc.frame_set(1)
print("SCENE built:", len(cams), "shots,", sc.frame_end, "frames")
