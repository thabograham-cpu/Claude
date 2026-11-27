"""The Complainer, animated: shots.py staged on one timeline inside the persistent hotel (9:16, 24 fps).
Build:  END_S=21.95 $PY tools/bl.py run projects/complainer/scene.py --blend projects/complainer/scene.blend --save
Render: render_range.py workers on scene.blend -> frames/f_####.png; then python3 finish.py (mix, captions).
Pipeline per shot: place/walk the cast (object keys) -> camera (designed cam_path, insert_on, or shotcraft) ->
acting for everyone (tools/acting.py, direction.py) -> props on bones (phones, bug box, the clerk's 14 bags),
foot IK on stairs, lip sync on quoted lines (tools/lipsync.py) -> focus pulls -> face boxes for captions."""
import os, sys, math, runpy, json
import bpy
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sb = runpy.run_path(os.path.join(HERE, "storyboard.py"), run_name="storyboard_lib")  # hotel, cast, poses, shot_camera
import look, camera as C, shotcraft as SC, acting as A, direction, hotelkit as HK, lipsync as LS  # storyboard put tools/ on sys.path

S, RIGS, OBJ, POSES, pose, ORIGIN = (sb[k] for k in ("S", "RIGS", "OBJ", "POSES", "pose", "ORIGIN"))
FPS, END_S = 24, float(os.environ.get("END_S", 21.95))
sc = bpy.context.scene; PAL = sb["HOTEL"]["palette"]
sc.render.fps = FPS; sc.frame_start, sc.frame_end = 1, round(END_S * FPS)
RES = tuple(int(v) for v in os.environ.get("RES", "432x768").split("x"))            # draft previews: RES=270x480 SAMPLES=6
look.eevee(sb, os.path.join(HERE, "frames", "f_"), RES, int(os.environ.get("SAMPLES", 12)))
bpy.data.objects["TXT_tag"].data.body = ""
for n in ("open_case", "roach_box", "roach"): OBJ[n].location = (0, -200, 0)

WALK = {"selfie_walk": "selfie", "film_walk": "film", "carry_climb": "carry_climb"}  # walkers: arms pose + acting walk cycle
STEP = 8
SPEED = {"carry_climb": 0.45}
HANDHELD = ("selfie", "film", "phone")
poser = lambda rig, p: pose(rig.name, rig, p)  # storyboard pose library; tools/acting.py POSES take precedence
CACHES = {n: A.PoseCache(r, poser) for n, r in RIGS.items()}
QUOTES = [dict(who="INF", phones="audio/q_deskboy.phones.json", start=14.40, emotion="arrogant")]  # lines a character performs


def frames_of(s): return round(s["t0"] * FPS) + 1, min(round(s["t1"] * FPS), sc.frame_end)


def key_place(name, f, loc, face):
    r = RIGS[name]; r.location = Vector(loc); r.rotation_euler = (0, 0, math.radians(face))
    r.keyframe_insert("location", frame=f); r.keyframe_insert("rotation_euler", frame=f)


def key_vis(ob, f, visible):  # hide_viewport too: hidden things must not block shotcraft's rays or cost render time
    ob.hide_render = ob.hide_viewport = not visible
    ob.keyframe_insert("hide_render", frame=f); ob.keyframe_insert("hide_viewport", frame=f)


def stand_z(set_, y):
    return max(0.0, 0.6 * y + 0.06) if set_ == "stairs" else 0.0  # smooth ramp through the treads; foot IK does the contact


def spec_for(s, name, f0, f1):
    """tools/acting.py spec for one character in one shot, from direction.py (defaults if a shot has none)."""
    x, y, face, p = s["chars"][name][:4]; o = ORIGIN[s["set"]]
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

    def where(v):
        if isinstance(v, tuple): return (v[0] + o[0], v[1] + o[1], v[2] + o[2])
        if v in RIGS and v not in s["chars"]: return (o[0] + x + ahead.x, o[1] + y + ahead.y, o[2] + 1.6)
        return v
    sp["look"] = [(t, where(v)) for t, v in sp.get("look", [])] or (
        [(0, s["cam"][1])] if s["cam"][1] in s["chars"] and s["cam"][1] != name else [])
    return sp


def rig_meshes(r): return [c for c in r.children_recursive if c.type == "MESH"]


def attach(ob, rig, bone, world):
    """Parent ob to a pose bone keeping a given world matrix at the current frame (it then rides the bone)."""
    ob.parent = rig; ob.parent_type = "BONE"; ob.parent_bone = bone; ob.matrix_parent_inverse = Matrix()
    bpy.context.view_layer.update(); ob.matrix_world = world; bpy.context.view_layer.update()


def frame_from(pos, x_axis, y_axis, z_axis):
    return Matrix.Translation(pos) @ Matrix((x_axis, y_axis, z_axis)).transposed().to_4x4()


# ---------------------------------------------------------------- 1. cast placement, props state, cameras
for s in S:
    if s["t0"] >= END_S: break
    f0, f1 = frames_of(s); o, set_ = Vector(ORIGIN[s["set"]]), s["set"]
    walking = any(c[3] in WALK for c in s["chars"].values())
    for name, r in RIGS.items():
        present = name in s["chars"]
        for m in rig_meshes(r): key_vis(m, f0, present)
        if not present:
            key_place(name, f0, (0, -100, 0), 0); continue
        x, y, face, p = s["chars"][name][:4]; extra = s["chars"][name][4] if len(s["chars"][name]) > 4 else {}
        if "path" in extra:                                                           # designed blocking: keyed path points
            for t, px, py, pf in extra["path"]:
                key_place(name, f0 + round(t * FPS), (o.x + px, o.y + py, o.z + stand_z(set_, py)), pf)
            if set_ == "stairs":                                                      # follow the stair ramp between path keys
                (ta, ya), (tb, yb) = (extra["path"][0][0], extra["path"][0][2]), (extra["path"][-1][0], extra["path"][-1][2])
                for f in range(f0, f1 + 1, 2):
                    u = min(1, max(0, (f - f0) / FPS - ta) / max(1e-6, tb - ta)); yy = ya + (yb - ya) * u
                    key_place(name, f, (o.x + x, o.y + yy, o.z + stand_z(set_, yy)), face)
        else:
            walks = walking and (p in WALK or p.startswith(HANDHELD))
            if walks and set_ == "lobby": face = 180
            fwd = Matrix.Rotation(math.radians(face), 3, "Z") @ Vector((0, -1, 0))
            travel = fwd * SPEED.get(p, 0.9) * (f1 - f0) / FPS if walks else Vector()
            start = Vector((o.x + x, o.y + y, 0)) - travel / 2
            for f in (list(range(f0, f1, STEP)) + [f1] if walks else [f0, f1]):
                pos = start + travel * ((f - f0) / max(1, f1 - f0)); pos.z = o.z + stand_z(set_, pos.y - o.y)
                key_place(name, f, pos, face)
        for pb in RIGS[name].pose.bones:                                               # static pose for camera framing (acting keys come later)
            q, _, l = CACHES[name].get(WALK.get(p, p))["q"][pb.name]; pb.matrix_basis = Matrix.Translation(l) @ q.to_matrix().to_4x4()
    show_bill = s["cam"][1] == "bill" or any(k in s["props"] for k in ("bill_text", "stamp")) or s["t0"] >= 69.8
    for ob in [OBJ["bill"], *OBJ["bill"].children]: key_vis(ob, f0, show_bill and (ob.name != "TXT_stamp" or "stamp" in s["props"]))
    for ob in [OBJ["lawbook"], *OBJ["lawbook"].children]: key_vis(ob, f0, s["t0"] >= 83.0)
    vip = sb["HOTEL"]["elevators"]["vip"]; HK.key_doors(vip, f0, 1.0)
    if "VIP doors close" in s["note"] or "doors close on them" in s["note"]:
        HK.key_doors(vip, f0 + (f1 - f0) // 3, 1.0); HK.key_doors(vip, f1, 0.0)
    cart = s["props"].get("cart", (-2.2, 3.6))
    cx, cy = (0, -200) if cart == "off" or set_ != "lobby" else cart
    OBJ["cart"].location = (o.x + cx, o.y + cy, o.z); OBJ["cart"].keyframe_insert("location", frame=f0)
    for w in OBJ["cart_wheels"]: w.rotation_euler.x = 0.0; w.keyframe_insert("rotation_euler", index=0, frame=f0)
    if "cart_from" in s["props"]:                                                    # rolls in, wheels turning, eases to a stop
        (ax, ay), n_roll = s["props"]["cart_from"], round(0.6 * FPS)
        for i in range(n_roll + 1):
            u = 1 - (1 - i / n_roll) ** 3; dist = math.hypot(cx - ax, cy - ay) * u
            OBJ["cart"].location = (o.x + ax + (cx - ax) * u, o.y + ay + (cy - ay) * u, o.z); OBJ["cart"].keyframe_insert("location", frame=f0 + i)
            for w in OBJ["cart_wheels"]: w.rotation_euler.x = -dist / 0.05; w.keyframe_insert("rotation_euler", index=0, frame=f0 + i)
    if s.get("insert_on"): continue                                                  # camera placed after the props are on the hand
    sc.frame_set(f1 if "cart_from" in s["props"] else f0); bpy.context.view_layer.update()
    s["_rig"] = sb["shot_camera"](s, f0, f1)[0]; sc.frame_set(f0)

# ---------------------------------------------------------------- 2. acting (+ the performed quote) for everyone in every shot
tracks = {}
for q in QUOTES:
    ph = json.load(open(os.path.join(HERE, q["phones"])))
    tracks.setdefault(q["who"], []).append(LS.plan(ph, q["emotion"], FPS, q["start"], q["who"]))
acted, notes = [], []
for s in S:
    if s["t0"] >= END_S: break
    f0, f1 = frames_of(s)
    specs = {n: spec_for(s, n, f0, f1) for n in s["chars"]}
    for n, sp in specs.items():
        sp_tracks = [t for t in tracks.get(n, []) if t["f0"] <= f1 and t["f1"] >= f0 and s["cam"][1] == n]
        A.perform(RIGS[n], sp, f0, f1, RIGS, poser, cache=CACHES[n], speech=sp_tracks, fps=FPS)
        acted.append((s["id"], n, sp))
    s["_specs"] = specs
for who, trs in tracks.items():                                                       # the mouth wins over the acting face
    for tr in trs: LS.apply(RIGS[who], tr, body=False)

# ---------------------------------------------------------------- 3. props that live on bones
PHONES = {}
for n in ("INF", "F1", "F2"):                                                         # screen faces the holder's eyes
    s = next(x for x in S if n in x["chars"] and x["chars"][n][3].startswith(HANDHELD))
    sc.frame_set(frames_of(s)[0] + 2); r = RIGS[n]; pb = r.pose.bones["wrist.R"]
    hand = r.matrix_world @ pb.tail; fwd = (r.matrix_world.to_3x3() @ (pb.tail - pb.head)).normalized()
    pos = hand + fwd * 0.05; eye = r.matrix_world @ A._eyes_point(r); n_ = (eye - pos).normalized()
    up = (Vector((0, 0, 1)) - n_ * n_.z).normalized()                                 # phone: -Y = screen (to the eyes), Z = long axis
    ph = HK.phone(n, sc.collection, PAL); attach(ph, r, "wrist.R", frame_from(pos, (-n_).cross(up), -n_, up)); PHONES[n] = ph
s4 = next(x for x in S if x.get("insert_on"))
f0, f1 = frames_of(s4); fa = f0 + round(0.9 * FPS)
sc.frame_set(fa); r = RIGS["INF"]; pb = r.pose.bones["wrist.R"]
palm = r.matrix_world @ pb.tail + (r.matrix_world.to_3x3() @ (pb.tail - pb.head)).normalized() * 0.02 + Vector((0, 0, 0.035))
face_dir = (r.matrix_world.to_3x3() @ Vector((0, -1, 0))).normalized()                # his front; the box label faces it
attach(OBJ["bugbox"], r, "wrist.R", frame_from(palm, (-face_dir).cross(Vector((0, 0, 1))), -face_dir, Vector((0, 0, 1))))  # label faces out
lid = bpy.data.objects["LID_inf"]; roach = OBJ["bugroach"]; ant = [c for c in roach.children if "Antenna" in c.name]
for f, ang in ((f0, 0), (f0 + round(1.78 * FPS), 0), (f0 + round(2.05 * FPS), -118)):
    lid.rotation_euler.x = math.radians(ang); lid.keyframe_insert("rotation_euler", index=0, frame=f)
for f, (y, z) in ((f0, (0.012, 0.004)), (f0 + round(2.1 * FPS), (0.012, 0.004)), (f0 + round(2.55 * FPS), (-0.005, 0.058))):
    roach.location = (0, y, z); roach.keyframe_insert("location", frame=f)
roach.rotation_euler.x = 0; roach.keyframe_insert("rotation_euler", index=0, frame=f0 + round(2.1 * FPS))
roach.rotation_euler.x = math.radians(-35); roach.keyframe_insert("rotation_euler", index=0, frame=f0 + round(2.55 * FPS))
for k, a_ in enumerate(ant):
    for f in range(f0 + round(2.1 * FPS), f1 + 1, 2):
        a_.rotation_euler.z = math.radians(18 * math.sin(f * 0.9 + k * 1.7)); a_.keyframe_insert("rotation_euler", index=2, frame=f)
box_parts = [OBJ["bugbox"], *OBJ["bugbox"].children_recursive]
for s in S:
    if s["t0"] >= END_S: break
    a0 = frames_of(s)[0]
    for ob in box_parts: key_vis(ob, a0, s["props"].get("small_box") == "INF")
    for n, ph in PHONES.items(): key_vis(ph, a0, n in s["chars"] and s["chars"][n][3].startswith(HANDHELD))
# the camera for the insert: in front of the box at the moment it's presented, shallow focus
sc.frame_set(fa); bp = OBJ["bugbox"].matrix_world.translation
name_, off, lens = s4["insert_on"]; rg = C.rig(f"S{s4['id']:02d}", bp + Vector(off), bp + Vector((0, 0, 0.04)), lens); s4["_rig"] = rg
# the clerk's fourteen bags for the stairs: on his back, two in each hand, under his arms, one hanging at his chest
st = [x for x in S if x["props"].get("bags_on") == "CLK" and x["t0"] < END_S]
if st:
    fs = frames_of(st[0])[0] + 6; sc.frame_set(fs); r = RIGS["CLK"]; M = r.matrix_world; R3 = M.to_3x3()
    lx, ly, lz = (R3 @ Vector(v) for v in ((1, 0, 0), (0, 1, 0), (0, 0, 1)))      # his left, his back, up (world)
    loc = lambda v: M @ Vector(v)
    BAGS = []
    def bag(kind, col, bone, pos, ax):
        b = HK.suitcase(f"clk{len(BAGS)}", kind, col, PAL, sc.collection); attach(b, r, bone, frame_from(pos, *ax)); BAGS.append(b)
    z = 0.98
    for kind, col in (("large", (0.9, 0.15, 0.4)), ("medium", (0.1, 0.1, 0.12)), ("medium", (0.95, 0.95, 0.95)), ("medium", (0.55, 0.2, 0.7)),
                      ("cabin", (1.0, 0.75, 0.1)), ("cabin", (0.0, 0.7, 0.8)), ("cabin", (0.45, 0.3, 0.2))):
        w, d, h = HK.SUITCASE[kind]                                               # lying flat, height across his back
        bag(kind, col, "spine02", loc((-(h + 0.06) / 2, 0.15 + w / 2, z + d / 2)), (ly, lz, lx)); z += d + 0.01
    for side, sx in (("L", 1), ("R", -1)):
        pb = r.pose.bones[f"wrist.{side}"]; hand = M @ pb.tail
        for j, (kind, col) in enumerate((("cabin", (0.9, 0.35, 0.1)), ("cabin", (0.2, 0.6, 0.3)))):
            h = HK.SUITCASE[kind][2]
            bag(kind, col, f"wrist.{side}", hand + lx * sx * (0.05 + j * 0.2) - lz * (h + 0.1), (ly, -lx, lz))
        bag("duffel", (0.15, 0.15, 0.17) if side == "L" else (0.5, 0.1, 0.1), f"upperarm02.{side}", loc((sx * 0.36, 0.0, 1.05)), (ly, -lx, lz))
    head = M @ r.pose.bones["head"].head
    bag("cabin", (0.85, 0.12, 0.35), "spine01", head - ly * 0.24 - lz * (HK.SUITCASE["cabin"][2] + 0.13), (lx, ly, lz))
    for s in S:
        if s["t0"] >= END_S: break
        for b in BAGS: key_vis(b, frames_of(s)[0], s["props"].get("bags_on") == "CLK")
    # feet on the treads (IK): both feet on the landing, then one tread per step
    s12 = st[0]; f0, f1 = frames_of(s12); o = Vector(ORIGIN["stairs"])
    foot = lambda side, k: o + Vector(((-0.1 if side == "L" else 0.1), (0.3 * k + 0.13) if k >= 0 else -0.08, 0.18 * (k + 1) if k >= 0 else 0.0))
    plants = [(f0, "L", foot("L", -1)), (f0, "R", foot("R", -1) + Vector((0, 0.06, 0)))]
    last = {}
    for t, side, k in s12["stairs_steps"]: plants.append((f0 + round(t * FPS), side, foot(side, k))); last[side] = k
    f_end = frames_of(st[-1])[1]
    A.foot_ik(RIGS["CLK"], f0, f_end, plants)

# ---------------------------------------------------------------- 4. focus: rack between targets, follow moving faces; markers
def focus_point(tgt, f, s):
    o = Vector(ORIGIN[s["set"]])
    if isinstance(tgt, tuple): return Vector(tgt) + o
    if tgt.startswith("obj:"): return bpy.data.objects[tgt[4:]].matrix_world.translation.copy() + Vector((0, 0, 0.05))
    r = RIGS[tgt]; return r.matrix_world @ A._eyes_point(r)
cams, rows = [], []
for s in S:
    if s["t0"] >= END_S: break
    f0, f1 = frames_of(s); rg = s["_rig"]; subj = s["cam"][1]
    if s.get("_aim_follow"):                                                          # operator keeps the eyes framed (0.15 s lag)
        r_, prev_ = RIGS[s["_aim_follow"]], None
        for f in range(f0, f1 + 1):
            sc.frame_set(f); e = r_.matrix_world @ A._eyes_point(r_) - Vector((0, 0, 0.03))
            prev_ = e if prev_ is None else prev_.lerp(e, 0.25); rg.target.location = prev_; rg.target.keyframe_insert("location", frame=f)
    fl = s.get("focus") or ([(0, subj)] if subj in RIGS else [])
    if fl:
        C.dof(rg, s.get("fstop", 2.8))
        for f in range(f0, f1 + 1):
            sc.frame_set(f); t = (f - f0) / FPS
            cur = [x for x in fl if x[0] <= t] or fl[:1]; a = cur[-1]; prev = cur[-2] if len(cur) > 1 else None
            p = focus_point(a[1], f, s)
            if prev is not None and t - a[0] < 0.35:                                 # 0.35 s rack between targets
                u = (t - a[0]) / 0.35; u = u * u * (3 - 2 * u); p = focus_point(prev[1], f, s).lerp(p, u)
            rg.focus.location = p; rg.focus.keyframe_insert("location", frame=f)
    m = sc.timeline_markers.new(rg.cam.name, frame=f0); m.camera = rg.cam
    cams.append((s["id"], f0, f1, rg.cam))
    rows.append(dict(id=s["id"], f0=f0, f1=f1, type=f"{s['cam'][0]} {s['cam'][2]}", subject=subj, purpose=s["note"],
                     **C.describe(rg, f0, f1, subj if rg.cam.data.dof.use_dof else None)))
    notes += [f"shot {s['id']}: {w}" for w in A.eyeline_lint(RIGS, s["_specs"], f0, f1)]
    print("SHOT", s["id"], f0, f1)
with open(os.path.join(HERE, "acting.md"), "w") as fh:
    fh.write("# Acting direction (built from direction.py)\n\n| shot | who | intention | preset | role | look | beats |\n|---|---|---|---|---|---|---|\n")
    for sid, n, sp in acted:
        lk = ", ".join(f"{t:.1f}s {v if isinstance(v, str) else 'point'}" for t, v in sp["look"])
        bt = "; ".join(f"{t:.2f}s {k} {v}" for t, k, v in sorted(sp.get("beats", [])))
        fh.write(f"| {sid} | {n} | {sp['intent']} | {sp['preset']} | {sp['role']} | {lk} | {bt} |\n")
for w in notes: print("EYELINE LINT:", w)

# ---------------------------------------------------------------- 5. face boxes per frame for caption placement
from bpy_extras.object_utils import world_to_camera_view
faces = {}
for sid, f0, f1, cam in cams:
    s = next(x for x in S if x["id"] == sid)
    for f in range(f0, f1 + 1, 2):
        sc.frame_set(f); boxes = []
        for n in s["chars"]:
            r = RIGS[n]; h = r.matrix_world @ r.pose.bones["head"].head
            pts = [world_to_camera_view(sc, cam, h + Vector(d)) for d in ((0, 0, 0.24), (0, 0, -0.14), (0.12, 0, 0.05), (-0.12, 0, 0.05), (0, 0.12, 0.05), (0, -0.12, 0.05))]
            if all(p.z > 0 for p in pts):
                xs, ys = [p.x for p in pts], [1 - p.y for p in pts]
                if max(xs) > 0 and min(xs) < 1 and max(ys) > 0 and min(ys) < 1: boxes.append([round(min(xs), 3), round(min(ys), 3), round(max(xs), 3), round(max(ys), 3)])
        for g in (f, f + 1): faces[str(g)] = boxes
json.dump(faces, open(os.path.join(HERE, "faces.json"), "w"))

# ---------------------------------------------------------------- 6. render only what this cut can see (speed)
used = {s["set"] for s in S if s["t0"] < END_S}
for area, sets in (("floors", {"hall"}), ("suite", {"suite"}), ("petstore", {"petstore"})):
    if not used & sets:
        for ob in bpy.data.collections[f"HOTEL_{area}"].all_objects: ob.hide_render = ob.hide_viewport = True
stair_objs = list(bpy.data.collections["HOTEL_stairs"].all_objects)
for s in S:
    if s["t0"] >= END_S: break
    for ob in stair_objs: key_vis(ob, frames_of(s)[0], s["set"] == "stairs" or s["set"] == "lobby" and abs(ob.matrix_world.translation.z) < 0.01 and "STAIR_floor" not in ob.name)

# ---------------------------------------------------------------- 7. interpolation, shot list
for ob in list(RIGS.values()) + [OBJ["cart"]]:
    is_rig = ob in RIGS.values()
    for fc in C._fcurves(ob):
        for kp in fc.keyframe_points:
            kp.interpolation = ("LINEAR" if fc.data_path == "location" else "BEZIER") if is_rig else "CONSTANT"
sc.camera = min(sc.timeline_markers, key=lambda m: m.frame).camera
SC.shotlist(rows, os.path.join(HERE, "shotlist.md"), FPS)
for w in SC.camera_lint(rows): print("CAMERA LINT:", w)
sc.frame_set(1)
print("SCENE built:", len(cams), "shots,", sc.frame_end, "frames")
