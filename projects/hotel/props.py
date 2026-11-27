"""Hero-prop check: suitcases (4 kinds), bug box (lid open) + cockroach, phone. STILL -> projects/hotel/stills/props.png"""
import os, sys, math, bpy
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))
import hotelkit as HK, camera as C
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
sc = bpy.context.scene; P = HK.palette(); c = sc.collection
mb = HK.MB("floor", c); mb.box((-3, -3, -0.1), (3, 3, 0), P["marble"]); mb.box((-3, 1.0, 0), (3, 1.1, 2), P["accent"]); mb.done()
for k, (kind, col) in enumerate((("cabin", (0.85, 0.12, 0.35)), ("medium", (0.1, 0.45, 0.75)), ("large", (0.95, 0.75, 0.15)), ("duffel", (0.15, 0.15, 0.17)))):
    o = HK.suitcase(f"t{k}", kind, col, P, c); o.location = (-0.9 + k * 0.55, 0.3, 0)
bb = HK.bug_box("t", c, P); bb.location = (0.15, -0.35, 0.0); bpy.data.objects["LID_t"].rotation_euler.x = math.radians(-110)
r = HK.cockroach("t", c, P); r.location = (0.15, -0.36, 0.03)
ph = HK.phone("t", c, P); ph.location = (0.45, -0.35, 0.08); ph.rotation_euler = (math.radians(-70), 0, math.radians(-20))
HK.light("key", "AREA", (-1.5, -2.0, 2.0), 300, size=1.5, aim=(0, 0, 0.3)); HK.light("fill", "AREA", (2, -1, 1.5), 80, size=2, aim=(0, 0, 0.3))
HK.eevee_quality(sc, 12); sc.render.resolution_x, sc.render.resolution_y = 768, 432
sc.world = bpy.data.worlds.new("w"); sc.world.color = (0.05, 0.05, 0.05)
rg = C.rig("props", (0.1, -1.6, 0.75), (0.0, 0.0, 0.25), 35); C.dof(rg, 8.0, (0.15, -0.35, 0.05)); sc.camera = rg.cam
sc.render.filepath = os.path.join(HERE, "stills", "props.png"); bpy.ops.render.render(write_still=True)
rg2 = C.rig("macro", (0.25, -0.62, 0.2), (0.15, -0.35, 0.04), 60); C.dof(rg2, 2.8, (0.15, -0.36, 0.04)); sc.camera = rg2.cam
sc.render.resolution_x, sc.render.resolution_y = 432, 432
sc.render.filepath = os.path.join(HERE, "stills", "props_macro.png"); bpy.ops.render.render(write_still=True); print("PROPS done")
