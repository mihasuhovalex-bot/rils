"""Голос v6 — стандарт с 2026-09-28 (вечер), для гулких/шумных исходников и вообще для новых роликов.
Общий модуль: в параллельной работе только читать (меняет только чат A).

Почему не v5: съёмка 28.09 (офис, без петлички) — исходник гулкий: тихие кадры всего на 18.5 dB ниже речи
(у a3 — 37). v5 подмешивает СЫРОЙ исходник на −12 dB (чтобы прятать микропровалы нейросети) — на таком
исходнике это возвращает гул: фон −26 dB от речи и всё равно 3 «лага». afftdn-подмес не помогает (это
реверберация, а не стационарный шум). Замер на ролике 6 (фон, dB от речи | скачки glitch_check):
    v5 (DF -a 100 + исходник −12)          −26.3 | 3
    DF -a 100 без подмеса                  −30.6 | 89   (нейросеть «рвёт» гулкую речь — это и есть «лаги»)
    DF -a 15  + починка                    −30.4 | 5
    DF -a 12  + починка   <- v6            −28.2 | 0
    DF -a 10  + починка                    −26.5 | 0
На тихом исходнике (a3) v6: паузы почти в ноль (−87), 1 скачок.

v6 = deep-filter.exe -D -a 12 (нейросеть сама подмешивает исходник, мягко, без рывков) → repair_holes (баг DF:
цифровой ноль/всплески) → БЕЗ отдельного подмеса → highpass 80 + EQ v5 (+2 dB @3.2 кГц) → компрессия 1.4:1
(фон не поднимаем). Музыка — V.MUSIC_AF (lowpass 5 кГц), как в v5.
Предел: гулкую комнату полностью не убрать без «лагов»; для чистого звука — петличка и WAV на съёмке.

    import voicefx_v6 as V
    voice = V.process(SRC, f"{BUILD}/assets/<N>", BUILD)
    V.speech_rms(voice), V.speech_peak(voice), V.MUSIC_AF, V.floor_db(voice)
"""
import os, subprocess
import numpy as np
from voicefx_v3 import SR, DF, LIM, read_wav, write_wav, speech_rms, speech_peak, lag, repair_holes, glitch_check
from voicefx_v5 import EQ, COMP, MUSIC_AF, floor_db

ATTEN_DB = 12


def process(src, tmp_dir, build_dir):
    os.makedirs(tmp_dir, exist_ok=True)
    raw_p = f"{tmp_dir}/_vfx6_raw.wav"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", src, "-vn", "-ac", "1",
                    "-ar", str(SR), "-c:a", "pcm_s16le", raw_p], check=True)
    dfd = f"{tmp_dir}/_vfx6_df"
    os.makedirs(dfd, exist_ok=True)
    subprocess.run([DF, "-D", "-a", str(ATTEN_DB), "-o", dfd, raw_p], check=True, capture_output=True)
    raw = read_wav(raw_p)
    df = np.nan_to_num(read_wav(os.path.join(dfd, os.path.basename(raw_p))))[: len(raw)]
    if len(df) < len(raw):
        df = np.concatenate([df, np.zeros((len(raw) - len(df), 1), np.float32)])
    assert lag(raw, df) == 0, "deep-filter сдвинул звук"
    fixed, n_fix = repair_holes(df, raw)
    gl = glitch_check(fixed, raw)
    mixed = f"{tmp_dir}/_vfx6_fixed.wav"
    write_wav(mixed, fixed)
    pre = f"{tmp_dir}/_vfx6_pre.wav"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", mixed,
                    "-af", f"highpass=f=80:p=2,{EQ}", "-c:a", "pcm_s16le", pre], check=True, cwd=build_dir)
    gain = -22 - 20 * np.log10(speech_rms(read_wav(pre)))
    out = f"{tmp_dir}/_vfx6_voice.wav"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", pre,
                    "-af", f"volume={gain:.2f}dB,{COMP},{LIM}", "-ac", "2", "-c:a", "pcm_s16le", out], check=True)
    v = np.nan_to_num(read_wav(out))[: len(raw)]
    print(f"голос (voicefx_v6): заплаток {n_fix}, скачков {len(gl)} {gl[:10]}, фон {floor_db(v):.1f} dB от речи "
          f"(исходник {floor_db(raw):.1f})")
    return v
