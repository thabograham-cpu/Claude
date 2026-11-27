"""Acting direction for "The Complainer": every character's intention in every 3D shot (tools/acting.py specs).
Times are seconds from the shot start, synced to the narration's word times (audio/words.json).
look targets: a cast name (must be in the shot), "self:phone", or a set-local (x, y, z) point - off-screen
partners are points just off the lens so front close-ups never stare into the camera.
Arcs: INF arrogant/performative -> shocked -> furious -> embarrassed -> exhausted.
      CLK polite -> disbelief -> exhausted -> worn out at 2 AM -> curious -> calm, quietly in control.
      F1/F2 always filming: eyes on the phone, glances, re-grips, laughs at his big moments.
"""
DIR = {}
INF_AT_DESK = (0.45, 0.95, 1.62)     # where INF stands at the desk, seen from behind it (just off a front lens)
CLK_AT_DESK = (-0.4, 2.6, 1.62)      # where the clerk stands, seen from the lobby side
FRIENDS = (-1.0, -4.0, 1.5)


def d(shot, who, intent, preset="neutral", look=None, beats=(), role=None, **kw):
    DIR.setdefault(shot, {})[who] = dict(intent=intent, preset=preset, look=look or [], beats=list(beats),
                                         **({"role": role} if role else {}), **kw)


def film(shot, who, subject="INF", react=(), role="background"):
    DIR.setdefault(shot, {})[who] = dict(filmer=subject, react=list(react), role=role,
                                         intent=f"film {subject}: catch every moment for the stream", preset="neutral")


# --- first 22 s (directed remake; shot ids match shots.py) ---
CART_TOP, CART_LOW, VIP_SIGN = (-2.3, 0.6, 2.1), (-2.3, 0.6, 0.7), (10.59, 2.5, 3.0)
d(1, "INF", "make an entrance worth streaming", "arrogant", [(0, "self:phone"), (1.15, "F1"), (1.5, "self:phone")], [(1.35, "accent", "scoff")])
film(1, "F1", role="background"); film(1, "F2", react=[(1.2, "phone_tap")])
d(2, "INF", "brag to his followers that he never pays", "arrogant", [(0, "self:phone"), (0.85, (0.95, -2.85, 1.6)), (1.25, "self:phone")],
  [(0.2, "accent", "lean_in"), (1.0, "accent", "scoff")])
film(2, "F1"); film(2, "F2")
d(3, "INF", "let us in on the trick, then hunt for something to complain about", "sarcastic",
  [(0, (0.0, -2.65, 1.6)), (0.95, (-0.7, -2.3, 2.1)), (1.25, (0.9, -2.4, 1.35)), (1.55, (0.25, -2.3, 2.5))],   # eye level and up, within ~35 deg of his front: a close-up must keep the face
  [(0.05, "accent", "lean_in"), (0.9, "react", "confused"), (1.55, "react", "sarcastic"), (1.6, "accent", "nod")])
d(4, "INF", "produce the problem he brought himself", "sarcastic", [(0, "self:wrist.R"), (2.3, (0.95, -2.85, 1.6))],
  [(0.3, "pose", "show_box_R"), (2.25, "accent", "scoff")], pose="pocket_R")   # out of the pocket at once: the insert is about the box
d(5, "CLK", "welcome guests - then clock the phones", "neutral", [(0, "INF"), (0.85, "F1"), (1.25, "INF")],
  [(0.3, "accent", "take"), (1.1, "react", "annoyed")], role="primary")
d(5, "INF", "own the lobby for the stream", "arrogant", [(0, "self:phone"), (1.0, "CLK")])
film(5, "F1", react=[(0.9, "phone_tap")]); film(5, "F2")
film(6, "F1", react=[(0.3, "phone_tap"), (0.9, "adjust_phone")], role="primary"); film(6, "F2", react=[(0.55, "laugh"), (1.2, "phone_tap")], role="primary")
d(6, "INF", "wait to be served", "arrogant", [(0, "CLK")], role="background")
d(6, "CLK", "keep a straight face", "annoyed", [(0, "INF")], role="listener")
d(7, "INF", "show off his luggage", "arrogant", [(0, "CLK"), (0.6, "cart")], role="background")
d(7, "CLK", "notice the trolley", "annoyed", [(0, "INF"), (0.8, CART_LOW)], role="listener")
film(7, "F1", "cart"); film(7, "F2", "INF")
d(8, "CLK", "take in fourteen suitcases", "neutral", [(0, CART_LOW), (0.3, CART_TOP)], [(0.05, "react", "disbelief")])
d(8, "INF", "wait", "arrogant", [(0, "CLK")], role="background")
film(8, "F1"); film(8, "F2")
d(9, "INF", "order the 'desk boy' around for the stream", "arrogant", [(0, "CLK")],
  [(0.56, "pose", "snap_R"), (1.0, "pose", "hand_hip_L"), (1.4, "pose", "point_up_R")])
d(9, "CLK", "take the order without reacting", "annoyed", [(0, "INF")], role="listener")
film(9, "F1"); film(9, "F2", react=[(0.7, "laugh")])
d(10, "INF", "point the clerk at the VIP elevator", "arrogant", [(0, "CLK"), (0.25, VIP_SIGN)], [(0.3, "pose", "point_side_R")])
d(10, "CLK", "follow his finger", "annoyed", [(0, "INF"), (0.55, VIP_SIGN)], role="listener")
film(10, "F1"); film(10, "F2")
d(11, "CLK", "realise: no elevator for him, fourteen bags, nine floors", "neutral", [(0, VIP_SIGN), (0.7, CART_TOP), (1.05, "INF")],
  [(0.1, "react", "surprised"), (0.55, "react", "disbelief"), (0.9, "accent", "shake")])
d(11, "INF", "enjoy it", "arrogant", [(0, "CLK")], role="background")
film(11, "F1"); film(11, "F2")
d(12, "CLK", "get all fourteen bags up the stairs without falling", "exhausted", [(0, (0, 2.6, 2.2)), (1.55, (0, 1.6, 9.0))],
  [(0.2, "accent", "sigh"), (1.55, "react", "disbelief"), (1.6, "accent", "take")], climb=True, pose="carry_two")
d(13, "CLK", "count the floors above him", "exhausted", [(0, (0, 1.6, 20.0))], [(0.4, "accent", "sigh")], pose="carry_two")
d(14, "CLK", "keep climbing while the chat mocks him", "exhausted", [(0, (0, 6.0, 5.5)), (1.6, (0, 1.0, 0.0))],
  [(0.6, "accent", "sigh")], climb=True)
# --- the night
d(17, "INF", "enjoy the comped luxury", "arrogant", [(0, (0.4, -1.5, 2.5))])
d(19, "CLK", "survive a 2 AM screaming call", "exhausted", [(0, (0.6, 0.6, 1.2))], [(0.4, "react", "annoyed"), (0.9, "accent", "sigh")])
d(21, "INF", "perform horror for 300,000 viewers", "surprised", [(0, (0.3, -0.2, 0.8)), (0.8, "F1")], [(0.2, "accent", "take")],
  camera_ok=False)
film(21, "F1", react=[(0.5, "lean_in")])
d(23, "MGR", "make the stream stop at any cost", "surprised", [(0, (0.6, -1.0, 1.6))], [(0.8, "accent", "shake")])
d(26, "CLK", "rewatch the stream for what doesn't add up", "confused", [(0, "self:phone")], [(1.2, "accent", "lean_in")])
d(34, "INF", "slip out of the pet store unseen", "embarrassed", [(0, (1.5, -3.0, 1.5)), (1.5, "self:wrist.R")])
# --- checkout: the tables turn
d(35, "INF", "collect his free stay like a victory lap", "arrogant", [(0, "self:phone"), (1.4, "CLK")])
d(35, "CLK", "wait for him - he already knows", "neutral", [(0, "INF")], role="listener")
film(35, "F1"); film(35, "F2")
d(36, "INF", "rub the comped bill in his face", "arrogant", [(0, CLK_AT_DESK)], [(0.6, "accent", "scoff")])
d(37, "INF", "send the desk boy for his bags", "arrogant", [(0, CLK_AT_DESK)], [(0.4, "accent", "beat")])
d(38, "CLK", "calmly put the bill back on", "neutral", [(0, INF_AT_DESK), (0.5, (0.0, 1.4, 1.0)), (1.0, INF_AT_DESK)])
d(40, "INF", "laugh off a bill he will never pay", "arrogant", [(0, CLK_AT_DESK)], [(0.3, "accent", "laugh"), (1.6, "accent", "laugh")])
d(41, "INF", "humiliate the clerk: 'what are you gonna do, cry?'", "sarcastic", [(0, "CLK")], [(0.5, "accent", "lean_in")])
d(41, "CLK", "let him finish", "neutral", [(0, "INF")], role="listener")
d(42, "CLK", "quietly decide to use the one rule he doesn't know", "neutral", [(0, INF_AT_DESK)], [(1.6, "accent", "nod")])
d(43, "CLK", "roll the bags out of reach", "neutral", [(0, (-0.4, 4.6, 0.8))])
d(47, "INF", "realise the hotel can sell his things", "disbelief", [(0, CLK_AT_DESK)], [(0.2, "react", "surprised"), (1.4, "react", "disbelief")])
d(48, "INF", "get his lawyer to fix it - live", "angry", [(0, "self:phone"), (1.6, "F1")], [(1.0, "accent", "beat")])
film(48, "F1"); film(48, "F2", react=[(2.0, "lean_in")])
d(50, "INF", "rally his chat against the hotel", "angry", [(0, "self:phone")], [(0.6, "accent", "beat"), (1.4, "accent", "beat")])
d(51, "INF", "accuse the hotel of theft, loudly", "angry", [(0, "self:phone")], [(0.4, "accent", "beat"), (1.2, "accent", "beat")])
d(52, "INF", "prove his clothes are inside", "angry", [(0, (0, -1.2, 0.2))], [(0.8, "react", "embarrassed")])
d(55, "INF", "pay and get out before the chat sees more", "embarrassed", [(0, (0, 1.4, 1.1))])
d(56, "CLK", "enjoy it - just a little", "sarcastic", [(0, INF_AT_DESK)], avert=0.0)
d(57, "CLK", "send him up the stairs this time", "sarcastic", [(0, INF_AT_DESK)], [(0.5, "accent", "nod")])
d(58, "INF", "catch the VIP elevator - and miss it", "surprised", [(0, (6.3 - 1.2, 1.3, 1.6))], [(0.4, "react", "disbelief")])
d(59, "INF", "get fourteen bags down nine floors, live", "exhausted", [(0, (0, -3.0, -1.0))], [(1.5, "accent", "sigh")], climb=True)
d(60, "INF", "keep going while chat calls him the luggage cart", "exhausted", [(0, (0, -2.0, 0.0))], [(1.2, "react", "embarrassed")], climb=True)
