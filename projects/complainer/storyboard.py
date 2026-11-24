"""Storyboard: blockout sets + MPFB cast, one Workbench still per shot from shots.py.
Run: $PY tools/bl.py run projects/complainer/storyboard.py   (from the repo root)
Writes projects/complainer/storyboard/raw/shot_XX.png (3D shots only; cards are made in storyboard_post.sh)."""
import sys, os, math, bpy
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, "..", "..", "tools")]
import json
import cast, camera as C, shotcraft as SC
from shots import S

OUT = os.path.join(HERE, "storyboard", "raw"); os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene
ORIGIN = {"lobby": (0, 0), "stairs": (40, 0), "suite": (80, 0), "petstore": (120, 0), "hall": (160, 0)}
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
    ox, oy = ORIGIN[set_] if set_ else (0, 0)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(c[0] + ox, c[1] + oy, c[2]))
    o = bpy.context.object; o.scale = size; return put(o, color, name)


def cyl(c, r, d, color, name=None, set_=None, rot=(0, 0, 0), v=16):
    ox, oy = ORIGIN[set_] if set_ else (0, 0)
    bpy.ops.mesh.primitive_cylinder_add(vertices=v, radius=r, depth=d, location=(c[0] + ox, c[1] + oy, c[2]), rotation=rot)
    return put(bpy.context.object, color, name)


def ball(c, r, color, scale=(1, 1, 1), name=None, set_=None):
    ox, oy = ORIGIN[set_] if set_ else (0, 0)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=(c[0] + ox, c[1] + oy, c[2]), segments=20, ring_count=10)
    o = bpy.context.object; o.scale = scale; bpy.ops.object.shade_smooth(); return put(o, color, name)


def text(body, c, size, color, rot=(math.pi / 2, 0, 0), name=None, set_=None):
    ox, oy = ORIGIN[set_] if set_ else (0, 0)
    cu = bpy.data.curves.new(name or "txt", "FONT"); cu.body = body; cu.size = size
    cu.align_x = "CENTER"; cu.align_y = "CENTER"; cu.extrude = 0.005
    o = bpy.data.objects.new(name or "TXT_" + body[:8], cu); sc.collection.objects.link(o)
    o.location = (c[0] + ox, c[1] + oy, c[2]); o.rotation_euler = rot
    cu.materials.append(mat(color)); return o


def group(name, objs):
    e = bpy.data.objects.new(name, None); sc.collection.objects.link(e)
    for o in objs: o.parent = e
    OBJ[name] = e; return e


# ============================ sets ============================
# LOBBY (camera side is -Y; desk at y=2 facing -Y; elevators on the +X wall)
L = "lobby"
for i in range(-7, 7):
    for j in range(-7, 5):
        box((i + 0.5, j + 0.5, -0.05), (1, 1, 0.1), "e8e2d6" if (i + j) % 2 else "c9bfae", set_=L)
box((0, 5, 2.5), (14, 0.2, 5), "6b2232", set_=L)              # back wall (burgundy)
box((-7, 0, 2.5), (0.2, 14, 5), "e9e3d7", set_=L)
box((7, 0, 2.5), (0.2, 14, 5), "e9e3d7", set_=L)
text("THE GRAND AURELIA", (0, 4.85, 3.4), 0.42, "d4af37", set_=L)
box((0, 2.0, 0.55), (4.4, 0.8, 1.1), "3b2418", "SM_Desk", set_=L); OBJ["desk"] = bpy.data.objects["SM_Desk"]
box((0, 1.95, 1.13), (4.6, 0.95, 0.06), "f0ece4", set_=L)     # marble desktop
box((1.2, 2.25, 1.35), (0.5, 0.05, 0.35), "111111", set_=L)   # monitor
ball((-1.0, 1.75, 1.2), 0.06, "d4af37", set_=L)                # bell
for x in (-4.5, 4.5):
    cyl((x, -1.5, 2.5), 0.35, 5, "f2eee6", set_=L)
ball((0, -1, 4.2), 0.6, "fff3c4", (1, 1, 0.6), set_=L)        # chandelier
box((0, -6.9, 1.6), (3.0, 0.15, 3.2), "9fc4d6", set_=L)       # glass entrance
for k, y in enumerate((0.4, 2.2)):                             # elevators on +X wall, facing -X
    box((6.85, y, 1.2), (0.1, 1.3, 2.4), "c9a227", f"SM_Elevator_{k}", set_=L)
text("VIP ONLY", (6.8, 1.3, 2.75), 0.32, "d4af37", rot=(math.pi / 2, 0, math.pi / 2), set_=L)
OBJ["elevator"] = bpy.data.objects["SM_Elevator_0"]
box((-6.85, 1.0, 1.05), (0.1, 1.0, 2.1), "7a6a58", set_=L)
text("STAIRS", (-6.8, 1.0, 2.35), 0.2, "ffffff", rot=(math.pi / 2, 0, -math.pi / 2), set_=L)
# bill on the desk
bill = [box((0.35, 1.7, 1.17), (0.3, 0.4, 0.004), "fbfbf6", "SM_Bill", set_=L)]
bill.append(text("$4,000", (0.35, 1.6, 1.18), 0.08, "222222", rot=(0, 0, 0), name="TXT_bill", set_=L))
bill.append(text("COMPED", (0.35, 1.8, 1.185), 0.07, "d11a1a", rot=(0, 0, 0.3), name="TXT_stamp", set_=L))
group("bill", bill)
group("lawbook", [box((-0.6, 1.75, 1.22), (0.45, 0.32, 0.12), "5a2a12", set_=L), text("LAW", (-0.6, 1.75, 1.29), 0.08, "d4af37", rot=(0, 0, 0), set_=L)])


def suitcase(c, color, s=1.0):
    return box(c, (0.42 * s, 0.25 * s, 0.6 * s), color)


CASE_COLS = ["e91e63", "111111", "f5f5f5", "9c27b0", "ffc107", "00bcd4", "795548", "e91e63", "222222", "ff5722", "8bc34a", "3f51b5", "f5f5f5", "ff9800"]
cart = [box((0, 0, 0.12), (1.2, 0.6, 0.06), "c9a227"), cyl((-0.55, 0, 1.1), 0.025, 2.0, "c9a227"), cyl((0.55, 0, 1.1), 0.025, 2.0, "c9a227"),
        cyl((0, 0, 2.1), 0.025, 1.12, "c9a227", rot=(0, math.pi / 2, 0))]
for k in range(14):
    col, row = k % 2, k // 2
    cart.append(suitcase(((col - 0.5) * 0.48, 0, 0.45 + row * 0.27), CASE_COLS[k], 0.95)); cart[-1].rotation_euler = (math.pi / 2, 0, 0)
group("cart", cart)
tag = text("HELD", (0, -0.4, 1.3), 0.25, "d11a1a", name="TXT_tag"); tag.parent = OBJ["cart"]
oc = [box((0, 0, 0.12), (1.0, 0.7, 0.24), "e91e63"), box((0, 0.45, 0.45), (1.0, 0.06, 0.7), "e91e63")]
robes = [ball((x * 0.22 - 0.33, y * 0.2 - 0.15, 0.3), 0.16, "ffffff", (1.2, 1, 0.6)) for x in range(4) for y in range(3)]
group("robes", robes); oc.append(OBJ["robes"])
group("open_case", oc)
rbox = [box((0, 0, 0.06), (0.16, 0.12, 0.12), "b08a5a")]
group("roach_box", rbox)
OBJ["small_box"] = box((0, 0, 0), (0.1, 0.08, 0.08), "b08a5a", "SM_SmallBox")
OBJ["phone"] = box((0, 0, 0), (0.075, 0.01, 0.15), "111111", "SM_Phone")

# STAIRWELL (climbs toward +Y)
T = "stairs"
for k in range(16):
    box((0, k * 0.3, (k + 1) * 0.09), (1.6, 0.3, (k + 1) * 0.18), "8c8c8c", set_=T)
box((0.85, 2.4, 2.5), (0.1, 8, 6), "d9d4c7", set_=T); box((-0.85, 2.4, 2.5), (0.1, 8, 6), "d9d4c7", set_=T)
cyl((0.7, 2.4, 2.4), 0.03, 6.0, "c9a227", set_=T, rot=(math.radians(-59), 0, 0))
text("9", (-0.79, 3.2, 3.6), 0.9, "c0392b", rot=(math.pi / 2, 0, -math.pi / 2), set_=T)
# SUITE
U = "suite"
box((0, 0, -0.05), (8, 8, 0.1), "6d5a4a", set_=U); box((0, 3, 1.6), (8, 0.2, 3.2), "e7dfcf", set_=U)
box((0, 2.95, 1.6), (3.0, 0.05, 1.8), "0b1530", set_=U)       # night window
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
box((0, 0, -0.05), (10, 6, 0.1), "9e9e9e", set_=P); box((0, 1.5, 2.0), (8, 0.3, 4), "2e7d32", set_=P)
text("PET PALACE", (0, 1.33, 3.3), 0.45, "fff176", set_=P); box((1.8, 1.34, 1.3), (2.6, 0.05, 1.6), "a8d8e8", set_=P)
group("tank", [box((-1.5, 0.6, 0.45), (0.8, 0.5, 0.9), "5d4037", set_=P), box((-1.5, 0.6, 1.15), (0.7, 0.4, 0.5), "bfe3ef", set_=P),
               text("$24.99", (-1.5, 0.38, 0.75), 0.09, "ffffff", set_=P)])
# HALL
H = "hall"
box((0, 0, -0.05), (3, 10, 0.1), "7b1f2a", set_=H); box((-1.5, 0, 1.4), (0.1, 10, 2.8), "e7dfcf", set_=H); box((1.5, 0, 1.4), (0.1, 10, 2.8), "e7dfcf", set_=H)
box((0, 4, 1.4), (3, 0.1, 2.8), "e7dfcf", set_=H)
group("door404", [box((0, 3.92, 1.05), (1.0, 0.06, 2.1), "5a3b2a", set_=H), text("404", (0, 3.87, 1.6), 0.16, "d4af37", set_=H)])

# roach (reparented per shot)
rp = [ball((0, 0, 0.02), 0.028, "4e2a10", (1.9, 1, 0.55))]
for s in (-1, 1):
    for k in (-1, 0, 1):
        rp.append(cyl((s * 0.035, k * 0.022, 0.01), 0.003, 0.06, "2b1608", rot=(0, math.pi / 2, 0), v=4))
group("roach", rp)

# ============================ cast ============================
CAST = {
    "INF": dict(gender=1, age=0.4, height=0.6, weight=0.45, skin="young_caucasian_male2", hair="cortu_short_messy_hair",
                clothes=["elvs_hooded_sweat_jacket1", "punkduck_male_classic_jeans", "culturalibre_sneakers"],
                colors={"hooded": "ff4fa3", "jeans": "1b1b1b", "sneakers": "f5f5f5"}),
    "CLK": dict(gender=1, age=0.38, height=0.55, weight=0.42, skin="young_asian_male", hair="short02",
                clothes=["elvs_male_shirt_tie_tucked1", "mindfront_male_trousers_1", "mindfront_shoes_oxford_male"],
                colors={"shirt": "f2f2f2", "trousers": "232323", "oxford": "111111"}),
    "F1": dict(gender=1, age=0.35, height=0.6, weight=0.5, skin="young_african_male", hair="short04",
               clothes=["elvs_male_logo_tshirt1", "cortu_cargo_pants", "punkduck_tennis_shoes"],
               colors={"tshirt": "1aa6a6", "cargo": "6b6b4a", "tennis": "ffffff"}),
    "F2": dict(gender=0, age=0.35, height=0.48, weight=0.42, skin="young_caucasian_female", hair="ponytail01",
               clothes=["punkduck_v_neck_top", "punkduck_female_tight_jeans", "punkduck_tennis_shoes"],
               colors={"v_neck": "ffd54f", "jeans": "6d8fc7", "tennis": "ffffff"}),
    "MGR": dict(gender=1, age=0.72, height=0.5, weight=0.62, skin="middleage_caucasian_male", hair="short01",
                clothes=["elvs_male_shirt_untucked_bd1", "elvs_male_trouser", "mindfront_shoes_oxford_male"],
                colors={"shirt": "b3cde0", "trouser": "55585e", "oxford": "111111"}),
}
SKIN = {"INF": "e8b89a", "CLK": "d9a77e", "F1": "6b4330", "F2": "f0c7aa", "MGR": "e3b294"}
RIGS = {}
for name, c in CAST.items():
    colors = c.pop("colors")
    body, rig = cast.human(name, **c)
    for o in rig.children_recursive:
        if o.type != "MESH": continue
        nm = o.name.lower()
        col = next((v for k, v in colors.items() if k in nm), None)
        if col is None:
            col = SKIN[name] if ("body" in nm or "teeth" in nm or "tongue" in nm) else ("222222" if ("eye" in nm or "hair" in nm or "short" in nm or "ponytail" in nm or "messy" in nm) else "ffffff")
            if "high-poly" in nm: col = "f5f5f5"
        for sl in o.material_slots:
            if sl.material: sl.material.diffuse_color = (*lin(col), 1)
    rig.location = (0, -100, 0)
    RIGS[name] = rig
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


# ============================ render setup ============================
sc.render.engine = "BLENDER_WORKBENCH"
sc.render.resolution_x, sc.render.resolution_y = 360, 640
sh = sc.display.shading
sh.light = "STUDIO"; sh.color_type = "MATERIAL"; sh.show_shadows = True; sh.show_cavity = True
sh.cavity_type = "BOTH"; sh.background_type = "WORLD"
w = bpy.data.worlds.new("W"); sc.world = w
sh.use_dof = True  # Workbench shows camera depth of field
LENS = {"wide": 20, "med": 30, "cu": 40, "ecu": 50, "insert": 40}
ANGLE = {"34": 35, "side": 90, "back": 180}
SKY = {"lobby": "3a2a20", "stairs": "202020", "suite": "0b1022", "petstore": "8ab4d8", "hall": "1b1b1b"}
WORDS = json.load(open(os.path.join(HERE, "audio", "words.json")))
FPS = 24


def place_prop(name, where, o):
    OBJ[name].location = (where[0] + o[0], where[1] + o[1], 0)


def names_of(ob):
    return {ob.name} | {c.name for c in ob.children_recursive}


records, seen_sets = [], set()
for s in S:
    if s["card"] and not s["set"]:
        continue
    set_ = s["set"]; o = ORIGIN[set_]
    w.color = lin(SKY[set_])
    # reset movable props
    for n in ("cart", "open_case", "small_box", "phone", "roach_box", "roach"):
        OBJ[n].location = (0, -200, 0); OBJ[n].parent = None
    OBJ["cart"].location = (-2.2 + o[0], 3.6 + o[1], 0) if set_ == "lobby" else (0, -200, 0)
    OBJ["robes"].hide_render = not s["props"].get("robes")
    bpy.data.objects["TXT_tag"].data.body = s["props"].get("tag", "")
    bpy.data.objects["TXT_stamp"].hide_render = "stamp" not in s["props"]
    for k in ("cart", "open_case"):
        if k in s["props"]: place_prop(k, o, s["props"][k])
    for n, r in RIGS.items():
        r.location = (0, -100, 0); r.rotation_euler = (0, 0, 0)
    for n, (x, y, face, p) in s["chars"].items():
        r = RIGS[n]; pose(n, r, p)
        r.location = (o[0] + x, o[1] + y, 0); r.rotation_euler = (0, 0, math.radians(face))
        if p == "lie_bed":
            r.rotation_euler = (math.radians(-90), 0, math.radians(face)); r.location.z = 0.62; r.location.y = o[1] + 2.4
        if p == "kneel": r.location.z = -0.38
        if set_ == "stairs": r.location.z = max(0.0, y) * 0.6  # stand on the step under them
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
    if roach_on == "lobster": OBJ["roach"].location = (o[0] - 1.85, o[1] - 0.6, 1.03)
    if roach_on == "desk":
        OBJ["roach_box"].location = (o[0] - 0.3, o[1] + 1.75, 1.16); OBJ["roach"].location = (o[0] - 0.3, o[1] + 1.75, 1.3)
    if roach_on == "hall": OBJ["roach"].location = (o[0], o[1] + 3.2, 0.0)
    bpy.context.view_layer.update()

    # ---- camera: shotcraft placement + camera.py rig/move
    framing, subj, angle = s["cam"]; lens = LENS[framing]; hd = None
    if subj in RIGS:
        r = RIGS[subj]; hd = head(r); ignore = names_of(r)
        lying = s["chars"][subj][3] == "lie_bed"
        front = Vector((0, -1, 0)) if lying else (Matrix.Rotation(r.rotation_euler.z, 3, "Z") @ Vector((0, -1, 0)))
        subject_pt = Vector((hd.x, hd.y, 1.1)) if framing == "wide" else hd
        dist = SC.distance_for(framing, lens)
    else:
        ob = OBJ[subj]; ignore = names_of(ob)
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
    if angle == "top":
        pos = subject_pt + Vector((0, -0.05, dist + 0.6)); info = {"clear": 1.0, "swung": 0}
    elif angle == "ots":  # over the clerk's shoulder toward the other character
        rc = RIGS["CLK"]; back = Matrix.Rotation(rc.rotation_euler.z, 3, "Z") @ Vector((0, 1, 0))
        pos = head(rc) + back * 0.9 + Vector((0.35, 0, 0.2)); info = {"clear": 1.0, "swung": 0}
        other = RIGS["INF"] if subj == "CLK" else RIGS[subj]; hd = head(other)
        subject_pt = hd - Vector((0, 0, 0.4 if framing == "wide" else 0.1))
    else:
        pos, info = SC.place(subject_pt, front, dist, ANGLE.get(angle, 0), height, ignore=ignore)
    pos.z = max(pos.z, 0.35)
    aim_pt = SC.aim_point(hd, framing, pos, lens) if (hd is not None and framing in SC.EYE_LINE and angle != "ots") else subject_pt
    rg = C.rig(f"S{s['id']:02d}", pos, aim_pt, lens); sc.camera = rg.cam
    n_frames = max(2, round((s["t1"] - s["t0"]) * FPS))
    if s.get("move"):
        C.apply(rg, s["move"], 1, n_frames, {n: (RIGS[n], "head") for n in RIGS})
    sc.frame_set(1)
    sc.render.filepath = os.path.join(OUT, f"shot_{s['id']:02d}.png"); bpy.ops.render.render(write_still=True)
    if s.get("move"):
        sc.frame_set(n_frames)
        sc.render.filepath = os.path.join(OUT, f"shot_{s['id']:02d}_end.png"); bpy.ops.render.render(write_still=True)
        sc.frame_set(1)
    eye = SC.on_screen(rg.cam, hd)[1] if hd is not None else True
    text = " ".join(x["w"] for x in WORDS if x["s"] < s["t1"] and x["e"] > s["t0"]) + " " + s["note"]
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
open(os.path.join(HERE, "storyboard", "lint.txt"), "w").write("\n".join(notes) + "\n")
print("LINT", len(notes), "notes")
