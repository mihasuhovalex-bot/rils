"""Ролик 18 — образцы голоса для офиса после слов автора 2026-09-30: «ко всем, где офис с синим задним фоном, — там
нужен голос обработанный, но не робота» (VoiceFixer / voicefx_v7 — «робот», убрать).

Все варианты — DeepFilterNet (тембр не пересобирается) + починка его дыр, БЕЗ VoiceFixer, без гейтов по уровню:
  1_myagko        — v6 как есть: DF -a 12
  2_sredne        — DF -a 18 + fill_dips (провал внутри слова подпирается исходником)
  3_sredne_pauzy  — как 2 + паузы между словами (> 0.25с по words.json) плавно тише на 8 dB (косинус 90 мс; это не
                    гейт: внутри слов ничего не трогается, управляет расшифровка, а не уровень). DF -a 24 отброшен:
                    12 скачков glitch_check — «лаги».
Фрагмент T0–T1: сначала голос отдельно, через 0.4с — он же с музыкой (song3 с 0:50, −22 dB), −14 LUFS.
Полные голоса сохраняются в assets/18/smp/_voice_<tag>.wav — выбранный пойдёт в ролик без пересчёта.
Результат: videos/18/audio-samples/*.mp3 и таблица (фон, провалы внутри слов, скачки)."""
import json, os, subprocess
import numpy as np
import voicefx_v6 as V
from dropcheck9 import drops

BUILD = os.path.dirname(os.path.abspath(__file__))
TMP = f"{BUILD}/assets/18/smp"
OUT = f"{BUILD}/../videos/18/audio-samples"
SRC = f"{BUILD}/../videos/18/source.mov"
T0, T1 = 16.2, 28.0
SR = V.SR
WORDS = json.load(open(f"{BUILD}/../videos/18/words.json", encoding="utf-8"))["words"]


def ff(*a, cwd=None):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *a], check=True, cwd=cwd)


def fill_dips(x, raw, hop=0.01):
    n = int(hop * SR); k = min(len(x), len(raw)) // n
    lv = lambda v: 20 * np.log10(np.sqrt((v[: k * n, 0].reshape(k, n) ** 2).mean(1)) + 1e-12)
    g = lv(x) - lv(raw)
    inw = np.zeros(k, bool)
    for w in WORDS:
        a, b = int((w["s"] + 0.02) / hop), int((w["e"] - 0.02) / hop)
        if b > a: inw[a:b] = True
    target = np.array([np.median(g[max(0, i - 6):i + 7]) for i in range(k)])
    need = np.where(inw & (g < target - 6), 10 ** (target / 20) - 10 ** (g / 20), 0.0)
    need = np.clip(np.convolve(need, np.ones(3) / 3, mode="same"), 0, 1)
    out = x.copy()
    out[: k * n] = x[: k * n] + raw[: k * n] * np.repeat(need, n)[:, None]
    return out


def duck_pauses(x, depth_db=8.0, ramp=0.09, min_gap=0.25, pad=0.06):
    """Между словами (пауза > min_gap) — плавно тише на depth_db. Внутри слов усиление = 1."""
    g = np.ones(len(x), np.float32)
    lo = 10 ** (-depth_db / 20)
    r = int(ramp * SR)
    edges = [(0.0, WORDS[0]["s"])] + [(a["e"], b["s"]) for a, b in zip(WORDS, WORDS[1:])] + [(WORDS[-1]["e"], len(x) / SR)]
    for a, b in edges:
        if b - a <= min_gap:
            continue
        i0, i1 = int((a + pad) * SR), int((b - pad) * SR)
        if i1 - i0 < 2 * r:
            continue
        down = lo + (1 - lo) * (0.5 + 0.5 * np.cos(np.linspace(0, np.pi, r)))
        g[i0:i0 + r] = down
        g[i0 + r:i1 - r] = lo
        g[i1 - r:i1] = down[::-1]
    return x * g[:, None]


def voice(tag, atten, dips, duck):
    raw_p = f"{TMP}/raw.wav"
    if not os.path.exists(raw_p):
        ff("-i", SRC, "-vn", "-ac", "1", "-ar", str(SR), "-c:a", "pcm_s16le", raw_p)
    raw = V.read_wav(raw_p)
    dfd = f"{TMP}/df{atten}"
    if not os.path.exists(f"{dfd}/raw.wav"):
        os.makedirs(dfd, exist_ok=True)
        subprocess.run([V.DF, "-D", "-a", str(atten), "-o", dfd, raw_p], check=True, capture_output=True)
    df = np.nan_to_num(V.read_wav(f"{dfd}/raw.wav"))[: len(raw)]
    assert V.lag(raw, df) == 0
    fx, nfix = V.repair_holes(df, raw)
    if dips:
        fx = fill_dips(fx, raw)
    gl, d = V.glitch_check(fx, raw), drops(fx, raw, WORDS)
    if duck:
        fx = duck_pauses(fx)
    V.write_wav(f"{TMP}/_{tag}_fx.wav", fx)
    pre = f"{TMP}/_{tag}_pre.wav"
    ff("-i", f"{TMP}/_{tag}_fx.wav", "-af", f"highpass=f=80:p=2,{V.EQ}", "-c:a", "pcm_s16le", pre, cwd=BUILD)
    g = -22 - 20 * np.log10(V.speech_rms(V.read_wav(pre)))
    out = f"{TMP}/_voice_{tag}.wav"
    ff("-i", pre, "-af", f"volume={g:.2f}dB,{V.COMP},{V.LIM}", "-ac", "2", "-c:a", "pcm_s16le", out)
    v = np.nan_to_num(V.read_wav(out))[: len(raw)]
    return v, len(gl), len(d), V.floor_db(v), V.floor_db(raw)


def main():
    os.makedirs(TMP, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    mw = f"{TMP}/_music.wav"
    ff("-ss", f"{50 + T0}", "-t", f"{T1 - T0 + 1}", "-i", f"{BUILD}/../audios/song3.mp3", "-af", V.MUSIC_AF,
       "-ac", "2", "-ar", str(SR), "-c:a", "pcm_s16le", mw)
    mus = V.read_wav(mw)
    gap = np.zeros((int(0.4 * SR), 2), np.float32)
    for tag, atten, dips, duck in [("1_myagko", 12, False, False), ("2_sredne", 18, True, False),
                                   ("3_sredne_pauzy", 18, True, True)]:
        v, gl, d, fl, fr = voice(tag, atten, dips, duck)
        seg = v[int(T0 * SR):int(T1 * SR)]
        m = mus[: len(seg)] * V.speech_rms(v) / (np.sqrt((mus[: len(seg)] ** 2).mean()) + 1e-12) * 10 ** (-22 / 20)
        p = f"{TMP}/_{tag}.wav"
        V.write_wav(p, np.concatenate([seg, gap, seg + m]))
        ff("-i", p, "-af", "volume=9dB,alimiter=limit=0.85:level=disabled", "-ar", "48000", "-c:a", "libmp3lame",
           "-b:a", "256k", f"{OUT}/{tag}.mp3")
        print(f"{tag:15} DF -a {atten:2} | фон {fl:6.1f} dB от речи (исходник {fr:.1f}) | скачков {gl} | провалов в словах {d}")


if __name__ == "__main__":
    main()
