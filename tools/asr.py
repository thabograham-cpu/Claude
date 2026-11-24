import json, sys
from faster_whisper import WhisperModel
m = WhisperModel("small.en", device="cpu", compute_type="int8")
import subprocess, numpy as np
pcm = np.frombuffer(subprocess.run(["ffmpeg","-v","error","-i",sys.argv[1],"-ac","1","-ar","16000","-f","s16le","-"],capture_output=True,check=True).stdout, np.int16).astype(np.float32)/32768
segs, info = m.transcribe(pcm, word_timestamps=True, vad_filter=False)
words, text = [], []
for s in segs:
    text.append(f"[{s.start:6.2f}-{s.end:6.2f}] {s.text.strip()}")
    for w in s.words: words.append({"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3)})
json.dump(words, open(sys.argv[2], "w"), indent=0)
print("\n".join(text))
