"""Rule-based shot placement + sequence checks (bpy only).

place(): camera distance from shot size + lens, line-of-sight test (walls, props, the camera
inside a solid), swings around the subject when blocked, eyes on the upper third.
lint(): 180-degree rule, jump cuts, too-short shots, repetitive sizes, beat-based size suggestions.
Coverage: vertical angles (eye/low/high/overhead), over-the-shoulder, shot-reverse-shot pairs, inserts.
Direction: PURPOSE presets (when to hold, follow, anticipate, reveal), camera_lint(), parallax(), shotlist().
"""
import math
import bpy
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view

# visible frame height (m) at the subject for each shot size
SIZE_H = {"ecu": 0.30, "cu": 0.55, "mcu": 0.85, "med": 1.30, "full": 2.30, "wide": 4.2, "insert": 0.6}
EYE_LINE = {"ecu": 0.55, "cu": 0.66, "mcu": 0.68, "med": 0.70, "full": 0.78}  # target screen height of the eyes


def distance_for(size, lens, sensor=24.0, height=None):
    """Distance that makes `size` (or an explicit visible height in m) fill the frame vertically."""
    return (height or SIZE_H[size]) * lens / sensor


def _cast(origin, direction, maxd, ignore):
    """First hit not belonging to `ignore` along a ray; returns distance or None."""
    sc, dg = bpy.context.scene, bpy.context.evaluated_depsgraph_get()
    o, travelled = Vector(origin), 0.0
    for _ in range(32):
        hit, loc, _n, _i, ob, _m = sc.ray_cast(dg, o, direction, distance=maxd - travelled)
        if not hit: return None
        step = (loc - o).length
        if ob is not None and (ob.name in ignore or (ob.parent and ob.parent.name in ignore)):
            travelled += step + 1e-3; o = loc + direction * 1e-3; continue
        return travelled + step
    return None


def place(subject_pt, front, dist, angle_deg=0.0, height=0.0, ignore=(), margin=0.2, min_ratio=0.75, search=(15, 30, 45, 60, 75, 90)):
    """Camera position around subject_pt. front = direction the camera should look FROM.
    Returns (pos, info). Pulls in before obstacles; swings around if that loses >25% distance."""
    ignore = set(ignore)
    def candidate(deg):
        d = Matrix.Rotation(math.radians(deg), 3, "Z") @ Vector(front).normalized()
        d = (d * dist + Vector((0, 0, height))).normalized(); full = (d * dist + Vector((0, 0, height))).length
        hit = _cast(subject_pt, d, full, ignore)
        reach = full if hit is None else max(0.0, hit - margin)
        return reach / full, Vector(subject_pt) + d * reach, deg
    best = candidate(angle_deg)
    if best[0] < min_ratio:
        for s in search:
            for deg in (angle_deg + s, angle_deg - s):
                c = candidate(deg)
                if c[0] > best[0] + 1e-6: best = c
            if best[0] >= min_ratio: break
    return best[1], {"clear": round(best[0], 2), "swung": best[2] - angle_deg}


# ---------------------------------------------------------------- coverage framings
ELEVATION = {"eye": 0.0, "low": -18.0, "high": 32.0, "overhead": 86.0}  # camera elevation seen from the subject (deg)


def place_angle(subject_pt, front, dist, angle_deg=0.0, vertical="eye", ignore=(), floor=0.2):
    """place() with a named vertical angle: eye | low (looks up: power) | high (looks down: small, vulnerable)
    | overhead (plan view of a table / floor). Camera stays at least `floor` m above the ground."""
    e = math.radians(ELEVATION[vertical])
    pos, info = place(subject_pt, front, dist * math.cos(e), angle_deg, dist * math.sin(e), ignore=ignore)
    pos.z = max(pos.z, floor); return pos, info


def lens_for(size, dist, sensor=24.0):
    """Focal length (mm) that frames `size` from a fixed camera distance."""
    return sensor * dist / SIZE_H[size]


def _screen_x(pos, aim, pt, lens, sensor_w):
    """Horizontal frame position (0..1) of pt for a level camera at pos looking at aim (pinhole, no bpy)."""
    f = (aim - pos).normalized(); r = f.cross(Vector((0, 0, 1))).normalized(); u = r.cross(f)
    v = pt - pos; z = v.dot(f)
    return 0.5 + (v.dot(r) / z) * lens / sensor_w if z > 0 else 9.0


def ots(subject_head, other_head, size="mcu", lens=40.0, side=1, back=1.0, rise=0.08, shoulder_x=0.12, subject_x=0.6,
        aspect=9 / 16, sensor=24.0):
    """Over-the-shoulder: camera behind `other`, looking past their shoulder at `subject`. side +1/-1 picks the
    shoulder (keep one side per conversation: see reverse_pair). A small deterministic search sets the lateral
    offset and aim so the other's shoulder sits at `shoulder_x` from one frame edge and the subject's eyes at
    `subject_x` toward the other edge; the lens frames `size` from where the camera physically is.
    Returns (pos, aim, lens)."""
    a, b = Vector(subject_head), Vector(other_head)
    u = Vector((b.x - a.x, b.y - a.y, 0)).normalized()        # from subject toward other (and beyond)
    right = Vector((u.y, -u.x, 0)) * side
    base = b + u * back + Vector((0, 0, rise)); sw = sensor * aspect
    near = b + right * 0.2 - Vector((0, 0, 0.18))             # the other's shoulder
    best = None
    for i in range(0, 31):                                   # lateral offset 0 .. 0.6 m
        pos = base + right * (i * 0.02)
        ln = lens_for(size, (a - pos).length, sensor) if size else lens
        for j in range(0, 41):                               # aim slides from the subject toward the shoulder
            aim = a.lerp(near, j * 0.0125)
            sx, ox = _screen_x(pos, aim, a, ln, sw), _screen_x(pos, aim, near, ln, sw)
            if (sx - 0.5) * (ox - 0.5) >= 0: continue
            sc_ = (abs(ox - 0.5) - (0.5 - shoulder_x)) ** 2 + (abs(sx - 0.5) - (subject_x - 0.5)) ** 2
            if best is None or sc_ < best[0]: best = (sc_, pos, aim, ln)
    _, pos, aim, ln = best
    eye_drop = (aim_point(a, size, pos, ln) - a) if size in EYE_LINE else Vector()
    return pos, aim + eye_drop, ln


def reverse_pair(a_head, b_head, size="mcu", side=1, **kw):
    """Shot-reverse-shot coverage for A and B: [(pos, aim, lens) on A over B, ... on B over A], both cameras on the
    same side of the A-B line (180-degree rule) so eye-lines match across the cut."""
    return [ots(a_head, b_head, size, side=side, **kw), ots(b_head, a_head, size, side=-side, **kw)]


def insert_shot(points, lens=50.0, front=(0, -1, 0), vertical="high", fill=1.6, ignore=()):
    """Object insert: frame the bounding points of a prop (a bill, a phone screen) to fill ~1/fill of the frame."""
    pts = [Vector(p) for p in points]; c = sum(pts, Vector()) / len(pts)
    ext = max(max(p[i] for p in pts) - min(p[i] for p in pts) for i in range(3))
    dist = distance_for(None, lens, height=max(0.12, ext * fill))
    pos, info = place_angle(c, front, dist, 0.0, vertical, ignore=ignore, floor=0.05)
    return pos, c, info


def aim_point(head, size, cam_pos, lens, sensor=24.0):
    """Aim below the eyes so they land on the size's eye line (upper third for most sizes)."""
    if size not in EYE_LINE: return Vector(head)
    vis = (Vector(head) - Vector(cam_pos)).length * sensor / lens
    return Vector(head) - Vector((0, 0, (EYE_LINE[size] - 0.5) * vis))


def on_screen(cam, pt):
    """(x, y) in 0..1 frame coordinates and whether the point is visible."""
    v = world_to_camera_view(bpy.context.scene, cam, Vector(pt))
    return (v.x, v.y), (0 <= v.x <= 1 and 0 <= v.y <= 1 and v.z > 0)


def side_of_line(a, b, p):
    """+1 / -1: which side of the line a->b (top view) point p is on."""
    a, b, p = Vector(a), Vector(b), Vector(p)
    return 1 if ((b - a).x * (p - a).y - (b - a).y * (p - a).x) >= 0 else -1


# ---------------------------------------------------------------- shot-size suggestion + lint
REACT = ("smile", "laugh", "panic", "scream", "cry", "shock", "drop", "smirk", "grin", "yell")
DETAIL = ("$", "bill", "box", "card", "clock", "lobster", "roach", "cockroach", "book", "tag", "plaque", "404", "champagne")  # not "phone": it is in almost every shot
PLACE = ("walk", "lobby", "stroll", "enter", "carried", "floors", "stairs", "street", "store", "hall")


def suggest_size(text, first_in_scene=False):
    t = text.lower()
    if first_in_scene: return "wide", "first shot in a new location: establish it"
    if any(k in t for k in REACT): return "cu", "emotional beat: get on the face"
    if any(k in t for k in DETAIL): return "insert", "story-critical object: show it"
    if any(k in t for k in PLACE): return "wide", "movement through space"
    if "'" in text or '"' in text: return "med", "dialogue: medium or close"
    return None, ""


PRINCIPALS = ("INF", "CLK", "MGR")

# ---------------------------------------------------------------- direction
# Narrative purpose -> default framing and camera behaviour. Most beats HOLD: movement is spent where it means
# something (reference: steady handheld-feel coverage, moves reserved for action, reveals and transitions).
PURPOSE = {
    "establish": dict(size="wide", vertical="high", move={"move": "arc", "amount": 14, "radius": -0.4}),
    "dialogue":  dict(size="mcu", framing="ots", move={"move": "hold", "handheld": 0.12}),
    "reaction":  dict(size="cu", move={"move": "hold", "handheld": 0.1}),
    "realise":   dict(size="cu", move={"move": "push", "amount": 0.25, "delay": 0.2}),
    "action":    dict(size="med", move={"move": "follow", "amount": 0.85}),
    "anticipate": dict(size="wide", move={"move": "anticipate", "lead": 12}),
    "reveal":    dict(size="wide", move={"move": "reveal"}),
    "insert":    dict(size="insert", vertical="high", move={"move": "hold"}),
    "power":     dict(size="med", vertical="low", move={"move": "hold"}),
    "vulnerable": dict(size="med", vertical="high", move={"move": "hold"}),
    "geography": dict(size="wide", vertical="overhead", move={"move": "hold"}),
    "transition": dict(move={"move": "whip_pan", "amount": 70}),
}


def choose(purpose, **override):
    """Default shot design for a narrative purpose (copy; override any key)."""
    d = {k: (dict(v) if isinstance(v, dict) else v) for k, v in PURPOSE[purpose].items()}
    d.update(override); return d


def parallax(cam, f0, f1, near=1.5, far=15.0, step=4):
    """Physical-move check: two points on ONE camera ray at f0 (near m and far m away) stay on top of each other
    under any pan, tilt, zoom or frame crop; only real camera travel pulls them apart. Returns their largest
    screen separation over [f0, f1] in frame fractions (0 = no parallax; > 0.02 reads as a physical move)."""
    sc = bpy.context.scene; sc.frame_set(f0); bpy.context.view_layer.update()
    m = cam.matrix_world; o = m.translation.copy(); d = (m.to_3x3() @ Vector((0.18, 0.12, -1))).normalized()  # a ray off the optical axis
    a, b = o + d * near, o + d * far; best = 0.0
    for f in list(range(f0, f1 + 1, step)) + [f1]:
        sc.frame_set(f); bpy.context.view_layer.update()
        pa, pb = world_to_camera_view(sc, cam, a), world_to_camera_view(sc, cam, b)
        best = max(best, math.hypot(pa.x - pb.x, pa.y - pb.y))
    return round(best, 3)


MOVING = ("dolly", "move", "truck", "pedestal", "crane", "pan", "tilt", "whip_pan", "orbit", "arc", "zoom",
          "dolly_zoom", "path", "track", "anticipate", "follow", "reveal")


def camera_lint(rows, max_moving=0.7, max_zoom=1.35):
    """rows: shot-list dicts (see shotlist()). Flags camera language that reads as automatic, not operated."""
    out = []
    kinds = [tuple(sorted({m.split()[0] for m in r["movement"].split("; ") if m.split() and m.split()[0] in MOVING})) for r in rows]
    moving = [k for k in kinds if k]
    if rows and len(moving) / len(rows) > max_moving:
        out.append(f"camera moves in {len(moving)}/{len(rows)} shots - hold some beats still (dialogue, reactions)")
    for i in range(2, len(rows)):
        if kinds[i] and kinds[i] == kinds[i - 1] == kinds[i - 2]:
            out.append(f"shot {rows[i]['id']}: third '{'+'.join(kinds[i])}' in a row - vary the move or hold")
    for r in rows:
        z = max(r["lens_start"], r["lens_end"]) / min(r["lens_start"], r["lens_end"])
        if z > max_zoom: out.append(f"shot {r['id']}: lens changes x{z:.2f} - dolly instead of zooming (keeps parallax)")
        if r.get("parallax") is not None and r["cam_start"] != r["cam_end"] and r["parallax"] < 0.02:
            out.append(f"shot {r['id']}: camera barely travels (parallax {r['parallax']:.3f}) - reads as a zoom; move further or hold")
        if not r.get("purpose"): out.append(f"shot {r['id']}: no narrative purpose")
    return out


def shotlist(rows, path=None, fps=24):
    """Markdown shot list. rows: dicts with id, f0, f1, type, subject, purpose + camera.describe() fields."""
    ts = lambda f: f"{(f - 1) / fps:05.2f}"
    xyz = lambda v: "(%.1f, %.1f, %.1f)" % v
    lines = ["| # | Time (s) | Shot type | Subject | Camera position (start -> end) | Lens (mm) | Movement | Focus | Purpose |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        cam = xyz(r["cam_start"]) + ("" if r["cam_start"] == r["cam_end"] else " -> " + xyz(r["cam_end"]))
        lens = f"{r['lens_start']:.0f}" + ("" if r["lens_start"] == r["lens_end"] else f" -> {r['lens_end']:.0f}")
        foc = r["focus"] + (f" f/{r['fstop']}" if r.get("fstop") else "")
        lines.append(f"| {r['id']} | {ts(r['f0'])}-{ts(r['f1'] + 1)} | {r['type']} | {r['subject']} | {cam} | {lens} | {r['movement']} | {foc} | {r.get('purpose', '')} |")
    md = "\n".join(lines) + "\n"
    if path: open(path, "w").write(md)
    return md


def lint(records, min_len=0.7):
    """records: dicts with id, set, t0, t1, size, subject, cam (Vector), chars {name: Vector}, text.
    Returns warning strings."""
    out, prev, streak, sides = [], None, 1, {}
    for r in records:
        dur = r["t1"] - r["t0"]
        if dur < min_len: out.append(f"shot {r['id']}: only {dur:.2f}s - hard to read, merge or extend")
        if prev and prev["set"] == r["set"] and prev["subject"] == r["subject"] and prev["size"] == r["size"] and r["cam"] and prev["cam"]:
            va, vb = prev["cam"] - prev["aim"], r["cam"] - r["aim"]
            if va.length and vb.length and va.angle(vb) < math.radians(25):
                out.append(f"shot {r['id']}: jump cut from shot {prev['id']} (same subject, size and angle) - change size or move 30+ degrees")
        streak = streak + 1 if prev and prev["size"] == r["size"] else 1
        if streak == 4: out.append(f"shot {r['id']}: 4 '{r['size']}' shots in a row - vary the framing")
        names = sorted(n for n in r.get("chars", {}) if n in PRINCIPALS)
        if r["cam"] and len(names) >= 2:  # the 180-degree line only matters between the principals
            a, b = names[0], names[1]
            key = (r["set"], a, b); side = side_of_line(r["chars"][a], r["chars"][b], r["cam"])
            if key in sides and sides[key][0] != side:
                out.append(f"shot {r['id']}: crosses the 180-degree line between {a} and {b} (set by shot {sides[key][1]})")
            sides.setdefault(key, (side, r["id"]))
        sug, why = suggest_size(r.get("text", ""), r.get("first_in_scene", False))
        ok = {"cu": ("ecu", "mcu"), "med": ("mcu", "cu", "ecu"), "insert": ("cu", "ecu")}.get(sug, ())
        if sug and sug != r["size"] and r["size"] not in ok:
            out.append(f"shot {r['id']}: is '{r['size']}', beat suggests '{sug}' ({why})")
        prev = r
    return out


def _selftest():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -2.0, 1)); wall = bpy.context.object; wall.scale = (6, 0.1, 4)
    bpy.ops.mesh.primitive_cube_add(size=0.4, location=(0, 0, 1.5)); hero = bpy.context.object; hero.name = "HERO"
    bpy.context.view_layer.update()
    pos, info = place((0, 0, 1.5), (0, -1, 0), 4.0, ignore={"HERO"}, min_ratio=0.0)
    assert pos.y > -2.0 and info["clear"] < 0.5, (pos, info)            # pulled in front of the wall
    pos, info = place((0, 0, 1.5), (0, -1, 0), 4.0, ignore={"HERO"})    # wall blocks -> swing round to open side
    assert info["clear"] >= 0.75 and abs(info["swung"]) >= 60, (pos, info)
    assert abs(distance_for("med", 30) - 1.625) < 1e-6
    assert side_of_line((0, 0, 0), (1, 0, 0), (0, 1, 0)) == 1 and side_of_line((0, 0, 0), (1, 0, 0), (0, -1, 0)) == -1
    V = Vector
    recs = [dict(id=1, set="a", t0=0, t1=2, size="cu", subject="X", cam=V((0, -2, 1.6)), aim=V((0, 0, 1.6)), chars={"INF": V((0, 0, 0)), "CLK": V((1, 0, 0))}, text=""),
            dict(id=2, set="a", t0=2, t1=2.4, size="cu", subject="X", cam=V((0.2, -2, 1.6)), aim=V((0, 0, 1.6)), chars={"INF": V((0, 0, 0)), "CLK": V((1, 0, 0))}, text=""),
            dict(id=3, set="a", t0=3, t1=5, size="med", subject="Y", cam=V((0, 3, 1.6)), aim=V((0, 0, 1.6)), chars={"INF": V((0, 0, 0)), "CLK": V((1, 0, 0))}, text="He laughed")]
    w = "\n".join(lint(recs))
    assert "jump cut" in w and "0.40s" in w and "180-degree" in w and "beat suggests 'cu'" in w, w
    # coverage: reverse pair keeps both cameras on one side of the A-B line; the lens frames the size
    A, B = V((0, 0, 1.6)), V((0, 2, 1.6))
    (p1, a1, l1), (p2, a2, l2) = reverse_pair(A, B, "mcu")
    assert side_of_line(A, B, p1) == side_of_line(A, B, p2), (p1, p2)
    assert abs(distance_for(None, l1, height=SIZE_H["mcu"]) - (A - p1).length) < 1e-6 and p1.y > B.y and p2.y < A.y
    cd0 = bpy.data.cameras.new("OTS"); cd0.lens = l1; cd0.sensor_fit = "VERTICAL"
    co0 = bpy.data.objects.new("OTS", cd0); bpy.context.scene.collection.objects.link(co0)
    bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 1080, 1920
    co0.location = p1; co0.rotation_euler = (a1 - p1).to_track_quat("-Z", "Y").to_euler(); bpy.context.view_layer.update()
    (sx, sy), vis = on_screen(co0, A); (ox, oy), _ = on_screen(co0, B + V((0.2, 0, -0.18)))  # B's near shoulder
    assert vis and 0.15 < sx < 0.85 and 0.0 < ox < 1.0 and (ox - 0.5) * (sx - 0.5) < 0, (sx, ox)  # shoulder in frame, opposite half
    lo, _ = place_angle(V((0, 0, 1.0)), (0, -1, 0), 3.0, vertical="low", ignore={"HERO"})
    hi, _ = place_angle(V((0, 0, 1.0)), (0, -1, 0), 3.0, vertical="overhead", ignore={"HERO"})
    assert lo.z < 1.0 and hi.z > 3.5, (lo, hi)
    assert choose("dialogue")["move"]["move"] == "hold" and choose("action", size="wide")["size"] == "wide"
    rows = [dict(id=i, f0=1 + 24 * i, f1=24 + 24 * i, type="cu", subject="X", purpose="p", cam_start=(0, 0, 1), cam_end=(1, 0, 1),
                 lens_start=35, lens_end=35 if i else 60, focus="X", fstop=2.0, movement="truck +1.00 m", parallax=0.01) for i in range(4)]
    w = "\n".join(camera_lint(rows))
    assert "moves in 4/4" in w and "third 'truck'" in w and "x1.71" in w and "barely travels" in w, w
    # parallax: a pan gives none, a truck gives plenty
    cd = bpy.data.cameras.new("PX"); co = bpy.data.objects.new("PX", cd); bpy.context.scene.collection.objects.link(co)
    co.location = (0, -5, 1.5); co.rotation_euler = (math.pi / 2, 0, 0); co.keyframe_insert("location", frame=1)
    co.keyframe_insert("rotation_euler", frame=1); co.rotation_euler = (math.pi / 2, 0, 0.4); co.keyframe_insert("rotation_euler", frame=20)
    co.keyframe_insert("location", frame=20); assert parallax(co, 1, 20) < 1e-3
    co.location = (1.5, -5, 1.5); co.keyframe_insert("location", frame=40); co.keyframe_insert("rotation_euler", frame=40)
    assert parallax(co, 20, 40) > 0.05, parallax(co, 20, 40)
    md = shotlist(rows); assert md.count("\n") == 6 and "00.00-01.00" in md, md
    print("shotcraft.py self-test OK")


if __name__ == "__main__":
    _selftest()
