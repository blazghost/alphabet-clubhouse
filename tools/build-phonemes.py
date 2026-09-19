"""usage: python build-phonemes.py OUTDIR [index.html]

Needs onnxruntime, numpy, librosa, praat-parselmouth, ffmpeg and a Piper
voice at ~/.local/share/piper/voices/en_US-lessac-high.onnx.

Build the 26 phonics clips for index.html from IPA, pick the best of several takes by
measurement, and write OUTDIR/<letter>.wav (and .mp3). With a page path,
the clips are embedded into it as the PHONEMES block.

Fricatives are not rendered alone (the voice model turns a bare "s" into
"s-uh" or a vowel); they are rendered after a vowel ("us.") and the
consonant is cut out at the point the vowel's low-frequency energy drops."""
import json, sys, os, wave, numpy as np, onnxruntime as ort, librosa, parselmouth

VOICE = "en_US-lessac-high"
base = os.path.expanduser("~/.local/share/piper/voices/") + f"{VOICE}.onnx"
cfg = json.load(open(base + ".json")); idmap = cfg["phoneme_id_map"]; SR = cfg["audio"]["sample_rate"]
sess = ort.InferenceSession(base, providers=["CPUExecutionProvider"])
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
PAGE = sys.argv[2] if len(sys.argv) > 2 else None
TAKES = 6

# Targets measured from clean lessac renderings, consistent with Hillenbrand
# (1995) adult-female means for General American.
V = {"æ": (940, 1800), "ɛ": (700, 1850), "ɪ": (430, 2250), "ɑ": (880, 1250), "ʌ": (760, 1200)}

# letter: (ipa, length_scale, kind)
#   vowel  - stressed short vowel, scored on F1/F2
#   hold   - sonorant held on its own
#   r      - scored on low F3 (r-colouring)
#   cut    - vowel + consonant, keep only the consonant
#   mid    - voiced fricative between vowels (it devoices at the end of a
#            phrase), keep the energy dip between the two vowels
#   stop   - consonant + the shortest schwa
PH = {
 "a": ("ˈæ", 1.7, "vowel"), "e": ("ˈɛ", 1.7, "vowel"), "i": ("ˈɪ", 1.9, "vowel"),
 "o": ("ˈɑ", 1.6, "vowel"), "u": ("ˈʌ", 1.6, "vowel"),
 "m": ("m.", 2.6, "hold"), "n": ("n.", 2.8, "hold"), "l": ("l.", 2.8, "hold"),
 "r": ("ɹɚ.", 1.6, "r"),
 "s": ("ʌs.", 2.6, "cut"), "f": ("ʌf.", 4.0, "cut"), "v": ("ʌvʌ", 6.0, "mid"),
 "z": ("ʌzʌ", 3.2, "mid"), "x": ("ɛks.", 1.6, "cut"),
 "b": ("bə", 1.0, "stop"), "c": ("kə", 1.0, "stop"), "d": ("də", 1.0, "stop"),
 "g": ("ɡə", 1.0, "stop"), "h": ("hə", 1.0, "stop"), "j": ("dʒə", 1.0, "stop"),
 "k": ("kə", 1.0, "stop"), "p": ("pə", 1.0, "stop"), "q": ("kwə", 1.0, "stop"),
 "t": ("tə", 1.0, "stop"), "w": ("wə", 1.0, "stop"), "y": ("jə", 1.0, "stop"),
}

def synth(ipa, ls, ns=0.4):
    ids = idmap["^"] + idmap["_"]
    for ch in ipa: ids += idmap[ch] + idmap["_"]
    x = np.array([ids + idmap["$"]], dtype=np.int64)
    return sess.run(None, {"input": x, "input_lengths": np.array([x.shape[1]], dtype=np.int64),
                           "scales": np.array([ns, ls, 0.6], dtype=np.float32)})[0].squeeze().astype(np.float64)

def formants(y):
    snd = parselmouth.Sound(y, sampling_frequency=SR)
    fm = snd.to_formant_burg(max_number_of_formants=5, maximum_formant=5500); pitch = snd.to_pitch()
    ts = [t for t in np.arange(0, snd.duration, .005) if pitch.get_value_at_time(t) == pitch.get_value_at_time(t)]
    if len(ts) < 4: return None
    mid = ts[len(ts)//4: 3*len(ts)//4]
    return [float(np.nanmedian([fm.get_value_at_time(k, t) for t in mid])) for k in (1, 2, 3)]

def trim(y, db=40):
    a, (s, e) = librosa.effects.trim(y, top_db=db, frame_length=256, hop_length=64)[0], \
                librosa.effects.trim(y, top_db=db, frame_length=256, hop_length=64)[1]
    return y[s:e]

def cut_consonant(y):
    """Everything after the vowel: first frame, past the vowel's peak, where
    either the <1 kHz share of energy falls below half or loudness falls
    below a third of the vowel's."""
    hop = 64
    S = np.abs(librosa.stft(y, n_fft=512, hop_length=hop)) ** 2
    f = librosa.fft_frequencies(sr=SR, n_fft=512)
    tot = S.sum(0) + 1e-12; low = S[f < 1000].sum(0) / tot
    rms = np.sqrt(tot); pk = int(np.argmax(rms))
    b = next((i for i in range(pk, len(rms)) if low[i] < 0.5 or rms[i] < rms[pk] / 3), len(rms) - 1)
    return trim(y[b * hop + 3 * hop:], 36)   # skip ~9 ms of formant transition

def cut_mid(y):
    hop = 64
    rms = librosa.feature.rms(y=y, frame_length=256, hop_length=hop)[0]
    h = len(rms) // 2
    p1 = int(np.argmax(rms[:h])); p2 = h + int(np.argmax(rms[h:]))
    lo = p1 + int(np.argmin(rms[p1:p2])); thr = rms[lo] + 0.5 * (min(rms[p1], rms[p2]) - rms[lo])
    a = b = lo
    while a > p1 and rms[a] < thr: a -= 1
    while b < p2 and rms[b] < thr: b += 1
    return y[(a + 2) * hop:(b - 2) * hop]

def fricative_score(y):
    """Length of the noisy stretch (s, f, z, x) or the whole cut (v)."""
    return len(y) / SR

def fade(y, fin=0.008, fout=0.04):
    y = y.copy(); a, b = int(fin * SR), int(fout * SR)
    y[:a] *= np.linspace(0, 1, a); y[-b:] *= np.linspace(1, 0, b) ** 2
    return y

report = {}
for L, (ipa, ls, kind) in PH.items():
    best, bscore, info = None, -1e9, ""
    for k in range(TAKES):
        y = synth(ipa, ls)
        if kind in ("cut", "mid"):
            y = cut_consonant(y) if kind == "cut" else cut_mid(y); sc = fricative_score(y); inf = f"{len(y)/SR:.2f}s"
        else:
            y = trim(y); F = formants(y)
            if kind == "vowel":
                t = V[ipa[-1]]
                sc = -np.hypot((F[0]-t[0])/t[0], (F[1]-t[1])/t[1]) if F else -9
            elif kind == "r":
                sc = -F[2] if F else -9e9
            else:
                sc = -abs(len(y)/SR - 0.45) if kind == "hold" else -abs(len(y)/SR - 0.25)
            inf = (f"F1 {F[0]:.0f} F2 {F[1]:.0f} F3 {F[2]:.0f}" if F else "unvoiced") + f"  {len(y)/SR:.2f}s"
        if sc > bscore: best, bscore, info = y, sc, inf
    # a held continuant should last long enough to hear and copy
    if kind in ("cut", "mid", "hold") and L != "x" and len(best) / SR < 0.55:
        best = librosa.effects.time_stretch(best, rate=(len(best) / SR) / 0.6)
        info += f" -> stretched {len(best)/SR:.2f}s"
    best = fade(best / np.abs(best).max() * 0.89)
    with wave.open(f"{OUT}/{L}.wav", "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((best * 32767).astype(np.int16).tobytes())
    report[L] = f"/{ipa.strip('.ˈ')}/ {kind:5s} {info}"
    print(L, report[L], flush=True)

def level_gain(path, rms_db=-16.0, peak_db=-1.0):
    """Even loudness across clips: loudnorm gates out most of a sub-second
    clip, so match RMS directly, never letting a peak pass peak_db."""
    import wave as _w, numpy as _np
    with _w.open(path) as w: x = _np.frombuffer(w.readframes(w.getnframes()), _np.int16) / 32768
    r = 20 * _np.log10(_np.sqrt(_np.mean(x ** 2))); pk = 20 * _np.log10(_np.abs(x).max())
    return round(min(rms_db - r, peak_db - pk), 2)

# Encode and write the PHONEMES block into the page.
if PAGE:
    import subprocess, base64, re
    data = {}
    for L in "abcdefghijklmnopqrstuvwxyz":
        out = f"{OUT}/{L}.mp3"; IN = f"{OUT}/{L}.wav"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", f"{OUT}/{L}.wav",
                        "-af", f"volume={level_gain(IN)}dB", "-ac", "1", "-ar", "22050",
                        "-c:a", "libmp3lame", "-b:a", "48k", out], check=True)
        data[L] = base64.b64encode(open(out, "rb").read()).decode()
    lines = ",\n".join(f'  {L}:"{b}"' for L, b in data.items())
    block = ("<script>\n/* Letter sounds, one clip per letter, rendered from IPA with the Piper\n"
             "   en_US-lessac voice by tools/build-phonemes.py. See DATA in the main script. */\n"
             "const PHONEMES = {\n" + lines + "\n};\n</script>\n")
    s = open(PAGE).read()
    s = re.sub(r"<script>\n/\* Letter sounds, one clip.*?</script>\n", "", s, flags=re.S)
    anchor = "<script>\n/* =====================================================================\n   DATA"
    assert anchor in s
    s = s.replace(anchor, block + anchor, 1)
    open(PAGE, "w").write(s)
    print({L: len(b) for L, b in data.items()}, sum(map(len, data.values())), "bytes of base64")
