"""Замер готового mp4: LUFS / истинный пик (ebur128) + уровень музыки в паузах речи относительно речи.
python measure_mix.py <mp4> <words.json|words_cap.json>"""
import sys, json, subprocess, re, numpy as np
mp4, wj = sys.argv[1], sys.argv[2]
r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", mp4, "-af", "ebur128=peak=true", "-f", "null", "-"],
                   capture_output=True, text=True, encoding="utf-8", errors="ignore").stderr
I = re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1]; TP = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)[-1]
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", mp4, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                     capture_output=True).stdout
x = np.frombuffer(raw, np.float32)
d = json.load(open(wj, encoding="utf-8")); ws = d["words"] if isinstance(d, dict) else d
S = [(w.get("s", w.get("start")), w.get("e", w.get("end"))) for w in ws]
sp = np.zeros(len(x), bool)
for a, b in S: sp[int(a * 16000):int(b * 16000)] = True
gap = np.zeros(len(x), bool)
for (a0, b0), (a1, b1) in zip(S, S[1:]):
    if a1 - b0 > 0.30: gap[int((b0 + 0.08) * 16000):int((a1 - 0.08) * 16000)] = True
db = lambda v: 20 * np.log10(np.sqrt((v ** 2).mean()) + 1e-12)
print(f"{mp4.split('/')[-1]}: {I} LUFS, пик {TP} dBTP, речь {db(x[sp]):.1f} dB, паузы (музыка) {db(x[gap]):.1f} dB -> {db(x[gap]) - db(x[sp]):.1f} dB от речи")
