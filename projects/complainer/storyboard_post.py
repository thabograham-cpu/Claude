"""Label storyboard stills, render 2D cards, build contact-sheet pages and a timed animatic.
Run from anywhere with plain python3 (needs ffmpeg). Inputs: storyboard/raw/*.png, shots.py, audio/."""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from shots import S

SB = os.path.join(HERE, "storyboard"); RAW = os.path.join(SB, "raw"); FIN = os.path.join(SB, "final"); TXT = os.path.join(SB, "txt")
for d in (FIN, TXT): os.makedirs(d, exist_ok=True)
FONT = os.path.join(HERE, "..", "..", "tools", "fonts", "PressStart2P-Regular.ttf")
WORDS = json.load(open(os.path.join(HERE, "audio", "words.json")))
W, H = 360, 640


def ff(*a):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *a], check=True)


def words(t0, t1):
    out = ""
    for w in (w["w"] for w in WORDS if w["s"] < t1 - 0.05 and w["e"] > t0 + 0.05):
        out += w if w[:1] in ",.'" or not out else " " + w  # whisper splits "$4,000" into "$4" + ",000"
    return out


def wrap(t, n):
    out, line = [], ""
    for w in t.split():
        if len(line) + len(w) + 1 > n: out.append(line); line = w
        else: line = (line + " " + w).strip()
    return "\n".join(out + [line])


def tf(name, text):
    p = os.path.join(TXT, name); open(p, "w").write(text); return p


def dt(textfile, x, y, size, color="white", box=True):
    b = ":box=1:boxcolor=black@0.55:boxborderw=6" if box else ""
    return f"drawtext=fontfile={FONT}:textfile={textfile}:x={x}:y={y}:fontsize={size}:fontcolor={color}:line_spacing=6{b}"


for s in S:
    i = s["id"]; src = os.path.join(RAW, f"shot_{i:02d}.png"); out = os.path.join(FIN, f"shot_{i:02d}.png")
    mv = s.get("move") or {}
    tag = mv.get("move") or ("rack focus" if "rack_to" in mv else ("handheld" if mv.get("handheld") else ""))
    head = tf(f"{i}_h.txt", f"{i:02d}  {s['t0']:.1f}-{s['t1']:.1f}s" + (f"  [{tag}]" if tag else ""))
    note = tf(f"{i}_n.txt", wrap(s["note"], 30))
    vo = tf(f"{i}_v.txt", wrap(words(s["t0"], s["t1"]).upper(), 20))
    filters = [dt(head, 8, 8, 12, "yellow"), dt(vo, "(w-tw)/2", "h*0.64", 13, "0xFF9A3C"), dt(note, 8, "h-th-10", 10)]
    if s["card"]:
        kind, _, body = s["card"].partition(":")
        card = tf(f"{i}_c.txt", wrap(body, 16))
        kt = tf(f"{i}_k.txt", {"chat": "LIVE CHAT", "viewers": "LIVE", "replay": "STREAM REPLAY", "search": "SEARCH", "result": "RESULT",
                               "map": "MAP", "story": "STORY", "title": "TITLE CARD", "call": "CALL"}.get(kind, kind.upper()))
        cf = [dt(kt, "(w-tw)/2", "h*0.30", 14, "red"), dt(card, "(w-tw)/2", "h*0.40", 16, "white", box=False)]
        if os.path.exists(src):  # card overlaid on a 3D shot
            ff("-i", src, "-vf", ",".join(cf + filters), out)
        else:
            ff("-f", "lavfi", "-i", f"color=c=0x15151f:s={W}x{H}", "-frames:v", "1", "-vf", ",".join(cf + filters), out)
    else:
        ff("-i", src, "-vf", ",".join(filters), out)
    end = os.path.join(RAW, f"shot_{i:02d}_end.png")
    if os.path.exists(end):  # last frame of a camera move
        eh = tf(f"{i}_e.txt", f"{i:02d}  END  [{tag}]")
        ff("-i", end, "-vf", ",".join([dt(eh, 8, 8, 12, "0x7CFC00")] + filters[1:]), os.path.join(FIN, f"shot_{i:02d}_end.png"))

# contact-sheet pages: 6 x 2 per page
def pages(files, prefix):
    for p in range(0, len(files), 12):
        page = files[p:p + 12]; n = len(page)
        ins = [a for f in page for a in ("-i", f)]
        fc = "".join(f"[{k}:v]scale=240:-1[v{k}];" for k in range(n))
        lay = "|".join(f"{(k % 6) * 244}_{(k // 6) * 431}" for k in range(n))
        ff(*ins, "-filter_complex", fc + "".join(f"[v{k}]" for k in range(n)) + f"xstack=inputs={n}:layout={lay}:fill=gray",
           "-frames:v", "1", os.path.join(SB, f"{prefix}_{p // 12 + 1:02d}.png"))


for old in os.listdir(SB):
    if old.endswith(".png") and old.startswith(("page_", "moves_")): os.remove(os.path.join(SB, old))
pages([os.path.join(FIN, f"shot_{s['id']:02d}.png") for s in S], "page")
moving = [s for s in S if os.path.exists(os.path.join(FIN, f"shot_{s['id']:02d}_end.png"))]
pages([os.path.join(FIN, f"shot_{s['id']:02d}{e}.png") for s in moving for e in ("", "_end")], "moves")  # start | end pairs

# animatic: each still held for its shot duration, under the voiceover
lst = os.path.join(SB, "animatic.txt")
with open(lst, "w") as f:
    for s in S:
        a, e, d = os.path.join(FIN, f"shot_{s['id']:02d}.png"), os.path.join(FIN, f"shot_{s['id']:02d}_end.png"), s["t1"] - s["t0"]
        if os.path.exists(e): f.write(f"file '{a}'\nduration {d / 2:.3f}\nfile '{e}'\nduration {d / 2:.3f}\n")
        else: f.write(f"file '{a}'\nduration {d:.3f}\n")
    f.write(f"file '{os.path.join(FIN, f'shot_{S[-1]['id']:02d}.png')}'\n")
ff("-f", "concat", "-safe", "0", "-i", lst, "-i", os.path.join(HERE, "audio", "voiceover.mp3"), "-vf", "fps=24,format=yuv420p",
   "-c:v", "libx264", "-crf", "20", "-c:a", "aac", "-shortest", os.path.join(SB, "animatic.mp4"))

assert all(os.path.exists(os.path.join(FIN, f"shot_{s['id']:02d}.png")) for s in S), "every shot needs a final still"
print("storyboard done:", len(S), "shots")
