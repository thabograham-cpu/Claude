"""Lighting test: one frame of the existing scene (identical cast, pose and camera) rendered with the current
light and with each hotelkit.LOOKS preset. Writes projects/complainer/lighting/<look>.png.
  $PY tools/bl.py run projects/complainer/lighting_test.py --blend projects/complainer/scene.blend   (FRAME=375)"""
import os, sys, bpy
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))
import hotelkit as HK
sc = bpy.context.scene; sc.frame_set(int(os.environ.get("FRAME", 375))); sc.eevee.taa_render_samples = 8
for c in bpy.data.collections:
    if c.name.startswith("HOTEL"): HK._COLL[c.name] = c
out = os.path.join(HERE, "lighting"); os.makedirs(out, exist_ok=True)
for look in os.environ.get("LOOKS", "current," + ",".join(HK.LOOKS)).split(","):
    if look != "current": HK.lighting(look, sc)
    sc.render.filepath = os.path.join(out, f"{look}.png"); bpy.ops.render.render(write_still=True); print("LIGHTING", look)
