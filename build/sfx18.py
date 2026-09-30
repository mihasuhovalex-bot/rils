"""Звук ролика 18 — копия sfx9.py (ролик 9, та же локация «офис»): голос voicefx_v7 (VoiceFixer режим 0, §6),
мастер master_v1 (линейное усиление + alimiter); музыка song3 с 0:50 (50 + 48.9 = 98.9с < 102с — затухание трека
не попадает, петля не нужна) через V.MUSIC_AF, −22 dB от RMS речи; соседи: 16 — song2 с 4:30, 17 — song2 с 0:30.
whoosh только на смене типа карточки, ≥4с, 0.025 от speech_peak(). Звука появления текста НЕТ."""
import os, sys, subprocess, wave
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import win_fonts  # noqa: F401 — Captions считает раскладку тем же шрифтом
from storyboard18 import SHOTS, CAPS, DUR, NUM_REVEALS

BUILD = os.path.dirname(os.path.abspath(__file__))
VIDEO_NUM = 18
SRC = f"{BUILD}/../videos/{VIDEO_NUM}/source.mov"
VID = f"{BUILD}/assets/{VIDEO_NUM}/_video_{VIDEO_NUM}.mp4"
OUT = f"{BUILD}/../videos/{VIDEO_NUM}/bridge_edit.mp4"
import voicefx_v7 as V   # §6: офис без петлички — VoiceFixer режим 0 (выбор автора на 06)
import master_v1 as M   # общий модуль — только чтение
speech_peak, speech_rms = V.speech_peak, V.speech_rms
SR = 48000


def env(n, a, d, curve=2.0):
    at = int(SR * a); dc = max(1, n - at)
    e = np.concatenate([np.linspace(0, 1, at) ** 0.6,
                        np.linspace(1, 0, dc) ** curve])
    return e[:n]


def low_whoosh(dur=0.42):
    n = int(SR * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    rng = np.random.default_rng(3)
    noise = rng.normal(0, 1, n)
    a = np.exp(-2 * np.pi * 180 / SR)
    y = np.zeros(n); prev = 0.0
    for i in range(n):
        prev = a * prev + (1 - a) * noise[i]
        y[i] = prev
    f0, f1 = 140.0, 34.0
    ph = 2 * np.pi * np.cumsum(f0 * (f1 / f0) ** (t / dur)) / SR
    sweep = np.sin(ph)
    s = 0.65 * y / (np.abs(y).max() + 1e-9) + 0.25 * sweep
    return s * env(n, 0.06, 0.0, 1.8)


def impact(dur=0.55):
    n = int(SR * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    f = 92 * np.exp(-t * 11) + 41
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t * 7.5)
    rng = np.random.default_rng(11)
    click = rng.normal(0, 1, n) * np.exp(-t * 150) * 0.25
    s = body + click
    return s / (np.abs(s).max() + 1e-9)


# Правка автора 2026-09-25 (через чат ролика 2): whoosh «бьют по ушам» -> реже и тише.
# Только на смене ТИПА карточки (лицо / вставка B / сетка), не чаще раза в WHOOSH_GAP,
# уровень 0.020 от пика голоса (было 0.040 на каждом резе), саб в свипе слабее (0.25 вместо 0.45).
WHOOSH_GAIN = 0.025   # §6: от speech_peak()
WHOOSH_GAP = 4.0     # §6: не чаще раза в 4с


def _card(kind):
    return "A" if kind in ("A1", "A2") else ("B" if kind == "stock" else "G")


def whoosh_cuts():
    out = []
    for prev, cur in zip(SHOTS, SHOTS[1:]):
        if _card(prev[2]) != _card(cur[2]) and (not out or cur[0] - out[-1] >= WHOOSH_GAP):
            out.append(cur[0])
    return out


def read_wav(p):
    w = wave.open(p)
    d = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    ch = w.getnchannels()
    return d.reshape(-1, ch) if ch > 1 else d.reshape(-1, 1)


def main():
    voice = V.process(SRC, f"{BUILD}/assets/{VIDEO_NUM}", BUILD)
    N = voice.shape[0]
    peak = speech_peak(voice)
    vrms_speech = speech_rms(voice)

    bed = np.zeros((N, 2), np.float32)

    def add(sig, t, gain):
        i = int(t * SR)
        if i < 0:
            return
        n = min(len(sig), N - i)
        if n <= 0:
            return
        bed[i:i + n, 0] += sig[:n] * gain
        bed[i:i + n, 1] += sig[:n] * gain

    WH, IM = low_whoosh(), impact()
    for c in whoosh_cuts():
        add(WH, c, peak * WHOOSH_GAIN)
    for t in NUM_REVEALS:
        add(IM, t + 0.05, peak * 0.070)
    music_path = f"{BUILD}/../audios/song3.mp3"  # с 0:50 (раздача чата A), без петли
    if os.path.exists(music_path):
        mw = f"{BUILD}/assets/{VIDEO_NUM}/_music_{VIDEO_NUM}.wav"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", "50", "-i", music_path,
                        "-af", V.MUSIC_AF, "-ac", "2", "-ar", str(SR), "-c:a", "pcm_s16le", mw], check=True)
        mus = read_wav(mw)
        if mus.shape[1] == 1:
            mus = np.repeat(mus, 2, axis=1)
        assert 50 + N / SR < 102 and len(mus) >= N, "song3 не хватит — затухание попадёт в ролик (§6)"
        track = mus[:N].copy()
        vr = vrms_speech   # v2: RMS речи (в v1 — всего файла с мусорным пиком arnndn)
        mr = np.sqrt((track ** 2).mean()) + 1e-9
        track *= (vr / mr) * (10 ** (-22 / 20))   # §6: −22 dB от RMS речи
        fi, fo = int(0.8 * SR), int(2.0 * SR)
        track[:fi] *= np.linspace(0, 1, fi)[:, None]
        track[-fo:] *= np.linspace(1, 0, fo)[:, None]
        bed += track.astype(np.float32)
        print("музыка: song3 с 0:50, %.1fс" % (N / SR))

    mix = voice + bed
    m = np.abs(mix).max()
    if m > 0.99:
        mix *= 0.99 / m
    out = f"{BUILD}/assets/{VIDEO_NUM}/_mix_{VIDEO_NUM}.wav"
    w = wave.open(out, "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes()); w.close()

    M.master(out, VID, OUT)   # линейное усиление + alimiter (§6)
    print("готово:", OUT)


if __name__ == "__main__":
    main()
