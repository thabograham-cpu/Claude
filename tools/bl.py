#!/usr/bin/env python3
"""Headless stand-in for Blender MCP. Run with the venv python:

  PY=/home/user/blender-shorts/.venv/bin/python
  $PY bl.py info  scene.blend [--out info.json]     # = get_scene_info
  $PY bl.py run   script.py [--blend scene.blend] [--save]   # = execute_blender_code
  $PY bl.py shot  scene.blend out.png [--engine workbench|eevee|cycles]
                  [--res 1280x720] [--samples 32] [--camera NAME] [--frame N]  # = get_viewport_screenshot / render still

`run` starts from an empty scene when --blend is missing or does not exist yet;
with --save it writes the scene back to --blend (created if new).
"""
import argparse, json, os, sys, runpy

import bpy


def open_or_empty(path):
    if path and os.path.exists(path):
        bpy.ops.wm.open_mainfile(filepath=os.path.abspath(path))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)


def scene_info():
    sc = bpy.context.scene
    objs = []
    tris_total = 0
    dg = bpy.context.evaluated_depsgraph_get()
    for o in sc.objects:
        d = {"name": o.name, "type": o.type,
             "location": [round(v, 3) for v in o.location],
             "dimensions": [round(v, 3) for v in o.dimensions],
             "collections": [c.name for c in o.users_collection],
             "materials": [s.material.name for s in getattr(o, "material_slots", []) if s.material]}
        if o.type == "MESH":
            m = o.evaluated_get(dg).to_mesh()
            m.calc_loop_triangles()
            d["tris"] = len(m.loop_triangles)
            d["verts"] = len(m.vertices)
            tris_total += d["tris"]
            o.evaluated_get(dg).to_mesh_clear()
        objs.append(d)
    return {"file": bpy.data.filepath or None, "scene": sc.name,
            "engine": sc.render.engine, "frame_range": [sc.frame_start, sc.frame_end],
            "camera": sc.camera.name if sc.camera else None,
            "object_count": len(objs), "tris_total": tris_total,
            "collections": [c.name for c in bpy.data.collections],
            "materials": [m.name for m in bpy.data.materials],
            "objects": objs}


def ensure_camera(sc, name=None):
    if name:
        sc.camera = bpy.data.objects[name]
    if sc.camera:
        return
    # No camera: frame all mesh objects from a 3/4 view.
    import mathutils
    pts = [o.matrix_world @ mathutils.Vector(c) for o in sc.objects if o.type == "MESH" for c in o.bound_box]
    if pts:
        lo = mathutils.Vector([min(p[i] for p in pts) for i in range(3)])
        hi = mathutils.Vector([max(p[i] for p in pts) for i in range(3)])
    else:
        lo, hi = mathutils.Vector((-1, -1, -1)), mathutils.Vector((1, 1, 1))
    ctr, size = (lo + hi) / 2, max((hi - lo).length, 0.1)
    cam = bpy.data.objects.new("CAM_AutoPreview", bpy.data.cameras.new("CAM_AutoPreview"))
    sc.collection.objects.link(cam)
    cam.location = ctr + mathutils.Vector((1, -1, 0.7)).normalized() * size * 1.6
    cam.rotation_euler = (ctr - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam
    if not any(o.type == "LIGHT" for o in sc.objects):
        sun = bpy.data.objects.new("LGT_AutoSun", bpy.data.lights.new("LGT_AutoSun", "SUN"))
        sun.rotation_euler = (0.8, 0.2, 0.6)
        sc.collection.objects.link(sun)


def shot(out, engine, res, samples, camera):
    sc = bpy.context.scene
    ensure_camera(sc, camera)
    eng = {"workbench": "BLENDER_WORKBENCH", "cycles": "CYCLES"}.get(engine)
    if eng is None:  # eevee: name differs across versions
        items = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
        eng = next(e for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE") if e in items)
    sc.render.engine = eng
    if eng == "CYCLES":
        sc.cycles.device = "CPU"
        sc.cycles.samples = samples
    elif "EEVEE" in eng:
        try:
            sc.eevee.taa_render_samples = samples
        except AttributeError:
            pass
    w, h = (int(x) for x in res.lower().split("x"))
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = w, h, 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = os.path.abspath(out)
    bpy.ops.render.render(write_still=True)
    print("wrote", sc.render.filepath)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("info"); a.add_argument("blend"); a.add_argument("--out", help="write JSON here instead of stdout")
    a = sub.add_parser("run"); a.add_argument("script"); a.add_argument("--blend"); a.add_argument("--save", action="store_true")
    a = sub.add_parser("shot"); a.add_argument("blend"); a.add_argument("out")
    a.add_argument("--engine", default="workbench", choices=["workbench", "eevee", "cycles"])
    a.add_argument("--res", default="1280x720"); a.add_argument("--samples", type=int, default=32)
    a.add_argument("--camera"); a.add_argument("--frame", type=int)
    args = ap.parse_args()

    if args.cmd == "info":
        open_or_empty(args.blend)
        info = json.dumps(scene_info(), indent=1)
        if args.out:
            open(args.out, "w").write(info); print("wrote", args.out)
        else:
            print(info)
    elif args.cmd == "run":
        open_or_empty(args.blend)
        runpy.run_path(os.path.abspath(args.script), run_name="__main__")
        if args.save:
            if not args.blend:
                sys.exit("--save needs --blend PATH")
            bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args.blend))
            print("saved", os.path.abspath(args.blend))
    elif args.cmd == "shot":
        open_or_empty(args.blend)
        if args.frame is not None:
            bpy.context.scene.frame_set(args.frame)
        shot(args.out, args.engine, args.res, args.samples, args.camera)


if __name__ == "__main__":
    main()
