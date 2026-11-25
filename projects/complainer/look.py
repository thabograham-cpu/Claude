"""EEVEE look for the Complainer sets: materials from the blockout colours, tinted cast clothes,
lobby lights, AgX, 9:16 render settings. Used by projects/camera-demo/demo.py and scene.py."""
import bpy
from mathutils import Vector
import cast

GOLD = {"d4af37", "c9a227"}


def to_lin(c):
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c[:3]]


def area(name, loc, target, energy, size, color=(1, 1, 1)):
    sc = bpy.context.scene
    L = bpy.data.lights.new(name, "AREA"); L.energy = energy; L.size = size; L.color = color
    o = bpy.data.objects.new(name, L); sc.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return o


def eevee(sb, filepath, res=(432, 768), samples=8):
    sc = bpy.context.scene
    for hexc, m in sb["MATS"].items():
        m.use_nodes = True; b = m.node_tree.nodes.get("Principled BSDF")
        b.inputs["Base Color"].default_value = (*to_lin(m.diffuse_color), 1)
        b.inputs["Roughness"].default_value = 0.25 if hexc in GOLD else (0.18 if hexc in ("e8e2d6", "c9bfae", "f0ece4") else 0.6)
        b.inputs["Metallic"].default_value = 1.0 if hexc in GOLD else 0.0
        if hexc == "fff3c4":  # chandelier glows
            b.inputs["Emission Color"].default_value = (1.0, 0.85, 0.6, 1); b.inputs["Emission Strength"].default_value = 6.0
    for name, rig in sb["RIGS"].items():
        for ob in rig.children_recursive:
            if ob.type == "MESH" and any(c in ob.name for c in sb["CAST"][name]["clothes"]):
                cast.tint_clothes(ob, ob.name.split(".", 1)[1], to_lin(ob.material_slots[0].material.diffuse_color))
    # lobby lights (same family as the human-cradle PoC)
    area("LGT_Key", (-2.5, -3.5, 4.5), (0, 1.5, 1.2), 1400, 5.0, (1.0, 0.95, 0.88))
    area("LGT_Fill", (3.5, -2.0, 3.0), (0, 1.5, 1.2), 450, 4.0, (0.9, 0.93, 1.0))
    area("LGT_Top", (0, 0.5, 5.2), (0, 0.5, 0), 900, 9.0, (1.0, 0.92, 0.8))
    area("LGT_Rim", (0, 4.6, 3.2), (0, 1.0, 1.4), 500, 3.0, (1.0, 0.75, 0.5))
    Lp = bpy.data.lights.new("LGT_Chandelier", "POINT"); Lp.energy = 350; Lp.color = (1.0, 0.8, 0.55)
    lp = bpy.data.objects.new("LGT_Chandelier", Lp); sc.collection.objects.link(lp); lp.location = (0, -1, 3.9)
    sc.world = sc.world or bpy.data.worlds.new("WLD_Lobby"); sc.world.color = (0.03, 0.022, 0.018)
    items = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    sc.render.engine = next(e for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE") if e in items)
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = *res, 100
    for attr, val in (("taa_render_samples", samples), ("use_raytracing", False), ("use_gtao", True)):
        try: setattr(sc.eevee, attr, val)
        except (AttributeError, TypeError): pass
    sc.view_settings.view_transform = "AgX"
    try: sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError: pass
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
