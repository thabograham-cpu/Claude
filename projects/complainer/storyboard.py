"""Storyboard: blockout sets + MPFB cast, one Workbench still per shot from shots.py.
Run: $PY tools/bl.py run projects/complainer/storyboard.py   (from the repo root)
Writes projects/complainer/storyboard/raw/shot_XX.png (3D shots only; cards are made in storyboard_post.sh)."""
import sys, os, math, bpy
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, "..", "..", "tools")]
import json
import cast, camera as C, shotcraft as SC, hotelkit as HK
from shots import S, LINT_OK

OUT = os.path.join(HERE, "storyboard", "raw"); os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene
ORIGIN = HK.ORIGIN  # set-local shot coordinates -> one hotel world (x, y, z); see tools/hotelkit.py
OBJ = {}  # named props


def lin(h):
    return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]


MATS = {}


def mat(hexc, rough=0.5, metal=0.0):
    if hexc in MATS: return MATS[hexc]
    m = bpy.data.materials.new("MAT_" + hexc); m.diffuse_color = (*lin(hexc), 1)
    m.roughness = rough; m.metallic = metal; m.use_fake_user = True  # MPFB purges orphans
    MATS[hexc] = m; return m


def put(o, color, name=None):
    o.data.materials.clear(); o.data.materials.append(mat(color))
    if name: o.name = name
    return o


def box(c, size, color, name=None, set_=None):
    ox, oy, oz = ORIGIN[set_] if set_ else (0, 0, 0)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(c[0] + ox, c[1] + oy, c[2] + oz))
    o = bpy.context.object; o.scale = size; return put(o, color, name)


def cyl(c, r, d, color, name=None, set_=None, rot=(0, 0, 0), v=16):
    ox, oy, oz = ORIGIN[set_] if set_ else (0, 0, 0)
    bpy.ops.mesh.primitive_cylinder_add(vertices=v, radius=r, depth=d, location=(c[0] + ox, c[1] + oy, c[2] + oz), rotation=rot)
    return put(bpy.context.object, color, name)


def ball(c, r, color, scale=(1, 1, 1), name=None, set_=None):
    ox, oy, oz = ORIGIN[set_] if set_ else (0, 0, 0)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=(c[0] + ox, c[1] + oy, c[2] + oz), segments=20, ring_count=10)
    o = bpy.context.object; o.scale = scale; bpy.ops.object.shade_smooth(); return put(o, color, name)


def text(body, c, size, color, rot=(math.pi / 2, 0, 0), name=None, set_=None):
    ox, oy, oz = ORIGIN[set_] if set_ else (0, 0, 0)
    cu = bpy.data.curves.new(name or "txt", "FONT"); cu.body = body; cu.size = size
    cu.align_x = "CENTER"; cu.align_y = "CENTER"; cu.extrude = 0.005
    o = bpy.data.objects.new(name or "TXT_" + body[:8], cu); sc.collection.objects.link(o)
    o.location = (c[0] + ox, c[1] + oy, c[2] + oz); o.rotation_euler = rot
    cu.materials.append(mat(color)); return o


def group(name, objs):
    e = bpy.data.objects.new(name, None); sc.collection.objects.link(e)
    for o in objs: o.parent = e
    OBJ[name] = e; return e


# ============================ sets ============================
# One persistent hotel (tools/hotelkit.py): street, facade, lobby + desk, elevator lobby, stairwell up nine floors,
# corridors on floors 4 and 9, suite 901, the pet store down the street. Shot coordinates stay set-local (ORIGIN).
HOTEL = HK.grand_aurelia()
OBJ["canopy"] = bpy.data.objects["EXT_canopy"]; OBJ["desk"] = HOTEL["obj"]["desk"]; OBJ["elevator"] = HOTEL["obj"]["elevator"]; OBJ["door404"] = HOTEL["obj"]["door404"]
L = "lobby"
# bill on the desk
bill = [box((0.35, 1.7, 1.17), (0.3, 0.4, 0.004), "fbfbf6", "SM_Bill", set_=L)]
bill.append(text("$4,000", (0.35, 1.6, 1.18), 0.08, "222222", rot=(0, 0, 0), name="TXT_bill", set_=L))
bill.append(text("COMPED", (0.35, 1.8, 1.185), 0.07, "d11a1a", rot=(0, 0, 0.3), name="TXT_stamp", set_=L))
group("bill", bill)
group("lawbook", [box((-0.6, 1.75, 1.22), (0.45, 0.32, 0.12), "5a2a12", set_=L), text("LAW", (-0.6, 1.75, 1.29), 0.08, "d4af37", rot=(0, 0, 0), set_=L)])


def suitcase(c, color, s=1.0):
    return box(c, (0.42 * s, 0.25 * s, 0.6 * s), color)


CASE_COLS = ["e91e63", "111111", "f5f5f5", "9c27b0", "ffc107", "00bcd4", "795548", "e91e63", "222222", "ff5722", "8bc34a", "3f51b5", "f5f5f5", "ff9800"]
cart = []                                                     # 14 suitcases on the kit's brass birdcage trolley
for k in range(14):
    col, row = k % 2, k // 2
    cart.append(suitcase(((col - 0.5) * 0.48, 0, 0.45 + row * 0.24), CASE_COLS[k], 0.9)); cart[-1].rotation_euler = (math.pi / 2, 0, 0)
OBJ["cart"] = HK.trolley("cart", HOTEL["palette"], sc.collection)
for o in cart: o.parent = OBJ["cart"]
tag = text("HELD", (0, -0.4, 1.3), 0.25, "d11a1a", name="TXT_tag"); tag.parent = OBJ["cart"]
oc = [box((0, 0, 0.12), (1.0, 0.7, 0.24), "e91e63"), box((0, 0.45, 0.45), (1.0, 0.06, 0.7), "e91e63")]
robes = [ball((x * 0.22 - 0.33, y * 0.2 - 0.15, 0.3), 0.16, "ffffff", (1.2, 1, 0.6)) for x in range(4) for y in range(3)]
group("robes", robes); oc.append(OBJ["robes"])
group("open_case", oc)
rbox = [box((0, 0, 0.06), (0.16, 0.12, 0.12), "b08a5a")]
group("roach_box", rbox)
OBJ["small_box"] = box((0, 0, 0), (0.1, 0.08, 0.08), "b08a5a", "SM_SmallBox")
OBJ["phone"] = box((0, 0, 0), (0.075, 0.01, 0.15), "111111", "SM_Phone")

# STAIRWELL: built by the hotel kit (switchback flights, floor signs 1..9)
# SUITE (props only; room, window and night view come from the kit)
U = "suite"
box((0.4, 1.6, 0.3), (2.0, 2.2, 0.6), "ffffff", set_=U); box((0.4, 2.75, 0.8), (2.1, 0.12, 1.6), "5a3b2a", set_=U)
box((-1.7, 2.3, 0.3), (0.5, 0.5, 0.6), "5a3b2a", set_=U)
group("clock", [box((-1.7, 2.3, 0.7), (0.3, 0.12, 0.18), "111111", set_=U), text("2:00 AM", (-1.7, 2.23, 0.7), 0.06, "ff2a2a", set_=U)])
box((-1.8, -0.6, 0.45), (1.0, 0.6, 0.9), "f5f0e6", "SM_RoomServiceCart", set_=U)
lob = [ball((-1.9, -0.6, 0.97), 0.13, "d32f2f", (1.8, 0.8, 0.5), set_=U), ball((-1.62, -0.72, 0.98), 0.06, "d32f2f", (1.6, 1, 0.8), set_=U),
       ball((-1.62, -0.48, 0.98), 0.06, "d32f2f", (1.6, 1, 0.8), set_=U), cyl((-1.9, -0.6, 0.91), 0.25, 0.02, "ffffff", set_=U)]
group("lobster", lob)
group("champagne", [cyl((-1.5, -0.45, 1.0), 0.1, 0.22, "c0c0c0", set_=U), cyl((-1.5, -0.45, 1.13), 0.035, 0.36, "0d3b1e", set_=U)])
# PET STORE (storefront faces -Y)
P = "petstore"
group("tank", [box((-1.5, 3.2, 0.45), (0.8, 0.5, 0.9), "5d4037", set_=P), box((-1.5, 3.2, 1.15), (0.7, 0.4, 0.5), "bfe3ef", set_=P),
               text("$24.99", (-1.5, 2.94, 0.75), 0.09, "ffffff", set_=P)])   # inside the shop, seen through its window
# HALL: floor-4 corridor and ROOM 404 come from the kit (OBJ['door404'])

# roach (reparented per shot)
rp = [ball((0, 0, 0.02), 0.028, "4e2a10", (1.9, 1, 0.55))]
for s in (-1, 1):
    for k in (-1, 0, 1):
        rp.append(cyl((s * 0.035, k * 0.022, 0.01), 0.003, 0.06, "2b1608", rot=(0, math.pi / 2, 0), v=4))
group("roach", rp)

# ============================ cast ============================
import castlist
CAST, SKIN = castlist.CAST, castlist.SKIN
RIGS = castlist.build()
REST = {n: {pb.name: pb.matrix.copy() for pb in r.pose.bones} for n, r in RIGS.items()}


def aim(rig, bone, d):
    bpy.context.view_layer.update()
    pb = rig.pose.bones[bone]; cur = (pb.tail - pb.head).normalized()
    q = cur.rotation_difference(Vector(d).normalized()); h = pb.matrix.translation.copy()
    pb.matrix = Matrix.Translation(h) @ q.to_matrix().to_4x4() @ Matrix.Translation(-h) @ pb.matrix
    bpy.context.view_layer.update()


def arms(ul, ll, ur, lr):
    return {"upperarm01.L": ul, "lowerarm01.L": ll, "upperarm01.R": ur, "lowerarm01.R": lr}


DOWN = arms((0.15, 0.02, -1), (0.1, -0.1, -1), (-0.15, 0.02, -1), (-0.1, -0.1, -1))
WALK = {"upperleg01.L": (0.03, -0.35, -1), "upperleg01.R": (-0.03, 0.3, -1), "lowerleg01.R": (0, 0.45, -1)}
SELF = {"upperarm01.R": (-0.35, -0.75, 0.15), "lowerarm01.R": (0.25, -0.6, 0.55)}
FILM = arms((0.25, -0.9, -0.25), (-0.3, -0.85, 0.45), (-0.25, -0.9, -0.25), (0.3, -0.85, 0.45))
POSES = {
    "stand": {}, "selfie": SELF, "selfie_walk": {**SELF, **WALK},
    "selfie_yell": {**SELF, "upperarm01.L": (0.8, -0.4, 0.3), "lowerarm01.L": (0.8, -0.2, 0.5), "head": (0, 0.2, 1)},
    "film": FILM, "film_walk": {**FILM, **WALK},
    "point_fwd": {"upperarm01.R": (-0.15, -1, 0.15), "lowerarm01.R": (-0.15, -1, 0.15)},
    "point_up": {"upperarm01.R": (-0.15, -0.2, 1), "lowerarm01.R": (-0.05, -0.1, 1)},
    "snap": {"upperarm01.R": (-0.3, -0.7, -0.4), "lowerarm01.R": (0.2, -0.7, 0.4)},
    "show_box": {"upperarm01.R": (-0.2, -0.6, -0.6), "lowerarm01.R": (0.1, -0.9, 0.2)},
    "carry_climb": {**arms((0.45, 0, -1), (0.3, 0, -1), (-0.45, 0, -1), (-0.3, 0, -1)), "upperleg01.L": (0.05, -0.6, -0.8), "lowerleg01.L": (0, 0.1, -1), "spine03": (0, -0.25, 1)},
    "lie_bed": {}, "phone_ear": {"upperarm01.R": (-0.5, -0.3, -0.4), "lowerarm01.R": (0.3, 0.1, 1)},
    "phone_look": {**arms((0.15, -0.3, -1), (-0.3, -0.9, 0.3), (-0.15, -0.3, -1), (0.3, -0.9, 0.3)), "head": (0, -0.5, 1)},
    "shocked": {**arms((0.5, -0.5, -0.2), (-0.45, -0.3, 0.85), (-0.5, -0.5, -0.2), (0.45, -0.3, 0.85)), "head": (0, 0.25, 1)},
    "hands_head": arms((0.7, -0.2, 0.6), (-0.6, 0.1, 0.6), (-0.7, -0.2, 0.6), (0.6, 0.1, 0.6)),
    "lean_desk": {"spine03": (0, -0.35, 1), **arms((0.2, -0.6, -0.8), (0, -0.5, -0.85), (-0.2, -0.6, -0.8), (0, -0.5, -0.85))},
    "flick": {"upperarm01.R": (-0.6, -0.4, -0.3), "lowerarm01.R": (-0.8, -0.2, 0.4)},
    "slide_bill": {"spine03": (0, -0.2, 1), "upperarm01.R": (-0.1, -0.7, -0.7), "lowerarm01.R": (0, -1, -0.1)},
    "laugh": {"head": (0, 0.55, 1), "spine03": (0, 0.15, 1), **arms((0.2, -0.2, -1), (-0.5, -0.6, 0.3), (-0.2, -0.2, -1), (0.5, -0.6, 0.3))},
    "push": {"spine03": (0, -0.25, 1), **arms((0.2, -1, -0.2), (0.1, -1, 0), (-0.2, -1, -0.2), (-0.1, -1, 0)), **WALK},
    "kneel": {"upperleg01.L": (0.05, -0.3, -1), "upperleg01.R": (-0.05, -0.3, -1), "lowerleg01.L": (0, 1, -0.15), "lowerleg01.R": (0, 1, -0.15),
              "spine03": (0, -0.4, 1), **arms((0.2, -0.7, -0.7), (0.1, -0.6, -0.8), (-0.2, -0.7, -0.7), (-0.1, -0.6, -0.8))},
    "pay": {"spine03": (0, -0.2, 1), "upperarm01.R": (-0.1, -0.7, -0.7), "lowerarm01.R": (0, -1, -0.1), "head": (0, -0.4, 1)},
    "phone_speaker": {"upperarm01.R": (-0.2, -0.5, -0.8), "lowerarm01.R": (0.2, -0.95, 0.2)},
}
ORDER = ["spine03", "head", "upperleg01.L", "upperleg01.R", "lowerleg01.L", "lowerleg01.R",
         "upperarm01.L", "upperarm01.R", "lowerarm01.L", "lowerarm01.R"]


def pose(name, rig, p):
    for pb in rig.pose.bones: pb.matrix_basis = Matrix()
    spec = {**DOWN, **POSES[p]}
    for b in ORDER:
        if b in spec:
            d = Vector(spec[b])
            aim(rig, b, d)


def hand(rig, side="R"):
    bpy.context.view_layer.update()
    pb = rig.pose.bones[f"wrist.{side}"]; return rig.matrix_world @ pb.tail


def head(rig):
    bpy.context.view_layer.update(); return rig.matrix_world @ rig.pose.bones["head"].head


LENS = {"wide": 20, "med": 30, "cu": 40, "ecu": 50, "insert": 40}
ANGLE = {"34": 35, "side": 90, "back": 180}


def names_of(ob):
    return {ob.name} | {c.name for c in ob.children_recursive}


def shot_camera(s, f0, f1):
    """shotcraft placement + camera.py rig/move for one shot; pose the scene for frame f0 first."""
    framing, subj, angle = s["cam"]; lens = LENS[framing]; hd = None
    if subj in RIGS:
        r = RIGS[subj]; hd = head(r); ignore = names_of(r)
        lying = s["chars"][subj][3] == "lie_bed"
        front = Vector((0, -1, 0)) if lying else (Matrix.Rotation(r.rotation_euler.z, 3, "Z") @ Vector((0, -1, 0)))
        subject_pt = Vector((hd.x, hd.y, 1.1)) if framing == "wide" else hd
        dist = SC.distance_for(framing, lens)
    else:
        ob = OBJ[subj]; ignore = names_of(ob)
        holder = s["props"].get(subj)  # a held prop: its holder's arm is not an obstacle
        if isinstance(holder, str) and holder in RIGS: ignore |= names_of(RIGS[holder])
        kids = [c for c in ob.children if c.type in ("MESH", "FONT")] if ob.type == "EMPTY" else [ob]
        pts = [c.matrix_world @ Vector(v) for c in kids for v in c.bound_box]
        subject_pt = sum(pts, Vector()) / len(pts); front = Vector((0, -1, 0))
        ext = max((max(p[i] for p in pts) - min(p[i] for p in pts)) for i in range(3))
        txt = [c for c in kids if c.type == "FONT"]
        if txt and framing in ("cu", "insert"): subject_pt = txt[0].matrix_world.translation.copy()
        if subj == "desk": subject_pt.z = 1.15
        if subj == "elevator": front = Vector((-1, 0, 0)); subject_pt.z = 1.4
        dist = SC.distance_for(framing, lens) if framing == "wide" else SC.distance_for(None, lens, height=max(0.35, ext * 1.6))
    height = {"low": -0.45, "high": 0.9}.get(angle, 0.05) * (dist if framing != "wide" else 0.5)
    if s.get("cam_at"):  # explicit placement (set-local camera point, aim point): establishing shots of buildings, specific views
        o3 = ORIGIN[s["set"]]; (cp, ap) = s["cam_at"]
        pos = Vector(cp) + Vector(o3); aim_pt = Vector(ap) + Vector(o3); info = {"clear": 1.0, "swung": 0}
        rg = C.rig(f"S{s['id']:02d}", pos, aim_pt, lens); sc.camera = rg.cam
        if s.get("move"): C.apply(rg, s["move"], f0, f1, {n: (RIGS[n], "head") for n in RIGS})
        return rg, pos, aim_pt, hd, info
    if angle.startswith("pov:"):  # a character's point of view: camera at <rig>:<bone> (eyes "head", phone "wrist.R"), aimed at the subject
        _, holder, bone = angle.split(":"); hr = RIGS[holder]; pb = hr.pose.bones[bone]
        src = hr.matrix_world @ (pb.tail if bone.startswith("wrist") else pb.head)
        tgt = hd if hd is not None else subject_pt
        pos = src + (tgt - src).normalized() * (0.1 if bone.startswith("wrist") else 0.18); info = {"clear": 1.0, "swung": 0}
        lens = 24 if bone.startswith("wrist") else lens   # a phone camera is wide
        aim_pt = tgt
        rg = C.rig(f"S{s['id']:02d}", pos, aim_pt, lens); sc.camera = rg.cam
        if s.get("move"): C.apply(rg, s["move"], f0, f1, {n: (RIGS[n], "head") for n in RIGS})
        return rg, pos, aim_pt, hd, info
    if angle == "top":
        pos = subject_pt + Vector((0, -0.05, dist + 0.6)); info = {"clear": 1.0, "swung": 0}
    elif angle == "ots":  # over the clerk's shoulder toward the other character
        rc = RIGS["CLK"]; back = Matrix.Rotation(rc.rotation_euler.z, 3, "Z") @ Vector((0, 1, 0))
        pos = head(rc) + back * 0.9 + Vector((0.35, 0, 0.2)); info = {"clear": 1.0, "swung": 0}
        other = RIGS["INF"] if subj == "CLK" else RIGS[subj]; hd = head(other)
        subject_pt = hd - Vector((0, 0, 0.4 if framing == "wide" else 0.1))
    else:
        pos, info = SC.place(subject_pt, front, dist, ANGLE.get(angle, 0), height, ignore=ignore)
    pos.z = max(pos.z, ORIGIN[s["set"]][2] + 0.35)
    pos = HK.keep_inside(pos, subject_pt)  # never inside a wall or outside the building's rooms
    aim_pt = SC.aim_point(hd, framing, pos, lens) if (hd is not None and framing in SC.EYE_LINE and angle != "ots") else subject_pt
    rg = C.rig(f"S{s['id']:02d}", pos, aim_pt, lens); sc.camera = rg.cam
    if s.get("move"):
        C.apply(rg, s["move"], f0, f1, {n: (RIGS[n], "head") for n in RIGS})
    return rg, pos, aim_pt, hd, info


# ============================ render setup ============================
def render_storyboard():
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.render.resolution_x, sc.render.resolution_y = 360, 640
    sh = sc.display.shading
    sh.light = "STUDIO"; sh.color_type = "MATERIAL"; sh.show_shadows = True; sh.show_cavity = True
    sh.cavity_type = "BOTH"; sh.background_type = "WORLD"
    w = bpy.data.worlds.new("W"); sc.world = w
    sh.use_dof = True  # Workbench shows camera depth of field
    SKY = {"lobby": "3a2a20", "stairs": "202020", "suite": "0b1022", "petstore": "8ab4d8", "hall": "1b1b1b"}
    WORDS = json.load(open(os.path.join(HERE, "audio", "words.json")))
    FPS = 24


    def place_prop(name, where, o):
        OBJ[name].location = (where[0] + o[0], where[1] + o[1], o[2])


    records, seen_sets = [], set()
    for s in S:
        if s["card"] and not s["set"]:
            continue
        set_ = s["set"]; o = ORIGIN[set_]
        w.color = lin(SKY[set_])
        # reset movable props
        for n in ("cart", "open_case", "small_box", "phone", "roach_box", "roach"):
            OBJ[n].location = (0, -200, 0); OBJ[n].parent = None
        OBJ["cart"].location = (-2.2 + o[0], 3.6 + o[1], o[2]) if set_ == "lobby" else (0, -200, 0)
        OBJ["robes"].hide_render = not s["props"].get("robes")
        bpy.data.objects["TXT_tag"].data.body = s["props"].get("tag", "")
        bpy.data.objects["TXT_stamp"].hide_render = "stamp" not in s["props"]
        for k in ("cart", "open_case"):
            if k in s["props"]: place_prop(k, o, s["props"][k])
        for n, r in RIGS.items():
            r.location = (0, -100, 0); r.rotation_euler = (0, 0, 0)
        for n, (x, y, face, p) in s["chars"].items():
            r = RIGS[n]; pose(n, r, p)
            r.location = (o[0] + x, o[1] + y, o[2]); r.rotation_euler = (0, 0, math.radians(face))
            if p == "lie_bed":
                r.rotation_euler = (math.radians(-90), 0, math.radians(face)); r.location.z = o[2] + 0.62; r.location.y = o[1] + 2.4
            if p == "kneel": r.location.z = o[2] - 0.38
            if set_ == "stairs": r.location.z = o[2] + max(0.0, y) * 0.6 + 0.18  # stand on the step under them
        bpy.context.view_layer.update()
        # hand props
        for n, (_, _, _, p) in s["chars"].items():
            if p.startswith(("selfie", "film", "phone")):
                OBJ["phone"].location = hand(RIGS[n])
        if s["props"].get("small_box"): OBJ["small_box"].location = hand(RIGS[s["props"]["small_box"]])
        bo = s["props"].get("bags_on")
        bags = []
        if bo:
            r = RIGS[bo]; base = Vector(r.location); fwd = Vector((0, -1, 0)); fwd.rotate(r.rotation_euler)
            side = fwd.cross(Vector((0, 0, 1)))
            for k, (sx, z) in enumerate(((0.48, 0.55), (-0.48, 0.55), (0.0, 1.05), (0.0, 1.45), (0.0, 1.85))):
                p = base + side * sx - fwd * (0.32 if sx == 0 else 0) + Vector((0, 0, z))
                bags.append(box(p, (0.45, 0.25, 0.4), CASE_COLS[k], f"TMP_bag{k}"))
                bags[-1].rotation_euler = r.rotation_euler
        roach_on = s["props"].get("roach_on")
        if roach_on == "lobster": OBJ["roach"].location = (o[0] - 1.85, o[1] - 0.6, o[2] + 1.03)
        if roach_on == "desk":
            OBJ["roach_box"].location = (o[0] - 0.3, o[1] + 1.75, o[2] + 1.16); OBJ["roach"].location = (o[0] - 0.3, o[1] + 1.75, o[2] + 1.3)
        if roach_on == "hall": OBJ["roach"].location = (o[0], o[1] + 3.2, o[2])
        bpy.context.view_layer.update()

        n_frames = max(2, round((s["t1"] - s["t0"]) * FPS))
        rg, pos, aim_pt, hd, info = shot_camera(s, 1, n_frames)
        sc.frame_set(1)
        sc.render.filepath = os.path.join(OUT, f"shot_{s['id']:02d}.png"); bpy.ops.render.render(write_still=True)
        if s.get("move"):
            sc.frame_set(n_frames)
            sc.render.filepath = os.path.join(OUT, f"shot_{s['id']:02d}_end.png"); bpy.ops.render.render(write_still=True)
            sc.frame_set(1)
        eye = SC.on_screen(rg.cam, hd)[1] if hd is not None else True
        text = " ".join(x["w"] for x in WORDS if s["t0"] <= (x["s"] + x["e"]) / 2 < s["t1"]) + " " + s["note"]  # words spoken IN the shot
        records.append(dict(id=s["id"], set=set_, t0=s["t0"], t1=s["t1"], size=framing, subject=subj, cam=pos.copy(), aim=aim_pt.copy(),
                            chars={n: Vector(RIGS[n].location) for n in s["chars"]}, text=text, first_in_scene=set_ not in seen_sets,
                            clear=info["clear"], swung=info["swung"], eye_visible=eye))
        seen_sets.add(set_)
        for ob_ in (rg.cam, rg.target, rg.focus): bpy.data.objects.remove(ob_)
        for b in bags: bpy.data.objects.remove(b)
        print("SHOT", s["id"], "done", info)

    # ---- review report
    notes = SC.lint(records)
    notes += [f"shot {r['id']}: camera swung {r['swung']:+.0f} deg to see past an obstacle" for r in records if r["swung"]]
    notes += [f"shot {r['id']}: subject's head is out of frame" for r in records if not r["eye_visible"]]
    is_ok = lambda n: any(n.startswith(f"shot {k}:") for k in LINT_OK)
    report = [n for n in notes if not is_ok(n)] + [f"accepted: shot {k}: {why}" for k, why in LINT_OK.items()]
    open(os.path.join(HERE, "storyboard", "lint.txt"), "w").write("\n".join(report) + "\n")
    print("LINT", len(notes), "notes")


if __name__ == "__main__":
    render_storyboard()
