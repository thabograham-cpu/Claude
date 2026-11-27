"""Modular hotel kit + "The Grand Aurelia", a persistent hotel location for any story (headless bpy).

One building in one world frame (metres, Z up, the street is on -Y):
  street + hotel facade (y = -7.25) -> entrance (x -1.5..1.5) -> lobby (x -7..7, y -7..5, 5 m high)
  lobby west door -> stairwell (x -11.3..-7.5, switchback flights, floor k at z = 3.6 k, ground = 0)
  lobby east opening -> elevator lobby (x 7.25..10.6) -> 2 elevator cars (standard + VIP)
  floors 4 and 9: corridor C1 (stair door -> elevator lobby) + corridor C2 (north, ends at a room door)
  floor 9: suite 901 at the end of C2; the pet store is on the same street (x 20.5..29.5)
Set origins for shot coordinates (set-local -> world) are in ORIGIN; ROOMS are interior volumes (camera
containment); ROUTES are walkable paths (check_routes); ANCHORS are named marks for blocking.
Style: grounded, slightly stylised (procedural marble, wood, carpet, plaster - no glossy plastic).
Usage:  import hotelkit as HK; W = HK.grand_aurelia(); W["obj"]["desk"], W["origin"]["lobby"], HK.keep_inside(p, aim)
"""
import math
import bpy, bmesh
from mathutils import Vector, Matrix, Euler

FLOOR_H = 3.6
ORIGIN = {"lobby": (0, 0, 0), "stairs": (-8.375, 0.5, 0), "hall": (0, 3.0, 4 * FLOOR_H), "suite": (0, 11.0, 9 * FLOOR_H),
          "petstore": (25, -8.75, 0), "street": (0, -9.5, 0)}
ROOMS, ROUTES, ANCHORS, OBJ, LIGHTS = {}, {}, {}, {}, []
SHADOW_LIGHTS = ("chandelier", "pendant", "canopy", "car_", "stair", "lamp")
_MATS, _COLL = {}, {}


# ---------------------------------------------------------------- materials (procedural, world-space)
def _lin(c): return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c[:3])


def _rgb(c): return (*_lin(c), 1.0)   # kit colours are written in sRGB (as picked); shaders want linear


def material(name, color, rough=0.6, metal=0.0, kind="plain", color2=None, scale=1.0, var=0.06, bump=0.15, emit=0.0, alpha=1.0, tile=None):
    """kind: plain | marble | wood | carpet | plaster | paver | wallpaper | glass. Textures use world position so
    nothing stretches; every surface gets value and roughness variation plus a little bump (no CG plastic)."""
    if name in _MATS: return _MATS[name]
    m = bpy.data.materials.new(name); m.use_nodes = True; m.diffuse_color = _rgb(color); m.use_fake_user = True
    nt = m.node_tree; N, Lk = nt.nodes, nt.links
    b = N["Principled BSDF"]; geo = N.new("ShaderNodeNewGeometry")
    mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (scale, scale, scale); Lk.new(geo.outputs["Position"], mp.inputs["Vector"])
    noise = N.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 4.0; noise.inputs["Detail"].default_value = 6.0
    Lk.new(mp.outputs["Vector"], noise.inputs["Vector"])
    c2 = color2 or tuple(max(0.0, x * (1 - 2 * var)) for x in color)
    ramp = N.new("ShaderNodeValToRGB"); ramp.color_ramp.elements[0].color = _rgb(c2); ramp.color_ramp.elements[1].color = _rgb(color)
    src = noise.outputs["Fac"]
    if kind == "marble":                                                   # thin wandering veins: a narrow band of a noise field
        vn = N.new("ShaderNodeTexNoise"); vn.inputs["Scale"].default_value = 1.3; vn.inputs["Detail"].default_value = 10.0
        vn.inputs["Distortion"].default_value = 1.2; Lk.new(mp.outputs["Vector"], vn.inputs["Vector"]); src = vn.outputs["Fac"]
        el = ramp.color_ramp.elements; el[0].color = _rgb(color); el[1].color = _rgb(color); el[1].position = 1.0
        for pos, cc in ((0.478, color), (0.5, c2), (0.522, color)): e = el.new(pos); e.color = _rgb(cc)
    elif kind == "wood":
        wv = N.new("ShaderNodeTexWave"); wv.inputs["Scale"].default_value = 2.5; wv.inputs["Distortion"].default_value = 3.0
        wv.inputs["Detail"].default_value = 3.0; Lk.new(mp.outputs["Vector"], wv.inputs["Vector"]); src = wv.outputs["Fac"]
    elif kind == "wallpaper":                                               # quiet vertical stripes
        wv = N.new("ShaderNodeTexWave"); wv.wave_type = "BANDS"; wv.bands_direction = "X"
        wv.inputs["Scale"].default_value = 3.0; wv.inputs["Distortion"].default_value = 0.0
        Lk.new(geo.outputs["Position"], wv.inputs["Vector"]); src = wv.outputs["Fac"]
        ramp.color_ramp.elements[0].position = 0.45; ramp.color_ramp.elements[1].position = 0.55
    Lk.new(src, ramp.inputs["Fac"]); col = ramp.outputs["Color"]
    if tile:                                                                # tiles / pavers / carpet pattern: brick texture
        br = N.new("ShaderNodeTexBrick"); Lk.new(geo.outputs["Position"], br.inputs["Vector"])
        br.inputs["Scale"].default_value = 1.0 / tile[0]; br.inputs["Mortar Size"].default_value = tile[1]
        br.inputs["Row Height"].default_value = tile[0]; br.inputs["Brick Width"].default_value = tile[0]
        br.offset = tile[3] if len(tile) > 3 else 0.0
        Lk.new(col, br.inputs["Color1"]); Lk.new(col, br.inputs["Color2"]); br.inputs["Mortar"].default_value = _rgb(tile[2])
        br.inputs["Bias"].default_value = 0.0; col = br.outputs["Color"]
    Lk.new(col, b.inputs["Base Color"])
    rr = N.new("ShaderNodeMapRange"); rr.inputs["To Min"].default_value = max(0.02, rough - 0.12); rr.inputs["To Max"].default_value = min(1.0, rough + 0.12)
    Lk.new(noise.outputs["Fac"], rr.inputs["Value"]); Lk.new(rr.outputs["Result"], b.inputs["Roughness"])
    b.inputs["Metallic"].default_value = metal
    if bump:
        bn = N.new("ShaderNodeBump"); bn.inputs["Strength"].default_value = bump; bn.inputs["Distance"].default_value = 0.02
        fine = N.new("ShaderNodeTexNoise"); fine.inputs["Scale"].default_value = 60.0 if kind in ("carpet", "plaster", "paver") else 25.0
        Lk.new(geo.outputs["Position"], fine.inputs["Vector"]); Lk.new(fine.outputs["Fac"], bn.inputs["Height"]); Lk.new(bn.outputs["Normal"], b.inputs["Normal"])
    if emit:
        b.inputs["Emission Color"].default_value = _rgb(color); b.inputs["Emission Strength"].default_value = emit
    if alpha < 1.0:
        b.inputs["Alpha"].default_value = alpha
        for attr, val in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND")):
            try: setattr(m, attr, val)
            except (AttributeError, TypeError): pass
    _MATS[name] = m
    return m


def palette():
    M = material
    return dict(
        marble=M("HK_Marble", (0.86, 0.82, 0.74), 0.3, kind="marble", color2=(0.55, 0.5, 0.45), scale=0.7, tile=(0.8, 0.004, (0.45, 0.4, 0.36)), bump=0.05),
        marble_dark=M("HK_MarbleDark", (0.13, 0.11, 0.1), 0.28, kind="marble", color2=(0.3, 0.27, 0.24), scale=0.9, bump=0.05),
        plaster=M("HK_Plaster", (0.82, 0.77, 0.68), 0.85, kind="plaster", var=0.03, bump=0.08),
        plaster_cool=M("HK_PlasterCool", (0.74, 0.73, 0.69), 0.88, kind="plaster", var=0.03, bump=0.08),
        ceiling=M("HK_Ceiling", (0.88, 0.86, 0.82), 0.9, var=0.02, bump=0.03),
        accent=M("HK_Burgundy", (0.36, 0.07, 0.1), 0.8, kind="wallpaper", color2=(0.3, 0.05, 0.08), bump=0.1),
        walnut=M("HK_Walnut", (0.3, 0.17, 0.09), 0.5, kind="wood", color2=(0.23, 0.12, 0.06), scale=1.5, bump=0.06),
        oak=M("HK_Oak", (0.55, 0.38, 0.22), 0.55, kind="wood", color2=(0.38, 0.24, 0.13), scale=1.5, bump=0.06),
        brass=M("HK_Brass", (0.8, 0.62, 0.3), 0.36, metal=1.0, var=0.05, bump=0.03),
        steel=M("HK_Steel", (0.66, 0.66, 0.68), 0.38, metal=1.0, var=0.04, bump=0.03),
        black=M("HK_BlackPaint", (0.04, 0.04, 0.045), 0.55, var=0.02),
        carpet=M("HK_Carpet", (0.34, 0.07, 0.09), 0.95, kind="carpet", color2=(0.26, 0.05, 0.07), scale=3.0, tile=(0.45, 0.005, (0.38, 0.22, 0.12), 0.5), bump=0.25),
        rug=M("HK_Rug", (0.12, 0.2, 0.26), 0.95, kind="carpet", color2=(0.08, 0.13, 0.17), scale=2.0, tile=(0.6, 0.006, (0.3, 0.26, 0.18)), bump=0.25),
        rug_warm=M("HK_RugWarm", (0.62, 0.52, 0.4), 0.95, kind="carpet", color2=(0.5, 0.4, 0.3), scale=2.5, bump=0.3),
        wallpaper=M("HK_Wallpaper", (0.72, 0.64, 0.5), 0.8, kind="wallpaper", color2=(0.66, 0.57, 0.43), bump=0.05),
        velvet=M("HK_Velvet", (0.05, 0.24, 0.26), 0.92, var=0.1, bump=0.2),
        mustard=M("HK_Mustard", (0.55, 0.37, 0.1), 0.9, var=0.1, bump=0.2),
        leather=M("HK_Leather", (0.24, 0.11, 0.05), 0.6, var=0.12, bump=0.15),
        leaf=M("HK_Leaf", (0.12, 0.28, 0.07), 0.65, color2=(0.05, 0.14, 0.04), var=0.2, bump=0.1),
        pot=M("HK_Pot", (0.1, 0.09, 0.085), 0.5, var=0.05),
        soil=M("HK_Soil", (0.09, 0.06, 0.04), 0.95),
        concrete=M("HK_Concrete", (0.55, 0.54, 0.52), 0.9, kind="plaster", var=0.08, bump=0.15),
        stairpaint=M("HK_StairPaint", (0.78, 0.77, 0.72), 0.85, var=0.03),
        stone=M("HK_Limestone", (0.64, 0.58, 0.49), 0.85, kind="plaster", color2=(0.55, 0.49, 0.41), scale=0.5, tile=(0.9, 0.008, (0.42, 0.38, 0.33)), bump=0.12),
        brick=M("HK_Brick", (0.45, 0.2, 0.14), 0.9, color2=(0.32, 0.14, 0.1), var=0.15, tile=(0.2, 0.01, (0.6, 0.57, 0.52), 0.5), bump=0.2),
        render_grey=M("HK_RenderGrey", (0.52, 0.52, 0.5), 0.9, kind="plaster", var=0.05),
        glass=M("HK_Glass", (0.6, 0.7, 0.72), 0.05, alpha=0.18, var=0.0, bump=0.0),
        winglass=M("HK_WindowGlass", (0.06, 0.08, 0.1), 0.08, metal=0.3, var=0.02, bump=0.0),
        winlit=M("HK_WindowLit", (0.95, 0.78, 0.5), 0.3, emit=1.2, var=0.0, bump=0.0),
        paver=M("HK_Paver", (0.55, 0.54, 0.51), 0.9, kind="paver", tile=(0.4, 0.01, (0.35, 0.34, 0.32), 0.5), bump=0.15),
        asphalt=M("HK_Asphalt", (0.13, 0.13, 0.135), 0.95, var=0.1, bump=0.3),
        paint_white=M("HK_RoadWhite", (0.8, 0.8, 0.76), 0.8, var=0.05),
        redcarpet=M("HK_RedCarpet", (0.45, 0.04, 0.05), 0.95, kind="carpet", bump=0.2),
        warm_light=M("HK_WarmLight", (1.0, 0.82, 0.55), 0.4, emit=6.0, var=0.0, bump=0.0),
        cool_light=M("HK_CoolLight", (0.9, 0.95, 1.0), 0.4, emit=4.0, var=0.0, bump=0.0),
        exit_green=M("HK_ExitGreen", (0.1, 0.8, 0.3), 0.4, emit=3.0, var=0.0, bump=0.0),
        sign_red=M("HK_SignRed", (0.75, 0.08, 0.06), 0.5, var=0.02),
        canvas=M("HK_Canvas", (0.55, 0.4, 0.28), 0.8, kind="marble", color2=(0.16, 0.22, 0.3), scale=0.6, var=0.2, bump=0.1),
        mirror=M("HK_Mirror", (0.85, 0.87, 0.88), 0.05, metal=1.0, var=0.0, bump=0.0),
        night_city=M("HK_NightCity", (0.03, 0.04, 0.09), 0.9, var=0.05, bump=0.0, emit=0.3),
        green_shop=M("HK_ShopGreen", (0.12, 0.38, 0.16), 0.7, var=0.05),
        fabric_white=M("HK_Linen", (0.9, 0.88, 0.84), 0.9, var=0.03, bump=0.1),
    )


# ---------------------------------------------------------------- mesh builder: many parts -> one object
class MB:
    def __init__(self, name, coll):
        self.name, self.coll, self.bm, self.mats, self.smooth = name, coll, bmesh.new(), [], []

    def _fin(self, verts, mat, smooth=False):
        if mat not in self.mats: self.mats.append(mat)
        k = self.mats.index(mat)
        for f in {f for v in verts for f in v.link_faces}:
            f.material_index = k; f.smooth = smooth

    def box(self, mn, mx, mat):
        c = [(a + b) / 2 for a, b in zip(mn, mx)]; s = [abs(b - a) for a, b in zip(mn, mx)]
        if min(s) <= 0: return
        r = bmesh.ops.create_cube(self.bm, size=1.0, matrix=Matrix.Translation(c) @ Matrix.Diagonal((*s, 1)))
        self._fin(r["verts"], mat)

    def cyl(self, c, r, h, mat, axis="Z", seg=16, r2=None, smooth=True):
        rot = {"Z": Matrix(), "X": Matrix.Rotation(math.pi / 2, 4, "Y"), "Y": Matrix.Rotation(math.pi / 2, 4, "X")}[axis]
        out = bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r, radius2=r if r2 is None else r2,
                                    depth=h, matrix=Matrix.Translation(c) @ rot)
        self._fin(out["verts"], mat, smooth)

    def rod(self, a, b, r, mat, seg=8):
        a, b = Vector(a), Vector(b); d = b - a
        q = Vector((0, 0, 1)).rotation_difference(d.normalized())
        out = bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r, radius2=r, depth=d.length,
                                    matrix=Matrix.Translation((a + b) / 2) @ q.to_matrix().to_4x4())
        self._fin(out["verts"], mat, True)

    def sphere(self, c, r, mat, scale=(1, 1, 1), rot=(0, 0, 0), seg=12):
        M = Matrix.Translation(c) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((*scale, 1))
        out = bmesh.ops.create_uvsphere(self.bm, u_segments=seg, v_segments=max(4, seg // 2), radius=r, matrix=M)
        self._fin(out["verts"], mat, True)

    def done(self, bevel=0.0, parent=None):
        me = bpy.data.meshes.new(self.name); self.bm.to_mesh(me); self.bm.free()
        for m in self.mats: me.materials.append(m)
        ob = bpy.data.objects.new(self.name, me); self.coll.objects.link(ob)
        if parent: ob.parent = parent
        if bevel:
            md = ob.modifiers.new("Bevel", "BEVEL"); md.width = bevel; md.segments = 2; md.limit_method = "ANGLE"
            md.harden_normals = False
        return ob


def coll(name, parent=None):
    if name in _COLL: return _COLL[name]
    c = bpy.data.collections.new(name); (parent or bpy.context.scene.collection).children.link(c); _COLL[name] = c
    return c


def empty(name, loc, c, rot=(0, 0, 0)):
    e = bpy.data.objects.new(name, None); c.objects.link(e); e.location = loc; e.rotation_euler = rot; return e


def text(body, loc, size, mat, c, rot=(math.pi / 2, 0, 0), name=None, extrude=0.008, align="CENTER", parent=None):
    cu = bpy.data.curves.new(name or f"TXT_{body[:10]}", "FONT"); cu.body = body; cu.size = size; cu.extrude = extrude
    cu.align_x = align; cu.align_y = "CENTER"; cu.materials.append(mat)
    o = bpy.data.objects.new(name or f"TXT_{body[:10]}", cu); c.objects.link(o); o.location = loc; o.rotation_euler = rot
    if parent: o.parent = parent
    return o


def facing_rot(n):
    """Text rotation for a sign whose readable face points along n (one of +-X, +-Y)."""
    return (math.pi / 2, 0, {(0, -1): 0, (0, 1): math.pi, (1, 0): math.pi / 2, (-1, 0): -math.pi / 2}[n])


def light(name, kind, loc, energy, color=(1.0, 0.85, 0.65), size=0.2, aim=None, c=None):
    L = bpy.data.lights.new(name, kind); L.energy = energy; L.color = color
    L.use_shadow = any(k in name for k in SHADOW_LIGHTS)                     # shortcut: fills skip shadows (render time); add names to SHADOW_LIGHTS for more
    if kind == "AREA": L.size = size
    else: L.shadow_soft_size = size
    o = bpy.data.objects.new(name, L); (c or bpy.context.scene.collection).objects.link(o); o.location = loc
    if aim is not None: o.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    LIGHTS.append(o); return o


# ---------------------------------------------------------------- architecture
def _bx(mb, axis, s0, s1, c0, c1, z0, z1, mat):
    if axis == "x": mb.box((s0, min(c0, c1), z0), (s1, max(c0, c1), z1), mat)
    else: mb.box((min(c0, c1), s0, z0), (max(c0, c1), s1, z1), mat)


def wall(mb, axis, c, a, b, z0, h, mat, inside=1, openings=(), t=0.25, trim=None):
    """A straight wall along `axis` ('x': at y=c, 'y': at x=c) from a to b. The interior face sits on c and the
    body extends away from the room (inside=+1: the room is on the + side). openings: [(s0, s1, top)] in
    absolute coordinates along the wall. trim: dict(base=mat, crown=mat, rail=mat, panel=mat) on the room side."""
    c_out = c - inside * t
    ops = sorted(openings); cur = a; spans = []
    for o0, o1, top in ops:
        if o0 > cur: spans.append((cur, o0))
        _bx(mb, axis, o0, o1, c_out, c, z0 + top, z0 + h, mat)                # lintel
        cur = max(cur, o1)
    if cur < b: spans.append((cur, b))
    for s0, s1 in spans: _bx(mb, axis, s0, s1, c_out, c, z0, z0 + h, mat)
    if not trim: return
    p = lambda d: (c, c + inside * d)
    for s0, s1 in spans:
        if trim.get("base"): _bx(mb, axis, s0, s1, *p(0.02), z0, z0 + 0.14, trim["base"])
        if trim.get("rail"): _bx(mb, axis, s0, s1, *p(0.035), z0 + 0.95, z0 + 1.0, trim["rail"])
        if trim.get("panel") and s1 - s0 > 0.9:                              # wainscot panel mouldings below the rail
            n = max(1, int((s1 - s0) / 1.1)); w = (s1 - s0) / n
            for k in range(n):
                q0, q1 = s0 + k * w + 0.12, s0 + (k + 1) * w - 0.12
                for (u0, u1, v0, v1) in ((q0, q1, 0.28, 0.31), (q0, q1, 0.78, 0.81), (q0, q0 + 0.03, 0.28, 0.81), (q1 - 0.03, q1, 0.28, 0.81)):
                    _bx(mb, axis, u0, u1, *p(0.015), z0 + v0, z0 + v1, trim["panel"])
    if trim.get("crown"): _bx(mb, axis, a, b, *p(0.06), z0 + h - 0.16, z0 + h, trim["crown"])


def room(name, x0, y0, x1, y1, z0, h, P, floor, wallm, ceil, walls, trim=None, c=None, slab=0.25):
    """Floor + ceiling + up to four walls (walls: dict side -> openings list, or None to skip a shared wall)."""
    mb = MB(f"ARCH_{name}", c)
    mb.box((x0 - 0.25, y0 - 0.25, z0 - slab), (x1 + 0.25, y1 + 0.25, z0), floor)
    if ceil: mb.box((x0 - 0.25, y0 - 0.25, z0 + h), (x1 + 0.25, y1 + 0.25, z0 + h + slab), ceil)
    for side, ops in walls.items():
        if ops is None: continue
        if side == "s": wall(mb, "x", y0, x0 - 0.25, x1 + 0.25, z0, h, wallm, 1, ops, trim=trim)
        if side == "n": wall(mb, "x", y1, x0 - 0.25, x1 + 0.25, z0, h, wallm, -1, ops, trim=trim)
        if side == "w": wall(mb, "y", x0, y0, y1, z0, h, wallm, 1, ops, trim=trim)
        if side == "e": wall(mb, "y", x1, y0, y1, z0, h, wallm, -1, ops, trim=trim)
    ROOMS[name] = (Vector((x0, y0, z0)), Vector((x1, y1, z0 + h)))
    return mb


def door(name, axis, c, s, z0, P, c_, w=0.95, h=2.15, face=1, kind="wood", number=None, open_deg=0.0, t=0.25):
    """Door in a wall opening (axis/c as wall(); s = centre along the wall). Casing on both faces, a leaf hinged
    on one jamb (open_deg swings it into the +face side), handle and number plate on the `face` side."""
    mb = MB(f"DOOR_{name}", c_)
    lo, hi = s - w / 2, s + w / 2
    for sg in (1, -1):                                                         # casings on both wall faces
        cc = c if sg == face else c - face * t
        q = (cc, cc + sg * 0.03) if sg == face else (cc, cc - face * 0.03)
        _bx(mb, axis, lo - 0.09, lo, *q, z0, z0 + h + 0.09, P["walnut"] if kind != "stair" else P["steel"])
        _bx(mb, axis, hi, hi + 0.09, *q, z0, z0 + h + 0.09, P["walnut"] if kind != "stair" else P["steel"])
        _bx(mb, axis, lo - 0.09, hi + 0.09, *q, z0 + h, z0 + h + 0.09, P["walnut"] if kind != "stair" else P["steel"])
    frame = mb.done()
    hinge = (lo, c - face * t / 2) if axis == "x" else (c - face * t / 2, lo)
    piv = empty(f"PIV_{name}", (hinge[0], hinge[1], z0), c_)
    lf = MB(f"LEAF_{name}", c_); m = P["walnut"] if kind == "wood" else (P["steel"] if kind == "stair" else P["glass"])
    if axis == "x":
        lf.box((0.005, -0.022, 0.005), (w - 0.005, 0.022, h - 0.005), m)
        lf.box((w - 0.12, face * 0.022, 1.0), (w - 0.08, face * 0.06, 1.04), P["brass"])
        if kind == "wood":
            for (u0, u1, v0, v1) in ((0.12, w - 0.12, 0.25, 0.95), (0.12, w - 0.12, 1.15, h - 0.2)):
                lf.box((u0, face * 0.022, v0), (u1, face * 0.032, v1), P["oak"])
    else:
        lf.box((-0.022, 0.005, 0.005), (0.022, w - 0.005, h - 0.005), m)
        lf.box((face * 0.022, w - 0.12, 1.0), (face * 0.06, w - 0.08, 1.04), P["brass"])
        if kind == "wood":
            for (u0, u1, v0, v1) in ((0.12, w - 0.12, 0.25, 0.95), (0.12, w - 0.12, 1.15, h - 0.2)):
                lf.box((face * 0.022, u0, v0), (face * 0.032, u1, v1), P["oak"])
    leaf = lf.done(parent=piv); piv.rotation_euler.z = math.radians(open_deg) * (face if axis == "x" else -face)
    if number:
        n = (0, face) if axis == "x" else (face, 0)
        loc = (s, c + face * 0.04, z0 + 1.6) if axis == "x" else (c + face * 0.04, s, z0 + 1.6)
        text(str(number), loc, 0.11, P["brass"], c_, rot=facing_rot(n), name=f"TXT_room_{number}")
    return dict(frame=frame, leaf=leaf, pivot=piv)


def elevator(name, center_y, x_wall, z0, P, c_, vip=False, w=1.1, h=2.3):
    """Elevator on a wall at x = x_wall facing -X: brushed steel (or brass for VIP) sliding doors, frame, call panel,
    floor indicator, and the car behind it (2 m deep) with wood walls, mirror, handrail and a ceiling light.
    Returns dict(left, right, closed=(yl, yr), car) - key doors with key_doors()."""
    root = empty(f"ELEV_{name}", (x_wall, center_y, z0), c_); m = P["brass"] if vip else P["steel"]
    fr = MB(f"ELEVFRAME_{name}", c_)
    fr.box((x_wall - 0.04, center_y - w / 2 - 0.16, z0), (x_wall + 0.02, center_y - w / 2, z0 + h + 0.16), m)
    fr.box((x_wall - 0.04, center_y + w / 2, z0), (x_wall + 0.02, center_y + w / 2 + 0.16, z0 + h + 0.16), m)
    fr.box((x_wall - 0.04, center_y - w / 2 - 0.16, z0 + h), (x_wall + 0.02, center_y + w / 2 + 0.16, z0 + h + 0.16), m)
    fr.box((x_wall - 0.05, center_y - 0.3, z0 + h + 0.25), (x_wall - 0.01, center_y + 0.3, z0 + h + 0.5), P["black"])   # indicator
    fr.box((x_wall - 0.03, center_y + w / 2 + 0.3, z0 + 1.0), (x_wall, center_y + w / 2 + 0.42, z0 + 1.3), m)            # call panel
    fr.sphere((x_wall - 0.035, center_y + w / 2 + 0.36, z0 + 1.2), 0.025, P["warm_light"])
    # car
    cx0, cx1 = x_wall + 0.25, x_wall + 2.05; cy0, cy1 = center_y - 0.9, center_y + 0.9
    fr.box((x_wall, cy0 - 0.1, z0 - 0.2), (cx1 + 0.2, cy1 + 0.1, z0), P["marble_dark"])
    fr.box((x_wall, cy0 - 0.1, z0 + 2.6), (cx1 + 0.2, cy1 + 0.1, z0 + 2.8), P["ceiling"])
    for (a, b) in (((x_wall, cy0 - 0.1), (cx1 + 0.2, cy0)), ((x_wall, cy1), (cx1 + 0.2, cy1 + 0.1)), ((cx1, cy0), (cx1 + 0.2, cy1))):
        fr.box((*a, z0), (*b, z0 + 2.6), P["walnut"])
    fr.box((cx1 - 0.01, cy0 + 0.3, z0 + 0.9), (cx1, cy1 - 0.3, z0 + 2.2), P["mirror"])
    for y in (cy0 + 0.06, cy1 - 0.06): fr.rod((cx0, y, z0 + 0.95), (cx1 - 0.05, y, z0 + 0.95), 0.02, P["brass"])
    fr.box((cx0 + 0.3, cy0 + 0.4, z0 + 2.58), (cx1 - 0.3, cy1 - 0.4, z0 + 2.6), P["warm_light"])
    frame = fr.done()
    text("9" if vip else "1", (x_wall - 0.055, center_y, z0 + h + 0.375), 0.18, P["warm_light"], c_, rot=facing_rot((-1, 0)), name=f"TXT_elev_{name}")
    ROOMS[f"car_{name}"] = (Vector((cx0, cy0, z0)), Vector((cx1, cy1, z0 + 2.6)))
    light(f"LGT_car_{name}", "AREA", ((cx0 + cx1) / 2, center_y, z0 + 2.5), 60, (1.0, 0.86, 0.66), 0.8, aim=((cx0 + cx1) / 2, center_y, 0), c=c_)
    leaves = []
    for k, sg in enumerate((-1, 1)):
        lf = MB(f"ELEVDOOR_{name}_{k}", c_)
        lf.box((-0.03, -w / 4 + 0.003, 0), (0.03, w / 4 - 0.003, h), m)
        ob = lf.done(); ob.location = (x_wall + 0.06, center_y + sg * w / 4, z0); leaves.append(ob)
    return dict(root=root, frame=frame, left=leaves[0], right=leaves[1], closed=(center_y - w / 4, center_y + w / 4), w=w)


def key_doors(e, frame, openness):
    """Key elevator doors at a frame: openness 0 = closed, 1 = fully open (leaves slide behind the frame)."""
    for ob, yc, sg in ((e["left"], e["closed"][0], -1), (e["right"], e["closed"][1], 1)):
        ob.location.y = yc + sg * openness * e["w"] / 2; ob.keyframe_insert("location", index=1, frame=frame)


# ---------------------------------------------------------------- furniture & props
def plant(name, at, P, c_, size=1.0, kind="palm", seed=0):
    import random
    rnd = random.Random(f"{name}{seed}"); mb = MB(f"PLANT_{name}", c_); x, y, z = at
    mb.cyl((x, y, z + 0.28 * size), 0.24 * size, 0.56 * size, P["pot"], r2=0.3 * size, seg=20)
    mb.cyl((x, y, z + 0.55 * size), 0.27 * size, 0.03, P["soil"], seg=20)
    if kind == "palm":
        mb.rod((x, y, z + 0.5 * size), (x + 0.04, y, z + 1.3 * size), 0.035 * size, P["walnut"])
        for k in range(14):
            a = k / 14 * 2 * math.pi + rnd.uniform(-0.2, 0.2); tilt = rnd.uniform(0.55, 1.15)
            L = rnd.uniform(0.55, 0.8) * size; top = Vector((x + 0.04, y, z + 1.3 * size))
            d = Vector((math.cos(a) * math.sin(tilt), math.sin(a) * math.sin(tilt), math.cos(tilt) * 0.6)).normalized()
            mb.sphere(top + d * L * 0.5, L * 0.5, P["leaf"], scale=(1, 0.16, 0.035),
                      rot=(0, -math.atan2(d.z, math.hypot(d.x, d.y)), a), seg=10)
    else:                                                                       # bushy fern/topiary
        for k in range(22 if kind == "fern" else 1):
            if kind == "topiary":
                mb.sphere((x, y, z + 1.15 * size), 0.45 * size, P["leaf"], seg=16); break
            a = rnd.uniform(0, 2 * math.pi); r = rnd.uniform(0.0, 0.28) * size
            mb.sphere((x + r * math.cos(a), y + r * math.sin(a), z + rnd.uniform(0.75, 1.15) * size), 0.32 * size, P["leaf"],
                      scale=(1, 0.3, 0.12), rot=(rnd.uniform(-0.6, 0.6), rnd.uniform(-0.6, 0.6), a), seg=10)
    return mb.done()


def sofa(name, at, rot, P, c_, length=2.0, fabric="velvet"):
    root = empty(f"SOFA_{name}", at, c_, (0, 0, rot)); mb = MB(f"SM_Sofa_{name}", c_); L = length / 2; f = P[fabric]
    mb.box((-L, -0.45, 0.12), (L, 0.45, 0.42), f)                               # seat base (front = -Y local)
    mb.box((-L, 0.2, 0.42), (L, 0.45, 0.88), f)                                 # back
    for sx in (-1, 1): mb.box((sx * L - (0.18 if sx > 0 else 0), -0.45, 0.12), (sx * L + (0.0 if sx > 0 else 0.18), 0.45, 0.66), f)
    for k in range(int(length // 0.65)):
        x0 = -L + 0.2 + k * ((length - 0.4) / int(length // 0.65))
        mb.box((x0 + 0.02, -0.42, 0.42), (x0 + (length - 0.4) / int(length // 0.65) - 0.02, 0.18, 0.55), f)
    for sx in (-1, 1):
        for sy in (-1, 1): mb.cyl((sx * (L - 0.08), sy * 0.35, 0.06), 0.025, 0.12, P["brass"], seg=8)
    mb.done(bevel=0.03, parent=root); return root


def armchair(name, at, rot, P, c_, fabric="mustard"):
    return sofa(name, at, rot, P, c_, length=0.95, fabric=fabric)


def table(name, at, P, c_, w=1.1, d=0.6, h=0.42, top="marble_dark", lamp=False):
    mb = MB(f"SM_Table_{name}", c_); x, y, z = at
    mb.box((x - w / 2, y - d / 2, z + h - 0.04), (x + w / 2, y + d / 2, z + h), P[top])
    for sx in (-1, 1):
        for sy in (-1, 1): mb.box((x + sx * (w / 2 - 0.06) - 0.02, y + sy * (d / 2 - 0.06) - 0.02, z), (x + sx * (w / 2 - 0.06) + 0.02, y + sy * (d / 2 - 0.06) + 0.02, z + h - 0.04), P["brass"])
    if lamp:
        mb.cyl((x, y, z + h + 0.18), 0.06, 0.36, P["brass"], r2=0.03)
        mb.cyl((x, y, z + h + 0.5), 0.2, 0.24, P["fabric_white"], r2=0.14, seg=20)
        light(f"LGT_lamp_{name}", "POINT", (x, y, z + h + 0.5), 35, (1.0, 0.78, 0.5), 0.12, c=c_)
    mb.box((x - 0.12, y - 0.1, z + h), (x + 0.1, y + 0.08, z + h + 0.03), P["sign_red"]) if not lamp and w > 0.8 else None  # a book
    return mb.done(bevel=0.008)


def rug(name, x0, y0, x1, y1, z, P, c_):
    mb = MB(f"SM_Rug_{name}", c_); mb.box((x0, y0, z), (x1, y1, z + 0.012), P["rug"]); return mb.done()


def column(name, at, r, h, P, c_):
    mb = MB(f"SM_Column_{name}", c_); x, y, z = at
    mb.box((x - r - 0.08, y - r - 0.08, z), (x + r + 0.08, y + r + 0.08, z + 0.3), P["marble_dark"])
    mb.cyl((x, y, z + h / 2), r, h - 0.6, P["plaster"], seg=24)
    mb.box((x - r - 0.1, y - r - 0.1, z + h - 0.3), (x + r + 0.1, y + r + 0.1, z + h), P["plaster"])
    mb.cyl((x, y, z + h - 0.36), r + 0.04, 0.06, P["brass"], seg=24)
    return mb.done(bevel=0.01)


def chandelier(name, at, P, c_, r=0.7, energy=700):
    mb = MB(f"SM_Chandelier_{name}", c_); x, y, z = at
    mb.rod((x, y, z + 1.2), (x, y, z + 0.25), 0.02, P["brass"])
    for ring, rr in ((0.0, r), (0.35, r * 0.65)):
        mb.cyl((x, y, z + ring), rr, 0.04, P["brass"], seg=28)
        n = int(rr * 18)
        for k in range(n):
            a = k / n * 2 * math.pi
            mb.sphere((x + rr * math.cos(a), y + rr * math.sin(a), z + ring - 0.12), 0.045, P["warm_light"], scale=(1, 1, 1.6), seg=8)
    mb.sphere((x, y, z - 0.2), 0.16, P["warm_light"], scale=(1, 1, 1.4), seg=12)
    light(f"LGT_chandelier_{name}", "POINT", (x, y, z - 0.15), energy, (1.0, 0.8, 0.52), 0.45, c=c_)
    return mb.done()


def sconce(name, at, n, P, c_, energy=45):
    """Wall light: plate on the wall, warm shade; n = direction away from the wall."""
    mb = MB(f"SM_Sconce_{name}", c_); x, y, z = at; nx, ny = n
    hx, hy = (0.03, 0.07) if nx else (0.07, 0.03)
    mb.box((x - hx, y - hy, z - 0.12), (x + hx, y + hy, z + 0.12), P["brass"])
    mb.cyl((x + nx * 0.12, y + ny * 0.12, z + 0.05), 0.09, 0.16, P["warm_light"], r2=0.06, seg=16)
    light(f"LGT_sconce_{name}", "POINT", (x + nx * 0.2, y + ny * 0.2, z + 0.05), energy, (1.0, 0.78, 0.5), 0.1, c=c_)
    return mb.done()


def art(name, at, n, w, h, P, c_):
    mb = MB(f"SM_Art_{name}", c_); x, y, z = at; nx, ny = n; d = 0.04
    if nx: mb.box((x, y - w / 2 - 0.06, z - h / 2 - 0.06), (x + nx * d, y + w / 2 + 0.06, z + h / 2 + 0.06), P["brass"]); mb.box((x + nx * d, y - w / 2, z - h / 2), (x + nx * (d + 0.005), y + w / 2, z + h / 2), P["canvas"])
    else: mb.box((x - w / 2 - 0.06, y, z - h / 2 - 0.06), (x + w / 2 + 0.06, y + ny * d, z + h / 2 + 0.06), P["brass"]); mb.box((x - w / 2, y + ny * d, z - h / 2), (x + w / 2, y + ny * (d + 0.005), z + h / 2), P["canvas"])
    return mb.done()


def trolley(name, P, c_):
    """Brass birdcage luggage trolley (origin on the floor, centre). Returns its root empty."""
    root = empty(name, (0, 0, 0), c_); mb = MB(f"SM_Trolley_{name}", c_)
    mb.box((-0.62, -0.32, 0.1), (0.62, 0.32, 0.16), P["walnut"]); mb.box((-0.6, -0.3, 0.16), (0.6, 0.3, 0.175), P["redcarpet"])
    for sx in (-1, 1):
        for sy in (-1, 1): mb.cyl((sx * 0.5, sy * 0.24, 0.05), 0.05, 0.035, P["black"], axis="Y", seg=12)
        mb.rod((sx * 0.56, -0.26, 0.16), (sx * 0.56, -0.26, 1.85), 0.022, P["brass"]); mb.rod((sx * 0.56, 0.26, 0.16), (sx * 0.56, 0.26, 1.85), 0.022, P["brass"])
        mb.rod((sx * 0.56, -0.26, 1.85), (sx * 0.56, 0.26, 1.85), 0.022, P["brass"])
    mb.rod((-0.56, 0, 1.95), (0.56, 0, 1.95), 0.025, P["brass"])
    for sx in (-1, 1): mb.rod((sx * 0.56, -0.26, 1.85), (sx * 0.56, 0, 1.95), 0.02, P["brass"]); mb.rod((sx * 0.56, 0.26, 1.85), (sx * 0.56, 0, 1.95), 0.02, P["brass"])
    mb.done(bevel=0.005, parent=root); return root


def sign(body, loc, n, size, P, c_, plate=None, mat="brass", name=None):
    """Lettering facing n; optional backing plate (w, h, material key)."""
    x, y, z = loc
    if plate:
        w, h, pm = plate; mb = MB(f"SM_SignPlate_{name or body[:8]}", c_)
        if n[0]: mb.box((x - n[0] * 0.03, y - w / 2, z - h / 2), (x, y + w / 2, z + h / 2), P[pm])
        else: mb.box((x - w / 2, y - n[1] * 0.03, z - h / 2), (x + w / 2, y, z + h / 2), P[pm])
        mb.done()
    return text(body, (x + n[0] * 0.006, y + n[1] * 0.006, z), size, P[mat], c_, rot=facing_rot(n), name=name)


# ---------------------------------------------------------------- the Grand Aurelia
def grand_aurelia(floors=9, corridor_floors=(4, 9)):
    """Build the whole hotel + street. Returns dict(origin, rooms, routes, anchors, obj, elevators)."""
    P = palette(); H = coll("HOTEL")
    C = {k: coll(f"HOTEL_{k}", H) for k in ("exterior", "street", "lobby", "elevators", "stairs", "floors", "suite", "petstore", "lights")}
    trimL = dict(base=P["walnut"], rail=P["walnut"], panel=P["walnut"], crown=P["plaster"])
    trimC = dict(base=P["walnut"], rail=P["walnut"], crown=P["ceiling"])

    # ---- lobby (5 m): entrance south, desk north, stairs door west, elevator opening east
    mb = room("lobby", -7, -7, 7, 5, 0, 5, P, P["marble"], P["plaster"], P["ceiling"],
              dict(w=[(-1.0, 0.0, 2.2)], e=[(-0.6, 3.2, 3.4)], n=None, s=None), trim=trimL, c=C["lobby"])
    wall(mb, "x", 5.0, -7.25, 7.25, 0, 5, P["accent"], -1, [(3.2, 4.2, 2.2)], trim=dict(base=P["walnut"], crown=P["plaster"]))
    mb.box((-6.75, -6.75, 0.0), (6.75, -6.35, 0.004), P["marble_dark"]); mb.box((-6.75, 4.35, 0.0), (6.75, 4.75, 0.004), P["marble_dark"])
    mb.box((-6.75, -6.75, 0.0), (-6.35, 4.75, 0.004), P["marble_dark"]); mb.box((6.35, -6.75, 0.0), (6.75, 4.75, 0.004), P["marble_dark"])
    mb.cyl((0, -2.5, 0.002), 1.6, 0.004, P["marble_dark"], seg=48, smooth=False); mb.cyl((0, -2.5, 0.004), 1.35, 0.004, P["marble"], seg=48, smooth=False)
    mb.box((-3.2, -5.5, 4.75), (3.2, 0.5, 5.0), P["ceiling"])                                    # coffer frame around the chandelier
    for x0, x1, y0, y1 in ((-3.2, 3.2, -5.5, -5.3), (-3.2, 3.2, 0.3, 0.5), (-3.2, -3.0, -5.5, 0.5), (3.0, 3.2, -5.5, 0.5)):
        mb.box((x0, y0, 4.62), (x1, y1, 4.75), P["plaster"])
    mb.done()
    lob = C["lobby"]
    for x in (-4.5, 4.5): column(f"L{x:+.0f}", (x, -1.5, 0), 0.35, 5.0, P, lob)
    sign("THE GRAND AURELIA", (0, 4.97, 3.5), (0, -1), 0.42, P, lob, name="TXT_GrandAurelia_back")
    sign("RECEPTION", (0, 1.58, 0.82), (0, -1), 0.13, P, lob, name="TXT_reception")
    sign("ELEVATORS", (6.98, 1.3, 3.75), (-1, 0), 0.24, P, lob, plate=(2.6, 0.5, "black"), name="TXT_elevators")
    sign("STAIRS", (-6.98, -0.5, 2.55), (1, 0), 0.14, P, lob, plate=(1.0, 0.28, "black"), name="TXT_stairs")
    sign("EXIT", (-6.97, -0.5, 2.95), (1, 0), 0.1, P, lob, plate=(0.4, 0.18, "black"), mat="exit_green", name="TXT_exit_lobby")
    # reception desk: walnut fluted front, marble top (1.16 m), brass kick; back counter + key wall
    root = empty("DESK", (0, 2.0, 0), lob); mb = MB("SM_Desk", lob)
    mb.box((-2.2, -0.4, 0.0), (2.2, 0.4, 1.12), P["walnut"])
    for k in range(22): mb.box((-2.15 + k * 0.2, -0.43, 0.1), (-2.05 + k * 0.2, -0.4, 1.06), P["oak"])
    mb.box((-2.2, -0.44, 0.0), (2.2, -0.4, 0.1), P["brass"])
    mb.box((-2.3, -0.48, 1.12), (2.3, 0.48, 1.16), P["marble"])
    mb.box((1.0, 0.1, 1.16), (1.5, 0.14, 1.5), P["black"]); mb.box((1.05, 0.095, 1.2), (1.45, 0.1, 1.46), P["cool_light"])
    mb.box((1.05, -0.15, 1.16), (1.45, 0.02, 1.18), P["black"]); mb.sphere((-1.0, -0.25, 1.19), 0.05, P["brass"], scale=(1, 1, 0.7))
    mb.box((-1.6, 0.05, 1.16), (-1.35, 0.25, 1.2), P["black"]); mb.box((-1.75, -0.3, 1.16), (-1.55, -0.18, 1.35), P["walnut"])  # phone, brochures
    desk = mb.done(bevel=0.01, parent=root)
    mb = MB("SM_BackCounter", lob)
    mb.box((-3.2, 3.95, 0), (3.2, 4.6, 0.95), P["walnut"]); mb.box((-3.25, 3.9, 0.95), (3.25, 4.65, 0.99), P["marble_dark"])
    for k in range(8): mb.box((-3.1 + k * 0.8, 3.93, 0.15), (-2.4 + k * 0.8, 3.95, 0.85), P["oak"])
    for i in range(9):                                                          # key / mail pigeonholes
        for j in range(3): mb.box((-1.8 + i * 0.4, 4.85, 1.5 + j * 0.3), (-1.45 + i * 0.4, 4.98, 1.75 + j * 0.3), P["walnut"])
    mb.done(bevel=0.006)
    for x in (-1.4, 0.0, 1.4):                                                  # pendants over the desk
        m2 = MB(f"SM_Pendant_{x:+.1f}", lob); m2.rod((x, 2.0, 5.0), (x, 2.0, 2.75), 0.008, P["black"])
        m2.cyl((x, 2.0, 2.65), 0.17, 0.22, P["brass"], r2=0.07, seg=20); m2.sphere((x, 2.0, 2.55), 0.06, P["warm_light"]); m2.done()
        light(f"LGT_pendant_{x:+.1f}", "POINT", (x, 2.0, 2.5), 70, (1.0, 0.8, 0.55), 0.1, c=lob)
    chandelier("lobby", (0, -2.5, 3.9), P, lob)
    # seating areas (west + east), rugs, side tables with lamps, art
    for sx in (-1, 1):
        x = sx * 5.0
        rug(f"seat{sx}", x - 1.4, -5.6, x + 1.4, -2.6, 0.0, P, lob)
        sofa(f"seat{sx}", (sx * 6.35, -4.1, 0), -sx * math.pi / 2, P, lob, 2.2)            # faces the room
        for y in (-5.0, -3.2): armchair(f"seat{sx}{y}", (sx * 3.8, y, 0), sx * math.pi / 2, P, lob)  # faces the sofa
        table(f"coffee{sx}", (x, -4.1, 0), P, lob)
        table(f"side{sx}", (sx * 6.35, -5.55, 0), P, lob, 0.45, 0.45, 0.55, lamp=True)
        art(f"lobby{sx}", (sx * 6.99, -4.1, 2.6), (-sx, 0), 2.0, 1.3, P, lob)
        for y in (-5.8, -2.4): sconce(f"lobby{sx}{y}", (sx * 6.99, y, 2.5), (-sx, 0), P, lob)
    for k, (x, y, s, kd) in enumerate(((-6.3, -6.3, 1.3, "palm"), (6.3, -6.3, 1.3, "palm"), (-6.3, 4.3, 1.2, "palm"), (6.3, 4.3, 1.2, "palm"),
                                       (-3.0, 1.9, 0.9, "fern"), (3.0, 1.9, 0.9, "fern"), (6.55, -1.15, 1.1, "palm"), (6.55, 3.75, 1.1, "palm"),
                                       (-2.4, -6.55, 0.9, "fern"), (2.4, -6.55, 0.9, "fern"))):
        plant(f"lobby{k}", (x, y, 0), P, lob, s, kd, seed=k)
    light("LGT_lobby_fill", "AREA", (0, -1.0, 4.85), 260, (1.0, 0.9, 0.78), 6.0, aim=(0, -1.0, 0), c=lob)
    light("LGT_desk_fill", "AREA", (0, 3.3, 4.85), 140, (1.0, 0.88, 0.72), 3.0, aim=(0, 3.3, 0), c=lob)

    # ---- elevator lobby + cars
    el = C["elevators"]
    mb = room("elevator_lobby", 7.25, -1.2, 10.6, 3.8, 0, 3.6, P, P["marble"], P["wallpaper"], P["ceiling"],
              dict(w=None, e=[(-0.4, 0.8, 2.3), (1.9, 3.1, 2.3)], n=[], s=[]), trim=trimC, c=el)    # west = the lobby wall
    mb.done()
    E = {"std": elevator("std", 0.2, 10.6, 0, P, el), "vip": elevator("vip", 2.5, 10.6, 0, P, el, vip=True)}
    for e in E.values(): key_doors(e, 1, 1.0)                                    # open by default; shots key them
    sign("VIP ONLY", (10.59, 2.5, 3.05), (-1, 0), 0.16, P, el, plate=(1.3, 0.3, "black"), name="TXT_vip")
    sign("GUESTS", (10.59, 0.2, 3.05), (-1, 0), 0.12, P, el, plate=(1.0, 0.24, "black"), name="TXT_guests")
    m2 = MB("SM_VipStanchions", el)
    for y in (1.75, 3.25):
        m2.cyl((9.95, y, 0.03), 0.16, 0.06, P["brass"], seg=16); m2.rod((9.95, y, 0.05), (9.95, y, 0.95), 0.025, P["brass"]); m2.sphere((9.95, y, 0.98), 0.045, P["brass"])
    m2.done()
    table("elev_console", (8.9, 3.55, 0), P, el, 1.2, 0.35, 0.85, top="marble_dark", lamp=True)
    art("elev", (8.9, 3.79, 1.75), (0, -1), 1.0, 0.8, P, el); plant("elev", (7.75, 3.4, 0), P, el, 0.9, "fern", 3)
    sconce("elevS", (8.9, -1.19, 2.3), (0, 1), P, el, 40)
    light("LGT_elev_lobby", "AREA", (8.9, 1.3, 3.5), 160, (1.0, 0.9, 0.75), 2.5, aim=(8.9, 1.3, 0), c=el)

    # ---- stairwell: switchback flights, one module per floor, instanced up the building
    st = C["stairs"]; mod = bpy.data.collections.new("KIT_StairFloor")
    sx0, sx1, sy0, sy1 = -11.3, -7.5, -1.3, 5.3
    mb = MB("STAIR_module", mod)
    mb.box((sx0, sy0, -0.25), (sx1, 0.5, 0.0), P["concrete"])                                    # floor landing
    mb.box((sx0, 3.5, 1.55), (sx1, sy1, 1.8), P["concrete"])                                       # mid landing
    AX0, AX1, BX0, BX1 = -9.05, -7.7, -11.1, -9.75                                 # flights 1.35 m, an open 0.7 m well between them
    for k in range(10):
        mb.box((AX0, 0.5 + 0.3 * k, 0.18 * (k + 1) - 0.4), (AX1, 0.5 + 0.3 * (k + 1), 0.18 * (k + 1)), P["concrete"])
        mb.box((AX0, 0.5 + 0.3 * k, 0.18 * (k + 1)), (AX1, 0.5 + 0.3 * k + 0.04, 0.18 * (k + 1) + 0.004), P["black"])   # nosing
        mb.box((BX0, 3.5 - 0.3 * (k + 1), 1.8 + 0.18 * (k + 1) - 0.4), (BX1, 3.5 - 0.3 * k, 1.8 + 0.18 * (k + 1)), P["concrete"])
        mb.box((BX0, 3.5 - 0.3 * k - 0.04, 1.8 + 0.18 * (k + 1)), (BX1, 3.5 - 0.3 * k, 1.8 + 0.18 * (k + 1) + 0.004), P["black"])
    for k in range(0, 11, 2):                                                     # balusters on both well edges
        mb.rod((AX0 - 0.03, 0.5 + 0.3 * k, 0.18 * k), (AX0 - 0.03, 0.5 + 0.3 * k, 0.18 * k + 0.95), 0.015, P["black"])
        mb.rod((BX1 + 0.03, 3.5 - 0.3 * k, 1.8 + 0.18 * k), (BX1 + 0.03, 3.5 - 0.3 * k, 1.8 + 0.18 * k + 0.95), 0.015, P["black"])
    mb.rod((AX0 - 0.03, 0.5, 0.95), (AX0 - 0.03, 3.5, 2.75), 0.025, P["walnut"]); mb.rod((BX1 + 0.03, 3.5, 2.75), (BX1 + 0.03, 0.5, 4.55), 0.025, P["walnut"])
    mb.rod((-7.55, 0.5, 0.95), (-7.55, 3.5, 2.75), 0.02, P["steel"]); mb.rod((-11.25, 3.5, 2.75), (-11.25, 0.5, 4.55), 0.02, P["steel"])
    wall(mb, "y", sx0, sy0 - 0.25, sy1 + 0.25, 0, FLOOR_H, P["stairpaint"], 1)
    wall(mb, "x", sy0, sx0, sx1, 0, FLOOR_H, P["stairpaint"], 1); wall(mb, "x", sy1, sx0, sx1, 0, FLOOR_H, P["stairpaint"], -1)
    wall(mb, "y", sx1, sy0, sy1, 0, FLOOR_H, P["stairpaint"], -1, [(-1.0, 0.0, 2.2)])
    mb.box((-7.52, -1.25, 2.4), (-7.5, -0.95, 2.6), P["exit_green"])
    mb.box((sx0 + 0.02, 4.2, 2.9), (sx0 + 0.04, 4.6, 3.1), P["cool_light"]); mb.box((sx0 + 0.02, -0.6, 2.9), (sx0 + 0.04, -0.2, 3.1), P["cool_light"])
    mb.done()
    for k in range(floors + 1):
        inst = empty(f"STAIR_floor{k}", (0, 0, k * FLOOR_H), st); inst.instance_type = "COLLECTION"; inst.instance_collection = mod
        label = "1" if k == 0 else ("M" if k == 1 else str(k))
        sign(label, (sx0 + 0.02, -0.4, k * FLOOR_H + 1.9), (1, 0), 0.5, P, st, mat="sign_red", name=f"TXT_floor_{label}")
        if k not in (0,) + tuple(corridor_floors):                                  # closed doors where no corridor is built
            door(f"stair{k}", "y", sx1, -0.5, k * FLOOR_H, P, st, w=1.0, h=2.2, face=1, kind="stair")
    door("stair0", "y", sx1, -0.5, 0, P, st, w=1.0, h=2.2, face=1, kind="stair", open_deg=-95)   # swung back into the shaft
    ROOMS["stairs"] = (Vector((sx0, sy0, 0)), Vector((sx1, sy1, (floors + 1) * FLOOR_H)))
    mb = MB("STAIR_roof", st); mb.box((sx0 - 0.25, sy0 - 0.25, (floors + 1) * FLOOR_H), (sx1 + 0.25, sy1 + 0.25, (floors + 1) * FLOOR_H + 0.3), P["concrete"]); mb.done()
    for k in (0, 1, 4, 9):
        light(f"LGT_stair{k}", "POINT", (-9.4, 2.0, k * FLOOR_H + 3.2), 120, (0.95, 0.97, 1.0), 0.3, c=st)

    # ---- upper floors with corridors (C1 stair door -> elevators, C2 north to the end room)
    fl = C["floors"]
    for k in corridor_floors:
        z = k * FLOOR_H; n = k * 100
        mb = room(f"corridor{k}", -7.25, -1.4, 7.25, 0.6, z, 2.8, P, P["carpet"], P["wallpaper"], P["ceiling"],
                  dict(w=None, e=[(-1.2, 0.6, 2.6)], s=[(x - 0.5, x + 0.5, 2.15) for x in (-5.0, -2.5, 2.5, 5.0)],
                       n=[(-1.5, 1.5, 2.8)] + [(x - 0.5, x + 0.5, 2.15) for x in (-5.0, -3.0, 3.0, 5.0)]), trim=trimC, c=fl)
        mb.done()
        for j, x in enumerate((-5.0, -2.5, 2.5, 5.0)): door(f"{k}s{j}", "x", -1.4, x, z, P, fl, face=1, number=n + 11 + j)
        for j, x in enumerate((-5.0, -3.0, 3.0, 5.0)): door(f"{k}n{j}", "x", 0.6, x, z, P, fl, face=-1, number=n + 21 + j)
        end_room = 4 if k == 4 else 1
        mb = room(f"corridorN{k}", -1.5, 0.6, 1.5, 7.0, z, 2.8, P, P["carpet"], P["wallpaper"], P["ceiling"],
                  dict(w=[(2.0, 2.95, 2.15), (4.5, 5.45, 2.15)], e=[(2.0, 2.95, 2.15), (4.5, 5.45, 2.15)], n=[(-0.5, 0.5, 2.15)], s=None), trim=trimC, c=fl)
        mb.done()
        for j, y in enumerate((2.475, 4.975)):
            door(f"{k}w{j}", "y", -1.5, y, z, P, fl, face=1, number=n + 31 + j); door(f"{k}e{j}", "y", 1.5, y, z, P, fl, face=-1, number=n + 41 + j)
        d = door(f"{k}end", "x", 7.0, 0.0, z, P, fl, face=-1, number=n + end_room, open_deg=(80 if k == 9 else 0))
        if k == 4: OBJ["door404"] = d["pivot"]
        for x in (-6.0, -3.75, 0.0, 3.75, 6.0): sconce(f"c{k}{x}", (x, -1.39, z + 1.9), (0, 1), P, fl, 25)
        for y in (2.0, 4.0, 6.0):
            m2 = MB(f"SM_Downlight_{k}_{y}", fl); m2.cyl((0, y, z + 2.79), 0.12, 0.02, P["warm_light"], seg=16); m2.done()
        light(f"LGT_corrN{k}", "AREA", (0, 3.5, z + 2.7), 90, (1.0, 0.85, 0.62), 1.2, aim=(0, 3.5, z), c=fl)
        light(f"LGT_corr{k}", "AREA", (0, -0.4, z + 2.7), 70, (1.0, 0.85, 0.62), 1.2, aim=(0, -0.4, z), c=fl)
        mb = room(f"elevlobby{k}", 7.25, -1.2, 10.6, 3.8, z, 2.8, P, P["carpet"], P["wallpaper"], P["ceiling"],
                  dict(w=[(-1.2, 0.6, 2.6)], e=[(-0.4, 0.8, 2.3), (1.9, 3.1, 2.3)], n=[], s=[]), trim=trimC, c=fl)
        mb.done()
        for nm, cy in (("std", 0.2), ("vip", 2.5)):
            m2 = MB(f"SM_ElevDoorsF{k}_{nm}", fl); m2.box((10.6 - 0.03, cy - 0.64, z), (10.6 + 0.03, cy + 0.64, z + 2.36), P["brass"] if nm == "vip" else P["steel"]); m2.done()
        plant(f"c{k}", (9.9, 3.4, z), P, fl, 0.8, "fern", k)
    # ---- suite 901 (floor 9, through the open end door of C2): walls, window to a night city
    su = C["suite"]; z = 9 * FLOOR_H
    mb = room("suite", -4.0, 7.25, 4.0, 14.0, z, 3.0, P, P["oak"], P["plaster"], P["ceiling"],
              dict(s=None, n=[(-1.5, 1.5, 2.6)], e=[], w=[]), trim=trimC, c=su)                  # south = corridor end wall
    mb.box((-1.5, 14.0, z), (1.5, 14.25, z + 0.4), P["plaster"]); mb.box((-1.5, 14.0, z + 0.4), (1.5, 14.05, z + 2.6), P["glass"])
    mb.box((-12, 17.0, z - 12), (12, 17.1, z + 12), P["night_city"])
    import random
    rr = random.Random(9)
    for k in range(70):                                                              # lit windows of the city at night
        x, zz = rr.uniform(-11, 11), z + rr.uniform(-10, 9)
        mb.box((x, 16.95, zz), (x + 0.5, 17.0, zz + 0.7), P["winlit"])
    mb.box((-2.6, 8.2, z), (2.6, 12.6, z + 0.01), P["rug_warm"]); mb.done()
    light("LGT_suite_lamp", "POINT", (-1.7, 13.0, z + 1.3), 60, (1.0, 0.75, 0.45), 0.15, c=su)
    light("LGT_suite_fill", "AREA", (0, 10.5, z + 2.9), 70, (1.0, 0.85, 0.65), 3.0, aim=(0, 10.5, z), c=su)

    # ---- exterior: facade, entrance, canopy; building shell up to the roof
    ex = C["exterior"]; top = (floors + 1) * FLOOR_H + 0.6; X0, X1, Y0, Y1 = -11.55, 12.9, -7.25, 14.5
    mb = MB("EXT_facade", ex); fy = Y0
    for (a, b) in ((X0, -6.6), (-2.0, -1.6), (1.6, 2.0), (6.6, X1)):              # ground-floor stone piers
        mb.box((a, fy, 0), (b, -7.0, 5.4), P["stone"])
    mb.box((X0, fy, 5.4), (X1, -7.0, top), P["stone"])
    mb.box((-6.6, fy, 4.4), (-2.0, -7.0, 5.4), P["stone"]); mb.box((2.0, fy, 4.4), (6.6, -7.0, 5.4), P["stone"]); mb.box((-1.6, fy, 3.4), (1.6, -7.0, 5.4), P["stone"])
    mb.box((-6.6, fy, 0), (-2.0, -7.0, 0.6), P["stone"]); mb.box((2.0, fy, 0), (6.6, -7.0, 0.6), P["stone"])
    for a, b in ((-6.6, -2.0), (2.0, 6.6)):                                        # storefront glass with brass mullions
        mb.box((a, -7.16, 0.6), (b, -7.1, 4.4), P["glass"])
        for k in range(4): mb.box((a + k * (b - a) / 3 - 0.03, -7.2, 0.6), (a + k * (b - a) / 3 + 0.03, -7.06, 4.4), P["brass"])
    for x in (-1.5, 1.5): mb.box((x - 0.05, -7.22, 0), (x + 0.05, -7.03, 3.4), P["brass"])
    for k in range(2, floors + 1):                                                 # window bays + cornice per floor
        z = k * FLOOR_H + 1.8
        mb.box((X0 - 0.12, fy - 0.12, k * FLOOR_H + 0.5), (X1 + 0.12, fy, k * FLOOR_H + 0.62), P["stone"])
        for i in range(8):
            x = X0 + 1.6 + i * (X1 - X0 - 3.2) / 7
            lit = (i * 7 + k * 3) % 5 == 0
            mb.box((x - 0.7, fy - 0.02, z - 0.9), (x + 0.7, fy + 0.12, z + 0.9), P["winlit"] if lit else P["winglass"])
            mb.box((x - 0.8, fy - 0.1, z - 1.0), (x + 0.8, fy, z - 0.9), P["stone"])
    mb.box((X0 - 0.3, fy - 0.3, top - 0.6), (X1 + 0.3, Y1 + 0.3, top), P["stone"])  # cornice / roof edge
    for (a, b, xx) in ((Y0, Y1, X0), (Y0, Y1, X1)):                                   # side walls
        mb.box((xx - (0.25 if xx < 0 else 0), a, 0), (xx + (0.25 if xx > 0 else 0), b, top), P["stone"])
    sz = 9 * FLOOR_H                                                                 # north wall with the suite window cut out
    mb.box((X0, Y1, 0), (X1, Y1 + 0.25, sz + 0.4), P["stone"]); mb.box((X0, Y1, sz + 2.6), (X1, Y1 + 0.25, top), P["stone"])
    mb.box((X0, Y1, sz + 0.4), (-1.5, Y1 + 0.25, sz + 2.6), P["stone"]); mb.box((1.5, Y1, sz + 0.4), (X1, Y1 + 0.25, sz + 2.6), P["stone"])
    mb.box((X0, Y0, top - 0.7), (X1, Y1, top - 0.6), P["concrete"])
    mb.done()
    mb = MB("EXT_canopy", ex)                                                       # entrance canopy with lettering
    mb.box((-3.2, -10.2, 3.9), (3.2, -7.25, 4.15), P["black"]); mb.box((-3.25, -10.25, 3.85), (3.25, -10.2, 4.2), P["brass"])
    for x in (-3.0, 3.0): mb.rod((x, -10.0, 0.0), (x, -10.0, 3.9), 0.05, P["brass"])
    for x in (-2.0, 0.0, 2.0): mb.cyl((x, -8.8, 3.885), 0.1, 0.02, P["warm_light"], seg=12)
    mb.box((-1.0, -12.0, 0.0), (1.0, -7.25, 0.012), P["redcarpet"])
    mb.done()
    text("THE GRAND AURELIA", (0, -10.27, 4.02), 0.26, P["brass"], ex, rot=facing_rot((0, -1)), name="TXT_GrandAurelia_canopy")
    for x in (-2.4, 2.4): light(f"LGT_canopy{x:+.0f}", "SPOT", (x, -8.8, 3.8), 300, (1.0, 0.82, 0.58), 0.1, aim=(x, -8.8, 0), c=ex)
    for x in (-2.3, 2.3): plant(f"topiary{x:+.0f}", (x, -7.8, 0), P, ex, 1.0, "topiary")
    m2 = MB("EXT_bladesign", ex); m2.box((12.9, -7.6, 8.0), (13.15, -6.9, 18.0), P["black"]); m2.done()
    for k, ch in enumerate("AURELIA"): text(ch, (13.16, -7.25, 17.2 - k * 1.3), 0.9, P["warm_light"], ex, rot=facing_rot((1, 0)), name=f"TXT_blade{k}")

    # ---- street: sidewalks, curb, road, markings, lights, trees; neighbours and the buildings opposite
    sw = C["street"]; mb = MB("STREET", sw)
    mb.box((-80, -12.0, -0.25), (80, Y0, 0.0), P["paver"]); mb.box((-80, -12.15, -0.25), (80, -12.0, 0.0), P["concrete"])
    mb.box((-80, -20.0, -0.4), (80, -12.0, -0.15), P["asphalt"]); mb.box((-80, -24.0, -0.25), (80, -20.0, 0.0), P["paver"])
    for k in range(-20, 21): mb.box((k * 4 - 1.2, -16.06, -0.15), (k * 4 + 1.2, -15.94, -0.148), P["paint_white"])
    for k in range(8): mb.box((-4.0 + k * 0.6, -19.6, -0.15), (-3.7 + k * 0.6, -12.4, -0.148), P["paint_white"])   # crosswalk
    mb.box((-200, -200, -0.6), (200, 200, -0.4), P["render_grey"])
    trees = []
    for x in range(-48, 49, 12):
        if abs(x) > 5:                                                               # no pole in front of the entrance
            mb.rod((x, -11.6, 0), (x, -11.6, 4.6), 0.06, P["black"]); mb.rod((x, -11.6, 4.6), (x, -12.4, 4.8), 0.04, P["black"])
            mb.sphere((x, -12.5, 4.72), 0.16, P["warm_light"], scale=(1.2, 1.2, 0.6))
        t = x + 6
        if abs(t) > 5 and not 19 < t < 31:                                               # keep the entrance + pet store clear
            mb.box((t - 0.6, -11.6, -0.02), (t + 0.6, -10.4, 0.01), P["soil"]); trees.append(t)
    mb.done()
    for t in trees: plant(f"tree{t}", (t, -11.0, 0), P, sw, 2.6, "fern", t)
    for x in (-12, 12): light(f"LGT_street{x:+d}", "POINT", (x, -12.5, 4.5), 250, (1.0, 0.78, 0.5), 0.2, c=sw)
    import random
    rnd = random.Random(7)
    def block(name, x0, x1, y_face, depth, h, mat, faces, shop=None):
        """A neighbouring building whose facade at y_face faces `faces` (+1 = +Y, -1 = -Y): windows, optional shopfront."""
        m3 = MB(f"BLDG_{name}", sw); yb = y_face - faces * depth
        m3.box((x0, min(y_face, yb), 0), (x1, max(y_face, yb), h), mat)
        proud = lambda a, b: (min(y_face + faces * a, y_face + faces * b), max(y_face + faces * a, y_face + faces * b))
        for fz in range(1, int(h // 3.3)):
            for i in range(int((x1 - x0) // 2.4)):
                x = x0 + 1.2 + i * 2.4; zz = fz * 3.3 + 1.0; y0, y1 = proud(-0.02, 0.06)
                m3.box((x - 0.55, y0, zz - 0.8), (x + 0.55, y1, zz + 0.8), P["winlit"] if rnd.random() < 0.18 else P["winglass"])
        if shop:
            y0, y1 = proud(-0.02, 0.06); m3.box((x0 + 0.4, y0, 0.4), (x1 - 0.4, y1, 2.8), P["winglass"])
            y0, y1 = proud(0.06, 0.9); m3.box((x0 + 0.2, y0, 2.9), (x1 - 0.2, y1, 3.3), P[shop])
        return m3.done()
    xs = [(-80, -52), (-52, -34), (-34, -11.8)]
    for i, (a, b) in enumerate(xs): block(f"W{i}", a, b, Y0, 12, rnd.choice((14, 18, 22)), P[rnd.choice(("brick", "render_grey", "stone"))], -1, shop=rnd.choice(("sign_red", "green_shop", None)))
    for i, (a, b) in enumerate(((13.1, 20.0), (30.0, 46), (46, 80))):
        block(f"E{i}", a, b, Y0, 12, rnd.choice((12, 16, 20)), P[rnd.choice(("brick", "render_grey"))], -1, shop=(None if i == 0 else "sign_red"))
    for i in range(10):
        a = -80 + i * 16; block(f"S{i}", a, a + 15.6, -24.0, 12, rnd.choice((10, 14, 18, 26)), P[rnd.choice(("brick", "render_grey", "stone", "brick"))], 1,
                                shop=rnd.choice(("sign_red", "green_shop", None)))

    # ---- pet store (same street, x 20..30): storefront, display window, door, a lit interior with tanks
    ps = C["petstore"]; ox, oy, _ = ORIGIN["petstore"]
    mb = room("petstore", 20.5, Y0 + 0.25, 29.5, -1.25, 0, 3.4, P, P["paver"], P["plaster_cool"], P["ceiling"],
              dict(s=None, n=[], e=[], w=[]), c=ps)
    for (a, b) in ((20.0, 21.5), (26.0, 26.8), (28.0, 30.0)): mb.box((a, Y0, 0), (b, -7.0, 4.2), P["green_shop"])
    mb.box((21.5, Y0, 0), (26.0, -7.0, 0.5), P["green_shop"]); mb.box((21.5, Y0, 3.0), (28.0, -7.0, 4.2), P["green_shop"])
    mb.box((21.5, -7.16, 0.5), (26.0, -7.1, 3.0), P["glass"]); mb.box((26.8, -7.16, 0.0), (28.0, -7.1, 2.4), P["glass"]); mb.box((26.8, Y0, 2.4), (28.0, -7.0, 3.0), P["green_shop"])
    mb.box((20.0, Y0 - 1.2, 3.0), (30.0, Y0, 3.15), P["green_shop"])
    for k in range(3): mb.box((21.0, -2.0, 0.6 + k * 0.7), (29.0, -1.6, 0.64 + k * 0.7), P["oak"])  # shelves on the back wall
    mb.done()
    text("PET PALACE", (25.0, Y0 - 0.02, 3.6), 0.5, P["warm_light"], ps, rot=facing_rot((0, -1)), name="TXT_petpalace")
    light("LGT_petstore", "AREA", (25.0, -4.2, 3.3), 220, (0.9, 0.97, 1.0), 4.0, aim=(25.0, -4.2, 0), c=ps)

    # ---- sun + sky (daylight through the entrance; interiors stay warm and practical-lit)
    sun = bpy.data.lights.new("SUN", "SUN"); sun.energy = 3.2; sun.angle = math.radians(2.0); sun.color = (1.0, 0.95, 0.86)
    so = bpy.data.objects.new("SUN", sun); C["lights"].objects.link(so); so.rotation_euler = Euler((math.radians(48), 0, math.radians(-28)))
    w = bpy.context.scene.world or bpy.data.worlds.new("WLD_Hotel"); bpy.context.scene.world = w; w.use_nodes = True
    nt = w.node_tree; bg = nt.nodes.get("Background") or nt.nodes.new("ShaderNodeBackground")
    sky = nt.nodes.new("ShaderNodeTexSky")
    for t in ("MULTIPLE_SCATTERING", "NISHITA", "HOSEK_WILKIE"):
        try: sky.sky_type = t; break
        except TypeError: continue
    try: sky.sun_elevation = math.radians(42); sky.sun_rotation = math.radians(118)
    except AttributeError: pass
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"]); bg.inputs["Strength"].default_value = 0.35
    out = nt.nodes.get("World Output") or nt.nodes.new("ShaderNodeOutputWorld"); nt.links.new(bg.outputs["Background"], out.inputs["Surface"])

    # ---- marks + routes + exterior volume for camera containment
    ROOMS["street"] = (Vector((-60, -24.0, -0.15)), Vector((60, Y0 - 0.05, 30)))
    ANCHORS.update(entrance=(0, -7.6, 0), lobby_center=(0, -2.5, 0), desk_guest=(0, 0.95, 0), desk_clerk=(0, 2.6, 0),
                   cart_home=(-2.2, 3.6, 0), stair_door=(-7.6, -0.5, 0), stair_bottom=(-8.5, 0.3, 0),
                   elev_vip=(9.6, 2.5, 0), elev_vip_inside=(11.6, 2.5, 0), elev_std=(9.6, 0.2, 0),
                   hall404=(0, 6.2, 4 * FLOOR_H), suite_door=(0, 7.5, 9 * FLOOR_H), petstore_door=(27.4, -9.0, 0))
    ROUTES.update(
        street_to_desk=[(0, -14.0 + 2.2, 0), (0, -7.6, 0), (0, -4.0, 0), (0, 0.95, 0)],
        desk_to_vip_elevator=[(0, 0.95, 0), (3.0, 0.9, 0), (6.6, 1.3, 0), (9.6, 2.5, 0), (11.6, 2.5, 0)],
        desk_to_stairs=[(0, 0.95, 0), (-4.0, 0.2, 0), (-6.6, -0.5, 0), (-8.0, -0.5, 0), (-8.5, 0.3, 0)],
        clerk_to_cart=[(0, 2.6, 0), (-2.2, 3.0, 0)],
        floor4_to_404=[(-8.2, -0.5, 4 * FLOOR_H), (-6.6, -0.4, 4 * FLOOR_H), (0.0, -0.4, 4 * FLOOR_H), (0.0, 6.2, 4 * FLOOR_H)],
        floor9_to_suite=[(-8.2, -0.5, 9 * FLOOR_H), (0.0, -0.4, 9 * FLOOR_H), (0.0, 6.6, 9 * FLOOR_H), (0.0, 9.0, 9 * FLOOR_H)],
        petstore_to_hotel=[(27.4, -9.5, 0), (10.0, -9.5, 0), (0.0, -9.0, 0), (0.0, -6.5, 0)],
    )
    OBJ.update(desk=desk, elevator=E["vip"]["frame"], elevators=E)
    return dict(origin=ORIGIN, rooms=ROOMS, routes=ROUTES, anchors=ANCHORS, obj=OBJ, elevators=E, palette=P)


# ---------------------------------------------------------------- checks
def inside(p, margin=0.2):
    p = Vector(p)
    for mn, mx in ROOMS.values():
        if all(mn[i] + margin <= p[i] <= mx[i] - margin for i in range(3)): return True
    return False


def keep_inside(pos, aim, margin=0.25):
    """Move a camera that ended up inside a wall or outside every room toward its aim point until it is inside a
    room volume (with margin). Returns the new position (unchanged if already inside)."""
    pos, aim = Vector(pos), Vector(aim)
    if inside(pos, margin): return pos
    for k in range(1, 101):
        q = pos.lerp(aim, k / 100)
        if inside(q, margin): return q
    return pos


def check_routes(min_clear=0.3):
    """Walk every route in 0.25 m steps: floor under each sample (ray down within 0.5 m of the mark's height)
    and nothing at knee/chest/head height along the way. Returns ["route: problem at (x, y, z)"]."""
    sc = bpy.context.scene; dg = bpy.context.evaluated_depsgraph_get(); bad = []
    for name, pts in ROUTES.items():
        for a, b in zip(pts, pts[1:]):
            a, b = Vector(a), Vector(b); d = b - a; n = max(1, int(d.length / 0.25))
            for k in range(n + 1):
                p = a.lerp(b, k / n)
                hit, loc, *_ = sc.ray_cast(dg, p + Vector((0, 0, 1.0)), Vector((0, 0, -1)), distance=1.6)
                if not hit or abs(loc.z - p.z) > 0.5: bad.append(f"{name}: no floor at {tuple(round(v, 2) for v in p)}"); break
                if d.length and k < n:
                    for hz in (0.35, 1.1, 1.65):
                        hit2, *_ = sc.ray_cast(dg, p + Vector((0, 0, hz)), d.normalized(), distance=d.length / n + min_clear)
                        if hit2: bad.append(f"{name}: blocked at {tuple(round(v, 2) for v in p)} h={hz}"); break
                    else: continue
                    break
    return bad


def eevee_quality(sc=None, samples=12, raytrace=True, shadow_scale=0.5):
    """EEVEE settings the kit is lit for: ray-traced reflections, fast GI / AO, soft shadows with enough rays for
    contact shadows, AgX with a little contrast. Every setting is optional across Blender versions."""
    sc = sc or bpy.context.scene; ee = sc.eevee
    items = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    sc.render.engine = next(e for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE") if e in items)
    for attr, val in (("taa_render_samples", samples), ("use_raytracing", raytrace), ("ray_tracing_method", "SCREEN"),
                      ("use_fast_gi", True), ("fast_gi_distance", 2.5), ("use_gtao", True), ("gtao_distance", 1.2),
                      ("use_shadows", True), ("shadow_ray_count", 2), ("shadow_step_count", 8), ("use_soft_shadows", True),
                      ("shadow_resolution_scale", shadow_scale), ("use_volumetric_shadows", False)):
        try: setattr(ee, attr, val)
        except (AttributeError, TypeError): pass
    try:
        ee.ray_tracing_options.resolution_scale = "4"; ee.ray_tracing_options.use_denoise = True
    except (AttributeError, TypeError): pass
    sc.view_settings.view_transform = "AgX"
    try: sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError: pass


# ---------------------------------------------------------------- hero props (story objects: recognisable, not blocks)
SUITCASE = {"cabin": (0.36, 0.22, 0.55), "medium": (0.44, 0.26, 0.68), "large": (0.5, 0.29, 0.78), "duffel": (0.62, 0.3, 0.3)}


def _shell(name, color, rough=0.45):
    return material(f"HK_Shell_{name}", color, rough, var=0.04, bump=0.04)


def suitcase(name, kind="medium", color=(0.7, 0.1, 0.3), P=None, c=None, parent=None):
    """A hard-shell spinner suitcase (or a duffel): rounded shell with ribs, zip seam, corner guards, carry
    handle, telescopic handle and four spinner wheels. Origin at the bottom centre; +Z up, front = -Y.
    Returns the object (one mesh, bevelled)."""
    P = P or palette(); c = c or bpy.context.scene.collection
    w, d, h = SUITCASE[kind]; sh = _shell(f"{kind}_{name}", color); mb = MB(f"SM_Case_{name}", c)
    if kind == "duffel":
        mb.cyl((0, 0, h / 2), h / 2, w, sh, axis="X", seg=20)
        for x in (-w * 0.3, w * 0.3): mb.cyl((x, 0, h / 2), h / 2 + 0.006, 0.04, P["black"], axis="X", seg=20)   # straps
        mb.rod((-w * 0.18, 0, h), (-w * 0.12, 0, h + 0.12), 0.012, P["black"]); mb.rod((w * 0.18, 0, h), (w * 0.12, 0, h + 0.12), 0.012, P["black"])
        mb.rod((-w * 0.12, 0, h + 0.12), (w * 0.12, 0, h + 0.12), 0.014, P["black"])
        ob = mb.done(bevel=0.01, parent=parent); return ob
    z0 = 0.06
    mb.box((-w / 2, -d / 2, z0), (w / 2, d / 2, z0 + h), sh)
    for k in range(1, 5):                                                    # vertical ribs on the front shell
        x = -w / 2 + k * w / 5; mb.box((x - 0.012, -d / 2 - 0.006, z0 + 0.05), (x + 0.012, -d / 2, z0 + h - 0.05), sh)
    mb.box((-w / 2 - 0.004, -0.006, z0 + 0.01), (w / 2 + 0.004, 0.006, z0 + h - 0.01), P["black"])          # zip seam
    for sx in (-1, 1):
        for sz in (z0, z0 + h - 0.05):
            x0, x1 = (w / 2 - 0.05, w / 2 + 0.004) if sx > 0 else (-w / 2 - 0.004, -w / 2 + 0.05)
            mb.box((x0, -d / 2 - 0.004, sz), (x1, d / 2 + 0.004, sz + 0.05), P["black"])             # corner guards
    mb.box((-0.07, -0.02, z0 + h), (0.07, 0.02, z0 + h + 0.012), P["black"]); mb.rod((-0.06, 0, z0 + h + 0.012), (-0.06, 0, z0 + h + 0.04), 0.008, P["black"])
    mb.rod((0.06, 0, z0 + h + 0.012), (0.06, 0, z0 + h + 0.04), 0.008, P["black"]); mb.rod((-0.06, 0, z0 + h + 0.04), (0.06, 0, z0 + h + 0.04), 0.011, P["black"])
    for x in (-0.09, 0.09): mb.box((x - 0.012, d / 2, z0 + h - 0.02), (x + 0.012, d / 2 + 0.02, z0 + h + 0.03), P["steel"])  # telescopic handle (stowed)
    mb.box((-0.1, d / 2, z0 + h + 0.03), (0.1, d / 2 + 0.025, z0 + h + 0.055), P["black"])
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((sx * (w / 2 - 0.05) - 0.02, sy * (d / 2 - 0.04) - 0.02, z0 - 0.012), (sx * (w / 2 - 0.05) + 0.02, sy * (d / 2 - 0.04) + 0.02, z0), P["black"])
            mb.cyl((sx * (w / 2 - 0.05), sy * (d / 2 - 0.04), 0.028), 0.028, 0.022, P["black"], axis="Y", seg=12)
    return mb.done(bevel=0.012, parent=parent)


def trolley_wheels(root, P):
    """Spinnable wheel objects for a trolley root (children; key rotation_euler.x to roll)."""
    out = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb = MB(f"SM_TrolleyWheel_{root.name}_{sx}{sy}", root.users_collection[0])
            mb.cyl((0, 0, 0), 0.05, 0.035, P["black"], axis="X", seg=16); mb.box((-0.02, -0.045, -0.006), (0.02, 0.045, 0.006), P["steel"])
            ob = mb.done(parent=root); ob.location = (sx * 0.5, sy * 0.24, 0.05); out.append(ob)
    return out


def cockroach(name, c=None, P=None):
    """A recognisable cockroach (~6 cm Madagascar hisser): segmented body, head, antennae, six jointed legs.
    Origin under the body; front = -Y. Returns the root empty (antennae are children for wiggle keys)."""
    P = P or palette(); c = c or bpy.context.scene.collection
    shell = material("HK_RoachShell", (0.24, 0.12, 0.05), 0.35, var=0.15, bump=0.2); dark = material("HK_RoachDark", (0.08, 0.04, 0.02), 0.5)
    root = empty(f"ROACH_{name}", (0, 0, 0), c); mb = MB(f"SM_Roach_{name}", c)
    for k in range(7):                                                        # abdomen plates, tapering to the tail
        y = 0.005 + k * 0.007; r = 0.016 - abs(k - 2) * 0.0016
        mb.sphere((0, y, 0.008), r, shell, scale=(1.0, 0.55, 0.45), seg=12)
    mb.sphere((0, -0.012, 0.009), 0.011, shell, scale=(1.1, 0.9, 0.5), seg=12)                     # pronotum
    mb.sphere((0, -0.024, 0.006), 0.006, dark, seg=10)                                              # head
    for sx in (-1, 1):
        for j, (y, a) in enumerate(((-0.01, -0.6), (0.004, 0.0), (0.018, 0.6))):
            hip = Vector((sx * 0.009, y, 0.006)); knee = hip + Vector((sx * 0.013, a * 0.006, 0.006)); foot = knee + Vector((sx * 0.01, a * 0.012, -0.012))
            mb.rod(hip, knee, 0.0012, dark, seg=5); mb.rod(knee, foot, 0.001, dark, seg=5)
    body = mb.done(parent=root)
    for sx in (-1, 1):
        am = MB(f"SM_RoachAntenna_{name}_{sx}", c); am.rod((0, 0, 0), (sx * 0.012, -0.026, 0.008), 0.0006, dark, seg=4)
        a = am.done(parent=root); a.location = (sx * 0.002, -0.028, 0.008)
    return root


def bug_box(name, c=None, P=None):
    """Pet-store insect carrier: kraft cardboard box with air holes, a 'LIVE INSECTS' band, wire handle and a
    hinged lid (child 'LID_<name>' rotates about X at the back edge). Origin at the bottom centre; ~10 x 8 x 8 cm."""
    P = P or palette(); c = c or bpy.context.scene.collection
    kraft = material("HK_Kraft", (0.62, 0.45, 0.28), 0.85, var=0.08, bump=0.25); label = material("HK_LabelGreen", (0.12, 0.42, 0.2), 0.6, var=0.02)
    root = empty(f"BUGBOX_{name}", (0, 0, 0), c); mb = MB(f"SM_BugBox_{name}", c); w, d, h = 0.1, 0.08, 0.075
    mb.box((-w / 2, -d / 2, 0), (w / 2, -d / 2 + 0.003, h), kraft); mb.box((-w / 2, d / 2 - 0.003, 0), (w / 2, d / 2, h), kraft)
    mb.box((-w / 2, -d / 2, 0), (-w / 2 + 0.003, d / 2, h), kraft); mb.box((w / 2 - 0.003, -d / 2, 0), (w / 2, d / 2, h), kraft)
    mb.box((-w / 2, -d / 2, 0), (w / 2, d / 2, 0.003), kraft)
    for (x0, y0, x1, y1) in ((-w / 2 - 0.0008, -d / 2 - 0.0008, w / 2 + 0.0008, -d / 2), (-w / 2 - 0.0008, d / 2, w / 2 + 0.0008, d / 2 + 0.0008),
                             (-w / 2 - 0.0008, -d / 2, -w / 2, d / 2), (w / 2, -d / 2, w / 2 + 0.0008, d / 2)):
        mb.box((x0, y0, 0.022), (x1, y1, 0.042), label)                        # printed band on the outside only
    for i in range(4):
        for sx in (-1, 1): mb.cyl((sx * (w / 2 + 0.0005), -0.025 + i * 0.017, 0.056), 0.0035, 0.002, P["black"], axis="X", seg=8)
    mb.rod((-0.03, 0, h + 0.004), (-0.025, 0, h + 0.03), 0.0012, P["steel"]); mb.rod((0.03, 0, h + 0.004), (0.025, 0, h + 0.03), 0.0012, P["steel"])
    mb.rod((-0.025, 0, h + 0.03), (0.025, 0, h + 0.03), 0.0012, P["steel"])
    mb.done(parent=root)
    hinge = empty(f"LID_{name}", (0, d / 2, h), c); hinge.parent = root
    lm = MB(f"SM_BugBoxLid_{name}", c); lm.box((-w / 2 - 0.002, -d - 0.002, 0.0), (w / 2 + 0.002, 0.002, 0.004), kraft)
    lm.box((-w / 2 - 0.002, -d - 0.002, -0.012), (w / 2 + 0.002, -d + 0.001, 0.0), kraft)            # front flap
    lm.done(parent=hinge)
    text("LIVE INSECTS", (0, -d / 2 - 0.0012, 0.032), 0.011, material("HK_LabelText", (0.95, 0.93, 0.85), 0.6), c, rot=(math.pi / 2, 0, 0), name=f"TXT_bugbox_{name}", extrude=0.0003, parent=root).location = (0, -d / 2 - 0.0012, 0.032)
    return root


def phone(name, c=None, P=None, screen=(0.55, 0.75, 1.0)):
    """Smartphone (7.4 x 15.2 x 0.8 cm): dark rounded body, bright screen on -Y (the face side), camera bump on +Y.
    Origin at its centre; long axis Z."""
    P = P or palette(); c = c or bpy.context.scene.collection
    scr = material(f"HK_PhoneScreen_{name}", screen, 0.2, emit=2.2, var=0.0, bump=0.0)
    mb = MB(f"SM_Phone_{name}", c)
    mb.box((-0.037, -0.004, -0.076), (0.037, 0.004, 0.076), P["black"]); mb.box((-0.034, -0.0045, -0.072), (0.034, -0.004, 0.072), scr)
    mb.box((0.008, 0.004, 0.045), (0.032, 0.0065, 0.07), P["black"]); mb.cyl((0.02, 0.0068, 0.058), 0.006, 0.002, P["steel"], axis="Y", seg=12)
    return mb.done(bevel=0.003)
