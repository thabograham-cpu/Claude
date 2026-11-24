"""Rule-based shot placement + sequence checks (bpy only).

place(): camera distance from shot size + lens, line-of-sight test (walls, props, the camera
inside a solid), swings around the subject when blocked, eyes on the upper third.
lint(): 180-degree rule, jump cuts, too-short shots, repetitive sizes, beat-based size suggestions.
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
DETAIL = ("$", "bill", "box", "card", "clock", "lobster", "roach", "cockroach", "book", "tag", "plaque", "404", "champagne", "phone")
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
    print("shotcraft.py self-test OK")


if __name__ == "__main__":
    _selftest()
