"""Narrative editing director: narration -> story beats -> what we SEE, who REACTS, how we SHOOT it, what we HEAR.

Grammar measured on the reference (Do Your Job.mp4, 122 s):
  * a new picture every 1.5-3 s, but few hard cuts: the camera moves through beats (dolly with the car from
    "drove up" into "threw a hundred-dollar"), and setups change with quick 4-5 frame dissolves or cuts on action;
  * every narrated action is performed on screen (the bill is thrown, picked up, the pump nozzle is shown);
  * quotes are played by the character in a closer shot; listeners react in their own shot;
  * jokes land, then the picture holds on the reaction (~1 s) before moving on;
  * an ambience/music bed sits ~10-14 dB under the narration; effects peak in the pauses.

    beats = segment(words)                      # sentence/clause beats with timings and a suggested function
    sheet = [dict(beat, visual=..., reaction=..., camera=..., sfx=[(at, kind, {args})], shots=[ids]), ...]
    problems = lint(sheet, shots, words)        # pacing, enactment, holds, variety, sound sync
    cues = compile_cues(sheet, words)           # sfx.render() cue list; `at` may be seconds or "word:bags"
    open("beats.md", "w").write(markdown(sheet))
Self-test: python3 tools/edit.py
"""
import re, statistics

FUNCS = ("establish", "action", "dialogue", "reaction", "insert", "reveal", "pov", "pause", "transition")
FRAMINGS = ("wide", "med", "cu", "ecu", "insert")
PACE = dict(min_shot=0.6, max_static=3.0, target=(1.4, 3.2), joke_hold=0.8)
LOUD = {"snap", "ding", "doors", "thud", "door", "whoosh", "shutter"}          # effects that must sync to what we see
_VERB = re.compile(r"\b(\w+ed|walked|threw|carried|ran|took|paid|ripped|slapped|kept|picked|pointed|snapped|called|"
                   r"brings|finds|laughed|smiled|stayed|ordered|said|came|went|left|grabbed|opened|closed|rolled)\b", re.I)


def _word(w): return re.sub(r"[^\w']", "", w["w"]).lower()


def segment(words, pause=0.3, min_words=3):
    """Beats: break after . ? ! always; after , ; : or a pause > `pause` s when the running clause already has
    >= min_words words. Returns [{id, t0, t1, text, func}] with a suggested function per beat."""
    out, cur = [], []
    for i, w in enumerate(words):
        cur.append(w); nxt = words[i + 1] if i + 1 < len(words) else None
        end = re.search(r"[.?!]$", w["w"]) or nxt is None
        soft = (re.search(r"[,;:]$", w["w"]) or (nxt and nxt["s"] - w["e"] > pause)) and len(cur) >= min_words
        if end or soft:
            out.append(dict(id=len(out) + 1, t0=cur[0]["s"], t1=cur[-1]["e"], text=" ".join(x["w"] for x in cur))); cur = []
    merged = []                                                               # a 1-word tail joins its clause
    for b in out:
        if merged and len(b["text"].split()) < 2 and not re.search(r"[.?!]$", merged[-1]["text"]):
            merged[-1].update(t1=b["t1"], text=merged[-1]["text"] + " " + b["text"])
        else: merged.append(b)
    out = merged
    for k, b in enumerate(out):
        b["id"] = k + 1
        b["gap_after"] = round((out[k + 1]["t0"] if k + 1 < len(out) else b["t1"] + 1.0) - b["t1"], 2)
        b["func"] = suggest(b, k == 0)
    return out


def suggest(b, first=False):
    """Heuristic first guess - the director overrides it in the beat sheet."""
    t = b["text"]; n = len(t.split())
    if first: return "establish"
    if t.rstrip().endswith("?") and n <= 4: return "pause"                 # set-up question: hold for the turn
    if re.match(r"^(desk boy|bill's|bring|what are|this hotel|pay the|bags are|elevators)", t, re.I) or re.search(r"\b(you|my bags|I'm)\b", t) and not re.search(r"\bI said\b", t):
        return "dialogue"
    if re.search(r"\$?\d[\d,]*|\binches\b|\bbill\b|\bbox\b|\bsuitcase", t, re.I) and n <= 8: return "insert"
    if _VERB.search(t): return "action"
    if b.get("gap_after", 0) > 0.45 and n <= 5: return "reaction"
    return "transition"


def anchor(at, words, t0=0.0):
    """Seconds, or 'word:<w>' = that word's start (first match at/after t0), 'word:<w>+0.2' with an offset."""
    if isinstance(at, (int, float)): return float(at)
    m = re.match(r"word:([\w'$,]+?)([+-][\d.]+)?$", at)
    if not m: raise ValueError(at)
    tgt = m.group(1).lower().strip("$")
    for w in words:
        if w["s"] >= t0 - 0.05 and _word(w).strip("$") == tgt: return w["s"] + float(m.group(2) or 0)
    raise KeyError(f"word {tgt!r} not found after {t0:.2f}s")


def compile_cues(sheet, words):
    """Beat-sheet sfx -> absolute cues for tools/sfx.py render()."""
    out = []
    for b in sheet:
        for at, kind, args in b.get("sfx", []):
            out.append(dict(t=round(anchor(at, words, b["t0"]), 3), kind=kind, beat=b["id"], **args))
    return sorted(out, key=lambda c: c["t"])


def lint(sheet, shots, words=None, fps=24):
    """Editing checks. shots: [{id, t0, t1, framing, move (bool), func}] in timeline order.
    Returns human-readable problems (empty = the cut reads)."""
    P = []
    for b in sheet:
        v = (b.get("visual") or "").lower()
        if not v or re.match(r"^(show|shows|we see|he is shown|close-up of)\b", v) or not re.search(r"\w+s\b|\w+ing\b|\w+ed\b", v):
            P.append(f"beat {b['id']}: visual must be an action we watch happen, not a character on display ({b.get('visual')!r})")
        if b.get("func") in ("reaction", "pause") or b.get("joke"):
            end = b["t1"]; cut = next((s["t1"] for s in shots if s["t0"] <= end < s["t1"]), None)
            if cut is not None and cut - end < PACE["joke_hold"] - 1e-6:
                P.append(f"beat {b['id']}: the joke/reaction needs {PACE['joke_hold']} s to land; the cut comes {cut - end:.2f} s after the line")
    lens = [s["t1"] - s["t0"] for s in shots]
    for s, L in zip(shots, lens):
        if L < PACE["min_shot"] - 1e-6 and not s.get("flash"): P.append(f"shot {s['id']}: {L:.2f} s is too short to read")
        if L > PACE["max_static"] and not s.get("move") and s.get("func") not in ("reaction", "establish"):
            P.append(f"shot {s['id']}: {L:.1f} s with no camera move or new action - add a move, an action beat or a cut")
    if lens:
        med = statistics.median(lens)
        if not PACE["target"][0] <= med <= PACE["target"][1]: P.append(f"median shot {med:.2f} s is outside the reference's {PACE['target']} s")
    for a, b, c in zip(shots, shots[1:], shots[2:]):
        if a.get("framing") == b.get("framing") == c.get("framing") and not (a.get("move") or b.get("move") or c.get("move")):
            P.append(f"shots {a['id']}-{c['id']}: three static {a['framing']} shots in a row - vary size/angle")
    if words:
        spoken = [(w["s"], w["e"]) for w in words]
        for c in compile_cues(sheet, words):
            if c["kind"] in LOUD and not c.get("sync"):
                for s0, s1 in spoken:
                    if s0 - 0.02 <= c["t"] < s1 - 0.05:
                        P.append(f"beat {c['beat']}: loud '{c['kind']}' at {c['t']:.2f}s lands inside a word - move it to a gap or mark it sync=True"); break
    return P


def markdown(sheet):
    rows = ["| beat | time | narration | function | visual action | reaction | camera | sound | shots |", "|---|---|---|---|---|---|---|---|---|"]
    for b in sheet:
        snd = ", ".join(f"{k}@{a}" for a, k, _ in b.get("sfx", []))
        rows.append(f"| {b['id']} | {b['t0']:.2f}-{b['t1']:.2f} | {b['text']} | {b.get('func', '')} | {b.get('visual', '')} | "
                    f"{b.get('reaction', '')} | {b.get('camera', '')} | {snd} | {','.join(map(str, b.get('shots', [])))} |")
    return "# Beat sheet\n\n" + "\n".join(rows) + "\n"


def _selftest():
    ws = []
    for i, w in enumerate("He walked into my lobby, live. Desk boy, bags. His trick? He laughed.".split()):
        ws.append(dict(w=w, s=i * 0.4, e=i * 0.4 + 0.3))
    ws[7]["s"] += 0.0
    bs = segment(ws)
    assert [b["text"] for b in bs] == ["He walked into my lobby, live.", "Desk boy, bags.", "His trick?", "He laughed."], [b["text"] for b in bs]
    assert bs[0]["func"] == "establish" and bs[1]["func"] == "dialogue" and bs[2]["func"] == "pause" and bs[3]["func"] == "action", [b["func"] for b in bs]
    assert abs(anchor("word:bags-0.3", ws) - ws[8]["s"] + 0.3) < 1e-9
    assert abs(anchor("word:bags", ws) - ws[8]["s"]) < 1e-9 and abs(anchor("word:bags+0.1", ws) - ws[8]["s"] - 0.1) < 1e-9
    sheet = [dict(bs[0], visual="He strides through the doors, phone up"), dict(bs[1], visual="snaps his fingers at the clerk", sfx=[("word:bags", "snap", {})]),
             dict(bs[2], visual="shows the box"), dict(bs[3], visual="laughs at the clerk")]
    shots = [dict(id=1, t0=0, t1=1.0, framing="wide", move=True), dict(id=2, t0=1.0, t1=2.0, framing="cu"),
             dict(id=3, t0=2.0, t1=2.3 + 0.4 * 3, framing="cu"), dict(id=4, t0=3.5, t1=4.0, framing="cu", func="reaction")]
    P = lint(sheet, shots, ws)
    assert any("beat 3: visual" in p for p in P), P                         # "shows ..." is display, not action
    assert any("loud 'snap'" in p for p in P), P                            # snap on top of a word, not marked sync
    assert any("three static cu" in p for p in P) and any("shot 4: 0.50 s" in p for p in P), P
    sheet[1]["sfx"] = [("word:bags", "snap", {"sync": True})]
    assert not any("loud 'snap'" in p for p in lint(sheet, shots, ws))
    assert compile_cues(sheet, ws)[0]["kind"] == "snap" and "| 2 |" in markdown(sheet)
    print("edit.py self-test OK")


if __name__ == "__main__":
    _selftest()
