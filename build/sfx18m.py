"""Звук версии «мультик» ролика 18: 15.2 — голос voicefx_v7 (собран прежней версией этого файла); с 15.3 — DeepFilterNet
(voice18_samples.py, без VoiceFixer),
музыка та же (song3 с 0:50 через V.MUSIC_AF, −22 dB от RMS речи), мастер master_v2. Whoosh — на сменах сцен мультика,
не чаще раза в 4с, 0.025 от speech_peak() (§6). Звука появления текста и предметов НЕТ."""
import os, sys, subprocess, wave
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sfx18 as S                      # генератор whoosh, чтение wav, V (voicefx_v7), M (master_v1)
from cartoon18 import SCENES, VID

BUILD = os.path.dirname(os.path.abspath(__file__))
OUT = f"{BUILD}/../videos/18/bridge_cartoon_v2.mp4"   # 15.3 (с фото автора); 15.2 — bridge_cartoon.mp4
SR = S.SR
# Голос: с 2026-09-30 без VoiceFixer («обработанный, но не робота», §6). Вариант из voice18_samples.py —
# имя можно передать аргументом: python sfx18m.py 1_myagko | 2_sredne | 3_sredne_pauzy (до выбора автора — 2).
VOICE_TAG = sys.argv[1] if len(sys.argv) > 1 else "2_sredne"
VOICE = f"{BUILD}/assets/18/smp/_voice_{VOICE_TAG}.wav"
V = S.V
import master_v2 as M          # с 2026-09-30: перепроверка пика после каждого прохода (§6)


def whoosh_cuts():
    out = []
    for a, b, n in SCENES[1:]:
        if not out or a - out[-1] >= S.WHOOSH_GAP:
            out.append(a)
    return out


def main():
    voice = np.nan_to_num(V.read_wav(VOICE))
    N = voice.shape[0]
    peak, vrms = V.speech_peak(voice), V.speech_rms(voice)
    bed = np.zeros((N, 2), np.float32)
    WH = S.low_whoosh()
    cuts = whoosh_cuts()
    for c in cuts:
        i = int(c * SR)
        n = min(len(WH), N - i)
        bed[i:i + n] += (WH[:n] * peak * S.WHOOSH_GAIN)[:, None]
    mw = f"{BUILD}/assets/18/_music_18m.wav"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", "50", "-i", f"{BUILD}/../audios/song3.mp3",
                    "-af", V.MUSIC_AF, "-ac", "2", "-ar", str(SR), "-c:a", "pcm_s16le", mw], check=True)
    mus = S.read_wav(mw)
    assert 50 + N / SR < 102 and len(mus) >= N, "song3 не хватит — затухание попадёт в ролик (§6)"
    track = mus[:N].copy()
    track *= (vrms / (np.sqrt((track ** 2).mean()) + 1e-9)) * (10 ** (-22 / 20))
    fi, fo = int(0.8 * SR), int(2.0 * SR)
    track[:fi] *= np.linspace(0, 1, fi)[:, None]
    track[-fo:] *= np.linspace(1, 0, fo)[:, None]
    bed += track.astype(np.float32)
    mix = voice + bed
    m = np.abs(mix).max()
    if m > 0.99:
        mix *= 0.99 / m
    out = f"{BUILD}/assets/18/_mix_18m.wav"
    w = wave.open(out, "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes()); w.close()
    print("голос:", VOICE_TAG, "| whoosh на сменах сцен:", cuts)
    M.master(out, VID, OUT)
    print("готово:", OUT)


if __name__ == "__main__":
    main()
