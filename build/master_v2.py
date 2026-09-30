"""Мастер звука v2 — с 2026-09-30 (ПРАВИЛА-МОНТАЖА.md §6). Общий модуль: только читать (меняет чат A).

Отличие от master_v1 (урок чата C, переозвучка ролика 8): v1 после поправки усиления пик не перепроверял и мог
вернуть как итог −14.2 LUFS при +1.4 dBTP — лимитер держит 0.80, но перелёт возникает в AAC. Здесь до 4 проходов:
после КАЖДОГО — замер готового mp4; пик выше −1 dBTP → потолок лимитера ниже на 0.05 (0.80 → 0.75 → 0.70 → 0.65);
промах по громкости > 0.3 LU → поправка усиления. Усиление по-прежнему ЛИНЕЙНОЕ (без loudnorm: он поднимает паузы),
соотношение речь/паузы не меняется. Если норма не достигнута — печатает «НЕ В НОРМЕ» и возвращает ok=False.

    import master_v2 as M
    i, tp = M.master(mix_wav, video_mp4, out_mp4)      # печатает итог: усиление, потолок лимитера, LUFS, пик
"""
import os, subprocess
from master_v1 import loudness, TARGET

PEAK_MAX = -1.0


def _mux(mix_wav, video, out, gain_db, limit):
    tmp = out + ".part.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", video, "-i", mix_wav,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-af", f"highpass=f=65,volume={gain_db:.2f}dB,alimiter=limit={limit:.2f}:level=disabled",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", tmp], check=True)
    os.replace(tmp, out)


def master(mix_wav, video, out):
    i0, _ = loudness(mix_wav)
    gain, limit = TARGET - i0, 0.80
    for n in range(4):
        _mux(mix_wav, video, out, gain, limit)
        i1, tp = loudness(out)
        ok = abs(i1 - TARGET) <= 0.3 and tp <= PEAK_MAX
        if ok:
            break
        if tp > PEAK_MAX:
            limit = round(max(0.60, limit - 0.05), 2)
        if abs(i1 - TARGET) > 0.3:
            gain += TARGET - i1
    print(f"мастер v2 (линейно): усиление {gain:+.2f} dB, лимитер {limit:.2f}, проходов {n + 1} → {i1:.1f} LUFS, "
          f"пик {tp:.1f} dBTP" + ("" if ok else "  — НЕ В НОРМЕ"))
    return i1, tp
