"""Hotel environment preview: builds tools/hotelkit.py's Grand Aurelia alone, checks the walking routes, and
renders review stills (exterior, lobby both ways, desk, elevators, stairwell, corridor 404, suite, overhead).
  rm -f projects/hotel/preview.blend; $PY tools/bl.py run projects/hotel/preview.py --blend projects/hotel/preview.blend --save
  STILLS=1 ... renders projects/hotel/stills/<name>.png (432x768, 16 samples)"""
import os, sys, bpy
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))
import hotelkit as HK, camera as C
sc = bpy.context.scene
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
W = HK.grand_aurelia()
HK.eevee_quality(sc, 16)
sc.render.resolution_x, sc.render.resolution_y = 432, 768
bad = HK.check_routes()
print("ROUTES:", "all clear" if not bad else ""); [print("ROUTE PROBLEM:", b) for b in bad]
Z4, Z9 = 4 * HK.FLOOR_H, 9 * HK.FLOOR_H
VIEWS = {  # name: (camera, aim, lens)
    "exterior": ((7.5, -21.5, 1.7), (0, -7.25, 5.5), 20),
    "lobby_in": ((0.6, -6.3, 1.65), (0, 2.5, 1.5), 20),
    "lobby_out": ((-0.8, 3.0, 1.75), (0.5, -7.0, 1.6), 20),
    "desk": ((1.3, -0.4, 1.6), (0, 2.0, 1.3), 35),
    "elevators": ((7.7, -0.9, 1.6), (10.6, 2.0, 1.4), 22),
    "stairwell": ((-8.2, -0.9, 1.5), (-9.4, 3.0, 6.0), 18),
    "corridor404": ((0.0, -0.9, Z4 + 1.55), (0, 7.0, Z4 + 1.2), 22),
    "suite": ((-3.3, 7.9, Z9 + 1.6), (1.0, 12.5, Z9 + 0.9), 20),
    "overhead": ((0.5, -2.0, 4.6), (0.3, -1.6, 0.0), 16),
}
for name, (p, a, lens) in VIEWS.items():
    p2 = HK.keep_inside(p, a)
    if (p2 - Vector(p)).length > 1e-6: print("CAMERA moved inside:", name, tuple(round(v, 2) for v in p2))
    C.rig(f"V_{name}", p2, a, lens)
print("HOTEL built:", len(bpy.data.objects), "objects,", len(HK.LIGHTS), "lights")
if os.environ.get("STILLS"):
    os.makedirs(os.path.join(HERE, "stills"), exist_ok=True)
    only = os.environ.get("ONLY", "").split(",") if os.environ.get("ONLY") else list(VIEWS)
    for name in only:
        sc.camera = bpy.data.objects[f"CAM_V_{name}"]; sc.render.filepath = os.path.join(HERE, "stills", f"{name}.png")
        bpy.ops.render.render(write_still=True); print("STILL", name)
