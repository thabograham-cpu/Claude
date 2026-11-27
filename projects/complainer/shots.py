"""Shot list for "The Complainer" (voiceover 134.2 s). One entry per shot, timed to the transcript.

cam: (framing, subject, angle)  framing: wide|med|cu|ecu|insert   angle: front|34|side|back|low|high|top|ots
chars: name -> (set-local x, y, facing degrees [0 = toward -Y], pose)
card: 2D graphic shot (phone UI, search, map...) - rendered as a card, not 3D
props: extra prop states for this shot
move: camera move applied over the shot by tools/camera.py apply() - see MOVES at the bottom
"""
# characters: INF influencer, CLK clerk (narrator), F1/F2 friends filming, MGR manager, ROACH
S = []


def shot(t0, t1, set_, cam, chars=None, props=None, card=None, note="", cam_at=None):
    """cam_at: optional explicit ((x, y, z) camera, (x, y, z) aim) in set-local coordinates."""
    S.append(dict(id=len(S) + 1, t0=t0, t1=t1, set=set_, cam=cam, chars=chars or {}, props=props or {}, card=card, note=note, cam_at=cam_at))


# --- first 22 s: directed remake (cam_path = designed camera keys; chars[5] = walk path; focus = rack/follow) ---
def P(*pts): return dict(path=list(pts))
WALKERS = {"INF": (0.3, -4.25, 180, "selfie"), "F1": (0.95, -2.85, 0, "film"), "F2": (-0.6, -5.15, 180, "film")}
DESK = {"INF": (0.1, 0.85, 180, "stand"), "F1": (-1.0, -0.3, 160, "film"), "F2": (1.05, -0.4, 200, "film"), "CLK": (0, 2.6, 0, "stand")}
shot(0.00, 1.95, "lobby", ("med", "INF", "track"),
     {"INF": (0.3, -4.25, 180, "selfie_walk", P((0, 0.45, -6.0, 180), (1.95, 0.3, -4.25, 180))),
      "F1": (0.95, -2.85, 0, "film", P((0, 1.0, -4.6, 10), (1.95, 0.95, -2.85, 5))),
      "F2": (-0.6, -5.15, 180, "film", P((0, -0.55, -6.9, 175), (1.95, -0.6, -5.15, 180)))},
     note="Medium-wide tracking: he strides through the lobby livestreaming, F1 walks backwards filming him, F2 films alongside")
S[-1].update(cam_path=[(0, (-2.75, -2.7, 1.4), (0.45, -6.0, 1.35), 24), (1.95, (-2.5, -0.95, 1.4), (0.3, -4.25, 1.35), 24)], focus=[(0, "INF")], fstop=4.0)
shot(1.95, 4.00, "lobby", ("cu", "INF", "34"), dict(WALKERS), note="Medium close-up, slow push: smug to his stream - 'five-star hotels for free'")
S[-1].update(cam_path=[(0, (-0.5, -3.15, 1.62), "INF", 50), (2.05, (-0.38, -3.38, 1.62), "INF", 50)], focus=[(0, "INF")], fstop=2.8)
shot(4.00, 5.90, "lobby", ("cu", "INF", "34"), {"INF": (0.3, -4.25, 180, "phone_check_R")}, note="Controlled close-up: 'His trick?' - then his eyes go hunting for a problem")
S[-1].update(cam_path=[(0, (1.0, -3.3, 1.64), "INF", 60), (1.9, (0.88, -3.45, 1.64), "INF", 60)], focus=[(0, "INF")], fstop=2.0)
shot(5.90, 8.80, "lobby", ("insert", "bugbox", "34"), {"INF": (0.3, -4.25, 180, "pocket_R")}, props={"small_box": "INF"},
     note="Insert, shallow focus: the little pet-store bug box comes out of his pocket, the lid flips, a cockroach peeks out")
S[-1].update(insert_on=("bugbox", (0.26, 0.32, 0.16), 70), focus=[(0, "obj:BUGBOX_inf")], fstop=2.0)
# --- arrival ---
shot(8.80, 10.45, "lobby", ("wide", "INF", "ots"),
     {"CLK": DESK["CLK"], "INF": (0.1, 0.85, 180, "selfie_walk", P((0, 0.25, -0.8, 180), (1.65, 0.1, 0.85, 180))),
      "F1": (-1.0, -0.3, 160, "film", P((0, -1.0, -1.9, 165), (1.65, -1.0, -0.3, 160))),
      "F2": (1.05, -0.4, 200, "film", P((0, 1.1, -2.0, 195), (1.65, 1.05, -0.4, 200)))}, props={"cart": "off"},
     note="Over the clerk's shoulder: they arrive at reception livestreaming; focus racks from the clerk to him")
S[-1].update(cam_path=[(0, (0.28, 3.4, 1.72), (0.12, -0.6, 1.45), 30), (1.65, (0.26, 3.36, 1.72), (0.12, 0.2, 1.45), 30)], focus=[(0, "CLK"), (0.5, "INF")], fstop=2.4)
shot(10.45, 12.00, "lobby", ("med", "F1", "34"), dict(DESK, INF=(0.1, 0.85, 180, "selfie")), props={"cart": "off"},
     note="Past his shoulder: the two friends working their phones - tap, re-frame, laugh")
S[-1].update(cam_path=[(0, (-0.05, 1.9, 1.85), (0.0, -0.35, 1.35), 18), (1.55, (0.05, 1.88, 1.85), (0.0, -0.35, 1.35), 18)], focus=[(0, "F1"), (0.85, "F2")], fstop=2.8)
shot(12.00, 13.80, "lobby", ("insert", "cart", "low"), dict(DESK, INF=(0.1, 0.85, 180, "selfie")), props={"cart": (-2.3, 0.6), "cart_from": (-2.3, -0.3)},
     note="Reveal: luggage wheels roll to a stop, the camera cranes up and back - fourteen suitcases")
S[-1].update(cam_path=[(0, (-1.4, -0.45, 0.16), (-1.8, 0.36, 0.06), 28), (0.55, (-1.4, -0.45, 0.17), (-1.8, 0.36, 0.08), 28),
                       (1.6, (-1.0, -1.25, 1.65), (-2.3, 0.6, 1.35), 28), (1.8, (-0.98, -1.28, 1.66), (-2.3, 0.6, 1.36), 28)], focus=[(0, "obj:cart")], fstop=4.0)
shot(13.80, 14.60, "lobby", ("cu", "CLK", "34"), dict(DESK, INF=(0.1, 0.85, 180, "selfie")), props={"cart": (-2.3, 0.6)},
     note="Comedic beat: the clerk's eyes climb the luggage tower - disbelief")
S[-1].update(cam_path=[(0, (-0.85, 1.25, 1.62), "CLK", 50), (0.8, (-0.8, 1.31, 1.62), "CLK", 50)], focus=[(0, "CLK")], fstop=2.8)
shot(14.60, 16.75, "lobby", ("med", "INF", "34"), dict(DESK, INF=(0.1, 0.85, 180, "hand_hip_L")), props={"cart": (-2.3, 0.6)},
     note="'Desk boy, bags, ninth floor' - lip-synced, snaps on 'bags', points up on 'ninth floor'")
S[-1].update(cam_path=[(0, (0.95, 2.15, 1.6), "INF", 38), (2.15, (0.9, 2.05, 1.6), "INF", 38)], focus=[(0, "INF")], fstop=2.8)
shot(16.75, 17.75, "lobby", ("med", "INF", "ots"), dict(DESK, INF=(0.1, 0.85, 180, "point_up_R")), props={"cart": (-2.3, 0.6)},
     note="'Elevators for VIPs': his pointing arm swings to the elevators; the camera pans with it and focus racks to the VIP sign")
S[-1].update(cam_path=[(0, (-0.35, -0.95, 1.65), (0.05, 0.8, 2.0), 30), (0.25, (-0.35, -0.95, 1.65), (0.1, 0.8, 2.0), 30),
                       (0.85, (-0.3, -0.92, 1.68), (10.59, 2.5, 2.8), 30), (1.0, (-0.3, -0.92, 1.68), (10.59, 2.5, 2.82), 30)],
              focus=[(0, "INF"), (0.45, (10.59, 2.5, 3.05))], fstop=2.8)
shot(17.75, 19.00, "lobby", ("cu", "CLK", "34"), dict(DESK, INF=(0.1, 0.85, 180, "point_up_R")), props={"cart": (-2.3, 0.6)},
     note="The clerk looks to the VIP elevator, then the fourteen bags - it lands")
S[-1].update(cam_path=[(0, (0.75, 1.2, 1.6), "CLK", 50), (1.2, (0.7, 1.28, 1.6), "CLK", 50)], focus=[(0, "CLK")], fstop=2.8)
shot(19.00, 20.95, "stairs", ("wide", "CLK", "side"), {"CLK": (0, 0.4, 180, "carry_two", P((0, 0, -0.05, 180), (1.95, 0, 0.8, 180)))}, props={"bags_on": "CLK"},
     note="Low angle from the steps above, backing up the flight: the clerk hauls all fourteen bags, step by step; he stops and looks up")
S[-1].update(cam_path=[(0, (0.42, 1.85, 1.48), (0, 0.0, 1.25), 18), (2.0, (0.42, 2.35, 1.78), (0, 0.8, 1.6), 18)], focus=[(0, "CLK")], fstop=4.0,
             stairs_steps=[(0.45, "R", 0), (1.1, "L", 1), (1.75, "R", 2)])
shot(20.95, 21.95, "stairs", ("wide", "CLK", "pov:CLK:head"), {"CLK": (0, 0.8, 180, "carry_two")}, props={"bags_on": "CLK"},
     note="His POV straight up the stairwell: nine floors of switchbacks")
S[-1].update(cam_path=[(0, (-1.025, 2.0, 1.5), (-1.025, 2.15, 30), 14), (1.0, (-1.025, 2.0, 1.5), (-0.95, 2.05, 30), 14)], fstop=8.0)
shot(21.95, 24.80, "stairs", ("med", "CLK", "high"), {"CLK": (0, 2.4, 180, "carry_climb")}, props={"bags_on": "CLK"}, card="chat:human luggage cart", note="Live chat overlay: 'human luggage cart'")
# --- the night ---
shot(24.80, 26.40, "suite", ("wide", "lobster", "34"), note="Room service: the suite, lobster on the cart")
shot(26.40, 27.40, "suite", ("insert", "champagne", "34"), note="Champagne")
shot(27.40, 28.80, "suite", ("med", "INF", "34"), {"INF": (0.4, 0.3, 200, "lie_bed")}, note="Spa robe, face mask, on the bed")
shot(28.80, 30.20, "suite", ("insert", "clock", "front"), note="Clock 2:00 AM")
shot(30.20, 31.40, "lobby", ("cu", "CLK", "front"), {"CLK": (0, 2.6, 0, "phone_ear")}, note="Desk phone - screaming on the line")
shot(31.40, 33.90, "suite", ("ecu", "lobster", "34"), props={"roach_on": "lobster"}, note="A cockroach in the lobster")
shot(33.90, 35.50, "suite", ("med", "INF", "front"), {"INF": (0, -0.8, 0, "shocked"), "F1": (-1.0, -1.6, 20, "film")}, note="Performs horror for the stream")
shot(35.50, 37.60, None, None, card="viewers:300,000 watching", note="Viewer counter ticks to 300K")
shot(37.60, 39.60, "lobby", ("cu", "MGR", "34"), {"MGR": (0.8, 2.6, 0, "hands_head")}, note="Manager panics")
shot(39.60, 41.40, "lobby", ("insert", "bill", "high"), props={"stamp": "COMPED"}, note="COMPED stamp on the bill")
shot(41.40, 42.90, "lobby", ("insert", "bill", "top"), props={"stamp": "COMPED", "bill_text": "$4,000"}, note="'$4,000, gone'")
# --- the investigation ---
shot(42.90, 44.80, "lobby", ("med", "CLK", "34"), {"CLK": (0, 2.6, 0, "phone_look")}, note="Night shift: rewatching the stream")
shot(44.80, 47.00, None, None, card="replay:that cockroach = 3 inches", note="Freeze-frame on the stream: roach next to a ruler")
shot(47.00, 49.00, "suite", ("ecu", "roach", "front"), props={"roach_on": "lobster"}, note="...and it hissed (macro)")
shot(49.00, 50.60, None, None, card="search:cockroach that hisses", note="Search bar typing")
shot(50.60, 52.60, None, None, card="result:Madagascar hissing cockroach", note="Search result card")
shot(52.60, 56.20, None, None, card="map:Madagascar", note="Globe spins, zooms to an island far away")
shot(56.20, 58.60, "petstore", ("wide", "tank", "front"), note="Pet store tank, price tag")
shot(58.60, 60.60, None, None, card="story:@influencer story - 9:14 AM", note="His own story from that morning")
shot(60.60, 64.40, "petstore", ("med", "INF", "low"), {"INF": (0, -1.2, 0, "show_box")}, props={"small_box": "INF"}, note="Him leaving a pet store holding a little box")
# --- checkout ---
shot(64.40, 66.80, "lobby", ("wide", "INF", "side"), {"INF": (0, 0.9, 0, "selfie_walk"), "F1": (-1.0, -0.2, 0, "film"), "F2": (1.0, -0.2, 0, "film"), "CLK": (0, 2.6, 0, "stand")}, note="Next morning, he strolls up")
shot(66.80, 68.40, "lobby", ("cu", "INF", "34"), {"INF": (0, 1.05, 0, "lean_desk")}, note="'Bill's comped, desk boy'")
shot(68.40, 69.80, "lobby", ("med", "INF", "34"), {"INF": (0, 1.05, 0, "flick")}, note="'Bring my bags down'")
shot(69.80, 71.40, "lobby", ("cu", "CLK", "front"), {"CLK": (0, 2.6, 0, "slide_bill")}, props={"bill_text": "$4,000"}, note="Calm: 'the bill's back on'")
shot(71.40, 73.40, "lobby", ("insert", "bill", "high"), props={"bill_text": "$4,000"}, note="$4,000")
shot(73.40, 76.40, "lobby", ("cu", "INF", "low"), {"INF": (0, 1.05, 0, "laugh")}, note="Laughs: 'I'm leaving without paying'")
shot(76.40, 78.20, "lobby", ("cu", "INF", "ots"), {"INF": (0, 1.1, 0, "lean_desk"), "CLK": (0, 2.6, 0, "stand")}, note="'What are you gonna do, cry?'")
shot(78.20, 81.40, "lobby", ("cu", "CLK", "front"), {"CLK": (0, 2.6, 0, "stand")}, note="Slow push in: the one thing he didn't expect")
shot(81.40, 83.00, "lobby", ("wide", "cart", "34"), {"CLK": (-1.6, 3.2, 0, "push")}, props={"cart": (-0.4, 3.6)}, note="Rolls the bags behind the desk")
shot(83.00, 84.80, "lobby", ("insert", "lawbook", "high"), note="An old law book thuds on the desk")
shot(84.80, 86.60, None, None, card="title:THE INNKEEPER'S LIEN", note="Title card")
shot(86.60, 89.60, "lobby", ("insert", "cart", "front"), props={"cart": (-0.4, 3.6), "tag": "HELD"}, note="Bags tagged HELD")
shot(89.60, 93.00, "lobby", ("cu", "INF", "front"), {"INF": (0, 1.05, 0, "shocked")}, props={"tag": "FOR SALE"}, note="'...it can sell it' - his face drops")
# --- meltdown ---
shot(93.00, 96.00, "lobby", ("med", "INF", "34"), {"INF": (0, 0.6, 0, "phone_speaker"), "F1": (-1.0, -0.4, 20, "film"), "F2": (1.0, -0.4, -20, "film")}, note="Calls his lawyer on speaker, live")
shot(96.00, 98.40, None, None, card="call:LAWYER - 'Pay the bill.'", note="Call screen")
shot(98.40, 100.90, "lobby", ("cu", "INF", "low"), {"INF": (0, 0.6, 0, "selfie")}, note="Turns the camera on himself to rally chat")
shot(100.90, 103.80, "lobby", ("ecu", "INF", "front"), {"INF": (0, 0.6, 0, "selfie_yell")}, note="'This hotel is stealing my designer clothes!'")
shot(103.80, 106.80, "lobby", ("med", "INF", "34"), {"INF": (0, -0.6, 0, "kneel")}, props={"open_case": (0, -1.2)}, note="Rips open his biggest suitcase")
shot(106.80, 110.80, "lobby", ("insert", "open_case", "top"), props={"open_case": (0, -1.2), "robes": True}, note="Stuffed with bathrobes from 30 hotels")
shot(110.80, 113.60, None, None, card="chat:@GrandPalace: that's OUR robe", note="Hotels flood the chat")
shot(113.60, 115.40, "lobby", ("insert", "desk", "high"), {"INF": (0, 1.05, 0, "pay")}, note="He slaps down the card. Paid.")
shot(115.40, 117.00, "lobby", ("ecu", "CLK", "front"), {"CLK": (0, 2.6, 0, "stand")}, note="'Then, I smiled.'")
shot(117.00, 118.60, "lobby", ("med", "CLK", "front"), {"CLK": (0, 2.6, 0, "point_up")}, note="'Bags are on the ninth floor'")
shot(118.60, 120.40, "lobby", ("med", "elevator", "front"), {"INF": (9.5, 2.5, 90, "shocked")}, note="VIP doors close in his face (callback)")
shot(120.40, 124.00, "stairs", ("wide", "INF", "high"), {"INF": (0, 1.05, 0, "carry_climb")}, props={"bags_on": "INF"}, note="He carries all 14 down nine floors, live")
shot(124.00, 127.00, "stairs", ("med", "INF", "low"), {"INF": (0, 2.0, 0, "carry_climb")}, props={"bags_on": "INF"}, card="chat:human luggage cart", note="Chat: now HE's the luggage cart")
shot(127.00, 129.10, "lobby", ("insert", "roach_box", "34"), props={"roach_on": "desk"}, note="'And the cockroach? He stayed.'")
shot(129.10, 132.60, "hall", ("wide", "door404", "low"), props={"roach_on": "hall"}, note="The one room nobody can book")
shot(132.60, 134.20, "hall", ("cu", "door404", "front"), props={"roach_on": "hall"}, note="ROOM 404")


# camera moves (tools/camera.py apply): dolly_in/out, pan_left/right, tilt_up/down, orbit, crane_up/down,
# zoom_in/out, dolly_zoom, whip_pan, follow; plus fstop/focus/rack_to/rack_at (DoF) and handheld
MOVES = {
    21: {"handheld": 0.8},                                                # fake panic for the stream
    23: {"move": "zoom_in", "amount": 1.3, "handheld": 1.0},             # manager panics
    28: {"move": "zoom_in", "amount": 1.8},                               # the hiss
    34: {"move": "pan_left", "amount": 12},                               # leaving the pet store
    35: {"move": "dolly_in", "amount": 1.0},                              # he strolls up
    40: {"handheld": 0.5},                                                # laughing
    41: {"fstop": 2.0, "focus": "INF", "rack_to": "CLK", "rack_at": 0.7},  # 'cry?' then focus snaps to the clerk
    42: {"move": "dolly_in", "amount": 0.35},                             # slow push: the thing he didn't expect
    47: {"move": "dolly_zoom", "amount": 1.8},                            # his face drops (vertigo)
    48: {"fstop": 2.2, "focus": "INF", "rack_to": "F1", "rack_at": 0.6},  # lawyer on speaker, focus to the filming friend
    53: {"move": "crane_up", "amount": 0.6},                              # robes reveal
    56: {"move": "dolly_in", "amount": 0.15},                             # 'Then, I smiled'
    58: {"move": "zoom_in", "amount": 1.4},                               # doors close in his face
    59: {"move": "crane_down", "amount": 1.0},                            # carrying down the stairs
    62: {"move": "dolly_in", "amount": 2.0},                              # down the corridor
    63: {"move": "zoom_in", "amount": 1.5},                               # ROOM 404
}
for _s in S:
    _s["move"] = MOVES.get(_s["id"])
assert all(any(x["id"] == k and x["set"] for x in S) for k in MOVES), "moves only on 3D shots"

# lint notes accepted on purpose (shot id -> reason); storyboard.py reports them as accepted, not as warnings
LINT_OK = {
    34: "medium keeps his face AND the box in one frame - the story needs both",
}
