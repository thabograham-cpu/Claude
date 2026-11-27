"""Shot list for "The Complainer" (voiceover 134.2 s). One entry per shot, timed to the transcript.

cam: (framing, subject, angle)  framing: wide|med|cu|ecu|insert   angle: front|34|side|back|low|high|top|ots
chars: name -> (set-local x, y, facing degrees [0 = toward -Y], pose)
card: 2D graphic shot (phone UI, search, map...) - rendered as a card, not 3D
props: extra prop states for this shot
move: camera move applied over the shot by tools/camera.py apply() - see MOVES at the bottom
"""
# characters: INF influencer, CLK clerk (narrator), F1/F2 friends filming, MGR manager, ROACH
S = []


def shot(t0, t1, set_, cam, chars=None, props=None, card=None, note=""):
    S.append(dict(id=len(S) + 1, t0=t0, t1=t1, set=set_, cam=cam, chars=chars or {}, props=props or {}, card=card, note=note))


# --- intro ---
shot(0.00, 2.00, "lobby", ("wide", "INF", "low"), {"INF": (0, -3.5, 0, "selfie_walk"), "F1": (-1.2, -4.6, 0, "film"), "F2": (1.2, -4.6, 0, "film")}, note="He struts into a five-star lobby, phone up")
shot(2.00, 3.50, "lobby", ("cu", "INF", "34"), {"INF": (0, -3.5, 0, "selfie")}, note="Smug to his own camera: 'for free'")
shot(3.50, 4.90, "lobby", ("ecu", "INF", "front"), {"INF": (0, -3.5, 0, "selfie")}, note="'His trick?' - slow push, smirk")
shot(4.90, 6.20, "lobby", ("med", "INF", "34"), {"INF": (0, -3.5, 0, "point_fwd"), "F1": (-0.9, -4.4, 20, "film")}, note="Points at a 'problem' while being filmed")
shot(6.20, 8.30, "lobby", ("insert", "small_box", "34"), {"INF": (0, -3.5, 0, "show_box")}, props={"small_box": "INF"}, note="'...he brings one' - pulls a little box from his pocket")
# --- arrival ---
shot(8.30, 10.60, "lobby", ("wide", "CLK", "ots"), {"CLK": (0, 2.6, 0, "stand"), "INF": (0, -2.5, 0, "selfie_walk"), "F1": (-1.2, -3.4, 0, "film"), "F2": (1.2, -3.4, 0, "film")}, note="Over the clerk's shoulder: they walk in livestreaming")
shot(10.60, 12.20, "lobby", ("med", "F1", "front"), {"F1": (-0.6, -2.5, 0, "film_walk"), "F2": (0.6, -2.7, 0, "film_walk")}, note="Two friends, phones up")
shot(12.20, 14.40, "lobby", ("wide", "cart", "34"), {"INF": (1.8, -1.6, -30, "stand")}, props={"cart": (0, -2.0)}, note="...and 14 suitcases on a brass cart")
shot(14.40, 16.30, "lobby", ("med", "INF", "ots"), {"INF": (0, 0.95, 180, "snap"), "CLK": (0, 2.6, 0, "stand")}, note="'Desk boy, bags' - snaps at the clerk, over the clerk's shoulder")
shot(16.30, 17.40, "lobby", ("med", "INF", "side"), {"INF": (0, 0.95, 180, "point_up"), "CLK": (0, 2.6, 0, "stand")}, note="'Ninth floor' - points up, in profile across the desk")
shot(17.40, 18.20, "lobby", ("med", "elevator", "front"), {"INF": (6.3, 1.3, -90, "selfie"), "F1": (6.3, 0.6, -90, "film"), "F2": (6.3, 2.0, -90, "film")}, note="'Elevators for VIPs' - VIP doors close on them")
shot(18.20, 19.30, "lobby", ("cu", "CLK", "front"), {"CLK": (0, 2.6, 0, "stand")}, props={"cart": (-1.4, 1.2)}, note="The clerk takes in 14 bags and nine floors: disbelief before the climb")
shot(19.30, 21.90, "stairs", ("wide", "CLK", "back"), {"CLK": (0, 1.2, 180, "carry_climb")}, props={"bags_on": "CLK"}, note="Clerk hauls 14 bags up nine floors - floor sign")
shot(21.90, 24.80, "stairs", ("med", "CLK", "high"), {"CLK": (0, 2.4, 180, "carry_climb")}, props={"bags_on": "CLK"}, card="chat:human luggage cart", note="Live chat overlay: 'human luggage cart'")
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
shot(118.60, 120.40, "lobby", ("med", "elevator", "front"), {"INF": (6.3, 1.3, -90, "shocked")}, note="VIP doors close in his face (callback)")
shot(120.40, 124.00, "stairs", ("wide", "INF", "high"), {"INF": (0, 1.05, 0, "carry_climb")}, props={"bags_on": "INF"}, note="He carries all 14 down nine floors, live")
shot(124.00, 127.00, "stairs", ("med", "INF", "low"), {"INF": (0, 2.0, 0, "carry_climb")}, props={"bags_on": "INF"}, card="chat:human luggage cart", note="Chat: now HE's the luggage cart")
shot(127.00, 129.10, "lobby", ("insert", "roach_box", "34"), props={"roach_on": "desk"}, note="'And the cockroach? He stayed.'")
shot(129.10, 132.60, "hall", ("wide", "door404", "low"), props={"roach_on": "hall"}, note="The one room nobody can book")
shot(132.60, 134.20, "hall", ("cu", "door404", "front"), props={"roach_on": "hall"}, note="ROOM 404")


# camera moves (tools/camera.py apply): dolly_in/out, pan_left/right, tilt_up/down, orbit, crane_up/down,
# zoom_in/out, dolly_zoom, whip_pan, follow; plus fstop/focus/rack_to/rack_at (DoF) and handheld
MOVES = {
    3: {"move": "dolly_in", "amount": 0.25},                              # 'His trick?' slow push
    6: {"move": "dolly_in", "amount": 0.8, "fstop": 2.8, "focus": "INF"},  # they walk in, clerk soft in foreground
    8: {"move": "crane_up", "amount": 1.2},                               # reveal the 14 suitcases
    12: {"move": "dolly_in", "amount": 0.12},                             # slow push on the clerk's disbelief
    13: {"move": "tilt_up", "amount": 12},                                # look up the stairwell
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
