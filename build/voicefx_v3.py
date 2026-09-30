"""Голос — стандарт с 2026-09-25 (ПРАВИЛА-МОНТАЖА.md §6): нейрошумодав DeepFilterNet + починка его глюков.

Принят автором на ролике 3 (a2): «кайф… были некоторые ошибки в звуке, но норм». Выбран после 5 раундов образцов
(videos/3/audio-samples/). Вывод раундов: RNNoise (arnndn) и гейты/экспандеры «лагают» — звук неестественный,
рваный; исходник не лагает. Самостоятельная копия цепочки build/voice3_neuro.py (ролик 3) — общий модуль,
в параллельной работе только читать; правки — новой версией (voicefx_v4.py).

Цепочка:
1. deep-filter.exe -D -a 100 (D:\\tools\\deepfilter, DeepFilterNet 0.5.6, синхрон 0 мс) на исходнике 48 кГц моно;
2. repair_holes: баг deep-filter — посреди речи кадры 10–30мс ЦИФРОВОГО НУЛЯ, всплески +15 dB и «заикание»
   (звук/ноль по 10мс) — «будто аппаратура лагает». Дыры -> исходник с косинусными стыками 3мс;
3. + исходник на −12 dB (паузы не падают в мёртвый ноль, звук естественный);
4. highpass 80 + EQ «диктор» (полка −5 dB @200, −4 dB @320, +4 dB @3.2 кГц, де-эссер, lowpass 11 кГц);
5. речь на −22 dBFS -> медленная компрессия 2.5:1 + лимитер. Без RNNoise и без гейтов.
Проверка: glitch_check() — 0 скачков (ролик 3: 50с, 0 на порогах 9 и 7 dB).

    import voicefx_v3 as V
    voice = V.process(SRC, f"{BUILD}/assets/<N>", BUILD)     # (N, 2) float32, длина = исходник
    V.speech_rms(voice), V.speech_peak(voice)                   # уровни музыки/SFX (§6)
"""
import os, subprocess, wave
import numpy as np

SR = 48000
DF = r"D:\tools\deepfilter\deep-filter.exe"
MIX_DB = -12
EQ = ("lowshelf=f=200:g=-5,equalizer=f=320:t=q:w=1.2:g=-4,equalizer=f=3200:t=q:w=1:g=4,"
      "deesser=i=0.4,lowpass=f=11000")
COMP = "acompressor=threshold=-24dB:ratio=2.5:attack=15:release=250:knee=6:makeup=1"
LIM = "alimiter=limit=0.89:level=disabled"


def read_wav(p):
    w = wave.open(p)
    d = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    ch = w.getnchannels()
    return d.reshape(-1, ch) if ch > 1 else d.reshape(-1, 1)


def write_wav(p, x):
    w = wave.open(p, "wb"); w.setnchannels(x.shape[1]); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes()); w.close()


def _speech_frames(x):
    m = x[:, 0]
    n = int(0.05 * SR)
    fr = m[: len(m) // n * n].reshape(-1, n)
    r = np.sqrt((fr ** 2).mean(1)) + 1e-12
    return fr[r > np.percentile(r, 95) * 10 ** (-30 / 20)]


def speech_rms(x):
    return float(np.sqrt((_speech_frames(x) ** 2).mean()))


def speech_peak(x):
    return float(np.percentile(np.abs(_speech_frames(x)), 99.9))


def lag(a, b, max_ms=60):
    """На сколько сэмплов b отстаёт от a (корреляция огибающих 1мс, в обе стороны)."""
    n = SR // 1000
    ea = np.abs(a[: len(a) // n * n, 0]).reshape(-1, n).mean(1)
    eb = np.abs(b[: len(b) // n * n, 0]).reshape(-1, n).mean(1)
    m = min(len(ea), len(eb)) - max_ms
    return max(range(-max_ms, max_ms), key=lambda k: np.dot(ea[max_ms:m], eb[max_ms + k:m + k])) * n


def repair_holes(df, raw, hop_ms=2.5, hole_db=-80.0, raw_db=-70.0, xf_ms=3.0):
    x = df[:, 0].copy()
    r = raw[: len(x), 0]
    n = int(hop_ms * SR / 1000)
    k = len(x) // n
    lv = lambda v: 20 * np.log10(np.sqrt((v[: k * n].reshape(k, n) ** 2).mean(1)) + 1e-12)
    lx, lr = lv(x), lv(r)
    hole = ((lx < hole_db) | (lx > lr + 6)) & (lr > raw_db)       # цифровой ноль или всплеск
    gap = int(30 / hop_ms)                                        # «заикание»: дыры ближе 30мс — одна заплатка
    idx = np.flatnonzero(hole)
    for a_, b_ in zip(idx[:-1], idx[1:]):
        if 1 < b_ - a_ <= gap:
            hole[a_:b_] = True
    gfr = np.convolve(np.where(lr > -50, 1.0, 10 ** (-9 / 20)), np.ones(8) / 8, mode="same")
    gf = np.concatenate([np.repeat(gfr, n), np.ones(len(x) - k * n)]).astype(np.float32)
    w = np.zeros(len(x), np.float32)
    xf = int(xf_ms * SR / 1000)
    n_fix, i = 0, 0
    while i < k:
        if not hole[i]:
            i += 1; continue
        j = i
        while j < k and hole[j]:
            j += 1
        A, B = i * n, j * n
        a, b = max(0, A - xf), min(len(x), B + xf)
        w[A:B] = 1
        w[a:A] = np.maximum(w[a:A], 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, A - a)))
        w[B:b] = np.maximum(w[B:b], 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, b - B)))
        n_fix += 1
        i = j
    return (x * (1 - w) + r * w * gf)[:, None].astype(np.float32), n_fix


def glitch_check(x, raw, jump_db=9.0, hop=0.01):
    """Скачки «обработанный − исходник» по 4 полосам туда-обратно за ≤50мс внутри речи. Норма — пустой список."""
    bands = [(100, 1000), (1000, 3000), (3000, 6000), (6000, 11000)]
    n = int(hop * SR)
    k = min(len(x), len(raw)) // n
    f = np.fft.rfftfreq(n, 1 / SR)

    def bdb(v):
        S = np.abs(np.fft.rfft(v[: k * n, 0].reshape(k, n) * np.hanning(n), axis=1)) ** 2
        return np.stack([10 * np.log10(S[:, (f >= a) & (f < b)].sum(1) + 1e-12) for a, b in bands], 1)

    X, R = bdb(x), bdb(raw)
    tot = 10 * np.log10((10 ** (R / 10)).sum(1))
    speech = tot > np.percentile(tot, 90) - 30
    r = X - R
    r -= np.median(r[speech], 0)
    d = np.abs(np.diff(r, axis=0)).max(1)
    out = [round((i + 1) * hop, 2) for i in range(1, len(d) - 5)
           if speech[i] and speech[i + 1] and d[i] > jump_db and d[i + 1:i + 6].max() > jump_db * 0.6]
    return [t for j, t in enumerate(out) if j == 0 or t - out[j - 1] > 0.08]


def process(src, tmp_dir, build_dir):
    """src (видео/аудио) -> голос (N, 2) float32 той же длины, без сдвига. Печатает число заплаток и скачков."""
    os.makedirs(tmp_dir, exist_ok=True)
    raw_p = f"{tmp_dir}/_vfx3_raw.wav"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", src, "-vn", "-ac", "1",
                    "-ar", str(SR), "-c:a", "pcm_s16le", raw_p], check=True)
    dfd = f"{tmp_dir}/_vfx3_df"
    os.makedirs(dfd, exist_ok=True)
    subprocess.run([DF, "-D", "-a", "100", "-o", dfd, raw_p], check=True, capture_output=True)
    raw = read_wav(raw_p)
    df = np.nan_to_num(read_wav(os.path.join(dfd, os.path.basename(raw_p))))[: len(raw)]
    if len(df) < len(raw):
        df = np.concatenate([df, np.zeros((len(raw) - len(df), 1), np.float32)])
    sh = lag(raw, df)
    assert sh == 0, f"deep-filter сдвинул звук на {sh} сэмплов"
    df, n_fix = repair_holes(df, raw)
    mix = df + raw * 10 ** (MIX_DB / 20)
    g = glitch_check(mix, raw)
    mixed = f"{tmp_dir}/_vfx3_mix.wav"
    write_wav(mixed, mix)
    pre = f"{tmp_dir}/_vfx3_pre.wav"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", mixed,
                    "-af", f"highpass=f=80:p=2,{EQ}", "-c:a", "pcm_s16le", pre], check=True, cwd=build_dir)
    gain = -22 - 20 * np.log10(speech_rms(read_wav(pre)))
    out = f"{tmp_dir}/_vfx3_voice.wav"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", pre,
                    "-af", f"volume={gain:.2f}dB,{COMP},{LIM}", "-ac", "2", "-c:a", "pcm_s16le", out], check=True)
    v = np.nan_to_num(read_wav(out))
    print(f"голос (voicefx_v3): заплаток {n_fix}, скачков {len(g)} {g[:10]}, {len(v) / SR:.2f}с")
    return v[: len(raw)]
