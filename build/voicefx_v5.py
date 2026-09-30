"""Голос v5 — стандарт с 2026-09-28 (ПРАВИЛА-МОНТАЖА.md §6). Общий модуль: в параллельной работе только читать.

Урок ролика 4 (a3), автор: «постарайся в следующий раз не создавать шум сам и убрать имеющийся».
Замер v3 на a3: фон между словами поднимали МЫ — компрессор 2.5:1 и подъём +4 dB @3.2 кГц (+~7 dB к фону),
а плотная яркая музыка (song2 с 2:00, синт-пэд до ~17 кГц) звучала под голосом как шум.
Подмес исходника −12 dB НЕ убирать: он прячет микропровалы DeepFilterNet (при −24 dB — 11 «лагов», при −12 — 0).

v5 = цепочка v3 (DeepFilterNet -D -a 100 + repair_holes + исходник −12 dB), но:
  - подъём середины +2 dB вместо +4 (меньше подчёркивает «песок»);
  - компрессия почти выключена: 1.4:1, порог −16 dB — тихие места и фон НЕ поднимаются;
  на a3: фон (5-й перцентиль кадров) −47.5 dB от речи против −42.6 у v3, скачков 0.
Музыка: music_filter() — lowpass 5 кГц (убирает «шипящий» верх любого трека); треки — спокойные и тёмные.

    import voicefx_v5 as V
    voice = V.process(SRC, f"{BUILD}/assets/<N>", BUILD)      # (N, 2) float32, длина = исходник, сдвиг 0
    V.speech_rms(voice), V.speech_peak(voice)                    # уровни музыки/SFX (§6)
    ffmpeg ... -af V.MUSIC_AF ...                                # музыку прогонять через этот фильтр
    V.floor_db(voice)                                            # контроль фона: норма ≤ −45 dB от речи
"""
import os, subprocess
import numpy as np
from voicefx_v3 import (SR, DF, LIM, read_wav, write_wav, speech_rms, speech_peak, lag, repair_holes,
                        glitch_check)

MIX_DB = -12
EQ = ("lowshelf=f=200:g=-5,equalizer=f=320:t=q:w=1.2:g=-4,equalizer=f=3200:t=q:w=1:g=2,"
      "deesser=i=0.4,lowpass=f=11000")
COMP = "acompressor=threshold=-16dB:ratio=1.4:attack=15:release=250:knee=6"
MUSIC_AF = "lowpass=f=5000:p=2,lowpass=f=5000:p=2"


def floor_db(x):
    """Фон: 5-й перцентиль 20-мс кадров относительно RMS речи (dB). v3 на a3: −42.6, v5: −47.5."""
    m = x[:, 0]
    k = int(0.02 * SR)
    fr = m[: len(m) // k * k].reshape(-1, k)
    e = 20 * np.log10(np.sqrt((fr ** 2).mean(1)) + 1e-12)
    return float(np.percentile(e, 5) - 20 * np.log10(speech_rms(x)))


def process(src, tmp_dir, build_dir):
    os.makedirs(tmp_dir, exist_ok=True)
    raw_p = f"{tmp_dir}/_vfx5_raw.wav"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", src, "-vn", "-ac", "1",
                    "-ar", str(SR), "-c:a", "pcm_s16le", raw_p], check=True)
    dfd = f"{tmp_dir}/_vfx5_df"
    os.makedirs(dfd, exist_ok=True)
    subprocess.run([DF, "-D", "-a", "100", "-o", dfd, raw_p], check=True, capture_output=True)
    raw = read_wav(raw_p)
    df = np.nan_to_num(read_wav(os.path.join(dfd, os.path.basename(raw_p))))[: len(raw)]
    if len(df) < len(raw):
        df = np.concatenate([df, np.zeros((len(raw) - len(df), 1), np.float32)])
    assert lag(raw, df) == 0, "deep-filter сдвинул звук"
    fixed, n_fix = repair_holes(df, raw)
    mix = fixed + raw * 10 ** (MIX_DB / 20)
    gl = glitch_check(mix, raw)
    mixed = f"{tmp_dir}/_vfx5_mix.wav"
    write_wav(mixed, mix)
    pre = f"{tmp_dir}/_vfx5_pre.wav"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", mixed,
                    "-af", f"highpass=f=80:p=2,{EQ}", "-c:a", "pcm_s16le", pre], check=True, cwd=build_dir)
    gain = -22 - 20 * np.log10(speech_rms(read_wav(pre)))
    out = f"{tmp_dir}/_vfx5_voice.wav"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", pre,
                    "-af", f"volume={gain:.2f}dB,{COMP},{LIM}", "-ac", "2", "-c:a", "pcm_s16le", out], check=True)
    v = np.nan_to_num(read_wav(out))[: len(raw)]
    print(f"голос (voicefx_v5): заплаток {n_fix}, скачков {len(gl)} {gl[:10]}, фон {floor_db(v):.1f} dB от речи")
    return v
