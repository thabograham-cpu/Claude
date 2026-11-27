"""Phoneme timings from dialogue audio + its text (forced alignment). Runs OUTSIDE Blender:

    /home/user/blender-shorts/lipsync/bin/python -I tools/phonemes.py line.mp3 "What he says." line.phones.json

Text -> ARPAbet (g2p_en: CMUdict + neural fallback for unknown words) -> espeak IPA tokens of the
facebook/wav2vec2-lv-60-espeak-cv-ft phoneme recogniser -> CTC Viterbi forced alignment (20 ms frames)
against the audio. Silences come from the alignment gaps plus an RMS check. Output JSON:
  {"duration", "words": [{"w", "s", "e"}], "phones": [{"p", "s", "e", "stress", "w"}], "silences": [[s, e]], "rms": [...100 Hz]}
Deterministic (eval mode, no sampling). Times in seconds from the start of the file.
"""
import json, re, subprocess, sys
import numpy as np

MODEL = "facebook/wav2vec2-lv-60-espeak-cv-ft"
SR = 16000
# ARPAbet -> IPA tokens in the model vocabulary (US English, espeak style). AH0 -> schwa, stressed AH -> wedge.
ARPA_IPA = {
    "AA": "ɑː", "AE": "æ", "AH": "ʌ", "AO": "ɔː", "AW": "aʊ", "AY": "aɪ", "B": "b", "CH": "tʃ", "D": "d", "DH": "ð",
    "EH": "ɛ", "ER": "ɚ", "EY": "eɪ", "F": "f", "G": "ɡ", "HH": "h", "IH": "ɪ", "IY": "iː", "JH": "dʒ", "K": "k",
    "L": "l", "M": "m", "N": "n", "NG": "ŋ", "OW": "oʊ", "OY": "ɔɪ", "P": "p", "R": "ɹ", "S": "s", "SH": "ʃ",
    "T": "t", "TH": "θ", "UH": "ʊ", "UW": "uː", "V": "v", "W": "w", "Y": "j", "Z": "z", "ZH": "ʒ",
}


def load_audio(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768


def g2p(text):
    """[(word, [(ARPA, stress)])] for the spoken words of text."""
    from g2p_en import G2p
    conv = G2p(); out = []
    for w in re.findall(r"[A-Za-z0-9']+", text):
        ph = [p for p in conv(w) if re.match(r"^[A-Z]+[0-2]?$", p)]
        out.append((w, [(re.sub(r"\d", "", p), int(p[-1]) if p[-1].isdigit() else -1) for p in ph]))
    return out


def ctc_align(logp, tokens, blank):
    """Viterbi CTC forced alignment. logp: (T, V) log-probs; tokens: target ids. Returns the first and last
    frame of each token (token spans exclude blanks)."""
    T, S = logp.shape[0], 2 * len(tokens) + 1
    ext = [blank if i % 2 == 0 else tokens[i // 2] for i in range(S)]
    NEG = -1e30; dp = np.full((T, S), NEG); bp = np.zeros((T, S), np.int32)
    dp[0, 0] = logp[0, blank]; dp[0, 1] = logp[0, ext[1]]
    for t in range(1, T):
        for s in range(S):
            cands = [(dp[t - 1, s], s)]
            if s >= 1: cands.append((dp[t - 1, s - 1], s - 1))
            if s >= 2 and ext[s] != blank and ext[s] != ext[s - 2]: cands.append((dp[t - 1, s - 2], s - 2))
            v, k = max(cands)
            dp[t, s] = v + logp[t, ext[s]]; bp[t, s] = k
    s = S - 1 if dp[T - 1, S - 1] >= dp[T - 1, S - 2] else S - 2
    path = []
    for t in range(T - 1, -1, -1):
        path.append(s); s = bp[t, s]
    path.reverse()
    spans = [[None, None] for _ in tokens]
    for t, s in enumerate(path):
        if s % 2 == 1:
            k = s // 2
            if spans[k][0] is None: spans[k][0] = t
            spans[k][1] = t
    return spans


def align(audio_path, text):
    import torch
    from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
    torch.manual_seed(0)
    x = load_audio(audio_path); dur = len(x) / SR
    words = g2p(text)
    proc = Wav2Vec2Processor.from_pretrained(MODEL); model = Wav2Vec2ForCTC.from_pretrained(MODEL).eval()
    vocab = proc.tokenizer.get_vocab(); blank = vocab["<pad>"]
    seq, owner = [], []
    for wi, (w, phs) in enumerate(words):
        for p, st in phs:
            ipa = "ə" if (p == "AH" and st == 0) else ARPA_IPA[p]
            seq.append(vocab[ipa]); owner.append((wi, p, st))
    with torch.no_grad():
        inp = proc(x, sampling_rate=SR, return_tensors="pt").input_values
        logp = torch.log_softmax(model(inp).logits[0], -1).numpy().astype(np.float64)
    fr = dur / logp.shape[0]                                     # ~20 ms per frame
    spans = ctc_align(logp, seq, blank)
    # RMS at 100 Hz for silence and intensity
    hop = SR // 100; rms = [float(np.sqrt(np.mean(x[i:i + hop] ** 2) + 1e-12)) for i in range(0, len(x), hop)]
    quiet = 0.08 * float(np.percentile(rms, 95))
    phones = []
    for k, ((a, b), (wi, p, st)) in enumerate(zip(spans, owner)):
        s0 = a * fr
        nxt = spans[k + 1][0] * fr if k + 1 < len(spans) else (b + 1) * fr + 0.08
        e0 = min(nxt, (b + 1) * fr + 0.25)                       # a phone lasts until the next starts (max +0.25 s)
        if k + 1 == len(spans):                                   # the last one ends when the audio goes quiet
            i = int(s0 * 100)
            while i < len(rms) and rms[i] > quiet: i += 1
            e0 = max((b + 1) * fr, min(e0, i / 100))
        phones.append({"p": p, "s": round(s0, 3), "e": round(e0, 3), "stress": st, "w": wi})
    # a gap of 150 ms+ of quiet audio inside a phone = silence: cut the phone short
    sil = []
    for ph in phones:
        i0, i1 = int(ph["s"] * 100), int(ph["e"] * 100)
        run = 0
        for i in range(i0, min(i1, len(rms))):
            run = run + 1 if rms[i] < quiet else 0
            if run == 15:
                cut = (i - 14) / 100; sil.append([round(cut, 2), ph["e"]]); ph["e"] = round(max(ph["s"] + 0.04, cut), 3); break
    for a_, b_ in zip(phones, phones[1:]):
        if b_["s"] - a_["e"] > 0.12: sil.append([a_["e"], b_["s"]])
    if phones and phones[0]["s"] > 0.1: sil.insert(0, [0.0, phones[0]["s"]])
    if phones and dur - phones[-1]["e"] > 0.1: sil.append([phones[-1]["e"], round(dur, 3)])
    merged = []
    for a_, b_ in sorted(sil):                                    # merge overlapping silence spans
        if merged and a_ <= merged[-1][1]: merged[-1][1] = max(merged[-1][1], b_)
        else: merged.append([a_, b_])
    sil = merged
    wout = []
    for wi, (w, _) in enumerate(words):
        ps = [p for p in phones if p["w"] == wi]
        if ps: wout.append({"w": w, "s": ps[0]["s"], "e": ps[-1]["e"]})
    return {"duration": round(dur, 3), "text": text, "words": wout, "phones": phones,
            "silences": sil, "rms": [round(r, 5) for r in rms]}


def _selftest():
    lp = np.log(np.full((12, 4), 0.01)); best = [0, 1, 1, 0, 2, 2, 0, 0, 3, 3, 0, 0]
    for t, k in enumerate(best): lp[t, k] = np.log(0.97)
    assert ctc_align(lp, [1, 2, 3], 0) == [[1, 2], [4, 5], [8, 9]]
    lp2 = np.log(np.full((6, 3), 0.01))
    for t, k in enumerate([1, 1, 0, 1, 1, 0]): lp2[t, k] = np.log(0.98)
    assert ctc_align(lp2, [1, 1], 0) == [[0, 1], [3, 4]]       # repeated token needs a blank between
    print("phonemes.py self-test OK")


if __name__ == "__main__":
    if len(sys.argv) == 1: _selftest(); sys.exit()
    out = align(sys.argv[1], sys.argv[2])
    json.dump(out, open(sys.argv[3], "w"), indent=0)
    print(" ".join(f"{p['p']}{p['s']:.2f}" for p in out["phones"]))
    print("words:", " ".join(f"{w['w']}[{w['s']:.2f}-{w['e']:.2f}]" for w in out["words"]), "| silences:", out["silences"])
