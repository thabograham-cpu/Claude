"""Acting test for tools/acting.py (8 s, 9:16): the Complainer beat in one take at a hotel desk.
  INF  arrogant: strolls in, turns to the desk, hand on hip, snaps for his bags, points up, scoffs
  F1   films him: eyes on the phone, glances over it, re-grips, laughs at the snap
  CLK  behind the desk: polite listener -> disbelief -> exhausted sigh, hand to the back of his neck
MODE=gallery builds the nine emotion presets on CLK instead (one still per preset).
Build:  rm -f projects/actingtest/actingtest.blend; MODE=scene $PY tools/bl.py run projects/actingtest/actingtest.py --blend projects/actingtest/actingtest.blend --save
Render: render_range.py -> frames/f_####.png; then python3 projects/actingtest/finish.py"""
import os, sys, math, json
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [os.path.join(ROOT, "tools"), os.path.join(ROOT, "projects", "complainer")]
import castlist, cast, camera as C, acting as A, lipsync as LS

FPS, MODE = 24, os.environ.get("MODE", "scene")
sc = bpy.context.scene
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
names = ["CLK"] if MODE == "gallery" else ["INF", "CLK", "F1"]
RIGS = castlist.build(names)
for n, r in RIGS.items():
    for ob in r.children_recursive:
        if ob.type == "MESH" and any(c in ob.name for c in castlist.CAST[n]["clothes"]):
            col = next(v for k, v in castlist.CAST[n]["colors"].items() if k in ob.name.lower())
            cast.tint_clothes(ob, ob.name.split(".", 1)[1], [x ** 2.2 for x in castlist.lin(col)])


def box(loc, size, rgb, name):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc); o = bpy.context.object; o.scale = size; o.name = name
    m = bpy.data.materials.new(name); m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*rgb, 1)
    m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.5
    o.data.materials.append(m); return o


def area(name, loc, target, energy, size, color):
    L = bpy.data.lights.new(name, "AREA"); L.energy = energy; L.size = size; L.color = color
    o = bpy.data.objects.new(name, L); sc.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()


def key_place(rig, f, loc, face):
    rig.location = loc; rig.rotation_euler = (0, 0, math.radians(face))
    rig.keyframe_insert("location", frame=f); rig.keyframe_insert("rotation_euler", frame=f)


box((0, 3.0, 2.5), (9, 0.2, 5), (0.2, 0.025, 0.04), "SM_WallBack")
if MODE == "scene":
    box((0, 0.05, 0.55), (2.4, 0.6, 1.1), (0.08, 0.035, 0.02), "SM_Desk")
    box((0, 0.05, 1.12), (2.6, 0.75, 0.05), (0.85, 0.82, 0.76), "SM_DeskTop")
box((0, 0, -0.05), (14, 14, 0.1), (0.6, 0.56, 0.5), "SM_Floor")
area("LGT_Key", (-2.2, -2.4, 3.2), (0, 0, 1.4), 420, 3.0, (1.0, 0.94, 0.86))
area("LGT_Fill", (2.6, -1.8, 2.0), (0, 0, 1.4), 120, 3.0, (0.85, 0.9, 1.0))
area("LGT_Rim", (0.5, 2.6, 2.6), (0, 0, 1.5), 220, 2.0, (1.0, 0.8, 0.6))
area("LGT_Top", (0, -0.5, 4.5), (0, -0.5, 0), 300, 6.0, (1.0, 0.93, 0.82))
sc.world = bpy.data.worlds.new("W"); sc.world.color = (0.05, 0.04, 0.035)
items = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
sc.render.engine = next(e for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE") if e in items)
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 432, 768, 100
for attr, val in (("taa_render_samples", 8), ("use_gtao", True)):
    try: setattr(sc.eevee, attr, val)
    except (AttributeError, TypeError): pass
sc.view_settings.view_transform = "AgX"
sc.render.image_settings.file_format = "PNG"; sc.render.fps = FPS
sc.render.filepath = os.path.join(HERE, "frames" if MODE == "scene" else "gallery", "f_")
for r in RIGS.values(): LS.prepare(r)
caches = {n: A.PoseCache(r) for n, r in RIGS.items()}

if MODE == "gallery":
    # each preset 2.0 s: react at its start with its signature pose; still at +1.3 s
    G = [("arrogant", "hand_hip_L"), ("annoyed", "arms_crossed"), ("disbelief", "palms_up"), ("embarrassed", "rub_neck_R"),
         ("angry", "fists_low"), ("confused", "chin_R"), ("sarcastic", "palm_up_R"), ("exhausted", "stand"), ("surprised", "stand")]
    beats = []
    for k, (pr, po) in enumerate(G):
        beats += [(0.3 + 2.0 * k, "react", pr), (0.6 + 2.0 * k, "pose", po)]
    n = int(2.0 * len(G) * FPS) + 12
    key_place(RIGS["CLK"], 1, (0, -1.2, 0), 0)
    spec = dict(name="CLK", preset="neutral", pose="stand", look=[(0, (0.9, -2.5, 1.5))], beats=beats, role="primary")
    A.perform(RIGS["CLK"], spec, 1, n, RIGS, cache=caches["CLK"])
    sc.frame_start, sc.frame_end = 1, n
    rg = C.rig("Gallery", (0.7, -4.4, 1.35), (0.0, -1.2, 1.12), 32); C.dof(rg, 4.0, RIGS["CLK"], "head")
    sc.camera = rg.cam
    stills = [round((1.6 + 2.0 * k) * FPS) for k in range(len(G))]
    json.dump({"stills": stills, "presets": [g[0] for g in G]}, open(os.path.join(HERE, "gallery.json"), "w"))
    print("GALLERY built:", stills)
else:
    D = 8.0; n = int(D * FPS)
    # placement: INF strolls in from camera-left and turns to the desk; CLK behind the desk; F1 filming from camera-left
    key_place(RIGS["INF"], 1, (1.2, -2.3, 0), 215); key_place(RIGS["INF"], 34, (0.45, -0.75, 0), 197)
    key_place(RIGS["CLK"], 1, (0.0, 0.75, 0), 0)
    key_place(RIGS["F1"], 1, (-1.0, -1.7, 0), 123)
    for fc in C._fcurves(RIGS["INF"]):
        for kp in fc.keyframe_points: kp.interpolation = "SINE"; kp.easing = "EASE_OUT"
    phone = box((0, 0, 0), (0.075, 0.009, 0.15), (0.02, 0.02, 0.025), "SM_Phone")
    for c_, kw in (("COPY_LOCATION", dict(head_tail=1.0)), ("COPY_ROTATION", {})):
        c = phone.constraints.new(c_); c.target = RIGS["F1"]; c.subtarget = "wrist.R"
        for k, v in kw.items(): setattr(c, k, v)
    SPECS = {
        "INF": dict(name="INF", intent="make the clerk serve him, on camera", preset="arrogant", role="primary", pose="stand",
                    look=[(0, "CLK"), (2.6, "F1"), (3.2, "CLK")],
                    beats=[(1.7, "pose", "hand_hip_L"), (2.4, "pose", "snap_R"), (3.3, "pose", "hand_hip_L"),
                           (4.3, "pose", "point_up_R"), (5.4, "pose", "hand_hip_L"), (5.6, "accent", "scoff")]),
        "CLK": dict(name="CLK", intent="stay professional; then realise what 'ninth floor' means", preset="neutral",
                    role="listener", pose="stand", look=[(0, "INF"), (4.4, (0.0, 0.0, 6.0)), (5.0, "INF")],
                    beats=[(4.7, "react", "disbelief"), (5.5, "pose", "palms_up"), (6.4, "pose", "stand"),
                           (6.5, "react", "exhausted"), (6.6, "accent", "sigh"), (7.3, "pose", "rub_neck_R")]),
        "F1": {**A.filmer("F1", "INF", D, react=[(2.5, "laugh"), (4.4, "nod")]), "pose": "phone_film", "preset": "neutral"},
    }
    for nm, spec in SPECS.items():
        A.perform(RIGS[nm], spec, 1, n, RIGS, cache=caches[nm])
    sc.frame_start, sc.frame_end = 1, n
    rg = C.rig("Wide", (-0.6, -3.9, 1.6), (0.0, 0.0, 1.3), 20); C.dof(rg, 5.6, RIGS["INF"], "head")  # F1 left, INF right, CLK between
    C.handheld(rg, 0.08, f0=1, f1=n)
    sc.camera = rg.cam
    for w in A.eyeline_lint(RIGS, SPECS, 1, n): print("EYELINE LINT:", w)
    open(os.path.join(HERE, "direction.md"), "w").write(
        "| who | intent | preset | role | beats |\n|---|---|---|---|---|\n" + "".join(
            f"| {k} | {s['intent']} | {s.get('preset', 'neutral')} | {s.get('role')} | "
            + "; ".join(f"{t:.1f}s {a} {v}" for t, a, v in sorted(s.get('beats', []))) + " |\n" for k, s in SPECS.items()))
sc.frame_set(1)
print("ACTINGTEST built:", MODE, sc.frame_end, "frames")
