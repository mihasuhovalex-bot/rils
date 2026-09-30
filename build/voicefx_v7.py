"""Голос v7 — для гулкой локации «офис» (съёмка 28.09 без петлички), с 2026-09-28. Общий модуль: только читать.

Автор про 06 (Эратосфен): v6 «будто не обработан»; образцы v6 разной силы «не отличаются» — мешает эхо ВНУТРИ слов,
а DeepFilterNet давит шум, не эхо. WPE (1 микрофон) не помог (−0.7 dB). Нейро-реставратор VoiceFixer помог; автор
выбрал образец 5 — режим 0 («в остальных ты мне голос начал менять»: режим 2 меняет тембр — не брать).
Замер на 15с ролика 9: фон −17.5 → −36 dB от речи, эхо после слов −11 → −13 dB, верха восстановлены.

Цепочка: исходник 48 кГц моно → VoiceFixer mode 0 (окружение D:\\tools\\enh-venv, модели D:\\tools\\home\\.cache,
USERPROFILE/HOME = D:\\tools\\home) → 48 кГц, выравнивание по исходнику (VF сдвигает на ~8 мс) → highpass 80,
−2 dB @300 Гц, де-эссер (ничего больше тембр не трогает) → речь на −22 dBFS → компрессия 1.4:1 → лимитер.
Мастер — master_v1.py. Для тихих исходников с петличкой (полки) — по-прежнему voicefx_v6.

    import voicefx_v7 as V
    voice = V.process(SRC, f"{BUILD}/assets/<N>", BUILD)
    V.speech_rms(voice), V.speech_peak(voice), V.MUSIC_AF, V.floor_db(voice)
"""
import os, subprocess
import numpy as np
from voicefx_v3 import SR, LIM, read_wav, write_wav, speech_rms, speech_peak, lag
from voicefx_v5 import COMP, MUSIC_AF, floor_db

VENV_PY = r"D:\tools\enh-venv\Scripts\python.exe"
HOME = r"D:\tools\home"
EQ = "highpass=f=80:p=2,equalizer=f=300:t=q:w=1.2:g=-2,deesser=i=0.4"


def _vfix(src, dst, build_dir, mode=0):
    env = dict(os.environ, USERPROFILE=HOME, HOME=HOME, TMP=r"D:\temp", TEMP=r"D:\temp")
    code = ("import sys; from voicefixer import VoiceFixer; "
            f"VoiceFixer().restore(input=sys.argv[1], output=sys.argv[2], cuda=False, mode={int(mode)})")
    subprocess.run([VENV_PY, "-c", code, src, dst], check=True, env=env, cwd=build_dir, capture_output=True)


def process(src, tmp_dir, build_dir):
    os.makedirs(tmp_dir, exist_ok=True)
    raw_p = f"{tmp_dir}/_vfx7_raw.wav"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", src, "-vn", "-ac", "1",
                    "-ar", str(SR), "-c:a", "pcm_s16le", raw_p], check=True)
    vf_p = f"{tmp_dir}/_vfx7_vf.wav"
    _vfix(raw_p, vf_p, build_dir, 0)
    vf48 = f"{tmp_dir}/_vfx7_vf48.wav"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", vf_p, "-ac", "1", "-ar", str(SR),
                    "-c:a", "pcm_s16le", vf48], check=True)
    raw, x = read_wav(raw_p), np.nan_to_num(read_wav(vf48))
    sh = lag(raw, x)
    x = x[sh:] if sh > 0 else np.concatenate([np.zeros((-sh, 1), np.float32), x])
    x = x[: len(raw)]
    if len(x) < len(raw):
        x = np.concatenate([x, np.zeros((len(raw) - len(x), 1), np.float32)])
    al = f"{tmp_dir}/_vfx7_al.wav"
    write_wav(al, x)
    pre = f"{tmp_dir}/_vfx7_pre.wav"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", al, "-af", EQ, "-c:a", "pcm_s16le", pre],
                   check=True)
    gain = -22 - 20 * np.log10(speech_rms(read_wav(pre)))
    out = f"{tmp_dir}/_vfx7_voice.wav"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", pre,
                    "-af", f"volume={gain:.2f}dB,{COMP},{LIM}", "-ac", "2", "-c:a", "pcm_s16le", out], check=True)
    v = np.nan_to_num(read_wav(out))[: len(raw)]
    print(f"голос (voicefx_v7, VoiceFixer 0): сдвиг VF {1000 * sh / SR:+.0f} мс выровнен, фон {floor_db(v):.1f} dB от речи "
          f"(исходник {floor_db(raw):.1f})")
    return v
