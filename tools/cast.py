"""Build realistic rigged humans with MPFB (MakeHuman for Blender) in headless bpy."""
import bpy, addon_utils
SUBDIV = 0  # 1 = smoother close-ups, ~2x memory/time

addon_utils.enable("bl_ext.user_default.mpfb", default_set=True)
from bl_ext.user_default.mpfb.services.humanservice import HumanService  # noqa: E402


def human(name, *, gender, age=0.42, muscle=0.5, weight=0.5, height=0.5, race=None,
          skin, hair, eyebrows="eyebrow001", clothes=(), rig="default", proportions=0.6):
    info = HumanService._create_default_human_info_dict()
    info["name"] = name
    info["phenotype"].update(gender=gender, age=age, muscle=muscle, weight=weight, height=height,
                             proportions=proportions)
    if race: info["phenotype"]["race"] = race
    info.update(
        rig=rig,
        eyes="high-poly.mhclo", eyes_material_type="MAKESKIN",
        eyebrows=f"{eyebrows}.mhclo", eyelashes="eyelashes01.mhclo",
        teeth="teeth_base.mhclo", tongue="tongue01.mhclo",
        hair=f"{hair}.mhclo" if hair else "",
        clothes=[f"{c}.mhclo" for c in clothes],
        skin_mhmat=f"{skin}.mhmat", skin_material_type="ENHANCED_SSS",
    )
    s = HumanService.get_default_deserialization_settings()
    s["subdiv_levels"] = SUBDIV
    body = HumanService.deserialize_from_dict(info, s)
    rig_obj = body.parent if body.parent and body.parent.type == "ARMATURE" else None
    return body, rig_obj


def tint_clothes(body, keyword, rgb, strength=0.85):
    """Recolour a clothing item: keep its texture's shading, push hue to rgb (linear)."""
    for ob in body.parent.children_recursive if body.parent else body.children_recursive:
        if ob.type != "MESH" or keyword.lower() not in ob.name.lower():
            continue
        for slot in ob.material_slots:
            m = slot.material
            if not m or not m.use_nodes: continue
            nt = m.node_tree
            bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
            if not bsdf: continue
            src = bsdf.inputs["Base Color"].links[0].from_socket if bsdf.inputs["Base Color"].links else None
            mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
            mix.inputs["Factor"].default_value = 1.0
            bw = nt.nodes.new("ShaderNodeRGBToBW")
            if src:
                nt.links.new(src, bw.inputs[0])
                # brighten the luminance so dark textures still carry the colour
                mr = nt.nodes.new("ShaderNodeMath"); mr.operation = "MULTIPLY_ADD"
                mr.inputs[1].default_value = 1.0 - strength * 0.4; mr.inputs[2].default_value = strength * 0.55
                nt.links.new(bw.outputs[0], mr.inputs[0])
                nt.links.new(mr.outputs[0], mix.inputs["A"])
            else:
                mix.inputs["A"].default_value = (0.8, 0.8, 0.8, 1)
            mix.inputs["B"].default_value = (*rgb, 1)
            nt.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
