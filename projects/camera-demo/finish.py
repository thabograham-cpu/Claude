"""Burn technique labels onto the rendered frames and encode the review MP4 (python3 + ffmpeg)."""
import os, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); FONTS = os.path.join(HERE, "..", "..", "tools", "fonts")
FPS = 24
SEGS = [  # (first frame, last frame, title, what to watch)
    (1, 96, "1  CAMERA TRACKING", "aim + focus follow him, camera trucks alongside"),
    (97, 180, "2  PAN", "camera stays put, view swings to the desk"),
    (181, 264, "3  DOLLY IN", "camera physically pushes in to a close-up"),
    (265, 348, "4  OPTICAL ZOOM", "camera locked, lens 20 mm to 85 mm"),
    (349, 456, "5  ORBIT", "camera circles the two-shot"),
    (457, 540, "6  DEPTH OF FIELD", "f/1.2: the bill sharp, the clerk soft"),
    (541, 636, "7  RACK FOCUS", "focus pulls from him to the clerk"),
    (637, 720, "8  OVER THE SHOULDER", "framed past the clerk's shoulder"),
]


def ts(f):
    t = (f - 1) / FPS; return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


ass = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Title,Press Start 2P,46,&H003C9AFF,&H003C9AFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,7,0,8,40,40,150,1
Style: Sub,Press Start 2P,24,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,5,0,8,60,60,235,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
for a, b, title, sub in SEGS:
    ass += f"Dialogue: 0,{ts(a)},{ts(b + 1)},Title,,0,0,0,,{{\\fscx118\\fscy118\\t(0,120,\\fscx100\\fscy100)}}{title}\n"
    ass += f"Dialogue: 0,{ts(a + 6)},{ts(b + 1)},Sub,,0,0,0,,{sub}\n"
open(os.path.join(HERE, "labels.ass"), "w").write(ass)
out = os.path.join(HERE, "CameraDemo_Hotel.mp4")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(HERE, "frames", "f_%04d.png"),
                "-vf", f"scale=1080:1920:flags=lanczos,ass={os.path.join(HERE, 'labels.ass')}:fontsdir={FONTS}",
                "-c:v", "libx264", "-crf", "17", "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], check=True)
print("wrote", out)
