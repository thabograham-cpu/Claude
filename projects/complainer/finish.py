"""Finish the Complainer cut: narration + ambience beds + beat-sheet sound effects (tools/sfx.py), reference-style
captions that avoid faces (tools/captions.py), loudness-normalised for YouTube (-14 LUFS).
Inputs: frames/f_####.png (scene.py render), audio/voiceover.mp3 + words.json, cues.json + beds.json (beats.py),
faces.json (scene.py build).
END_S=20 python3 projects/complainer/finish.py  ->  projects/complainer/Complainer_<END_S>s.mp4 (+ _mix.wav)"""
import os, sys, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, "..", "..", "tools")]
import captions, sfx, beats
FONTS = os.path.join(HERE, "..", "..", "tools", "fonts")
FPS, END = 24, float(os.environ.get("END_S", 20)); TAG = os.environ.get("TAG", "")

words = json.load(open(os.path.join(HERE, "audio", "words.json"))); words = words["words"] if isinstance(words, dict) else words
faces = json.load(open(os.path.join(HERE, "faces.json"))) if os.path.exists(os.path.join(HERE, "faces.json")) else None
caps = [c for c in captions.build(words, faces, FPS, beats.CAPTION_FIX) if c["t0"] < END]
caps[-1]["t1"] = min(caps[-1]["t1"], END)
open(os.path.join(HERE, "captions.ass"), "w").write(captions.ass(caps))

cues = [c for c in json.load(open(os.path.join(HERE, "cues.json"))) if c["t"] < END]
beds = [dict(b, t1=min(b["t1"], END)) for b in json.load(open(os.path.join(HERE, "beds.json"))) if b["t0"] < END]
mix = os.path.join(HERE, f"Complainer_{END:g}s_mix.wav")
sfx.render(cues, beds, END, mix, narration=os.path.join(HERE, "audio", "voiceover.mp3"))

out = os.path.join(HERE, f"Complainer_{END:g}s{TAG}.mp4")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(HERE, "frames", "f_%04d.png"), "-i", mix,
                "-vf", f"scale=1080:1920:flags=lanczos,ass={os.path.join(HERE, 'captions.ass')}:fontsdir={FONTS}",
                "-af", f"loudnorm=I=-14:TP=-1.5:LRA=11,afade=t=out:st={END - 0.3}:d=0.3", "-ar", "48000", "-t", str(END),
                "-c:v", "libx264", "-crf", "17", "-preset", "slow", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart", out], check=True)
print("wrote", out, "-", len(caps), "captions,", len(cues), "sound cues,", len(beds), "ambience beds")
