"""Camera coverage demo: one continuous scene in the persistent hotel lobby, covered like an operated film.
Build:  bash projects/camera-demo/build.sh coverage   (fresh -> projects/camera-demo/coverage.blend)
Writes coverage_shotlist.md + coverage_segs.json BEFORE any render; render frames_cov/ with render_range.py, then
SEGS=coverage_segs.json OUT=CameraCoverage_Hotel.mp4 FRAMES=frames_cov python3 projects/camera-demo/finish.py

Story: he walks in livestreaming, demands service at the desk, slaps down the bill, laughs. The clerk reacts.
Every shot is a camera.py rig with a narrative purpose (shotcraft.PURPOSE); most beats hold, moves are motivated."""
import os, sys, json, math, runpy
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sb = runpy.run_path(os.path.join(ROOT, "projects", "complainer", "storyboard.py"), run_name="storyboard_lib")
import look, camera as C, shotcraft as SC  # storyboard put complainer/ and tools/ on sys.path

RIGS, OBJ, POSES, head = (sb[k] for k in ("RIGS", "OBJ", "POSES", "head"))
sc = bpy.context.scene; FPS = 24
look.eevee(sb, os.path.join(HERE, "frames_cov", "f_"))
look.add_step_poses(POSES)
C.motion_blur(True, 0.5)
RIGS["MGR"].location = (0, -100, 0)
for n in ("open_case", "small_box", "roach_box", "roach"): OBJ[n].location = (0, -200, 0)
OBJ["cart"].location = (-2.2, 3.6, 0)
bpy.data.objects["TXT_stamp"].hide_render = True; bpy.data.objects["TXT_tag"].data.body = ""
key = lambda *a: look.key_rig(sb, *a)

# ---------------- blocking (one take; the camera covers it) ----------------
WALK0, WALK1 = 1, 216                         # entrance -> desk, 7.5 m in 9 s
INF_DESK, CLK_POS = (0.2, 1.05, 0), (0, 2.6, 0)
for k, f in enumerate(list(range(WALK0, WALK1, 8)) + [WALK1]):
    y = -6.45 + 7.5 * (f - WALK0) / (WALK1 - WALK0)
    key("INF", f, "selfie_step" + "LR"[k % 2], (0.2, y, 0), 180)
    key("F1", f, "film_step" + "RL"[k % 2], (-0.8, y - 1.3, 0), 180)
    key("F2", f, "film_step" + "LR"[k % 2], (1.1, y - 1.4, 0), 180)
BEATS = [(217, "selfie", "stand"), (289, "snap", "stand"), (361, "lean_desk", "stand"), (469, "selfie", "slide_bill"),
         (529, "point_up", "stand"), (589, "lean_desk", "stand"), (709, "laugh", "stand"), (781, "laugh", "stand")]
for (f, pi, pc), (g, _, _) in zip(BEATS, BEATS[1:] + [(789, 0, 0)]):
    for k in (f, g - 8):  # hold the pose through the beat, change over the last 8 frames before the next
        key("INF", k, pi, INF_DESK, 180); key("CLK", k, pc, CLK_POS, 0)
        key("F1", k, "film", (-1.5, -0.4, 0), 200); key("F2", k, "film", (1.8, -0.5, 0), 160)
key("CLK", 1, "stand", CLK_POS, 0)
for name in ("INF", "F1", "F2", "CLK"):
    for fc in C._fcurves(RIGS[name]):
        for kp in fc.keyframe_points: kp.interpolation = "LINEAR" if fc.data_path == "location" else "BEZIER"
PHONES = []
for name in ("INF", "F1", "F2"):  # phones ride the right wrist
    ph = OBJ["phone"] if name == "INF" else OBJ["phone"].copy(); PHONES.append(ph.name)
    if name != "INF": sc.collection.objects.link(ph)
    ph.location = (0, 0, 0)
    c = ph.constraints.new("COPY_LOCATION"); c.target = RIGS[name]; c.subtarget = "wrist.R"; c.head_tail = 1.0
    c = ph.constraints.new("COPY_ROTATION"); c.target = RIGS[name]; c.subtarget = "wrist.R"
sc.frame_start, sc.frame_end = 1, 780


def at(f): sc.frame_set(f); bpy.context.view_layer.update()


def H(name, f): at(f); return head(RIGS[name])


def names(*who): return {n for w in who for n in [RIGS[w].name, *(c.name for c in RIGS[w].children_recursive)]} | set(PHONES)


def clear(pos_info, what):  # a blocked placement must fail loudly, never park the camera inside someone
    pos, info = pos_info; assert info["clear"] >= 0.75, f"{what}: camera placement blocked {info}"; return pos


pillar = min((o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("Cylinder")),
             key=lambda o: (o.matrix_world.translation - Vector((-4.5, -1.5, 2.5))).length)
bill = OBJ["bill"]; bill_pts = [c.matrix_world @ Vector(v) for c in bill.children for v in c.bound_box]
SUBJ = {n: (RIGS[n], "head") for n in RIGS} | {"bill": (bill.children[0], None)}

# ---------------- shot plan: (f0, f1, label, shot type, subject, purpose, design) ----------------
shots = []


def shot(f0, f1, label, kind, subject, purpose, pos, aim, lens, spec, why):
    shots.append(dict(f0=f0, f1=f1, label=label, type=kind, subject=subject, purpose=f"{purpose}: {why}",
                      pos=Vector(pos), aim=Vector(aim), lens=lens, spec=spec))


# 1 ESTABLISH: high wide arc over the lobby as he comes through the doors
mid = Vector((0, -2.5, 1.0)); pos, _ = SC.place_angle(mid, (0.45, -1, 0), 6.2, vertical="high")
shot(1, 84, "ESTABLISH", "wide high-angle", "lobby + INF", "establish", pos, mid, 20,
     SC.choose("establish")["move"] | {"amount": 16}, "where we are; slow arc gives parallax on the pillars")
# 2 BACKWARD TRACKING: camera leads him toward the desk, friends filming behind
h = H("INF", 85); shot(85, 168, "TRACKING", "medium, leading", "INF", "action", h + Vector((0.45, 1.9, 0.05)), h, 32,
                       {"move": "follow", "subject": "INF", "amount": 0.8, "fstop": 2.8, "focus": "INF"}, "camera walks backward ahead of him")
# 3 ANTICIPATION: locked camera at the desk; the aim leads him into the frame
shot(169, 216, "ANTICIPATE", "medium wide", "INF", "anticipate", (2.4, 1.3, 1.5), H("INF", 169), 30,
     {"move": "anticipate", "subject": "INF", "lead": 14, "follow_focus": "INF", "fstop": 4.0}, "the frame waits where he is going")
# 4 FOREGROUND REVEAL: slide out from behind the pillar to find the clerk
hc = H("CLK", 217); d = (pillar.matrix_world.translation - hc); d.z = 0; d.normalize()
shot(217, 288, "REVEAL", "wide, foreground pillar", "CLK", "reveal", pillar.matrix_world.translation.xy.to_3d() + d * 1.4 + Vector((0, 0, 1.55)), hc, 40,
     {"move": "reveal", "occluder": pillar, "subject": "CLK", "fstop": 4.0, "focus": "CLK"}, "the pillar wipes away to reveal who he is about to bully")
# 5-6 SHOT / REVERSE SHOT dialogue (same side of the line), intentional holds with subtle handheld
(p1, a1, l1), (p2, a2, l2) = SC.reverse_pair(H("INF", 289), H("CLK", 289), "mcu", side=1)
shot(289, 360, "OVER THE SHOULDER", "OTS mcu", "INF", "dialogue", p1, a1, l1,
     {"move": "hold", "handheld": 0.12, "fstop": 2.2, "focus": "INF"}, "'Desk boy' - his line, over the clerk's shoulder")
shot(361, 420, "REVERSE SHOT", "OTS mcu (reverse)", "CLK", "dialogue", p2, a2, l2,
     {"move": "hold", "handheld": 0.12, "fstop": 2.2, "focus": "CLK"}, "the clerk takes it; eye-lines match across the cut")
# 7 REACTION close-up: held
hc = H("CLK", 421); p = clear(SC.place(hc, (-0.6, -1, 0), SC.distance_for("cu", 55), 0, 0.02, ignore=names("CLK")), "reaction")
shot(421, 468, "REACTION", "close-up", "CLK", "reaction", p, SC.aim_point(hc, "cu", p, 55), 55,
     {"move": "hold", "handheld": 0.1, "fstop": 2.0, "focus": "CLK"}, "hold on the face; no move competes with it")
# 8 INSERT + RACK FOCUS: the bill on the desk, then focus pulls to the clerk behind it
p, c, _ = SC.insert_shot(bill_pts, 40, front=(1, -0.35, 0), vertical="high")
shot(469, 528, "INSERT + RACK FOCUS", "insert, high angle", "bill -> CLK", "insert", p, c.lerp(H("CLK", 469), 0.2), 40,
     {"move": "hold", "fstop": 1.8, "focus": "bill", "rack_to": "CLK", "rack_at": 0.55}, "the story object, then who has to deal with it")
# 9 LOW ANGLE + TILT: he points up - power
hi = H("INF", 529); p = clear(SC.place_angle(hi - Vector((0, 0, 0.35)), (-1, -0.25, 0), SC.distance_for("med", 28), vertical="low", ignore=names("INF")), "low angle")
shot(529, 588, "LOW ANGLE + TILT", "medium low-angle", "INF", "power", p, hi - Vector((0, 0, 0.4)), 28,
     {"move": "tilt_up", "amount": 12, "delay": 0.15}, "looking up at him: he owns the room")
# 10 OVERHEAD: plan view of the desk standoff
m = H("INF", 589).lerp(H("CLK", 589), 0.5); m.z = 1.3; p = clear(SC.place_angle(m, (0, -1, 0), 3.4, vertical="overhead"), "overhead")
shot(589, 636, "OVERHEAD", "overhead two-shot", "desk", "geography", p, m, 24,
     {"move": "hold"}, "who stands where, at a glance")
# 11 LATERAL TRUCK: slide along the desk; he passes through the foreground, the wall stays far
shot(637, 708, "LATERAL TRUCK", "medium, tracking sideways", "desk", "geography", (-2.5, -0.55, 1.85), (-2.5, 3.0, 1.35), 30,
     {"move": "truck_right", "amount": 2.7, "fstop": 3.5, "focus": "CLK"}, "the desk and both of them in one move, real parallax")
# 12 PUSH-IN + small optical change: the laugh lands
hi = H("INF", 709); p = clear(SC.place(hi, (0.6, 0.8, 0), SC.distance_for("mcu", 35), 0, 0.03, ignore=names("INF")), "push-in")
shot(709, 780, "DOLLY IN + LENS", "mcu -> cu", "INF", "realise", p, SC.aim_point(hi, "mcu", p, 35), 35,
     {"move": "push", "amount": 0.35, "delay": 0.15, "fstop": 2.0, "focus": "INF", "zoom_to": 41}, "slow push while the lens tightens a little")

# ---------------- build rigs + shot list (before any render) ----------------
rows, segs = [], []
for k, s in enumerate(shots, 1):
    at(s["f0"]); r = C.rig(f"Cov{k:02d}", s["pos"], s["aim"], s["lens"])
    spec = dict(s["spec"]); z = spec.pop("zoom_to", None)
    C.apply(r, spec, s["f0"], s["f1"], SUBJ)
    if z: C.zoom(r, s["f0"] + 10, s["f1"], s["lens"], z)  # lens channel animates independently of position
    m = sc.timeline_markers.new(r.cam.name, frame=s["f0"]); m.camera = r.cam
    row = dict(id=k, f0=s["f0"], f1=s["f1"], type=s["type"], subject=s["subject"], purpose=s["purpose"],
               **C.describe(r, s["f0"], s["f1"], spec.get("focus") or spec.get("follow_focus")))
    if row["cam_start"] != row["cam_end"]: row["parallax"] = SC.parallax(r.cam, s["f0"], s["f1"])
    rows.append(row); segs.append((s["f0"], s["f1"], f"{k}  {s['label']}", s["purpose"].split(": ", 1)[1]))
sc.camera = bpy.data.objects["CAM_Cov01"]; sc.frame_set(1)
md = SC.shotlist(rows, os.path.join(HERE, "coverage_shotlist.md"), FPS)
json.dump(segs, open(os.path.join(HERE, "coverage_segs.json"), "w"), indent=0)
print(md)
for w in SC.camera_lint(rows): print("CAMERA LINT:", w)
for r in rows:
    if "parallax" in r: print("PARALLAX", r["id"], r["parallax"])
print("COVERAGE built:", len(rows), "shots,", sc.frame_end, "frames")
