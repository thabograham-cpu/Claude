"""Reference-style captions (Do Your Job.mp4) as an ASS file for ffmpeg/libass.

Look: white Montserrat ExtraBold (tools/fonts), sentence case as spoken (transcript casing), 1-3 words per
caption, at most 2 lines of ~14 characters, a thin dark outline + soft shadow, centred at 74% of the frame
height. Captions never sit on a face: give face boxes per frame and they move to the upper safe band.
Vertical-video safe area (YouTube Shorts): text stays inside x 9..82% (right-side buttons) and y 12..80%
(title/channel UI at the bottom).

    python3 tools/captions.py words.json out.ass [faces.json] [fps]
    words.json: [{"w", "s", "e"}] (tools/asr.py); faces.json: {"<frame>": [[x0, y0, x1, y1], ...]} in 0..1, y down.
Self-test: python3 tools/captions.py
"""
import json, re, sys

W, H = 1080, 1920
Y_MAIN, Y_ALT = 0.74, 0.30          # caption centre (fraction of height): default and face-free alternative
SAFE_X, SAFE_Y = (0.09, 0.82), (0.12, 0.80)
MAX_WORDS, MAX_LINE, MAX_GAP = 3, 14, 0.35
STYLE = ("Style: Cap,Montserrat ExtraBold,64,&H00FFFFFF,&H00FFFFFF,&H00141414,&H64000000,0,0,0,0,100,100,0,0,1,"
         "2.6,1.6,5,40,40,40,1")


def clean(w):
    """Spoken word as it should read: drop quotes and trailing . , ; : (keep ? ! and abbreviations like a.m.);
    commas and points inside numbers stay ($4,000)."""
    w = re.sub(r"[\"“”()]", "", w.replace("’", "'")).strip()
    return w if re.search(r"\w\.\w\.$", w) else re.sub(r"[.,;:]+$", "", w)


def merge(words, fix=None):
    """Repair ASR tokenisation for display: "five" "-star" -> "five-star", "$4" ",000" -> "$4,000",
    "a" ".m." -> "a.m."; then whole-word spelling fixes (fix = {"lean": "lien"})."""
    out = []
    for w in words:
        if out and re.match(r"^[-,.][\w.]", w["w"]):
            out[-1] = dict(out[-1], w=out[-1]["w"] + w["w"], e=w["e"]); continue
        out.append(dict(w))
    for w in out:
        core = re.sub(r"[^\w']", "", w["w"]).lower()
        if fix and core in fix: w["w"] = w["w"].lower().replace(core, fix[core]) if w["w"].islower() else w["w"].replace(w["w"].strip(".,?!"), fix[core])
    return out


def chunks(words):
    """Group words into captions: <= MAX_WORDS, break after sentence/clause punctuation or a pause > MAX_GAP,
    and keep each caption to 2 lines of MAX_LINE characters."""
    out, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        txt = " ".join(clean(x["w"]) for x in cur)
        brk = (nxt is None or len(cur) >= MAX_WORDS or re.search(r"[.,?!;:]$", w["w"]) or nxt["s"] - w["e"] > MAX_GAP
               or len(txt + " " + clean(nxt["w"])) > 2 * MAX_LINE)
        if brk:
            out.append(dict(text=txt, s=cur[0]["s"], e=cur[-1]["e"])); cur = []
    return [c for c in out if c["text"]]


def wrap(text):
    if len(text) <= MAX_LINE: return text
    ws = text.split(); best = None
    for k in range(1, len(ws)):
        a, b = " ".join(ws[:k]), " ".join(ws[k:])
        sc = max(len(a), len(b))
        if best is None or sc < best[0]: best = (sc, a + "\\N" + b)
    return best[1] if best else text


def timed(caps, lead=0.04, hold=0.6):
    """On screen from just before the first word until the next caption (or a short hold in a pause)."""
    for i, c in enumerate(caps):
        nxt = caps[i + 1]["s"] - lead if i + 1 < len(caps) else None
        c["t0"] = max(0.0, c["s"] - lead)
        c["t1"] = min(nxt, c["e"] + hold) if nxt is not None else c["e"] + hold
        c["t1"] = max(c["t1"], c["t0"] + 0.25)
    return caps


def place(caps, faces=None, fps=24):
    """Caption centre y per caption: Y_MAIN unless a face box overlaps the caption band during it."""
    for c in caps:
        lines = c["text"].count("\\N") + 1 if "\\N" in c.get("text", "") else (2 if len(c["text"]) > MAX_LINE else 1)
        half = 0.025 * lines + 0.01
        band = (Y_MAIN - half, Y_MAIN + half)
        hit = False
        if faces:
            for f in range(int(c["t0"] * fps) + 1, int(c["t1"] * fps) + 2):
                for x0, y0, x1, y1 in faces.get(str(f), faces.get(f, [])):
                    if y0 < band[1] and y1 > band[0] and x0 < 0.75 and x1 > 0.25: hit = True; break
                if hit: break
        c["y"] = Y_ALT if hit else Y_MAIN
    return caps


def ts(t): return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def ass(caps, extra_styles=(), extra_events=""):
    head = ("[Script Info]\nScriptType: v4.00+\nPlayResX: %d\nPlayResY: %d\nWrapStyle: 2\n\n[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, "
            "StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            % (W, H)) + "\n".join((STYLE,) + tuple(extra_styles)) + "\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    x = int(W * (SAFE_X[0] + SAFE_X[1]) / 2)
    ev = "".join(f"Dialogue: 0,{ts(c['t0'])},{ts(c['t1'])},Cap,,0,0,0,,{{\\pos({x},{int(c['y'] * H)})}}{wrap(c['text'])}\n" for c in caps)
    return head + ev + extra_events


def build(words, faces=None, fps=24, fix=None):
    return place(timed(chunks(merge(words, fix))), faces, fps)


def _selftest():
    ws = [dict(w=w, s=i * 0.3, e=i * 0.3 + 0.25) for i, w in enumerate("Desk boy, bags, ninth floor, elevators for VIPs.".split())]
    ws += [dict(w="So", s=3.5, e=3.7), dict(w="I", s=3.75, e=3.85), dict(w="carried", s=3.9, e=4.2), dict(w="all", s=4.25, e=4.4)]
    c = build(ws)
    texts = [x["text"] for x in c]
    assert texts[:4] == ["Desk boy", "bags", "ninth floor", "elevators for VIPs"], texts
    assert texts[4] == "So I carried" and texts[5] == "all", texts          # pause before "So" starts a caption; max 3 words
    assert all(a["t1"] <= b["t0"] + 1e-9 for a, b in zip(c, c[1:])), "captions overlap"
    assert wrap("threw a hundred-dollar") == "threw a\\Nhundred-dollar"
    face = {str(f): [[0.35, 0.65, 0.65, 0.85]] for f in range(1, 30)}
    assert place(timed(chunks(ws[:2])), face)[0]["y"] == Y_ALT and place(timed(chunks(ws[:2])))[0]["y"] == Y_MAIN
    assert SAFE_Y[0] < Y_ALT < Y_MAIN < SAFE_Y[1]
    m = merge([dict(w="five", s=0, e=0.2), dict(w="-star", s=0.2, e=0.4), dict(w="$4", s=1, e=1.2), dict(w=",000,", s=1.2, e=1.5),
               dict(w="The", s=2, e=2.1), dict(w="innkeepers", s=2.1, e=2.5), dict(w="lean.", s=2.5, e=2.8)], {"lean": "lien"})
    assert [w["w"] for w in m] == ["five-star", "$4,000,", "The", "innkeepers", "lien."], [w["w"] for w in m]
    assert [c["text"] for c in chunks(m)] == ["five-star", "$4,000", "The innkeepers lien"], [c["text"] for c in chunks(m)]
    assert clean("a.m.,") == "a.m" or clean("a.m.") == "a.m.", clean("a.m.")
    assert "Montserrat ExtraBold" in ass(c) and "\\pos(" in ass(c)
    print("captions.py self-test OK")


if __name__ == "__main__":
    if len(sys.argv) == 1: _selftest(); sys.exit()
    W_ = json.load(open(sys.argv[1])); W_ = W_["words"] if isinstance(W_, dict) else W_
    F = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else None
    open(sys.argv[2], "w").write(ass(build(W_, F, int(sys.argv[4]) if len(sys.argv) > 4 else 24)))
    print("wrote", sys.argv[2])
