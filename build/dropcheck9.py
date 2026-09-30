"""Ролик 9 — строгая проверка «лагов»: провал ВНУТРИ слова (words.json, без 40мс по краям), которого нет в исходнике.
Кадр 10мс считается провалом, если обработка упала > 12 dB ниже медианы своих соседей ±60мс, а исходник в этом
кадре упал меньше чем на 6 dB. Ложных срабатываний glitch_check на начале слов после пауз тут нет по построению."""
import json, sys, numpy as np
import voicefx_v6 as V


def drops(x, raw, words, hop=0.01):
    n = int(hop * V.SR); k = min(len(x), len(raw)) // n
    lv = lambda v: 20 * np.log10(np.sqrt((v[: k * n, 0].reshape(k, n) ** 2).mean(1)) + 1e-12)
    lx, lr = lv(x), lv(raw)
    inw = np.zeros(k, bool)
    for w in words:
        a, b = int((w["s"] + 0.04) / hop), int((w["e"] - 0.04) / hop)
        if b > a: inw[a:b] = True
    out = []
    for i in np.flatnonzero(inw):
        a, b = max(0, i - 6), min(k, i + 7)
        if lx[i] < np.median(lx[a:b]) - 12 and lr[i] > np.median(lr[a:b]) - 6:
            out.append(round(i * hop, 2))
    return [t for j, t in enumerate(out) if j == 0 or t - out[j - 1] > 0.05]


if __name__ == "__main__":
    words = json.load(open("../videos/9/words.json", encoding="utf-8"))["words"]
    raw = V.read_wav("assets/9/_vfx6_raw.wav")
    for tag, p in [("-a 12 (сдан)", "assets/9/_vfx6_df/_vfx6_raw.wav"), ("-a 18", "assets/9/_dfa18/_vfx6_raw.wav"),
                   ("-a 24", "assets/9/_dfa24/_vfx6_raw.wav"), ("-a 100", "assets/9/_dfa100/_vfx6_raw.wav")]:
        df = np.nan_to_num(V.read_wav(p))[: len(raw)]
        fx, nfix = V.repair_holes(df, raw)
        d = drops(fx, raw, words)
        print(f"{tag:14} фон {V.floor_db(fx):6.1f} | провалов внутри слов {len(d):2d} {d[:8]} | glitch_check {len(V.glitch_check(fx, raw))}")
