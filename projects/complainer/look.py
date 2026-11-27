"""EEVEE look for the Complainer: prop materials from the blockout colours, tinted cast clothes, the hotel
kit's render quality (lights live in tools/hotelkit.py), 9:16 render settings. Used by projects/camera-demo/demo.py and scene.py."""
import math
import bpy
from mathutils import Vector
import cast, hotelkit

GOLD = {"d4af37", "c9a227"}


def to_lin(c):
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c[:3]]


def area(name, loc, target, energy, size, color=(1, 1, 1)):
    sc = bpy.context.scene
    L = bpy.data.lights.new(name, "AREA"); L.energy = energy; L.size = size; L.color = color
    o = bpy.data.objects.new(name, L); sc.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return o


def eevee(sb, filepath, res=(432, 768), samples=12):
    sc = bpy.context.scene
    for hexc, m in sb["MATS"].items():
        m.use_nodes = True; b = m.node_tree.nodes.get("Principled BSDF")
        b.inputs["Base Color"].default_value = (*to_lin(m.diffuse_color), 1)
        b.inputs["Roughness"].default_value = 0.38 if hexc in GOLD else (0.3 if hexc in ("e8e2d6", "c9bfae", "f0ece4") else 0.65)  # no plastic sheen
        b.inputs["Metallic"].default_value = 1.0 if hexc in GOLD else 0.0
        if hexc == "fff3c4":  # chandelier glows
            b.inputs["Emission Color"].default_value = (1.0, 0.85, 0.6, 1); b.inputs["Emission Strength"].default_value = 6.0
    for name, rig in sb["RIGS"].items():
        for ob in rig.children_recursive:
            if ob.type == "MESH" and any(c in ob.name for c in sb["CAST"][name]["clothes"]):
                cast.tint_clothes(ob, ob.name.split(".", 1)[1], to_lin(ob.material_slots[0].material.diffuse_color))
    # lighting, sky, reflections, AO and shadows come from the hotel kit (tools/hotelkit.py)
    hotelkit.eevee_quality(sc, samples)
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = *res, 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = filepath


def add_step_poses(POSES):
    """Walk-cycle keys: <arms>_stepL / _stepR for selfie + film, and carry_climbR (mirror of carry_climb)."""
    L = {"upperleg01.L": (0.03, -0.35, -1), "upperleg01.R": (-0.03, 0.3, -1), "lowerleg01.R": (0, 0.45, -1)}
    R = {"upperleg01.R": (-0.03, -0.35, -1), "upperleg01.L": (0.03, 0.3, -1), "lowerleg01.L": (0, 0.45, -1)}
    for arms in ("selfie", "film"):
        base = {k: v for k, v in POSES[arms].items() if "leg" not in k}
        POSES[f"{arms}_stepL"] = {**base, **L}; POSES[f"{arms}_stepR"] = {**base, **R}
    c = POSES["carry_climb"]
    POSES["carry_climbR"] = {k: v for k, v in c.items() if "leg" not in k} | {"upperleg01.R": (-0.05, -0.6, -0.8), "lowerleg01.R": (0, 0.1, -1)}


def key_rig(sb, name, f, p, loc, face):
    """Key a cast rig's place, facing (deg, 0 = toward -Y) and pose at frame f. MPFB pose bones are Euler XYZ,
    so key whichever rotation channel each bone actually uses."""
    r = sb["RIGS"][name]; r.location = Vector(loc); r.rotation_euler = (0, 0, math.radians(face))
    r.keyframe_insert("location", frame=f); r.keyframe_insert("rotation_euler", frame=f)
    sb["pose"](name, r, p)
    for pb in r.pose.bones:
        pb.keyframe_insert("rotation_quaternion" if pb.rotation_mode == "QUATERNION" else "rotation_euler", frame=f)
        pb.keyframe_insert("location", frame=f)
