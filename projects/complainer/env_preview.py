"""Environment previews (stills) before animation: the hotel with its props, story cast at reception, the trolley,
a background guest reading and the manager at the back counter, lit with hotelkit.lighting(LOOK).
  $PY tools/bl.py run projects/complainer/env_preview.py     (LOOK=cinematic, SAMPLES=8, ONLY=wide,medium,...)
Writes projects/complainer/env/<view>.png."""
import os, sys, math, runpy, bpy
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sb = runpy.run_path(os.path.join(HERE, "storyboard.py"), run_name="storyboard_lib")
import camera as C, acting as A, hotelkit as HK, castlist
RIGS, OBJ, pose = sb["RIGS"], sb["OBJ"], sb["pose"]
sc = bpy.context.scene
RIGS.update(castlist.build(["GST"]))
for n, r in RIGS.items():                                        # clothes tint like look.eevee
    for ob in r.children_recursive:
        if ob.type == "MESH" and any(c in ob.name for c in castlist.CAST[n]["clothes"]):
            col = next(v for k, v in castlist.CAST[n]["colors"].items() if k in ob.name.lower())
            HK_lin = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in castlist.lin(col)]
            sb["cast"].tint_clothes(ob, ob.name.split(".", 1)[1], HK_lin)
HK.eevee_quality(sc, int(os.environ.get("SAMPLES", 8))); HK.lighting(os.environ.get("LOOK", "cinematic"), sc)
sc.render.resolution_x, sc.render.resolution_y = 432, 768
for n in ("open_case", "roach_box", "roach", "small_box", "lawbook", "bill"): OBJ[n].location = (0, -200, 0)
OBJ["cart"].location = (-2.3, 0.6, 0)
poser = lambda rig, p: pose(rig.name, rig, p)
BLOCK = {"CLK": ((0, 2.6, 0), 0, "stand"), "INF": ((0.1, 0.85, 0), 180, "hand_hip_L"), "F1": ((-1.0, -0.3, 0), 160, "film"),
         "F2": ((1.05, -0.4, 0), 200, "film"), "MGR": ((1.7, 4.15, 0), 180, "phone_check_R"), "GST": ((-5.95, -3.7, -0.4), 90, "sit_read")}
for n, (loc, face, p) in BLOCK.items():
    r = RIGS[n]; r.location = loc; r.rotation_euler = (0, 0, math.radians(face))
    cache = A.PoseCache(r, poser); snap = cache.get(p)["q"]
    for pb in r.pose.bones:
        q, _, l = snap[pb.name]; pb.matrix_basis = Matrix.Translation(l) @ q.to_matrix().to_4x4()
bpy.context.view_layer.update()
mag = sb["box"]((0, 0, 0), (0.3, 0.22, 0.01), "c0392b", "SM_Magazine")           # the guest's magazine
mag.location = RIGS["GST"].matrix_world @ ((RIGS["GST"].pose.bones["wrist.L"].tail + RIGS["GST"].pose.bones["wrist.R"].tail) / 2)
mag.rotation_euler = (math.radians(60), 0, math.radians(90))
VIEWS = {  # name: camera, aim, lens, focus (None = no DoF)
    "wide": ((5.6, -6.4, 1.7), (-1.0, 1.4, 1.35), 18, None),
    "medium": ((1.7, -1.3, 1.55), (0.0, 2.2, 1.25), 30, (0.0, 2.6, 1.6)),
    "closeup": ((-0.45, 0.95, 1.33), (-1.05, 1.75, 1.2), 40, (-1.0, 1.7, 1.2)),
    "closeup_staff": ((1.75, 3.25, 1.45), (0.75, 2.2, 0.95), 30, (0.95, 2.2, 1.0)),
    "exterior": ((7.5, -21.5, 1.7), (0, -7.25, 5.0), 20, None),
    "elevators": ((7.7, -0.9, 1.6), (10.6, 2.0, 1.4), 22, None),
}
out = os.path.join(HERE, "env"); os.makedirs(out, exist_ok=True)
only = os.environ.get("ONLY", ",".join(VIEWS)).split(",")
for name in only:
    p, a, lens, foc = VIEWS[name]; rg = C.rig(f"ENV_{name}", HK.keep_inside(p, a), a, lens)
    if foc: C.dof(rg, 2.8, foc)
    sc.camera = rg.cam; sc.render.filepath = os.path.join(out, f"{name}.png"); bpy.ops.render.render(write_still=True); print("ENV", name)
