"""Мастер звука — стандарт с 2026-09-28 (ПРАВИЛА-МОНТАЖА.md §6). Общий модуль: только читать (меняет чат A).

Почему не однопроходный loudnorm (довод чата C, ролики 8/11/13): с TP он почти всегда уходит в dynamic-режим и
работает как автомат громкости — подтягивает тихие места и паузы, т.е. поднимает фон (против «не создавать шум
самому»). Здесь: замер интегральной громкости микса (ebur128) → ЛИНЕЙНОЕ усиление до −14 LUFS → alimiter только
на пиках → AAC → замер готового mp4; если промах > 0.3 LU или пик > −1 dBTP — одна поправка усиления.
Соотношение речь/паузы не меняется.

    import master_v1 as M
    M.master(mix_wav, video_mp4, out_mp4)      # печатает итог: LUFS, пик
"""
import os, re, subprocess

TARGET = -14.0


def loudness(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    tail = r[r.rfind("Summary:"):]
    return (float(re.search(r"I:\s+(-?[\d.]+) LUFS", tail).group(1)),
            float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", tail).group(1)))


def _mux(mix_wav, video, out, gain_db):
    tmp = out + ".part.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", video, "-i", mix_wav,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-af", f"highpass=f=65,volume={gain_db:.2f}dB,alimiter=limit=0.80:level=disabled",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", tmp], check=True)
    os.replace(tmp, out)


def master(mix_wav, video, out):
    i0, _ = loudness(mix_wav)
    gain = TARGET - i0
    _mux(mix_wav, video, out, gain)
    i1, tp = loudness(out)
    if abs(i1 - TARGET) > 0.3 or tp > -1.0:
        gain += (TARGET - i1) if tp <= -1.0 else min(TARGET - i1, -1.0 - tp)
        _mux(mix_wav, video, out, gain)
        i1, tp = loudness(out)
    print(f"мастер (линейно): усиление {gain:+.2f} dB → {i1:.1f} LUFS, пик {tp:.1f} dBTP")
    return i1, tp
