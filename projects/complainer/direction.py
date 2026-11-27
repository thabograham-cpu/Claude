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


# --- intro: performing for his own camera
d(1, "INF", "make an entrance worth streaming", "arrogant", [(0, "self:phone")], [(1.2, "accent", "scoff")])
film(1, "F1"); film(1, "F2")
d(2, "INF", "brag to his followers that he never pays", "arrogant", [(0, "self:phone")], [(0.96, "accent", "scoff")], camera_ok=True)  # his phone IS the lens
d(3, "INF", "let the audience in on his trick", "arrogant", [(0, "self:phone")], [(0.3, "accent", "lean_in"), (0.64, "accent", "nod")])
d(4, "INF", "find something to complain about, on camera", "arrogant", [(0, (0.6, -5.6, 0.3))],
  [(0.18, "pose", "point_fwd")], pose="stand")
film(4, "F1", react=[(0.4, "nod")])
d(5, "INF", "show off the 'problem' he brought himself", "sarcastic", [(0, "self:phone"), (1.0, "self:wrist.R"), (1.7, FRIENDS)],
  [(1.6, "pose", "show_box")], pose="stand")
# --- arrival
d(6, "CLK", "welcome guests professionally - then clock the phones", "neutral", [(0, "INF"), (0.6, "F1"), (1.0, "INF")],
  [(0.2, "accent", "nod"), (0.9, "react", "annoyed")], role="listener")
d(6, "INF", "own the lobby for the stream", "arrogant", [(0, "self:phone"), (0.5, "CLK"), (1.0, "self:phone")])
film(6, "F1", react=[(0.6, "laugh")]); film(6, "F2")
film(7, "F1", role="primary"); film(7, "F2", react=[(0.8, "laugh")])
d(8, "INF", "present his fourteen suitcases like trophies", "arrogant", [(0, (0, -2.0, 0.9)), (1.3, FRIENDS)],
  [(0.5, "pose", "palm_up_R"), (1.6, "pose", "stand")], pose="stand")
# --- the order: shot-reverse-shot, INF faces the clerk
d(9, "INF", "order the 'desk boy' around in front of his chat", "arrogant", [(0, "CLK"), (1.1, (1.2, -1.0, 1.4)), (1.4, "CLK")],
  [(0.76, "pose", "snap"), (1.25, "pose", "stand"), (1.85, "pose", "point_up")], pose="hand_hip_L")
d(9, "CLK", "stay polite while being snapped at", "neutral", [(0, "INF")], [(0.8, "react", "annoyed")], role="listener")
d(10, "INF", "make it clear he will not carry anything", "arrogant", [(0, "CLK"), (0.55, (0, 1.0, 4.0)), (0.8, "CLK")],
  [(0.66, "accent", "beat"), (0.95, "pose", "hand_hip_L"), (1.0, "accent", "scoff")], pose="point_up")
d(10, "CLK", "take the order in silence", "annoyed", [(0, "INF")], role="listener")
d(11, "INF", "cut the line to the VIP elevator, still streaming", "arrogant", [(0, "self:phone")], [(0.4, "accent", "scoff")])
film(11, "F1"); film(11, "F2", react=[(0.5, "laugh")])
# disbelief BEFORE the physical consequence
d(12, "CLK", "process it: fourteen bags, nine floors, no elevator", "neutral",
  [(0, INF_AT_DESK), (0.35, (-1.6, 0.4, 0.7)), (0.75, INF_AT_DESK)],
  [(0.15, "react", "disbelief"), (0.85, "accent", "shake")])
d(13, "CLK", "get up nine floors without dropping anything", "exhausted", [(0, (0, 6.0, 4.5))], [(1.2, "accent", "sigh")], climb=True)
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
