"""Encode the rendered frames with the voiceover and burned-in word captions (python3 + ffmpeg).
END_S=20 python3 projects/complainer/finish.py  ->  projects/complainer/Complainer_<END_S>s.mp4"""
import os, json, re, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); FONTS = os.path.join(HERE, "..", "..", "tools", "fonts")
FPS, END = 24, float(os.environ.get("END_S", 20))


def ts(t):
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def chunks(words, n=3):
    """Caption lines of up to n words; a line ends early after . , ? !"""
    out, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) == n or re.search(r"[.,?!]$", w["w"]): out.append(cur); cur = []
    return out + ([cur] if cur else [])


words = [w for w in json.load(open(os.path.join(HERE, "audio", "words.json"))) if w["s"] < END]
lines = chunks(words)
assert sum(len(c) for c in lines) == len(words)
ass = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Press Start 2P,52,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,8,0,2,60,60,430,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
for k, c in enumerate(lines):
    t0 = c[0]["s"]; t1 = min(END, lines[k + 1][0]["s"] if k + 1 < len(lines) else c[-1]["e"] + 0.4)
    text = " ".join(w["w"] for w in c).upper().replace(" -", "-")  # whisper splits "five -star"
    ass += f"Dialogue: 0,{ts(t0)},{ts(t1)},Cap,,0,0,0,,{{\\fscx112\\fscy112\\t(0,90,\\fscx100\\fscy100)}}{text}\n"
open(os.path.join(HERE, "captions.ass"), "w").write(ass)
out = os.path.join(HERE, f"Complainer_{END:g}s.mp4")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(HERE, "frames", "f_%04d.png"),
                "-i", os.path.join(HERE, "audio", "voiceover.mp3"),
                "-vf", f"scale=1080:1920:flags=lanczos,ass={os.path.join(HERE, 'captions.ass')}:fontsdir={FONTS}",
                "-af", f"atrim=0:{END},afade=t=out:st={END - 0.3}:d=0.3", "-t", str(END),
                "-c:v", "libx264", "-crf", "17", "-preset", "slow", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart", out], check=True)
print("wrote", out, "-", len(lines), "caption lines")
