"""Beat sheet for "The Complainer" (tools/edit.py): each narration beat -> what we watch happen, who reacts,
the camera, and the sound. Beats come from edit.segment(audio/words.json); this file is the director's pass.
sfx: (at, kind, args) with at = seconds or "word:<w>[+offset]" (synced to the narration).
Run: python3 projects/complainer/beats.py  -> beats.md, cues.json (sfx), beds.json (ambience), and lint notes."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, "..", "..", "tools")]
import edit

W = json.load(open(os.path.join(HERE, "audio", "words.json"))); W = W["words"] if isinstance(W, dict) else W
CAPTION_FIX = {"lean": "lien"}
S = lambda **k: k
SHEET = {
    1: S(func="establish", shots=[1, 2], visual="INF strides off the street under the canopy into the hotel, phone up, friends filming behind",
         reaction="doorman-style topiaries; passers-by unbothered", camera="wide from the street behind them, then his phone's own selfie view",
         sfx=[(0.05, "steps", dict(n=5, every=0.36, surface="marble", gain=-2)), ("word:free+0.5", "ping", {})]),
    2: S(func="pause", shots=[3], joke=True, visual="INF leans into his phone and smirks", reaction="", camera="ECU, slow push"),
    3: S(func="action", shots=[4], visual="INF stops mid-lobby and points at a spot on the floor for the camera", reaction="F1 swings her phone to it",
         camera="medium 3/4", sfx=[("word:problem+0.45", "shutter", {})]),
    4: S(func="transition", shots=[5], visual="INF's hand slides into his hoodie pocket", reaction="", camera="insert on his hand"),
    5: S(func="insert", shots=[5], joke=True, visual="INF pulls a little cardboard box out and turns it in his fingers", reaction="",
         camera="insert holds on the box through the pause", sfx=[("word:brings", "cardboard", dict(sync=True))]),
    6: S(func="action", shots=[6, 7, 8], visual="INF walks in livestreaming; F1 and F2 walk backwards filming him; the brass trolley rolls in with 14 suitcases",
         reaction="CLK straightens behind the desk, then sees the phones", camera="over the clerk's shoulder; friends medium; reveal of the trolley",
         sfx=[(9.12, "steps", dict(n=4, every=0.36, surface="marble")), (10.65, "steps", dict(n=4, every=0.4, surface="marble", gain=-2)),
              (12.25, "wheels", dict(dur=1.2)), (13.35, "thud", dict(gain=-6, sync=True))]),
    7: S(func="dialogue", shots=[9], visual="INF snaps his fingers at the clerk on 'bags'", reaction="CLK's smile tightens", camera="over the clerk's shoulder",
         sfx=[("word:bags", "snap", dict(sync=True))]),
    8: S(func="dialogue", shots=[10, 11, 12], joke=True, visual="INF jabs a finger at the ceiling; the three of them step into the VIP car and the brass doors close",
         reaction="CLK alone at the desk: disbelief, a look at the trolley, a slow head shake", camera="profile; inside the car; clerk close-up push",
         sfx=[("word:elevators", "ding", dict(sync=True, space="lobby")), (17.7, "doors", dict(dur=0.5, sync=True, space="lobby"))]),
    9: S(func="action", shots=[13, 14], visual="CLK climbs the stairwell with fourteen bags strapped to him, floor numbers passing",
         reaction="chat overlay mocks him", camera="wide from below, then high looking down the well",
         sfx=[(19.35, "steps", dict(n=8, every=0.65, surface="concrete")), ("word:floors+0.3", "breath", {}), (22.2, "thud", dict(gain=-6, sync=True))]),
    10: S(func="action", visual="a room-service cart is wheeled into the suite: lobster under a cloche", camera="wide suite, lamplight", sfx=[(25.2, "wheels", dict(dur=1.0, gain=-4))]),
    11: S(func="insert", visual="champagne is poured; INF in a robe and face mask flops onto the bed", camera="insert, then medium"),
    12: S(func="insert", visual="the bedside clock flips to 2:00", camera="insert", sfx=[("word:two", "tap", {})]),
    13: S(func="action", visual="CLK at the dark desk picks up the ringing phone", reaction="CLK winces at the volume", camera="close-up"),
    14: S(func="reveal", visual="a cockroach crawls out of the lobster", reaction="INF screams at his phone, F1 films", camera="ECU macro, then medium"),
    15: S(func="insert", visual="the viewer counter races to 300,000", camera="phone UI card", sfx=[("word:people+0.4", "ping", {})]),
    16: S(func="action", visual="the manager clutches his head and stamps the bill", reaction="CLK watches, deadpan", camera="close-up, zoom"),
    17: S(func="insert", joke=True, visual="the COMPED stamp slams onto the $4,000 bill", camera="insert from above", sfx=[(40.4, "thud", dict(gain=-4))]),
    18: S(func="action", visual="night shift: CLK scrubs back through the stream on his phone", camera="medium, phone glow", sfx=[("word:rewatched", "tap", {})]),
    19: S(func="insert", visual="freeze-frame: the roach next to a ruler", camera="phone UI card"),
    20: S(func="reveal", joke=True, visual="the roach rears up and hisses", camera="macro push", sfx=[("word:hissed+0.2", "whoosh", dict(gain=-4))]),
    21: S(func="action", visual="CLK types into a search bar", camera="screen card", sfx=[(49.3, "tap", {}), (49.5, "tap", {}), (49.7, "tap", {})]),
    22: S(func="insert", visual="the result card: Madagascar hissing cockroach", camera="card"),
    23: S(func="reveal", visual="a globe spins and dives to an island", camera="map card"),
    24: S(func="transition", visual="the island far away; the hotel on the other side of the world", camera="map pull-back"),
    25: S(func="reveal", joke=True, visual="the pet store tank with a price tag", camera="wide through the shop window, street noise"),
    26: S(func="pause", visual="CLK taps INF's own story from that morning", camera="phone card", sfx=[(59.0, "tap", {})]),
    27: S(func="action", visual="INF walks out of PET PALACE, glancing both ways", camera="low medium from the sidewalk, pan with him"),
    28: S(func="insert", joke=True, visual="the little box in his hand", camera="insert follow"),
    29: S(func="action", visual="next morning INF strolls back across the lobby to the desk", reaction="CLK waits behind the desk", camera="wide side, dolly",
          sfx=[(64.6, "steps", dict(n=5, every=0.4, surface="marble"))]),
    30: S(func="dialogue", visual="INF leans on the desk and smirks: 'Bill's comped'", reaction="CLK holds still", camera="close-up"),
    31: S(func="dialogue", visual="INF flicks his fingers toward the stairs", camera="medium"),
    32: S(func="action", visual="CLK slides the bill back across the desk", reaction="INF's smirk freezes", camera="close-up on CLK, then insert"),
    33: S(func="insert", joke=True, visual="$4,000 on the bill under CLK's fingertip", camera="insert"),
    34: S(func="dialogue", visual="INF throws his head back laughing", reaction="friends laugh on cue", camera="low close-up, handheld"),
    35: S(func="dialogue", visual="INF leans over the desk: 'cry?'", reaction="rack focus to CLK, unblinking", camera="over the shoulder, rack focus"),
    36: S(func="pause", visual="CLK's slow push-in; the faintest smile", camera="close-up push"),
    37: S(func="action", visual="CLK rolls the trolley of bags behind the desk", reaction="INF's jaw drops", camera="wide", sfx=[(81.6, "wheels", dict(dur=1.2))]),
    38: S(func="action", visual="an old law book thuds onto the desk", camera="insert from above", sfx=[(83.0, "thud", dict(sync=True))]),
    39: S(func="insert", visual="title card: The innkeeper's lien", camera="card"),
    40: S(func="action", visual="a HELD tag is hung on the trolley", camera="insert"),
    41: S(func="insert", visual="the trolley parked behind the desk", camera="insert"),
    42: S(func="transition", visual="the tag flips to FOR SALE", camera="insert"),
    43: S(func="transition", visual="INF's face falls", camera="close-up"),
    44: S(func="reaction", joke=True, visual="dolly-zoom on INF as it sinks in", camera="dolly zoom"),
    45: S(func="action", visual="INF dials his lawyer on speaker, live", reaction="friends lean in", camera="medium, rack to F1", sfx=[(93.0, "tap", {})]),
    46: S(func="action", visual="he holds the phone up to the chat", camera="medium"),
    47: S(func="insert", visual="call screen: LAWYER", camera="card"),
    48: S(func="dialogue", joke=True, visual="the lawyer's voice; INF's face", reaction="F2 stifles a laugh", camera="close-up"),
    49: S(func="action", visual="INF flips the camera to himself", camera="low close-up"),
    50: S(func="dialogue", visual="INF yells into his phone", reaction="guests turn to look", camera="ECU, handheld"),
    51: S(func="action", visual="INF kneels and rips open his biggest suitcase", camera="medium", sfx=[("word:ripped", "cardboard", dict(sync=True, gain=-2))]),
    52: S(func="reveal", joke=True, visual="the suitcase is stuffed with hotel bathrobes", reaction="friends' phones dip", camera="top-down crane"),
    53: S(func="insert", visual="chat floods with hotels: 'that's OUR robe'", camera="chat card", sfx=[(111.1, "ping", {}), (111.6, "ping", {}), (112.0, "ping", {})]),
    54: S(func="action", visual="INF slaps his card on the desk", camera="insert from above", sfx=[(113.6, "thud", dict(sync=True, gain=-4))]),
    55: S(func="reaction", joke=True, visual="CLK smiles", camera="ECU, slow push"),
    56: S(func="dialogue", visual="CLK points up: bags are on the ninth floor", camera="medium"),
    57: S(func="dialogue", joke=True, visual="the VIP doors close in INF's face", camera="medium at the elevator", sfx=[(118.8, "doors", dict(dur=0.8, sync=True))]),
    58: S(func="action", visual="INF hauls the bags down the stairwell, live", camera="high wide", sfx=[(120.6, "steps", dict(n=8, every=0.6, surface="concrete"))]),
    59: S(func="action", visual="INF staggers on the landing", reaction="chat: human luggage cart", camera="low medium", sfx=[("word:called+0.2", "breath", {})]),
    60: S(func="pause", visual="the empty roach box on the desk", camera="insert"),
    61: S(func="reveal", joke=True, visual="the cockroach crawls out and sits up", camera="macro"),
    62: S(func="action", visual="the corridor to the one door nobody books", camera="wide low, dolly down the corridor"),
    63: S(func="reveal", joke=True, visual="ROOM 404; the roach slips under the door", camera="close-up zoom", sfx=[(133.0, "door", dict(gain=-4))]),
}
BEDS = [dict(t0=0.0, t1=2.0, kind="street"), dict(t0=2.0, t1=17.4, kind="lobby"), dict(t0=17.4, t1=18.2, kind="elevator"),
        dict(t0=18.2, t1=19.3, kind="lobby", gain=-4), dict(t0=19.3, t1=24.8, kind="stairs"), dict(t0=24.8, t1=30.2, kind="room"),
        dict(t0=30.2, t1=31.4, kind="lobby", gain=-6), dict(t0=31.4, t1=37.6, kind="room"), dict(t0=37.6, t1=56.2, kind="lobby", gain=-3),
        dict(t0=56.2, t1=64.4, kind="street"), dict(t0=64.4, t1=120.4, kind="lobby"), dict(t0=120.4, t1=127.0, kind="stairs"),
        dict(t0=127.0, t1=129.1, kind="lobby", gain=-4), dict(t0=129.1, t1=134.2, kind="corridor")]


def sheet():
    out = []
    for b in edit.segment(W):
        out.append(dict(b, **SHEET.get(b["id"], {})))
    return out


if __name__ == "__main__":
    import shots
    sh = sheet()
    open(os.path.join(HERE, "beats.md"), "w").write(edit.markdown(sh))
    json.dump(edit.compile_cues(sh, W), open(os.path.join(HERE, "cues.json"), "w"), indent=1)
    json.dump(BEDS, open(os.path.join(HERE, "beds.json"), "w"), indent=1)
    end = float(os.environ.get("END_S", 20))
    SH = [dict(id=s["id"], t0=s["t0"], t1=s["t1"], framing=s["cam"][0] if s["cam"] else "card",
               move=bool(s.get("move")) or any(p[3].endswith("_walk") or p[3] == "carry_climb" for p in s["chars"].values()),
               func="reaction" if "disbelief" in s["note"] or "smirk" in s["note"] else "") for s in shots.S if s["t0"] < end]
    probs = edit.lint([b for b in sh if b["t0"] < end], SH, W)
    print("\n".join(f"EDIT LINT: {p}" for p in probs) or "EDIT LINT: clean")
    print("beats:", len(sh), "| sfx cues:", len(edit.compile_cues(sh, W)))
