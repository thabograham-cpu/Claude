"""30 s camera-technique demo in the Complainer hotel lobby (EEVEE, 9:16, 24 fps, 720 frames).
Build:  bash projects/camera-demo/build.sh   ->  projects/camera-demo/scene.blend
Reuses the storyboard's lobby + MPFB cast (projects/complainer/storyboard.py) unchanged; adds EEVEE
materials, lighting, a walk cycle and one camera.py rig per technique."""
import os, sys, math, runpy
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import camera as C, shotcraft as SC, cast

sb = runpy.run_path(os.path.join(ROOT, "projects", "complainer", "storyboard.py"), run_name="storyboard_lib")
RIGS, OBJ, POSES, pose, head, hand, CAST = (sb[k] for k in ("RIGS", "OBJ", "POSES", "pose", "head", "hand", "CAST"))
sc = bpy.context.scene
FPS, END = 24, 720
sc.render.fps = FPS; sc.frame_start, sc.frame_end = 1, END


def to_lin(c):
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c[:3]]


# ---------------- EEVEE look: set materials from the blockout colours, cast clothes tinted ----------------
GOLD = {"d4af37", "c9a227"}
for hexc, m in sb["MATS"].items():
    m.use_nodes = True; b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*to_lin(m.diffuse_color), 1)
    b.inputs["Roughness"].default_value = 0.25 if hexc in GOLD else (0.18 if hexc in ("e8e2d6", "c9bfae", "f0ece4") else 0.6)
    b.inputs["Metallic"].default_value = 1.0 if hexc in GOLD else 0.0
    if hexc == "fff3c4":  # chandelier glows
        b.inputs["Emission Color"].default_value = (1.0, 0.85, 0.6, 1); b.inputs["Emission Strength"].default_value = 6.0
for name, rig in RIGS.items():
    for ob in rig.children_recursive:
        if ob.type == "MESH" and any(c in ob.name for c in CAST[name]["clothes"]):
            col = to_lin(ob.material_slots[0].material.diffuse_color)
            cast.tint_clothes(ob, ob.name.split(".", 1)[1], col)  # body arg is any object under the rig
RIGS["MGR"].location = (0, -100, 0)
for n in ("open_case", "small_box", "roach_box", "roach"): OBJ[n].location = (0, -200, 0)  # parked as in the storyboard
OBJ["cart"].location = (-2.2, 3.6, 0)  # behind the desk (storyboard lobby default)

# ---------------- lights + render settings (same family as the human-cradle PoC) ----------------
def area(name, loc, target, energy, size, color=(1, 1, 1)):
    L = bpy.data.lights.new(name, "AREA"); L.energy = energy; L.size = size; L.color = color
    o = bpy.data.objects.new(name, L); sc.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()


area("LGT_Key", (-2.5, -3.5, 4.5), (0, 1.5, 1.2), 1400, 5.0, (1.0, 0.95, 0.88))
area("LGT_Fill", (3.5, -2.0, 3.0), (0, 1.5, 1.2), 450, 4.0, (0.9, 0.93, 1.0))
area("LGT_Top", (0, 0.5, 5.2), (0, 0.5, 0), 900, 9.0, (1.0, 0.92, 0.8))
area("LGT_Rim", (0, 4.6, 3.2), (0, 1.0, 1.4), 500, 3.0, (1.0, 0.75, 0.5))
Lp = bpy.data.lights.new("LGT_Chandelier", "POINT"); Lp.energy = 350; Lp.color = (1.0, 0.8, 0.55)
lp = bpy.data.objects.new("LGT_Chandelier", Lp); sc.collection.objects.link(lp); lp.location = (0, -1, 3.9)
sc.world = sc.world or bpy.data.worlds.new("WLD_Lobby"); sc.world.color = (0.03, 0.022, 0.018)
items = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
sc.render.engine = next(e for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE") if e in items)
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 432, 768, 100
for attr, val in (("taa_render_samples", 8), ("use_raytracing", False), ("use_gtao", True)):
    try: setattr(sc.eevee, attr, val)
    except (AttributeError, TypeError): pass
sc.view_settings.view_transform = "AgX"
try: sc.view_settings.look = "AgX - Medium High Contrast"
except TypeError: pass
sc.render.image_settings.file_format = "PNG"
sc.render.filepath = os.path.join(HERE, "frames", "f_")
bpy.data.objects["TXT_stamp"].hide_render = True; bpy.data.objects["TXT_tag"].data.body = ""

# ---------------- cast animation ----------------
L_FWD = {"upperleg01.L": (0.03, -0.35, -1), "upperleg01.R": (-0.03, 0.3, -1), "lowerleg01.R": (0, 0.45, -1)}
R_FWD = {"upperleg01.R": (-0.03, -0.35, -1), "upperleg01.L": (0.03, 0.3, -1), "lowerleg01.L": (0, 0.45, -1)}
for arms in ("selfie", "film"):
    base = {k: v for k, v in POSES[arms].items() if "leg" not in k}
    POSES[f"{arms}_stepL"] = {**base, **L_FWD}; POSES[f"{arms}_stepR"] = {**base, **R_FWD}


def facing(src, dst):
    d = Vector(dst) - Vector(src); return math.degrees(math.atan2(d.x, -d.y))  # 0 = looking toward -Y


def keypose(name, f, p, loc=None, face=None):
    r = RIGS[name]
    if loc is not None: r.location = Vector(loc)
    if face is not None: r.rotation_euler = (0, 0, math.radians(face))
    r.keyframe_insert("location", frame=f); r.keyframe_insert("rotation_euler", frame=f)
    pose(name, r, p)
    for pb in r.pose.bones:
        pb.keyframe_insert("rotation_quaternion", frame=f); pb.keyframe_insert("location", frame=f)


def hold(name, f0, f1, p, loc, face):  # same pose at both ends -> no drift inside a segment
    keypose(name, f0, p, loc, face); keypose(name, f1, p, loc, face)


SEG = [(1, 96), (97, 180), (181, 264), (265, 348), (349, 456), (457, 540), (541, 636), (637, 720)]
INF_DESK, CLK_POS = (0.2, 1.05, 0), (0, 2.6, 0)
# 1 tracking: walk in from the entrance, friends filming behind
for k, f in enumerate(range(1, 97, 12)):
    t = (f - 1) / 95; y = -5.8 + 5.4 * t
    keypose("INF", f, "selfie_step" + "LR"[k % 2], (0, y, 0), 0)
    keypose("F1", f, "film_step" + "RL"[k % 2], (-0.9, y - 1.2, 0), 0)
    keypose("F2", f, "film_step" + "LR"[k % 2], (0.9, y - 1.3, 0), 0)
keypose("INF", 96, "selfie_stepL", (0, -0.4, 0), 0); keypose("F1", 96, "film_stepR", (-0.9, -1.6, 0), 0); keypose("F2", 96, "film_stepL", (0.9, -1.7, 0), 0)
hold("CLK", 1, 96, "stand", CLK_POS, 0)
# 2..8: at the desk
F1P, F2P = (-1.6, 0.0, 0), (1.7, -0.1, 0)
hold("INF", 97, 180, "selfie", INF_DESK, 180)
hold("F1", 97, 720, "film", F1P, facing(F1P, INF_DESK)); hold("F2", 97, 720, "film", F2P, facing(F2P, INF_DESK))
hold("CLK", 97, 348, "stand", CLK_POS, 0)
hold("INF", 181, 456, "lean_desk", INF_DESK, 180)
hold("CLK", 349, 540, "slide_bill", CLK_POS, 0)
hold("INF", 457, 540, "lean_desk", (-0.9, 1.05, 0), 180)
hold("INF", 541, 636, "lean_desk", INF_DESK, 180); hold("CLK", 541, 720, "stand", CLK_POS, 0)
hold("INF", 637, 720, "laugh", INF_DESK, 180)
for name in ("INF", "F1", "F2", "CLK"):  # walk positions linear; poses held exactly at segment cuts
    for fc in C._fcurves(RIGS[name]):
        for kp in fc.keyframe_points: kp.interpolation = "LINEAR" if fc.data_path == "location" else "BEZIER"

# phones ride the right wrist
for name in ("INF", "F1", "F2"):
    ph = OBJ["phone"] if name == "INF" else OBJ["phone"].copy()
    if name != "INF": ph.data = OBJ["phone"].data; sc.collection.objects.link(ph)
    ph.location = (0, 0, 0)
    c = ph.constraints.new("COPY_LOCATION"); c.target = RIGS[name]; c.subtarget = "wrist.R"; c.head_tail = 1.0
    t = ph.constraints.new("COPY_ROTATION"); t.target = RIGS[name]; t.subtarget = "wrist.R"

# ---------------- cameras: one rig per technique ----------------
def at(f): sc.frame_set(f); bpy.context.view_layer.update()


def H(name, f): at(f); return head(RIGS[name])


def names(name): r = RIGS[name]; return {r.name} | {c.name for c in r.children_recursive}


rigs = []
# 1 TRACKING - camera trucks alongside, aim + focus follow his head with operator lag
f0, f1 = SEG[0]; r = C.rig("01_Tracking", (2.6, -7.6, 1.45), H("INF", f0), 32); rigs.append((f0, r))
C.track(r, RIGS["INF"], f0, f1, bone="head", smooth=0.7); C.dof(r, 4.0)
r.cam.keyframe_insert("location", frame=f0); r.cam.location = (2.6, -2.4, 1.45); r.cam.keyframe_insert("location", frame=f1)
# 2 PAN - from the friend filming to the desk
f0, f1 = SEG[1]; cpos = Vector((3.6, -3.4, 1.55)); a, b = H("F1", f0), H("INF", f0).lerp(H("CLK", f0), 0.5)
r = C.rig("02_Pan", cpos, a, 28); rigs.append((f0, r))
ang = math.degrees(math.atan2((b - cpos).y, (b - cpos).x) - math.atan2((a - cpos).y, (a - cpos).x))
C.pan(r, f0 + 6, f1 - 6, ang)
# 3 DOLLY-IN - medium to close-up on the clerk
f0, f1 = SEG[2]; hd = H("CLK", f0); dist = SC.distance_for("med", 35)
pos, _ = SC.place(hd, Vector((0, -1, 0)), dist, -30, 0.05, ignore=names("CLK"))
end = hd + (pos - hd).normalized() * SC.distance_for("cu", 35)
r = C.rig("03_DollyIn", pos, SC.aim_point(hd, "cu", end, 35), 35); rigs.append((f0, r))  # framed for the close-up it ends on
C.dolly(r, f0, f1, dist - SC.distance_for("cu", 35)); C.dof(r, 2.8, RIGS["CLK"], "head")
# 4 OPTICAL ZOOM - wide lobby, lens zooms onto the 14 suitcases (camera never moves)
f0, f1 = SEG[3]; cart = OBJ["cart"].matrix_world.translation + Vector((0, 0, 1.2))
r = C.rig("04_Zoom", (4.8, -5.8, 1.7), cart, 20); rigs.append((f0, r)); C.zoom(r, f0 + 6, f1 - 4, 20, 85)
# 5 ORBIT - circle the desk two-shot
f0, f1 = SEG[4]; mid = H("INF", f0).lerp(H("CLK", f0), 0.5) - Vector((0, 0, 0.15))
r = C.rig("05_Orbit", mid + Vector((2.4, -2.2, 0.15)), mid, 30); rigs.append((f0, r)); C.orbit(r, f0, f1, -70)
C.dof(r, 4.0)
# 6 DEPTH OF FIELD - the $4,000 bill sharp, clerk melting into bokeh
f0, f1 = SEG[5]; bill = bpy.data.objects["SM_Bill"].matrix_world.translation.copy(); hc = H("CLK", f0)
r = C.rig("06_DoF", bill + Vector((0.1, -0.6, 0.3)), bill, 50); rigs.append((f0, r))
best = None  # bill on the lower third (sharp), clerk's head on the upper third (soft)
for back in (0.5, 0.7, 0.9, 1.1, 1.3):
    for up in (0.1, 0.2, 0.3, 0.4):
        for t in [k / 10 for k in range(0, 8)]:
            r.cam.location = bill + Vector((0.1, -back, up)); r.target.location = bill.lerp(hc, t)
            bpy.context.view_layer.update()
            (bx, by), vb = SC.on_screen(r.cam, bill); (cx, cy), vc = SC.on_screen(r.cam, hc)
            score = (by - 0.28) ** 2 + (cy - 0.74) ** 2 + (bx - 0.4) ** 2 + (0 if vb and vc else 9)  # bill origin is its left edge
            if best is None or score < best[0]: best = (score, r.cam.location.copy(), r.target.location.copy())
r.cam.location, r.target.location = best[1], best[2]
C.dof(r, 1.2, bill); C.dolly(r, f0, f1, 0.12)
# 7 RACK FOCUS - his face (foreground) -> the clerk
f0, f1 = SEG[6]; hi, hc = H("INF", f0), H("CLK", f0)
r = C.rig("07_RackFocus", hi + Vector((0.2, -0.55, 0.06)), hc + Vector((-0.12, 0, -0.08)), 45); rigs.append((f0, r))
C.dof(r, 1.6, RIGS["INF"], "head"); C.rack_focus(r, f0 + 36, f0 + 54, RIGS["INF"], RIGS["CLK"], "head", "head")
# 8 OVER-THE-SHOULDER - behind the clerk onto the laughing influencer
f0, f1 = SEG[7]; hc, hi = H("CLK", f0), H("INF", f0)
r = C.rig("08_OTS", hc + Vector((0, 0.7, 0.1)), hi, 40); rigs.append((f0, r))
best = None  # search a small grid: clerk's head at the frame's left edge, influencer right of centre
for dx in [x / 100 for x in range(-30, 31, 3)]:
    for back in (0.6, 0.75, 0.9, 1.05):
        for ax in (-0.15, -0.08, 0.0, 0.08, 0.15):
            r.cam.location = hc + Vector((dx, back, 0.12)); r.target.location = hi + Vector((ax, 0, -0.08))
            bpy.context.view_layer.update()
            (cx, cy), _ = SC.on_screen(r.cam, hc); (ix, iy), vis = SC.on_screen(r.cam, hi)
            score = (cx - 0.12) ** 2 + (ix - 0.62) ** 2 + (iy - 0.62) ** 2 + (0 if vis else 9)
            if best is None or score < best[0]: best = (score, r.cam.location.copy(), r.target.location.copy())
r.cam.location, r.target.location = best[1], best[2]
C.dof(r, 2.4, RIGS["INF"], "head"); C.dolly(r, f0, f1, 0.18)

for f, r in rigs:
    m = sc.timeline_markers.new(r.cam.name, frame=f); m.camera = r.cam
sc.camera = rigs[0][1].cam; sc.frame_set(1)
print("DEMO built:", len(rigs), "camera rigs")

# framing check: foreground/background characters actually in frame where the technique needs them
chk = {"06_DoF": (500, ("CLK",)), "07_RackFocus": (600, ("INF", "CLK")), "08_OTS": (700, ("CLK", "INF")), "03_DollyIn": (262, ("CLK",))}
for f, r in rigs:
    nm = r.cam.name[4:]
    if nm in chk:
        fr, who = chk[nm]; sc.frame_set(fr); bpy.context.view_layer.update()
        pts = {w: head(RIGS[w]) for w in who}
        if nm == "06_DoF": pts["bill"] = bpy.data.objects["SM_Bill"].matrix_world.translation
        print("FRAME", nm, {w: tuple(round(v, 2) for v in SC.on_screen(r.cam, p)[0]) for w, p in pts.items()})
sc.frame_set(1)
