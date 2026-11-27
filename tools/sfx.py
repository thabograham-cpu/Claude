"""Procedural sound effects + a narration-safe mixer (numpy only, deterministic, no downloads).

Kinds: step (marble | carpet | concrete), wheels (luggage trolley), ding (elevator), doors (elevator slide +
thunk), door (swing + latch), snap (fingers), tap / ping / shutter (phone), cardboard, thud (bag), breath
(exhausted), whoosh (fast camera move), and ambience beds: lobby, street, stairs, corridor, elevator, room.
Levels follow the reference (Do Your Job.mp4): narration ~ -16 dBFS RMS; bed ~ 18 dB under it; effects
peak at or below the narration and are ducked ~6 dB while words are spoken (the reference saves its big
effects for the pauses).

    cues = [dict(t=15.16, kind="snap"), dict(t=17.4, kind="ding"), dict(t=19.4, kind="steps", n=6, every=0.62, surface="concrete")]
    beds = [dict(t0=0, t1=2.0, kind="street"), dict(t0=2.0, t1=18.2, kind="lobby")]
    sfx.render(cues, beds, 20.0, "mix.wav", narration="voice.mp3")
Self-test: python3 tools/sfx.py
"""
import math, subprocess, wave, zlib
import numpy as np

SR = 48000
LEVEL = {"step": -24, "wheels": -21, "ding": -19, "doors": -22, "door": -22, "snap": -15, "tap": -24, "ping": -22, "shutter": -22,
         "cardboard": -22, "thud": -18, "breath": -25, "whoosh": -24}       # peak dBFS before ducking
BED_RMS = -32                                                                  # ambience RMS dBFS (~15 dB under narration)
SPACE = {"lobby": 0.9, "stairs": 1.6, "corridor": 0.35, "street": 0.25, "elevator": 0.3, "room": 0.4}


def rng(*k): return np.random.default_rng(zlib.crc32("|".join(map(str, k)).encode()))


def band(n, lo, hi, seed):
    """White noise band-limited to lo..hi Hz (FFT mask, soft edges)."""
    x = rng("band", seed, n, lo, hi).standard_normal(n); X = np.fft.rfft(x); f = np.fft.rfftfreq(n, 1 / SR)
    m = np.clip((f - lo * 0.8) / (lo * 0.4 + 1e-9), 0, 1) * np.clip((hi * 1.2 - f) / (hi * 0.4), 0, 1)
    y = np.fft.irfft(X * m, n); return y / (np.abs(y).max() + 1e-9)


def env(n, attack, decay):
    t = np.arange(n) / SR; a = np.clip(t / max(attack, 1e-4), 0, 1); return a * np.exp(-np.maximum(0, t - attack) / max(decay, 1e-4))


def tone(n, f, decay, partials=((1, 1.0),)):
    t = np.arange(n) / SR; return sum(a * np.sin(2 * math.pi * f * r * t) * np.exp(-t / (decay / r ** 0.5)) for r, a in partials)


def norm(x, peak_db):
    return x / (np.abs(x).max() + 1e-9) * 10 ** (peak_db / 20)


def sec(s): return int(s * SR)


# ---------------------------------------------------------------- effects (each returns a mono array, peak 1)
def step(surface="marble", seed=0):
    n = sec(0.25)
    if surface == "carpet": x = band(n, 60, 700, ("c", seed)) * env(n, 0.004, 0.035)
    elif surface == "concrete": x = band(n, 90, 3500, ("k", seed)) * env(n, 0.002, 0.03) + 0.6 * band(n, 50, 220, ("kb", seed)) * env(n, 0.003, 0.05)
    else: x = band(n, 1500, 7000, ("m", seed)) * env(n, 0.001, 0.012) + 0.7 * band(n, 70, 400, ("mb", seed)) * env(n, 0.003, 0.04)
    return x / np.abs(x).max()


def wheels(dur, seed=0, speed=0.9):
    n = sec(dur); t = np.arange(n) / SR
    am = 0.75 + 0.25 * np.sin(2 * math.pi * 3.1 * t + rng("w", seed).uniform(0, 6))
    x = band(n, 50, 320, ("wr", seed)) * am + 0.25 * band(n, 800, 3000, ("wh", seed)) * am
    for k, tt in enumerate(np.arange(0.2, dur - 0.1, 0.8 / max(0.2, speed))):   # tile seams: tick-tick
        i = sec(tt); m = min(n - i, sec(0.06)); x[i:i + m] += 1.5 * band(m, 700, 4000, ("seam", seed, k)) * env(m, 0.001, 0.01)
    x *= np.clip(t / 0.15, 0, 1) * np.clip((dur - t) / 0.25, 0, 1)
    return x / np.abs(x).max()


def ding(seed=0):
    n = sec(1.6); return norm(tone(n, 1046.5, 0.9, ((1, 1.0), (2.76, 0.35), (5.4, 0.12))) + 0.6 * tone(n, 1318.5, 0.7) * (np.arange(n) > sec(0.18)), 0)


def doors(dur=1.2, seed=0):
    n = sec(dur + 0.3); t = np.arange(n) / SR
    slide = band(n, 250, 1800, ("ds", seed)) * np.sin(np.clip(t / dur, 0, 1) * math.pi) ** 2 * (t < dur)
    hum = 0.3 * np.sin(2 * math.pi * 110 * t) * (t < dur)
    i = sec(dur); m = n - i; thunk = np.zeros(n); thunk[i:] = band(m, 50, 260, ("dt", seed)) * env(m, 0.002, 0.06) * 1.8
    return norm(slide + hum + thunk, 0)


def door(seed=0):
    n = sec(1.0); t = np.arange(n) / SR
    creak = np.sin(2 * math.pi * (300 + 180 * t) * t) * 0.25 * np.exp(-t / 0.3)
    latch = np.zeros(n); i = sec(0.75); latch[i:] = band(n - i, 600, 5000, ("dl", seed)) * env(n - i, 0.001, 0.02)
    return norm(creak + band(n, 100, 600, ("db", seed)) * 0.2 * np.exp(-t / 0.4) + latch, 0)


def snap(seed=0):
    n = sec(0.3); return norm(band(n, 1500, 9000, ("sn", seed)) * env(n, 0.0008, 0.018) + 0.3 * tone(n, 2100, 0.03), 0)


def tap(seed=0):
    n = sec(0.08); return norm(band(n, 2000, 6000, ("tp", seed)) * env(n, 0.0005, 0.006), 0)


def ping(seed=0):
    n = sec(0.5); return norm(tone(n, 1760, 0.12) + tone(n, 2349, 0.18) * (np.arange(n) > sec(0.09)), 0)


def shutter(seed=0):
    x = np.zeros(sec(0.2)); a = tap(("s1", seed)); b = tap(("s2", seed)); x[:len(a)] += a; x[sec(0.07):sec(0.07) + len(b)] += 0.8 * b
    return norm(x, 0)


def cardboard(seed=0):
    n = sec(0.5); x = np.zeros(n)
    for k in range(6):
        i = sec(rng("cb", seed).uniform(0, 0.35)); m = min(n - i, sec(0.05))
        x[i:i + m] += band(m, 300, 3500, ("cb", seed, k)) * env(m, 0.002, 0.015)
    return norm(x, 0)


def thud(seed=0):
    n = sec(0.4); return norm(band(n, 40, 240, ("th", seed)) * env(n, 0.003, 0.07) + 0.3 * band(n, 400, 1500, ("tm", seed)) * env(n, 0.002, 0.02), 0)


def breath(seed=0):
    n = sec(1.1); t = np.arange(n) / SR
    e = np.sin(np.clip(t / 0.45, 0, 1) * math.pi) * (t < 0.45) * 0.7 + np.sin(np.clip((t - 0.5) / 0.55, 0, 1) * math.pi) * (t > 0.5)
    return norm(band(n, 300, 2600, ("br", seed)) * e, 0)


def whoosh(seed=0):
    n = sec(0.45); t = np.arange(n) / SR; return norm(band(n, 300, 5000, ("wo", seed)) * np.sin(np.pi * t / 0.45) ** 3, 0)


def ambience(kind, dur, seed=0):
    """Room tone beds: always there, never noticed. RMS-normalised by the mixer."""
    n = sec(dur); t = np.arange(n) / SR
    if kind == "street":
        x = band(n, 40, 500, ("st", seed)) + 0.3 * band(n, 500, 3000, ("sth", seed))
        for k in range(int(dur / 4) + 1):                                     # a car passes now and then
            c = rng("car", seed, k).uniform(0, dur); w = 2.2
            x += 1.6 * band(n, 80, 1200, ("car", seed, k)) * np.exp(-((t - c) / (w / 2)) ** 2)
    elif kind == "lobby":
        mur = band(n, 250, 1100, ("lm", seed)) * (0.6 + 0.4 * np.abs(np.sin(2 * math.pi * 0.7 * t + 1)))   # distant guests
        x = 0.7 * band(n, 40, 900, ("lb", seed)) + 0.5 * mur + 0.08 * np.sin(2 * math.pi * 60 * t)
    elif kind == "stairs":
        x = band(n, 40, 400, ("sw", seed)) + 0.15 * np.sin(2 * math.pi * 120 * t)
    elif kind == "elevator":
        x = 0.6 * band(n, 40, 300, ("el", seed)) + 0.3 * np.sin(2 * math.pi * 98 * t)
    else:                                                                     # corridor / room: HVAC hush
        x = band(n, 60, 1500, ("rm", kind, seed)) * 0.6
    return x / (np.sqrt(np.mean(x ** 2)) + 1e-9)


def reverb(x, rt, seed=0):
    """Exponential-noise impulse response (rt = time to -60 dB), FFT convolution; 30% wet."""
    if rt <= 0: return x
    m = sec(rt); ir = rng("ir", rt, seed).standard_normal(m) * np.exp(-6.9 * np.arange(m) / m); ir[0] = 0
    n = len(x) + m; y = np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(ir, n), n)[:len(x) + m]
    y = y / (np.abs(y).max() + 1e-9) * np.abs(x).max()
    out = np.zeros(len(x) + m); out[:len(x)] += x; out += 0.3 * y; return out


MAKE = dict(wheels=wheels, ding=ding, doors=doors, door=door, snap=snap, tap=tap, ping=ping, shutter=shutter,
            cardboard=cardboard, thud=thud, breath=breath, whoosh=whoosh)


def cue_audio(c, k=0):
    kind = c["kind"]
    if kind == "steps":                                                       # n footsteps every `every` s
        surf = c.get("surface", "marble"); ev = c.get("every", 0.62); out = np.zeros(sec(ev * c["n"] + 0.3))
        for j in range(c["n"]):
            s = step(surf, (k, j)) * (0.8 + 0.2 * (j % 2)); i = sec(j * ev); out[i:i + len(s)] += s
        return norm(out, LEVEL["step"] + c.get("gain", 0))
    args = {key: c[key] for key in ("dur", "speed") if key in c}
    x = MAKE[kind](seed=(k, c["t"]), **args) if kind in MAKE else step(kind, k)
    return norm(x, LEVEL.get(kind, -24) + c.get("gain", 0))


def load(path, dur):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float64) / 32768; out = np.zeros(sec(dur)); out[:min(len(x), len(out))] = x[:len(out)]; return out


def speech_mask(v, attack=0.01, release=0.15, below=18.0):
    """0..1 'words are being spoken' envelope from the narration (for ducking). Threshold = 18 dB under the
    narration's loud frames (95th percentile), so breaths and the recording's noise floor don't count."""
    hop = sec(0.01); fr = np.sqrt(np.add.reduceat(v ** 2, np.arange(0, len(v), hop)) / hop)
    thr = max(10 ** (-50 / 20), np.percentile(fr, 95) * 10 ** (-below / 20)) if fr.any() else 1.0
    on = (fr > thr).astype(float); g = np.zeros_like(on); a, r = 1 - math.exp(-0.01 / attack), 1 - math.exp(-0.01 / release)
    for i in range(len(on)): g[i] = g[i - 1] + (on[i] - g[i - 1]) * (a if on[i] > g[i - 1] else r) if i else on[i]
    return np.repeat(g, hop)[:len(v)]


def render(cues, beds, dur, out, narration=None, duck_db=6.0, bed_duck_db=4.0):
    """Mix narration + ambience beds (cross-faded, ducked a little) + effects (reverb per space, ducked under
    words). Writes a 48 kHz mono WAV and returns the arrays (voice, beds, fx) for checks."""
    n = sec(dur); voice = load(narration, dur) if narration else np.zeros(n)
    mask = speech_mask(voice) if narration else np.zeros(n)
    bed = np.zeros(n)
    for b in beds:
        i0, i1 = sec(b["t0"]), min(n, sec(b["t1"])); m = i1 - i0
        if m <= 0: continue
        a = ambience(b["kind"], (m + sec(0.6)) / SR, b.get("seed", 0)) * 10 ** ((BED_RMS + b.get("gain", 0)) / 20)
        f = np.ones(m + sec(0.6)); fl = sec(0.3); f[:fl] = np.linspace(0, 1, fl); f[-fl:] = np.linspace(1, 0, fl)
        s0 = max(0, i0 - sec(0.3)); seg = (a * f)[: n - s0]; bed[s0:s0 + len(seg)] += seg
    fx = np.zeros(n)
    for k, c in enumerate(sorted(cues, key=lambda c: c["t"])):
        x = reverb(cue_audio(c, k), SPACE.get(c.get("space", ""), 0.0), k); i = sec(c["t"])
        if i >= n: continue
        m = min(len(x), n - i); fx[i:i + m] += x[:m]
    fx *= 10 ** (-duck_db * mask / 20); bed *= 10 ** (-bed_duck_db * mask / 20)
    mix = voice + bed + fx; peak = np.abs(mix).max()
    if peak > 0.98: mix *= 0.98 / peak
    with wave.open(out, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype(np.int16).tobytes())
    return voice, bed, fx


def _selftest():
    import os, tempfile
    for k in list(MAKE) + ["marble", "carpet", "concrete"]:
        x = MAKE[k]() if k in MAKE and k != "wheels" else (wheels(1.0) if k == "wheels" else step(k))
        assert np.isfinite(x).all() and 0.5 < np.abs(x).max() <= 1.0 + 1e-9, k
    assert np.allclose(snap(3), snap(3)) and not np.allclose(step("marble", 1), step("marble", 2)), "deterministic per seed"
    for kind in ("lobby", "street", "stairs", "corridor"): assert abs(np.sqrt(np.mean(ambience(kind, 2.0) ** 2)) - 1) < 1e-6
    v = np.zeros(sec(3)); v[sec(1):sec(2)] = 0.2 * np.sin(np.arange(sec(1)) * 0.05)
    m = speech_mask(v); assert m[sec(1.5)] > 0.9 and m[sec(0.5)] < 0.01 and m[sec(2.8)] < 0.2
    p = os.path.join(tempfile.mkdtemp(), "t.wav")
    _, bed, fx = render([dict(t=0.5, kind="snap", space="lobby"), dict(t=1.0, kind="steps", n=3, surface="concrete")],
                        [dict(t0=0, t1=3, kind="lobby")], 3.0, p)
    assert abs(20 * np.log10(np.abs(fx).max()) - LEVEL["snap"]) < 1.5
    assert abs(20 * np.log10(np.sqrt(np.mean(bed[sec(0.5):sec(2.5)] ** 2))) - BED_RMS) < 2.0
    with wave.open(p) as w: assert w.getframerate() == SR and w.getnframes() == sec(3)
    print("sfx.py self-test OK")


if __name__ == "__main__":
    _selftest()
