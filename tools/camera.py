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
    C.follow(r, hero, 1, 96, bone="head", lag=0.85)             # tracking shot: camera travels with the subject
    C.truck(r, 1, 48, 1.0); C.pedestal(r, 1, 48, 0.4)          # lateral / vertical slide, aim travels too
    C.reveal(r, 1, 60, pillar, hero, bone="head")               # slide out from behind a foreground object
    C.hold(r, 1, 48)                                            # intentional locked-off hold
    C.follow_focus(r, hero, 1, 96, bone="head")                 # focus rides the subject, camera untouched

Rig = CAM_<name> (Track To) + EMPTY_CamTarget_<name> (aim) + EMPTY_CamFocus_<name> (DoF focus).
Each move keys every frame of [f0, f1] from the rig's state at f0, so moves on *different* channels
(camera position / aim / lens / focus) combine freely; moves on the same channel must not overlap in time.
Subjects can be an object, an armature + bone name, or a point (x, y, z).
Everything is deterministic: per-frame keys from scene state, noise phases from object names (no randomness).
Rig.log records every move for shot lists (describe()).
"""
import math, zlib
import bpy
from bpy_extras import anim_utils
from mathutils import Vector, Matrix

EASE = {
    "linear": lambda t: t,
    "inout": lambda t: t * t * t * (t * (6 * t - 15) + 10),  # smootherstep: no jolt at start or stop
    "in": lambda t: t * t * t,                               # accelerate into a cut / whip
    "out": lambda t: 1 - (1 - t) ** 3,                       # land softly from a cut
}


class Rig:
    def __init__(self, cam, target, focus):
        self.cam, self.target, self.focus = cam, target, focus
        self.log = []  # (move, f0, f1, detail) for shot lists


def _note(r, move, f0, f1, detail=""):
    r.log.append((move, f0, f1, detail))


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
    _note(r, "dolly", f0, f1, f"{distance:+.2f} m")
    _at(f0); a = r.cam.location.copy(); d = (r.target.location - a).normalized()
    def s(f, t): r.cam.location = a + d * distance * t; _key(r.cam, "location", f)
    _run(f0, f1, ease, s)


def move(r, f0, f1, delta, ease="inout"):
    """Truck / pedestal: translate camera AND aim together by delta (x, y, z)."""
    _note(r, "move", f0, f1, "(%.2f, %.2f, %.2f) m" % tuple(delta))
    _at(f0); a, b = r.cam.location.copy(), r.target.location.copy(); dv = Vector(delta)
    def s(f, t):
        r.cam.location = a + dv * t; r.target.location = b + dv * t
        _key(r.cam, "location", f); _key(r.target, "location", f)
    _run(f0, f1, ease, s)


def crane(r, f0, f1, height, ease="inout"):
    """Raise/lower the camera only; aim stays put, so the view tilts to follow."""
    _note(r, "crane", f0, f1, f"{height:+.2f} m")
    _at(f0); a = r.cam.location.copy()
    def s(f, t): r.cam.location = a + Vector((0, 0, height * t)); _key(r.cam, "location", f)
    _run(f0, f1, ease, s)


def pan(r, f0, f1, degrees, tilt=0.0, ease="inout"):
    """Swing the aim around the camera (pan = yaw, tilt = pitch); camera stays put."""
    _note(r, "pan" if degrees else "tilt", f0, f1, (f"{degrees:+.0f} deg" + (f", tilt {tilt:+.0f} deg" if tilt else "") if degrees else f"{tilt:+.0f} deg"))
    _at(f0); c = r.cam.location.copy(); v0 = r.target.location - c
    side = v0.cross(Vector((0, 0, 1))).normalized()
    def s(f, t):
        v = Matrix.Rotation(math.radians(degrees * t), 3, "Z") @ v0
        if tilt: v = Matrix.Rotation(math.radians(tilt * t), 3, side) @ v
        r.target.location = c + v; _key(r.target, "location", f)
    _run(f0, f1, ease, s)


def whip_pan(r, f0, f1, degrees=80):
    """Fast motivated pan; pair with motion_blur(True)."""
    pan(r, f0, f1, degrees, ease="in"); r.log[-1] = ("whip_pan",) + r.log[-1][1:]


def orbit(r, f0, f1, degrees, rise=0.0, radius=0.0, ease="inout"):
    """Circle the camera around the aim point. Arc: add rise (m up) and radius (m out; negative pushes in)."""
    _note(r, "orbit" if not (rise or radius) else "arc", f0, f1, f"{degrees:+.0f} deg" + (f" rise {rise:+.2f}" if rise else "") + (f" radius {radius:+.2f}" if radius else ""))
    _at(f0); p = r.target.location.copy(); v0 = r.cam.location - p
    h0 = Vector((v0.x, v0.y, 0)).length or 1e-6
    def s(f, t):
        v = Matrix.Rotation(math.radians(degrees * t), 3, "Z") @ v0
        hv = Vector((v.x, v.y, 0)) * ((h0 + radius * t) / h0)
        r.cam.location = p + hv + Vector((0, 0, v0.z + rise * t)); _key(r.cam, "location", f)
    _run(f0, f1, ease, s)


def zoom(r, f0, f1, lens0, lens1, ease="inout"):
    """Optical zoom: animate focal length (mm)."""
    _note(r, "zoom", f0, f1, f"{lens0:.0f}->{lens1:.0f} mm")
    def s(f, t): r.cam.data.lens = lens0 + (lens1 - lens0) * t; _key(r.cam.data, "lens", f)
    _run(f0, f1, ease, s)


def dolly_zoom(r, f0, f1, lens1, ease="inout"):
    """'Vertigo': change lens while dollying so the aim point keeps its on-screen size."""
    _note(r, "dolly_zoom", f0, f1, f"->{lens1:.0f} mm")
    _at(f0); a = r.cam.location.copy(); p = r.target.location.copy(); l0 = r.cam.data.lens
    d0 = (p - a).length; u = (a - p).normalized()
    def s(f, t):
        lens = l0 + (lens1 - l0) * t
        r.cam.data.lens = lens; r.cam.location = p + u * d0 * lens / l0   # distance / lens stays constant
        _key(r.cam.data, "lens", f); _key(r.cam, "location", f)
    _run(f0, f1, ease, s)


def track(r, subject, f0, f1, bone=None, offset=(0, 0, 0), smooth=0.0, focus=True, lead=0):
    """Aim (and focus) follow a moving subject; camera stays put (a follow pan).
    smooth 0..0.95 = lazy operator-style lag; lead = frames of anticipation (aim where the subject is going)."""
    _note(r, "track" if not lead else "anticipate", f0, f1, getattr(subject, "name", "point") + (f" lead {lead}f" if lead else ""))
    off = Vector(offset); prev = None
    for f in range(f0, f1 + 1):
        _at(f + lead); ahead = where(subject, bone) + off
        if lead: _at(f)
        raw = where(subject, bone) + off
        prev = ahead if prev is None else prev.lerp(ahead, 1 - smooth)
        r.target.location = prev; _key(r.target, "location", f)
        if focus: r.focus.location = raw; _key(r.focus, "location", f)


def follow(r, subject, f0, f1, bone=None, offset=None, lag=0.85, lead=0, aim_offset=(0, 0, 0), focus=True):
    """Tracking shot: the camera TRAVELS with a moving subject at a fixed offset (camera minus subject, world m;
    default = where the camera sits at f0). Camera in front of a walker = backward tracking (leading),
    behind = forward tracking (following), beside = parallel tracking. lag 0..0.95 = operator catch-up;
    lead = frames the aim anticipates the subject's path."""
    _note(r, "follow", f0, f1, getattr(subject, "name", "point") + (f" lead {lead}f" if lead else ""))
    _at(f0); off = Vector(offset) if offset is not None else r.cam.location - where(subject, bone)
    ao = Vector(aim_offset); cam = aim = None
    for f in range(f0, f1 + 1):
        _at(f + lead); ahead = where(subject, bone) + ao
        _at(f); p = where(subject, bone)
        cam = p + off if cam is None else cam.lerp(p + off, 1 - lag)
        aim = ahead if aim is None else aim.lerp(ahead, 1 - lag * 0.6)  # the operator re-aims faster than they walk
        r.cam.location, r.target.location = cam, aim; _key(r.cam, "location", f); _key(r.target, "location", f)
        if focus: r.focus.location = p; _key(r.focus, "location", f)


def truck(r, f0, f1, distance, ease="inout"):
    """Lateral slide along the camera's own right axis (negative = left); aim travels with it."""
    _at(f0); fwd = r.target.location - r.cam.location; right = Vector((fwd.y, -fwd.x, 0)).normalized()
    move(r, f0, f1, right * distance, ease); r.log[-1] = ("truck", f0, f1, f"{distance:+.2f} m")


def pedestal(r, f0, f1, height, ease="inout"):
    """Raise/lower camera AND aim together (framing height changes, angle doesn't)."""
    move(r, f0, f1, (0, 0, height), ease); r.log[-1] = ("pedestal", f0, f1, f"{height:+.2f} m")


def hold(r, f0, f1, focus=True):
    """Intentional static hold: camera, aim, lens (and focus) keyed identical at f0 and f1 (nothing drifts).
    focus=False leaves the focus channel free for a rack or follow focus inside the hold."""
    _note(r, "hold", f0, f1)
    chans = [(r.cam, "location"), (r.target, "location"), (r.cam.data, "lens")] + ([(r.focus, "location")] if focus else [])
    _at(f0); state = [(o, p, getattr(o, p).copy() if hasattr(getattr(o, p), "copy") else getattr(o, p)) for o, p in chans]
    for f in (f0, f1):
        for o, p, v in state: setattr(o, p, v); _key(o, p, f)


def reveal(r, f0, f1, occluder, subject, bone=None, side=0, margin=0.12, ease="inout"):
    """Foreground reveal: the shot opens blocked by `occluder`; the camera slides sideways (aim held on the
    subject) exactly far enough that the occluder clears the line of sight. side +1 right, -1 left, 0 = shorter.
    Place the camera so the occluder sits between it and the subject at f0. Returns the slide (m)."""
    _at(f0); c = r.cam.location.copy(); sp = where(subject, bone)
    fwd = sp - c; D = fwd.length; fwd.normalize(); right = Vector((fwd.y, -fwd.x, 0)).normalized()
    corners = [occluder.matrix_world @ Vector(v) for v in occluder.bound_box]
    need_r, need_l = [], []
    for q in corners:
        z = (q - c).dot(fwd)
        if not 0 < z < D: continue
        lat, k = (q - c).dot(right), 1 - z / D   # the sight line's lateral offset at depth z is s * k
        need_r.append((lat + margin) / k); need_l.append((lat - margin) / k)
    if not need_r: raise ValueError(f"{occluder.name} is not between the camera and the subject")
    sr, sl = max(need_r), min(need_l)
    s_ = sr if side > 0 or (side == 0 and abs(sr) <= abs(sl)) else sl
    _note(r, "reveal", f0, f1, f"past {occluder.name}, slide {s_:+.2f} m")
    def st(f, t): r.cam.location = c + right * s_ * t; _key(r.cam, "location", f)
    _run(f0, f1, ease, st)
    r.target.location = sp; _key(r.target, "location", f0); _key(r.target, "location", f1)
    return s_





def path(r, points, f0, f1, ease="inout"):
    """Camera rides a smooth curve through points (replaces any keyed camera position)."""
    _note(r, "path", f0, f1, f"{len(points)} points")
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


def handheld(r, strength=0.25, scale=14.0, f0=None, f1=None):
    """Operator shake as noise on the aim (+ a little on the camera). 0.1-0.3 subtle (default),
    0.5-0.8 documentary, 1.0+ panic. f0/f1 limit it to one shot with soft 6-frame ramps.
    Deterministic: noise phase comes from the object name."""
    _note(r, "handheld", f0 or 0, f1 or 0, f"{strength:.2f}")
    for obj, k in ((r.target, 0.03), (r.cam, 0.008)):
        if not _fcurves(obj): obj.keyframe_insert("location", frame=f0 or bpy.context.scene.frame_start)
        for fc in _fcurves(obj):
            if fc.data_path == "location":
                n = fc.modifiers.new("NOISE"); n.strength = strength * k * 2; n.scale = scale
                n.phase = (zlib.crc32(obj.name.encode()) % 997) / 10 + 13 * fc.array_index
                if f0 is not None and f1 is not None:
                    n.use_restricted_range = True; n.frame_start, n.frame_end = f0, f1
                    n.blend_in = n.blend_out = min(6, (f1 - f0) / 3)


# ---------------------------------------------------------------- focus
def dof(r, fstop=2.8, focus=None, bone=None, blades=0):
    """Enable depth of field; focus empty placed on the subject (or keep it on the aim)."""
    d = r.cam.data.dof; d.use_dof = True; d.aperture_fstop = fstop; d.aperture_blades = blades
    d.focus_object = r.focus
    p = where(focus, bone)
    if p is not None: r.focus.location = p


def rack_focus(r, f0, f1, a, b, bone_a=None, bone_b=None, ease="inout"):
    """Pull focus from subject a to subject b (focus empty glides between them)."""
    _note(r, "rack_focus", f0, f1, f"{getattr(a, 'name', 'point')} -> {getattr(b, 'name', 'point')}")
    if not r.cam.data.dof.use_dof: dof(r)
    _at(f0); pa = where(a, bone_a); _at(f1); pb = where(b, bone_b)
    def s(f, t): r.focus.location = pa.lerp(pb, t); _key(r.focus, "location", f)
    _run(f0, f1, ease, s)


def follow_focus(r, subject, f0, f1, bone=None):
    """Focus distance rides a moving subject every frame; camera and aim are untouched."""
    _note(r, "follow_focus", f0, f1, getattr(subject, "name", "point"))
    if not r.cam.data.dof.use_dof: dof(r)
    for f in range(f0, f1 + 1):
        _at(f); r.focus.location = where(subject, bone); _key(r.focus, "location", f)


def describe(r, f0, f1, focus_name=None):
    """Shot-list facts for a rig over [f0, f1]: camera start/end, lens, f-stop, focus, logged moves."""
    out = {}
    for tag, f in (("start", f0), ("end", f1)):
        _at(f); bpy.context.view_layer.update()
        out[f"cam_{tag}"] = tuple(round(v, 2) for v in r.cam.matrix_world.translation)
        out[f"lens_{tag}"] = round(r.cam.data.lens, 1)
        out[f"aim_{tag}"] = tuple(round(v, 2) for v in r.target.matrix_world.translation)
    d = r.cam.data.dof
    out["fstop"] = round(d.aperture_fstop, 1) if d.use_dof else None
    out["focus"] = focus_name or ("aim" if not d.use_dof else r.focus.name)
    moves = [f"{m} {x}".strip() for m, a, b, x in r.log if (a, b) == (0, 0) or (a <= f1 and b >= f0)]
    out["movement"] = "; ".join(moves) or "static"
    return out


def motion_blur(on=True, shutter=0.5):
    sc = bpy.context.scene; sc.render.use_motion_blur = on; sc.render.motion_blur_shutter = shutter


# ---------------------------------------------------------------- shot-list hook
def apply(r, spec, f0, f1, subjects=None):
    """Apply a shot-list move dict, e.g. {"move": "dolly_in", "amount": 0.8, "fstop": 2, "focus": "INF",
    "rack_to": "CLK", "rack_at": 0.5, "handheld": 0.2}. subjects: name -> (object, bone).
    No "move" (or "hold") = an intentional locked-off hold. Moves start after `delay` (0..1 of the shot)."""
    subjects = subjects or {}
    sub = lambda n: subjects.get(n, (None, None))
    m, amt = spec.get("move", "hold"), spec.get("amount")
    g0 = f0 + int((f1 - f0) * spec.get("delay", 0)); e = spec.get("ease", "inout")
    if m in ("hold", None): hold(r, f0, f1, focus=not ("rack_to" in spec or spec.get("follow_focus")))
    elif m in ("dolly_in", "push"): dolly(r, g0, f1, amt or 0.6, e)
    elif m in ("dolly_out", "pull"): dolly(r, g0, f1, -(amt or 0.6), e)
    elif m in ("pan_left", "pan_right"): pan(r, g0, f1, (amt or 25) * (1 if m == "pan_left" else -1), ease=e)
    elif m in ("tilt_up", "tilt_down"): pan(r, g0, f1, 0, tilt=(amt or 15) * (1 if m == "tilt_up" else -1), ease=e)
    elif m in ("truck_left", "truck_right"): truck(r, g0, f1, (amt or 0.8) * (1 if m == "truck_right" else -1), e)
    elif m in ("pedestal_up", "pedestal_down"): pedestal(r, g0, f1, (amt or 0.4) * (1 if m == "pedestal_up" else -1), e)
    elif m == "orbit": orbit(r, g0, f1, amt or 30, ease=e)
    elif m == "arc": orbit(r, g0, f1, amt or 20, spec.get("rise", 0.0), spec.get("radius", -0.3), e)
    elif m == "crane_up": crane(r, g0, f1, amt or 1.0, e)
    elif m == "crane_down": crane(r, g0, f1, -(amt or 1.0), e)
    elif m == "zoom_in": zoom(r, g0, f1, r.cam.data.lens, r.cam.data.lens * (amt or 1.3), e)
    elif m == "zoom_out": zoom(r, g0, f1, r.cam.data.lens, r.cam.data.lens / (amt or 1.3), e)
    elif m == "dolly_zoom": dolly_zoom(r, g0, f1, r.cam.data.lens * (amt or 2.0), e)
    elif m == "whip_pan": whip_pan(r, g0, f1, amt or 80); motion_blur(True)
    elif m in ("track", "anticipate", "follow", "reveal"):
        so, sb_ = sub(spec.get("subject"))
        if m == "track": track(r, so, f0, f1, bone=sb_, smooth=amt if amt is not None else 0.6, lead=spec.get("lead", 0))
        elif m == "anticipate": track(r, so, f0, f1, bone=sb_, smooth=0.7, lead=spec.get("lead", 12))
        elif m == "follow": follow(r, so, f0, f1, bone=sb_, lag=amt if amt is not None else 0.85, lead=spec.get("lead", 0))
        else:
            occ = spec["occluder"]; occ = bpy.data.objects[occ] if isinstance(occ, str) else occ
            reveal(r, g0, f1, occ, so, bone=sb_, side=spec.get("side", 0), ease=e)
    else: raise ValueError(f"unknown camera move {m!r}")
    if "fstop" in spec or "focus" in spec:
        dof(r, spec.get("fstop", 2.8), *sub(spec.get("focus")))
    if spec.get("follow_focus"):
        fo, fb = sub(spec["follow_focus"]); follow_focus(r, fo, f0, f1, bone=fb)
    if "rack_to" in spec:
        at = f0 + int((f1 - f0) * spec.get("rack_at", 0.5)); dur = max(8, int((f1 - f0) * 0.25))
        a, ba = sub(spec.get("focus")); b, bb = sub(spec["rack_to"])
        rack_focus(r, at, min(f1, at + dur), a, b, ba, bb)
    if spec.get("handheld"): handheld(r, spec["handheld"], f0=f0, f1=f1)


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
    # smooth starts/stops: first and last frame steps are tiny next to the middle step
    _at(1); y0 = r3.cam.location.y; _at(2); y1 = r3.cam.location.y; _at(20); ym = r3.cam.location.y; _at(21)
    assert abs(y1 - y0) < 0.05 * abs(r3.cam.location.y - ym), "move must ease in"
    # new moves on a walker: W walks +Y 0 -> 6 m over frames 101-160
    sc.frame_end = 300
    w = _link(bpy.data.objects.new("W", None)); w.location = (0, 0, 1.6); w.keyframe_insert("location", frame=101)
    w.location = (0, 6, 1.6); w.keyframe_insert("location", frame=160)
    for fc in _fcurves(w):
        for kp in fc.keyframe_points: kp.interpolation = "LINEAR"
    rf = rig("F", (0, 2.5, 1.7), (0, 0, 1.6))               # in front of him: backward (leading) tracking
    follow(rf, w, 101, 200, lag=0.8); _at(200)
    assert (rf.cam.location - Vector((0, 8.5, 1.7))).length < 0.02, rf.cam.location   # settles at the same offset
    ra = rig("AN", (3, 3, 1.6), (0, 0, 1.6)); track(ra, w, 101, 130, lead=12); _at(115)
    assert ra.target.location.y > w.location.y, "anticipation aims ahead of the walker"
    rt = rig("TR", (0, -5, 1.5), (0, 0, 1.5)); truck(rt, 1, 20, 1.0); _at(20)
    assert abs(rt.cam.location.x - 1.0) < 1e-4 and abs(rt.target.location.x - 1.0) < 1e-4   # +X is camera-right here
    ro = rig("AR", (0, -4, 1.5), (0, 0, 1.5)); orbit(ro, 1, 30, 90, rise=0.5, radius=-1.0); _at(30)
    assert abs(Vector((ro.cam.location.x, ro.cam.location.y)).length - 3.0) < 1e-3 and abs(ro.cam.location.z - 2.0) < 1e-4
    rh = rig("H", (0, -4, 1.5), (0, 0, 1.5)); hold(rh, 1, 50); handheld(rh, 0.25, f0=1, f1=50); _at(25)
    p25 = rh.cam.matrix_world.translation.copy(); _at(1)
    assert (p25 - Vector((0, -4, 1.5))).length < 0.02, "hold + subtle handheld stays put"
    n = [m for fc in _fcurves(rh.target) for m in fc.modifiers][0]
    assert abs(n.phase - (zlib.crc32(rh.target.name.encode()) % 997) / 10) < 1e-4, "deterministic noise phase"
    # reveal: a pillar blocks the view at f0 and clears by f1
    bpy.ops.mesh.primitive_cylinder_add(radius=0.3, depth=3, location=(0.1, -2, 1.5)); pil = bpy.context.object
    s_ = bpy.data.objects.new("SUBJ", None); _link(s_); s_.location = (0, 2, 1.5)
    rv = rig("RV", (0, -4, 1.5), s_.location); slide = reveal(rv, 1, 40, pil, s_)
    dg = bpy.context.evaluated_depsgraph_get()
    def blocked(f):
        _at(f); bpy.context.view_layer.update(); c = rv.cam.matrix_world.translation; d = s_.location - c
        return sc.ray_cast(bpy.context.evaluated_depsgraph_get(), c, d.normalized(), distance=d.length)[0]
    assert blocked(1) and not blocked(40) and slide < 0, (slide,)          # pillar is right of centre -> slide left
    ra2 = rig("AP", (0, 2.5, 1.7), (0, 0, 1.6)); apply(ra2, {"move": "follow", "subject": "W", "amount": 0.8}, 101, 200, {"W": (w, None)})
    _at(200); assert (ra2.cam.location - Vector((0, 8.5, 1.7))).length < 0.02
    dsc = describe(rv, 1, 40)
    assert dsc["cam_start"] != dsc["cam_end"] and "reveal" in dsc["movement"], dsc
    print("camera.py self-test OK")


if __name__ == "__main__":
    _selftest()
