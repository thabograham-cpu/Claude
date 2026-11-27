"""Mix the dialogue lines at their start times and encode two MP4s (python3 + ffmpeg):
  FaceTest.mp4          clean, with dialogue captions
  FaceTest_debug.mp4    + per-frame speaker / phoneme heard / top visemes (for frame-by-frame inspection)"""
import os, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); FONTS = os.path.join(HERE, "..", "..", "tools", "fonts")
D = json.load(open(os.path.join(HERE, "dialogue.json"))); FPS = D["fps"]
T = json.load(open(os.path.join(HERE, "timing.json")))
n = len([f for f in os.listdir(os.path.join(HERE, "frames")) if f.endswith(".png")])

# audio: each line delayed to its start
ins, flt = [], []
for i, ln in enumerate(D["lines"]):
    ins += ["-i", os.path.join(HERE, ln["audio"])]
    ms = int(round(ln["start"] * 1000)); flt.append(f"[{i}]adelay={ms}|{ms},aformat=channel_layouts=mono[a{i}]")
mix = os.path.join(HERE, "mix.wav")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *ins, "-filter_complex",
                ";".join(flt) + ";" + "".join(f"[a{i}]" for i in range(len(D["lines"]))) + f"amix=inputs={len(D['lines'])}:normalize=0,apad",
                "-t", f"{n / FPS:.3f}", "-ar", "48000", mix], check=True)


def ts(t): return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


head = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,DejaVu Sans,54,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,1,0,0,0,100,100,0,0,1,4,2,2,60,60,300,1
Style: Dbg,DejaVu Sans Mono,34,&H0000FFFF,&H0000FFFF,&H00000000,&HA0000000,1,0,0,0,100,100,0,0,3,2,0,7,30,30,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
cap = "".join(f"Dialogue: 0,{ts(ln['start'])},{ts(ln['start'] + 0.2 + len(ln['text']) * 0.065)},Cap,,0,0,0,,"
              f"{ln['speaker']} ({ln['emotion']}): {ln['text']}\n" for ln in D["lines"])
dbg = ""
for r in T:
    t = (r["f"] - 1) / FPS
    vis = "  ".join(f"{v.split('_')[0]}:{w:.2f}" for v, w in r["vis"]) or "rest"
    dbg += f"Dialogue: 1,{ts(t)},{ts(t + 1 / FPS)},Dbg,,0,0,0,,f{r['f']:03d} {r['who']}  heard:{r['ph']:<3}\\N{vis}\n"
for name, extra in (("FaceTest.mp4", ""), ("FaceTest_debug.mp4", dbg)):
    ass = os.path.join(HERE, "check", name.replace(".mp4", ".ass")); os.makedirs(os.path.dirname(ass), exist_ok=True)
    open(ass, "w").write(head + cap + extra)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(HERE, "frames", "f_%04d.png"),
                    "-i", mix, "-vf", f"scale=1080:1920:flags=lanczos,ass={ass}:fontsdir={FONTS}", "-c:v", "libx264", "-crf", "17",
                    "-preset", "slow", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
                    os.path.join(HERE, name)], check=True)
    print("wrote", name)
