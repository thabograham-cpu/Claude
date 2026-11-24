"""Reusable camera rig + moves for headless Blender (bpy only).

    import camera as C
    r = C.rig("Shot12", loc=(0, -5, 1.6), target=(0, 0, 1.5), lens=35)
    C.track(r, rig_obj, bone="head", f0=1, f1=48, smooth=0.6)   # aim follows a moving subject
    C.dolly(r, 1, 48, 1.2)                                       # push in 1.2 m (ease in/out)
    C.pan(r, 49, 72, 30); C.zoom(r, 73, 96, 35, 85); C.dolly_zoom(r, 1, 48, 85)
    C.orbit(r, 1, 96, 90); C.crane(r, 1, 48, 1.5); C.whip_pan(r, 60, 90)
    C.path(r, [(0,-5,1.6), (3,-3,2), (4,0,1.6)], 1, 96)        # camera rides a curve
    C.dof(r, 2.0, focus=hero, bone="head"); C.rack_focus(r, 40, 52, hero, other, bone_b="head")
    C.handheld(r, 0.6); C.motion_blur(True)

Rig = CAM_<name> (Track To) + EMPTY_CamTarget_<name> (aim) + EMPTY_CamFocus_<name> (DoF focus).
Each move keys every frame of [f0, f1] from the rig's state at f0, so moves on *different* channels
(camera position / aim / lens / focus) combine freely; moves on the same channel must not overlap in time.
Subjects can be an object, an armature + bone name, or a point (x, y, z).
"""
import math
import bpy
from bpy_extras import anim_utils
from mathutils import Vector, Matrix

EASE = {
    "linear": lambda t: t,
    "inout": lambda t: t * t * (3 - 2 * t),
    "in": lambda t: t * t,
    "out": lambda t: 1 - (1 - t) * (1 - t),
}


class Rig:
    def __init__(self, cam, target, focus):
        self.cam, self.target, self.focus = cam, target, focus


def _link(o, col=None):
    (col or bpy.context.scene.collection).objects.link(o); return o


def rig(name, loc, target, lens=35.0, collection=None, vertical=True):
    """Camera aimed at an empty via Track To; also creates the DoF focus empty."""
    cam = _link(bpy.data.objects.new(f"CAM_{name}", bpy.data.cameras.new(f"CAM_{name}")), collection)
    tgt = _link(bpy.data.objects.new(f"EMPTY_CamTarget_{name}", None), collection)
    foc = _link(bpy.data.objects.new(f"EMPTY_CamFocus_{name}", None), collection)
    cam.location, tgt.location, foc.location = Vector(loc), Vector(target), Vector(target)
    cam.data.lens = lens; cam.data.clip_start = 0.02
    if vertical: cam.data.sensor_fit = "VERTICAL"
    c = cam.constraints.new("TRACK_TO"); c.target = tgt; c.track_axis = "TRACK_NEGATIVE_Z"; c.up_axis = "UP_Y"
    return Rig(cam, tgt, foc)


def where(subject, bone=None, head_tail=0.0):
    """World position of an object, an armature bone, or a plain point."""
    if subject is None: return None
    if not hasattr(subject, "matrix_world"): return Vector(subject)
    if bone:
        pb = subject.pose.bones[bone]
        return subject.matrix_world @ pb.head.lerp(pb.tail, head_tail)
    return subject.matrix_world.translation.copy()


def _fcurves(idb):
    ad = idb.animation_data
    if not ad or not ad.action: return []
    cb = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)
    return list(cb.fcurves) if cb else []


def _at(frame):
    bpy.context.scene.frame_set(frame)


def _run(f0, f1, ease, step):
    """Call step(frame, eased_t) for every frame f0..f1 (inclusive)."""
    e = EASE[ease]; n = max(1, f1 - f0)
    for f in range(f0, f1 + 1):
        step(f, e((f - f0) / n))


def _key(obj, path, f):
    obj.keyframe_insert(path, frame=f)


# ---------------------------------------------------------------- moves
def dolly(r, f0, f1, distance, ease="inout"):
    """Move the camera along its view line (positive = toward the target)."""
    _at(f0); a = r.cam.location.copy(); d = (r.target.location - a).normalized()
    def s(f, t): r.cam.location = a + d * distance * t; _key(r.cam, "location", f)
    _run(f0, f1, ease, s)


def move(r, f0, f1, delta, ease="inout"):
    """Truck / pedestal: translate camera AND aim together by delta (x, y, z)."""
    _at(f0); a, b = r.cam.location.copy(), r.target.location.copy(); dv = Vector(delta)
    def s(f, t):
        r.cam.location = a + dv * t; r.target.location = b + dv * t
        _key(r.cam, "location", f); _key(r.target, "location", f)
    _run(f0, f1, ease, s)


def crane(r, f0, f1, height, ease="inout"):
    """Raise/lower the camera only; aim stays put, so the view tilts to follow."""
    _at(f0); a = r.cam.location.copy()
    def s(f, t): r.cam.location = a + Vector((0, 0, height * t)); _key(r.cam, "location", f)
    _run(f0, f1, ease, s)


def pan(r, f0, f1, degrees, tilt=0.0, ease="inout"):
    """Swing the aim around the camera (pan = yaw, tilt = pitch); camera stays put."""
    _at(f0); c = r.cam.location.copy(); v0 = r.target.location - c
    side = v0.cross(Vector((0, 0, 1))).normalized()
    def s(f, t):
        v = Matrix.Rotation(math.radians(degrees * t), 3, "Z") @ v0
        if tilt: v = Matrix.Rotation(math.radians(tilt * t), 3, side) @ v
        r.target.location = c + v; _key(r.target, "location", f)
    _run(f0, f1, ease, s)


def whip_pan(r, f0, f1, degrees=80):
    """Fast motivated pan; pair with motion_blur(True)."""
    pan(r, f0, f1, degrees, ease="in")


def orbit(r, f0, f1, degrees, ease="inout"):
    """Circle the camera around the aim point."""
    _at(f0); p = r.target.location.copy(); v0 = r.cam.location - p
    def s(f, t): r.cam.location = p + Matrix.Rotation(math.radians(degrees * t), 3, "Z") @ v0; _key(r.cam, "location", f)
    _run(f0, f1, ease, s)


def zoom(r, f0, f1, lens0, lens1, ease="inout"):
    """Optical zoom: animate focal length (mm)."""
    def s(f, t): r.cam.data.lens = lens0 + (lens1 - lens0) * t; _key(r.cam.data, "lens", f)
    _run(f0, f1, ease, s)


def dolly_zoom(r, f0, f1, lens1, ease="inout"):
    """'Vertigo': change lens while dollying so the aim point keeps its on-screen size."""
    _at(f0); a = r.cam.location.copy(); p = r.target.location.copy(); l0 = r.cam.data.lens
    d0 = (p - a).length; u = (a - p).normalized()
    def s(f, t):
        lens = l0 + (lens1 - l0) * t
        r.cam.data.lens = lens; r.cam.location = p + u * d0 * lens / l0   # distance / lens stays constant
        _key(r.cam.data, "lens", f); _key(r.cam, "location", f)
    _run(f0, f1, ease, s)


def track(r, subject, f0, f1, bone=None, offset=(0, 0, 0), smooth=0.0, focus=True):
    """Aim (and focus) follow a moving subject. smooth 0..0.95 = lazy operator-style lag."""
    off = Vector(offset); prev = None
    for f in range(f0, f1 + 1):
        _at(f); raw = where(subject, bone) + off
        prev = raw if prev is None else prev.lerp(raw, 1 - smooth)
        r.target.location = prev; _key(r.target, "location", f)
        if focus: r.focus.location = raw; _key(r.focus, "location", f)


def path(r, points, f0, f1, ease="inout"):
    """Camera rides a smooth curve through points (replaces any keyed camera position)."""
    cu = bpy.data.curves.new(f"PATH_{r.cam.name}", "CURVE"); cu.dimensions = "3D"
    sp = cu.splines.new("BEZIER"); sp.bezier_points.add(len(points) - 1)
    for bp, p in zip(sp.bezier_points, points):
        bp.co = Vector(p); bp.handle_left_type = bp.handle_right_type = "AUTO"
    po = _link(bpy.data.objects.new(f"PATH_{r.cam.name}", cu))
    ad = r.cam.animation_data
    if ad and ad.action:
        cb = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)
        for fc in [fc for fc in cb.fcurves if fc.data_path == "location"]: cb.fcurves.remove(fc)
    r.cam.location = (0, 0, 0)
    c = r.cam.constraints.new("FOLLOW_PATH"); c.target = po; c.use_fixed_location = True
    r.cam.constraints.move(len(r.cam.constraints) - 1, 0)  # ride the path first, then aim
    def s(f, t): c.offset_factor = t; c.keyframe_insert("offset_factor", frame=f)
    _run(f0, f1, ease, s)
    return po


def handheld(r, strength=0.5, scale=14.0):
    """Organic operator shake: noise on the aim + a little on the camera. strength 0.2 subtle .. 1.5 shaky."""
    for obj, k in ((r.target, 0.03), (r.cam, 0.008)):
        if not _fcurves(obj): obj.keyframe_insert("location", frame=bpy.context.scene.frame_start)
        for fc in _fcurves(obj):
            if fc.data_path == "location":
                n = fc.modifiers.new("NOISE"); n.strength = strength * k * 2; n.scale = scale; n.phase = 13 * fc.array_index + id(obj) % 97


# ---------------------------------------------------------------- focus
def dof(r, fstop=2.8, focus=None, bone=None, blades=0):
    """Enable depth of field; focus empty placed on the subject (or keep it on the aim)."""
    d = r.cam.data.dof; d.use_dof = True; d.aperture_fstop = fstop; d.aperture_blades = blades
    d.focus_object = r.focus
    p = where(focus, bone)
    if p is not None: r.focus.location = p


def rack_focus(r, f0, f1, a, b, bone_a=None, bone_b=None, ease="inout"):
    """Pull focus from subject a to subject b (focus empty glides between them)."""
    if not r.cam.data.dof.use_dof: dof(r)
    _at(f0); pa = where(a, bone_a); _at(f1); pb = where(b, bone_b)
    def s(f, t): r.focus.location = pa.lerp(pb, t); _key(r.focus, "location", f)
    _run(f0, f1, ease, s)


def motion_blur(on=True, shutter=0.5):
    sc = bpy.context.scene; sc.render.use_motion_blur = on; sc.render.motion_blur_shutter = shutter


# ---------------------------------------------------------------- shot-list hook
def apply(r, spec, f0, f1, subjects=None):
    """Apply a shot-list move dict, e.g. {"move": "dolly_in", "amount": 0.8, "fstop": 2, "focus": "INF",
    "rack_to": "CLK", "rack_at": 0.5, "handheld": 0.4}. subjects: name -> (object, bone)."""
    subjects = subjects or {}
    sub = lambda n: subjects.get(n, (None, None))
    m, amt = spec.get("move"), spec.get("amount")
    if m == "dolly_in": dolly(r, f0, f1, amt or 0.6)
    elif m == "dolly_out": dolly(r, f0, f1, -(amt or 0.6))
    elif m in ("pan_left", "pan_right"): pan(r, f0, f1, (amt or 25) * (1 if m == "pan_left" else -1))
    elif m in ("tilt_up", "tilt_down"): pan(r, f0, f1, 0, tilt=(amt or 15) * (1 if m == "tilt_up" else -1))
    elif m == "orbit": orbit(r, f0, f1, amt or 30)
    elif m == "crane_up": crane(r, f0, f1, amt or 1.0)
    elif m == "crane_down": crane(r, f0, f1, -(amt or 1.0))
    elif m == "zoom_in": zoom(r, f0, f1, r.cam.data.lens, r.cam.data.lens * (amt or 1.6))
    elif m == "zoom_out": zoom(r, f0, f1, r.cam.data.lens, r.cam.data.lens / (amt or 1.6))
    elif m == "dolly_zoom": dolly_zoom(r, f0, f1, r.cam.data.lens * (amt or 2.0))
    elif m == "whip_pan": whip_pan(r, f0, f1, amt or 80); motion_blur(True)
    elif m == "follow": track(r, *sub(spec.get("subject")), f0, f1, smooth=amt if amt is not None else 0.6)
    elif m: raise ValueError(f"unknown camera move {m!r}")
    if "fstop" in spec or "focus" in spec:
        dof(r, spec.get("fstop", 2.8), *sub(spec.get("focus")))
    if "rack_to" in spec:
        at = f0 + int((f1 - f0) * spec.get("rack_at", 0.5)); dur = max(4, int((f1 - f0) * 0.25))
        a, ba = sub(spec.get("focus")); b, bb = sub(spec["rack_to"])
        rack_focus(r, at, min(f1, at + dur), a, b, ba, bb)
    if spec.get("handheld"): handheld(r, spec["handheld"])


# ---------------------------------------------------------------- self-check
def _selftest():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene; sc.frame_start, sc.frame_end = 1, 100
    a = _link(bpy.data.objects.new("A", None)); a.location = (0, 0, 1.5)
    b = _link(bpy.data.objects.new("B", None)); b.location = (2, 3, 1.5)
    r = rig("T", (0, -5, 1.5), (0, 0, 1.5), lens=35)
    dolly(r, 1, 20, 2.0); _at(20); assert abs(r.cam.location.y + 3.0) < 1e-4, r.cam.location
    _at(10); assert -5 < r.cam.location.y < -3                               # eased midway
    zoom(r, 21, 30, 35, 70); _at(30); assert abs(r.cam.data.lens - 70) < 1e-4
    dolly_zoom(r, 31, 40, 140); _at(40)
    assert abs((r.target.location - r.cam.location).length / r.cam.data.lens - 3.0 / 70) < 1e-4  # size kept
    pan(r, 41, 50, 90); _at(50); v = r.target.location - r.cam.location
    assert abs(v.x) > abs(v.y), v                                             # aim swung 90 degrees sideways
    rack_focus(r, 51, 60, a, b); _at(51); assert (r.focus.location - a.location).length < 1e-4
    _at(60); assert (r.focus.location - b.location).length < 1e-4 and r.cam.data.dof.use_dof
    b.keyframe_insert("location", frame=61); b.location = (4, 3, 1.5); b.keyframe_insert("location", frame=70)
    track(r, b, 61, 70, smooth=0.0); _at(70); assert (r.target.location - Vector((4, 3, 1.5))).length < 1e-4
    r2 = rig("P", (0, -5, 1.5), (0, 0, 1.5)); dolly(r2, 1, 10, 1.0)   # path must override keyed position
    path(r2, [(0, -5, 1.5), (3, -3, 2.0), (4, 0, 1.5)], 1, 30); _at(30); bpy.context.view_layer.update()
    assert (r2.cam.matrix_world.translation - Vector((4, 0, 1.5))).length < 0.05, r2.cam.matrix_world.translation
    handheld(r2, 0.5)
    r3 = rig("S", (0, -5, 1.5), (0, 0, 1.5))
    apply(r3, {"move": "dolly_in", "amount": 1.0, "fstop": 2.0, "focus": "A", "rack_to": "B"}, 1, 40,
          {"A": (a, None), "B": (b, None)})
    _at(40); assert abs(r3.cam.location.y + 4.0) < 1e-4 and r3.cam.data.dof.aperture_fstop == 2.0
    print("camera.py self-test OK")


if __name__ == "__main__":
    _selftest()
