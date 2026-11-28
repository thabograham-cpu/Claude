"""Licensed external 3D assets: download into assets/cache/<name>/ (git-ignored) and import into Blender.
Sources must be CC0 or CC-BY; credits are listed in assets/CREDITS.md (CC-BY requires attribution in the video
description). Fetch: python3 tools/assets.py   (idempotent; prints what it downloaded)."""
import os, sys, json, urllib.request
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..")); CACHE = os.path.join(ROOT, "assets", "cache")
KHR = "https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Assets/main/Models/{0}/glTF-Binary/{0}.glb"
ASSETS = {  # name: (url, license, author, what it is in the hotel)
    "GlamVelvetSofa": (KHR, "CC-BY-4.0", "Eric Chadwick (Wayfair)", "lobby sofa"),
    "SheenWoodLeatherSofa": (KHR, "CC-BY-4.0 / CC0-1.0", "Eric Chadwick, Fran Calvente", "lobby sofa (leather)"),
    "ChairDamaskPurplegold": (KHR, "CC-BY-4.0", "Eric Chadwick (Wayfair)", "lobby armchair"),
    "SheenChair": (KHR, "CC0-1.0", "Eric Chadwick (Wayfair)", "armchair"),
    "SpecularSilkPouf": (KHR, "CC-BY-4.0", "Eric Chadwick (Wayfair)", "pouf / footstool"),
    "GlassVaseFlowers": (KHR, "CC0-1.0", "Eric Chadwick, Rico Cilliers", "flowers on the reception desk"),
    "DiffuseTransmissionPlant": (KHR, "CC-BY-4.0 / CC0-1.0", "Eric Chadwick, Rico Cilliers", "potted plant"),
    "WaterBottle": (KHR, "CC0-1.0", "Microsoft", "bottle on the desk"),
}


def path(name): return os.path.join(CACHE, name, f"{name}.glb")


def fetch():
    out = []
    for name, (url, *_ ) in ASSETS.items():
        p = path(name)
        if os.path.exists(p) and os.path.getsize(p) > 1000: continue
        os.makedirs(os.path.dirname(p), exist_ok=True)
        urllib.request.urlretrieve(url.format(name), p + ".part"); os.replace(p + ".part", p); out.append((name, os.path.getsize(p)))
    with open(os.path.join(ROOT, "assets", "CREDITS.md"), "w") as f:
        f.write("# 3D asset credits\n\nFrom the Khronos glTF-Sample-Assets repository (github.com/KhronosGroup/glTF-Sample-Assets).\n"
                "CC-BY assets need this attribution wherever the video is published.\n\n| asset | license | author | used as |\n|---|---|---|---|\n")
        for name, (_, lic, who, use) in ASSETS.items(): f.write(f"| {name} | {lic} | {who} | {use} |\n")
    return out


_LOADED = {}


def place(name, loc, rot_z=0.0, scale=1.0, coll=None, height=None):
    """Import a cached asset once (glTF), then place linked copies. height: rescale so it is that tall (m).
    Returns the root empty of this instance."""
    import bpy, math
    from mathutils import Vector
    if name not in _LOADED:
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=path(name))
        objs = [o for o in bpy.data.objects if o not in before]
        tmpl = bpy.data.collections.new(f"ASSET_{name}")
        for o in objs:
            for c in list(o.users_collection): c.objects.unlink(o)
            tmpl.objects.link(o)
        meshes = [o for o in objs if o.type == "MESH"]
        bpy.context.view_layer.update()
        zs = [(o.matrix_world @ Vector(v)).z for o in meshes for v in o.bound_box]
        _LOADED[name] = (tmpl, max(zs) - min(zs), min(zs))
    tmpl, h, z0 = _LOADED[name]
    s = scale * (height / h if height else 1.0)
    e = bpy.data.objects.new(f"AST_{name}", None); (coll or bpy.context.scene.collection).objects.link(e)
    e.instance_type = "COLLECTION"; e.instance_collection = tmpl
    e.location = (loc[0], loc[1], loc[2] - z0 * s); e.rotation_euler = (0, 0, math.radians(rot_z)); e.scale = (s, s, s)
    return e


if __name__ == "__main__":
    got = fetch(); print("downloaded:", got or "nothing new"); print("cache:", sorted(os.listdir(CACHE)))
