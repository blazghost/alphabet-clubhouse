"""usage: python check-phonemes.py [index.html]   (needs ffmpeg, numpy, praat-parselmouth)

Decode every PHONEMES clip in the page and check it against Kilpatrick (2021),
"Pronouncing phonemes in isolation": whispered sounds carry no voicing, stops
carry almost none (no "puh"), held sounds last long enough to copy, r is
r-coloured. Exits 1 if any letter fails."""
import sys, re, base64, subprocess, tempfile, os, numpy as np, parselmouth

RULE = {**{c: ("whispered", 0.02) for c in "ptkchsfx"},     # max voiced seconds
        **{c: ("clipped", 0.11) for c in "bdgjwyq"},
        **{c: ("held", None) for c in "mnlrvz"},
        **{c: ("vowel", None) for c in "aeiou"}, "A": ("name", None)}

page = open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "index.html")).read()
clips = dict(re.findall(r'^  ([a-zA-Z]):"([A-Za-z0-9+/=]+)"', page, re.M))
assert set(clips) == set(RULE), sorted(set(RULE) ^ set(clips))
bad = 0
with tempfile.TemporaryDirectory() as d:
    for L in sorted(clips):
        mp3, wav = f"{d}/{L}.mp3", f"{d}/{L}.wav"
        open(mp3, "wb").write(base64.b64decode(clips[L]))
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", mp3, "-ac", "1", "-ar", "22050", wav], check=True)
        snd = parselmouth.Sound(wav)
        p = snd.to_pitch(time_step=0.005, pitch_floor=120, pitch_ceiling=500)
        f0 = p.selected_array["frequency"]; vt = (f0 > 0).sum() * 0.005
        kind, lim = RULE[L]
        ok = vt <= lim if lim is not None else (snd.duration >= 0.45 if kind == "held" else vt > 0.2)
        extra = ""
        if L == "r":
            fm = snd.to_formant_burg(max_number_of_formants=5, maximum_formant=5500)
            f3 = np.nanmedian([fm.get_value_at_time(3, p.get_time_from_frame_number(i + 1)) for i in np.nonzero(f0 > 0)[0]])
            ok = ok and f3 < 2100; extra = f"  F3 {f3:.0f} Hz"
        bad += not ok
        print(f"{L} {kind:9s} {snd.duration:.2f}s long, {vt:.2f}s voiced{extra}  {'ok' if ok else 'FAIL'}")
print("all letter sounds pass" if not bad else f"{bad} letter sound(s) fail")
sys.exit(1 if bad else 0)
