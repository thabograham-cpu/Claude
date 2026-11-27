"""Facial animation test: three dialogue lines (neutral / angry / sarcastic), close-ups, real phoneme lip sync.
Prep (outside Blender, once per line):
  /home/user/blender-shorts/lipsync/bin/python -I tools/phonemes.py audio/<line>.mp3 "<text>" audio/<line>.phones.json
Build:  rm -f projects/facetest/facetest.blend; $PY tools/bl.py run projects/facetest/facetest.py --blend projects/facetest/facetest.blend --save
Render: render_range.py -> frames/f_####.png;  then python3 projects/facetest/finish.py
Only the speaker of a line gets lip sync; the other character is a listener (blinks, eyes, expression, no mouth)."""
import os, sys, json, math
import bpy
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [os.path.join(ROOT, "tools"), os.path.join(ROOT, "projects", "complainer")]
import castlist, cast, camera as C, shotcraft as SC, lipsync as LS

FPS = 24
LINES = json.load(open(os.path.join(HERE, "dialogue.json")))["lines"]
sc = bpy.context.scene
for o in list(bpy.data.objects): bpy.data.objects.remove(o)

RIGS = castlist.build(["CLK", "INF"])
POS = {"CLK": ((0.0, 0.55, 0), 0), "INF": ((0.12, -0.55, 0), 180)}  # facing each other across 1.1 m
for n, (loc, face) in POS.items():
    r = RIGS[n]; r.location = loc; r.rotation_euler = (0, 0, math.radians(face))
bpy.context.view_layer.update()


def arm_down(rig):  # relaxed arms instead of the MPFB A-pose (no pose library needed for close-ups)
    for side, sx in (("L", 1), ("R", -1)):
        pb = rig.pose.bones[f"upperarm01.{side}"]; pb.rotation_mode = "XYZ"; pb.rotation_euler = (0, 0, 0)
        bpy.context.view_layer.update()
        cur = (pb.tail - pb.head).normalized(); want = Vector((0.18 * sx, 0.02, -1)).normalized()
        q = cur.rotation_difference(want); h = pb.matrix.translation.copy()
        pb.matrix = Matrix.Translation(h) @ q.to_matrix().to_4x4() @ Matrix.Translation(-h) @ pb.matrix
        bpy.context.view_layer.update()


for r in RIGS.values(): arm_down(r)
for n, r in RIGS.items():  # tint clothes like the Complainer look
    for ob in r.children_recursive:
        if ob.type == "MESH" and any(c in ob.name for c in castlist.CAST[n]["clothes"]):
            col = next(v for k, v in castlist.CAST[n]["colors"].items() if k in ob.name.lower())
            cast.tint_clothes(ob, ob.name.split(".", 1)[1], [x ** 2.2 for x in castlist.lin(col)])

# set: hotel-burgundy back wall + desk edge, soft key/fill/rim, AgX
def box(loc, size, rgb, name):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc); o = bpy.context.object; o.scale = size; o.name = name
    m = bpy.data.materials.new(name); m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*rgb, 1)
    m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.5
    o.data.materials.append(m); return o


box((0, 3.2, 2.5), (8, 0.2, 5), (0.2, 0.025, 0.04), "SM_WallBack")
box((0, -3.2, 2.5), (8, 0.2, 5), (0.55, 0.5, 0.42), "SM_WallFront")
box((0.06, 0.05, 0.55), (2.4, 0.6, 1.1), (0.08, 0.035, 0.02), "SM_Desk")
box((0.06, 0.05, 1.12), (2.6, 0.75, 0.05), (0.85, 0.82, 0.76), "SM_DeskTop")
box((0, 0, -0.05), (10, 10, 0.1), (0.6, 0.56, 0.5), "SM_Floor")


def area(name, loc, target, energy, size, color):
    L = bpy.data.lights.new(name, "AREA"); L.energy = energy; L.size = size; L.color = color
    o = bpy.data.objects.new(name, L); sc.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()


area("LGT_Key", (-1.6, -1.2, 2.6), (0, 0, 1.6), 260, 2.0, (1.0, 0.94, 0.86))
area("LGT_KeyB", (1.6, 1.8, 2.6), (0, 0, 1.6), 200, 2.0, (1.0, 0.94, 0.86))
area("LGT_Fill", (1.8, -1.5, 1.7), (0, 0, 1.6), 70, 3.0, (0.85, 0.9, 1.0))
area("LGT_Rim", (0.4, 2.6, 2.4), (0, 0, 1.6), 160, 1.5, (1.0, 0.8, 0.6))
sc.world = bpy.data.worlds.new("W"); sc.world.color = (0.05, 0.04, 0.035)
items = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
sc.render.engine = next(e for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE") if e in items)
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 540, 960, 100
for attr, val in (("taa_render_samples", 16), ("use_gtao", True)):
    try: setattr(sc.eevee, attr, val)
    except (AttributeError, TypeError): pass
sc.view_settings.view_transform = "AgX"
try: sc.view_settings.look = "AgX - Medium High Contrast"
except TypeError: pass
sc.render.image_settings.file_format = "PNG"; sc.render.filepath = os.path.join(HERE, "frames", "f_")
sc.render.fps = FPS

# ---------------- face performance: speaker lip sync, listener idles ----------------
for r in RIGS.values(): LS.prepare(r)
end = 0
plans = []
for ln in LINES:
    ph = json.load(open(os.path.join(HERE, ln["phones"])))
    tr = LS.plan(ph, ln["emotion"], FPS, ln["start"], ln["speaker"])
    other = next(n for n in RIGS if n != ln["speaker"])
    LS.apply(RIGS[ln["speaker"]], tr, look_at=RIGS[other])
    plans.append((ln, tr)); end = max(end, tr["f1"])
sc.frame_start, sc.frame_end = 1, end + 6
# listeners: every span where a character is not speaking (including before/after/between lines)
spans = {n: [] for n in RIGS}
for n in RIGS:
    busy = sorted((tr["f0"], tr["f1"]) for ln, tr in plans if ln["speaker"] == n)
    cur = 1
    for a, b in busy + [(sc.frame_end + 1, sc.frame_end + 1)]:
        if a - 1 >= cur:
            spk = next((ln for ln, tr in plans if tr["f0"] <= a - 1 <= tr["f1"] and ln["speaker"] != n), None)
            LS.idle(RIGS[n], cur, a - 1, emotion=(spk or {}).get("listener_emotion", "neutral"),
                    look_at=RIGS[next(m for m in RIGS if m != n)])
        cur = b + 1

# ---------------- cameras: one close-up per line, held, whisper of handheld ----------------
sc.frame_set(1); bpy.context.view_layer.update()
rows = []
for k, (ln, tr) in enumerate(plans, 1):
    n = ln["speaker"]; r = RIGS[n]; hd = r.matrix_world @ r.pose.bones["head"].head
    front = Matrix.Rotation(r.rotation_euler.z, 3, "Z") @ Vector((0, -1, 0))
    lens = 70; pos, info = SC.place(hd, front, SC.distance_for("cu", lens) * 0.85, ln.get("cam_angle", 18), 0.02,
                                    ignore={r.name, *(c.name for c in r.children_recursive)})
    assert info["clear"] >= 0.75, info
    f0 = 1 if k == 1 else tr["f0"] - 4; f1 = sc.frame_end if k == len(plans) else plans[k][1]["f0"] - 5
    rg = C.rig(f"Face{k:02d}", pos, SC.aim_point(hd, "cu", pos, lens), lens)
    C.hold(rg, f0, f1, focus=False); C.handheld(rg, 0.06, f0=f0, f1=f1); C.dof(rg, 2.8, r, "head")
    m = sc.timeline_markers.new(rg.cam.name, frame=f0); m.camera = rg.cam
    rows.append(dict(id=k, f0=f0, f1=f1, type="close-up", subject=n, purpose=f"{ln['emotion']}: {ln['text']}",
                     **C.describe(rg, f0, f1, n)))
sc.camera = bpy.data.objects["CAM_Face01"]
SC.shotlist(rows, os.path.join(HERE, "shotlist.md"), FPS)
# timing sheet for frame-by-frame inspection: frame -> speaker, phoneme, top visemes
sheet = []
for ln, tr in plans:
    ph = json.load(open(os.path.join(HERE, ln["phones"])))
    for i in range(tr["f1"] - tr["f0"] + 1):
        t = i / FPS; cur = next((p["p"] for p in ph["phones"] if p["s"] <= t < p["e"]), "-")
        top = sorted(((tr["keys"][v][i], v) for v in LS.VISEMES if v in tr["keys"]), reverse=True)[:2]
        sheet.append({"f": tr["f0"] + i, "who": ln["speaker"], "ph": cur, "vis": [(v, round(w, 2)) for w, v in top if w > 0.05]})
json.dump(sheet, open(os.path.join(HERE, "timing.json"), "w"), indent=0)
sc.frame_set(1)
print("FACETEST built:", len(plans), "lines,", sc.frame_end, "frames")
