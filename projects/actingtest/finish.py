"""Encode the acting test: ActingTest.mp4 (clean) and ActingTest_debug.mp4 (each character's intention and the
beat being played, burned in, for frame-by-frame review). Reads direction.md written by actingtest.py."""
import os, re, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); FONTS = os.path.join(HERE, "..", "..", "tools", "fonts"); FPS = 24
rows = [l.split("|")[1:-1] for l in open(os.path.join(HERE, "direction.md")) if l.startswith("| ") and not l.startswith("| who")]


def ts(t): return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


ev, top = "", ""
for k, (who, intent, preset, role, beats) in enumerate([c.strip() for c in r] for r in rows):
    top += f"{who} ({preset}, {role}): {intent}\\N"
    for b in filter(None, (x.strip() for x in beats.split(";"))):
        t, kind, val = re.match(r"([\d.]+)s (\w+) (\S+)", b).groups(); t = float(t)
        ev += f"Dialogue: 1,{ts(t)},{ts(t + 0.9)},Beat,,0,0,{90 + 46 * k},,{who}: {kind} {val}\n"
head = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Top,DejaVu Sans,26,&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,1,0,0,0,100,100,0,0,3,2,0,7,30,30,30,1
Style: Beat,DejaVu Sans Mono,40,&H0000FFFF,&H0000FFFF,&H00000000,&H90000000,1,0,0,0,100,100,0,0,3,2,0,1,30,30,90,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
n = len([f for f in os.listdir(os.path.join(HERE, "frames")) if f.endswith(".png")])
for name, extra in (("ActingTest.mp4", ""), ("ActingTest_debug.mp4", f"Dialogue: 0,{ts(0)},{ts(n / FPS)},Top,,0,0,0,,{top}\n" + ev)):
    ass = os.path.join(HERE, "check", name.replace(".mp4", ".ass")); os.makedirs(os.path.dirname(ass), exist_ok=True)
    open(ass, "w").write(head + extra)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(HERE, "frames", "f_%04d.png"),
                    "-vf", f"scale=1080:1920:flags=lanczos,ass={ass}:fontsdir={FONTS}", "-c:v", "libx264", "-crf", "18",
                    "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart", os.path.join(HERE, name)], check=True)
    print("wrote", name)
