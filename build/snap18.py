"""Блок 1 — уточнение пословных границ ролика 18 по огибающей звука.

Whisper API ставит концы слов грубо (конец часто = начало следующего, или слово длиной 0.02с).
Здесь: огибающая RMS 10мс, порог = пол шума + 12 dB. Начало слова двигается на первый
«звучащий» кадр рядом с оценкой API, конец — на последний звучащий кадр перед следующим
словом. Паузы между словами становятся реальными — по ним ставятся резы и рвутся блоки.
Результат: videos/18/words.json (время уже в обрезанном source.mov: минус HEAD).

Ролик 18: исходник 28.09/vid28.09 (13).MP4 без правок (source.mov = копия source_raw.mp4). Текст сверен с gpt-4o-transcribe (§1).
"""
import os, sys, json, subprocess, wave
import numpy as np

BUILD = os.path.dirname(os.path.abspath(__file__))
VID = f"{BUILD}/../videos/18"
HOP = 0.01
HEAD = 0.0   # срез тишины в начале не нужен
# ручные правки таймингов по огибающей (время исходника): индекс слова -> (начало, конец|None)
TFIX = {}
WFIX_T = {}
# ролик 18: слова, сжатые whisper/snap, — по провалам огибающей (слово, время ≈ после snap, начало, конец)
TFIX_NEAR = [("в", 9.86, 9.86, 9.97), ("ромб", 10.18, 9.98, 10.24),
             ("тысячи", 13.90, 13.90, 14.24), ("тонн", 14.61, 14.27, 14.49), ("а", 14.66, 14.61, 14.80),
             ("в", 22.80, 22.85, 22.95), ("мороз", 23.36, 22.97, 23.26), ("в", 23.38, 23.36, 23.53), ("жару", 23.62, 23.55, 23.77),
             ("Поэтому", 27.80, 28.19, 28.45), ("в", 28.19, 28.47, 28.64), ("конструкторы", 28.68, 28.66, 29.05),
             ("берут", 29.02, 29.07, 29.28), ("тех", 29.28, 29.30, 29.55),
             ("расчёте", 25.82, 25.82, 26.12), ("не", 26.24, 26.19, 26.48),      # провал −51 dB 26.10–26.19 (QA-рез 26.16)
             ("в", 32.98, 33.00, 33.15), ("школе", 33.40, 33.17, 33.48),
             ("напишите", 44.40, 44.40, 44.68), ("в", 44.72, 44.70, 44.80), ("комментариях", 45.26, 44.80, 45.30),
             ("слово", 45.28, 45.32, 45.53), ("пробное", 45.50, 45.55, 45.96)]

# правки распознавания (по слуху/смыслу)
FIX = {"«пробное»": "пробное", "–": "—", "громкой": "кнопкой", "рамиц": "равенства", "теорем": "теорема",
       "ребенок": "ребёнок", "ее": "её", "идет": "идёт"}   # сверка с gpt-4o-transcribe + перерасшифровка вырезок 25.0–28.2, 33.8–38.0


def envelope():
    tmp = f"{BUILD}/assets/_env18.wav"
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", f"{VID}/source.mov",
                    "-vn", "-ac", "1", "-ar", "16000", "-af", "highpass=f=90", "-c:a", "pcm_s16le", tmp],
                   check=True)
    w = wave.open(tmp)
    x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    n = int(16000 * HOP)
    fr = x[: len(x) // n * n].reshape(-1, n)
    db = 20 * np.log10(np.sqrt((fr ** 2).mean(1)) + 1e-9)
    return db, len(x) / 16000


def main():
    d = json.load(open(f"{VID}/whisper_raw.json", encoding="utf-8"))
    words = [dict(w=w["word"], s=w["start"], e=w["end"]) for w in d["words"]]
    db, dur = envelope()
    floor = np.percentile(db, 10)
    thr = floor + 12
    on = db > thr
    log = [f"пол шума {floor:.1f} dB, порог {thr:.1f} dB, длительность {dur:.2f}с"]

    def fi(t):
        return int(np.clip(round(t / HOP), 0, len(on) - 1))

    for i, w in enumerate(words):
        if w["w"] in FIX and FIX[w["w"]]:
            w["w"] = FIX[w["w"]]

    # речевые сегменты: звучащие кадры, склеенные через провалы <0.12с, без щелчков <0.05с
    segs, i = [], 0
    while i < len(on):
        if on[i]:
            j = i
            while j < len(on) and on[j]:
                j += 1
            if segs and (i - segs[-1][1]) * HOP < 0.12:
                segs[-1][1] = j
            else:
                segs.append([i, j])
            i = j
        else:
            i += 1
    segs = [(a * HOP, b * HOP) for a, b in segs if (b - a) * HOP >= 0.05]
    log.append("сегменты речи: " + " ".join(f"{a:.2f}-{b:.2f}" for a, b in segs))

    # слово, открывающее сегмент, получает начало сегмента; закрывающее — его конец
    starts = [a for a, _ in segs]
    ends = [b for _, b in segs]
    orig = [(w["s"], w["e"]) for w in words]
    for k, (a, b) in enumerate(segs):
        # первое слово, чья оценка начала в окне [a-0.25, a+0.30]
        cand = [i for i, (s0, _) in enumerate(orig) if a - 0.25 <= s0 <= a + 0.30]
        if cand:
            words[cand[0]]["s"] = a
        # последнее слово, чья оценка конца в окне [b-0.45, b+0.60] и начало внутри сегмента
        cand = [i for i, (s0, e0) in enumerate(orig) if b - 0.45 <= e0 <= b + 0.60 and s0 < b]
        if cand:
            words[cand[-1]]["e"] = min(b + 0.03, dur)
    changed = 0
    for i, w in enumerate(words):
        if i + 1 < len(words) and w["e"] > words[i + 1]["s"]:
            w["e"] = max(w["s"] + 0.06, words[i + 1]["s"])
        if w["e"] < w["s"] + 0.06:
            w["e"] = w["s"] + 0.06
        s0, e0 = orig[i]
        if abs(w["s"] - s0) > 0.03 or abs(w["e"] - e0) > 0.03:
            changed += 1
            log.append(f"{w['w']:>14}  {s0:6.2f}-{e0:6.2f}  ->  {w['s']:6.2f}-{w['e']:6.2f}")
        w["s"], w["e"] = round(w["s"], 2), round(w["e"], 2)

    for i, (a, b) in TFIX.items():
        words[i]["s"] = a
        if b: words[i]["e"] = b
    for w in words:
        if w["w"] in WFIX_T:
            a, b = WFIX_T[w["w"]]
            w["s"] = a
            if b: w["e"] = b
    for ww, t, a, b in TFIX_NEAR:
        k = min((i for i, w in enumerate(words) if w["w"] == ww), key=lambda i: abs(words[i]["s"] - t))
        assert abs(words[k]["s"] - t) < 0.15, (ww, t, words[k]["s"])
        words[k]["s"], words[k]["e"] = a, b
    for w in words:
        w["s"], w["e"] = round(w["s"] - HEAD, 2), round(w["e"] - HEAD, 2)
    dur -= HEAD
    words = [w for w in words if w["w"] not in ("—",)]
    # урок друга (ролик 12): после snap — строго последовательные тайминги, без нахлёста
    for i in range(1, len(words)):
        words[i]["s"] = round(max(words[i]["s"], words[i - 1]["s"] + 0.02), 2)
    for i in range(len(words) - 1):
        words[i]["e"] = round(max(min(words[i]["e"], words[i + 1]["s"]), words[i]["s"] + 0.02), 2)
    json.dump(dict(duration=round(dur, 3), words=words), open(f"{VID}/words.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    open(f"{BUILD}/snap18.log", "w", encoding="utf-8").write("\n".join(log))
    print(f"words.json: {len(words)} слов, уточнено границ: {changed}")


if __name__ == "__main__":
    main()
