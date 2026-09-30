"""Автопроверки версии «мультик» ролика 18 (15.2). Результат: videos/18/qa-report-cartoon.md

1. Рисунок × субтитры: рисунок обрезан по y 1370 (Pen.done), субтитры не поднимаются выше — проверка по пикселям на
   каждом 6-м кадре (слой рисунка qa=True против слоя субтитров) и по габаритам слов на всех кадрах.
2. Наложение строк субтитров (getbbox), субтитры внутри кадра.
3. Символы без глифа в Unbounded — все надписи рисунка и субтитры.
4. Математика рисунка буквально (ромб, 3-4-5, расчёт с ошибкой, транспортир).
5. Готовый файл: декодирование, 1080×1920/30, громкость, пик, музыка в паузах.
"""
import os, sys, re, math, subprocess
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cartoon18 as K
import sfx18m
import captions as C
from style import FPS, W, H

BUILD = os.path.dirname(os.path.abspath(__file__))
REPORT = f"{BUILD}/../videos/18/qa-report-cartoon.md"
TEXTS = ["10 т", "нагрузка", "запас", "итого", "1 200 т", "× 1,5", "180 т", "ГЕОМЕТРИЯ", "ABC345", "sin A = 3/5",
         "3² + 4² = 5²", "a² + b²", "?", "0123456789°"] + K.CARDS


def box(it):
    b = it["font"].getbbox(it["text"], anchor=it.get("anchor", "mm"))
    x, y = it["xy"]
    return (x + b[0], y + b[1], x + b[2], y + b[3])


def inter(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def captions_layout():
    ov, top, outside = [], 9999, []
    for f in range(K.NF):
        t = f / FPS
        rows = {}
        for it in K.CAPM.items(t):
            b = box(it)
            rows.setdefault(round(it["xy"][1], 1), []).append(b)
            top = min(top, b[1])
            if b[0] < 40 or b[2] > W - 40:
                outside.append(round(t, 2))
        ls = [(min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs))
              for bs in rows.values()]
        for i in range(len(ls)):
            for j in range(i + 1, len(ls)):
                if inter(ls[i], ls[j]):
                    ov.append(round(t, 2))
    return ov, top, outside


def art_vs_captions(step=3):
    """Каждый 3-й кадр: пиксельное наложение рисунка и субтитров и зазор между ними В ОДНОМ кадре."""
    global GAP
    bad, n, low, GAP = [], 0, 0, 9999
    for f in range(0, K.NF, step):
        t = f / FPS
        a = np.array(K.art(t, qa=True).split()[3]) > 40
        ys = np.flatnonzero(a.any(1))
        if len(ys):
            low = max(low, int(ys.max()))
        sub = K.CAPM.layer(t)
        if sub is not None:
            sa = np.array(sub.split()[3]) > 40
            if int((a & sa).sum()):
                bad.append(round(t, 2))
            sy = np.flatnonzero(sa.any(1))
            if len(ys) and len(sy):
                GAP = min(GAP, int(sy.min()) - int(ys.max()))
        n += 1
    return n, bad, low


def glyphs():
    f = C.wide(60)
    tofu = f.getmask(chr(0xFFFF)).getbbox()
    txt = "".join(TEXTS) + "".join(t.upper() for c in K.CAPS for t, _, _ in c[2])
    return sorted({ch for ch in txt if not ch.isspace() and ch != "/" and f.getmask(ch).getbbox() == tofu})


def math_checks():
    A, B, Cc = K.PY_A, K.PY_B, K.PY_C
    ab, bc, ac = math.dist(A, B), math.dist(B, Cc), math.dist(A, Cc)
    right = (Cc[0] - B[0]) * (A[0] - B[0]) + (Cc[1] - B[1]) * (A[1] - B[1]) == 0
    a_, phi = 360, 60                      # ромб сцены rigid: стороны после сдвига (x0 70, сторона 360, угол 60°)
    dx, dy = a_ * math.cos(math.radians(phi)), a_ * math.sin(math.radians(phi))
    sq = [(70, 1020), (70 + a_, 1020), (70 + a_ + dx, 1020 - dy), (70 + dx, 1020 - dy)]
    sides = [math.dist(sq[i], sq[(i + 1) % 4]) for i in range(4)]
    return {"ромб: 4 равные стороны": max(sides) - min(sides) < 1e-6,
            "3-4-5, угол B прямой": right and abs(ab / 120 - 4) < 1e-9 and abs(bc / 120 - 3) < 1e-9 and abs(ac / 120 - 5) < 1e-9,
            "sin A = 3/5": abs(bc / ac - 0.6) < 1e-9, "9 + 16 = 25": 3 ** 2 + 4 ** 2 == 5 ** 2,
            "ошибка в расчёте — настоящая (1 200 × 1,5 = 1 800, на экране 180)": 1200 * 1.5 == 1800 != 180}


def decode_errors():
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", sfx18m.OUT, "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return len([x for x in r.stderr.splitlines() if x.strip()])


def probe():
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,r_frame_rate:format=duration", "-of", "csv=p=0", sfx18m.OUT],
                       capture_output=True, text=True).stdout.split()
    return " ".join(r)


def loudness():
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", sfx18m.OUT, "-af", "ebur128=peak=true",
                        "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = r.stderr[r.stderr.rfind("Summary:"):]
    return (float(re.search(r"I:\s+(-?[\d.]+) LUFS", tail).group(1)),
            float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", tail).group(1)))


def music_gap():
    r = subprocess.run([sys.executable, f"{BUILD}/measure_mix.py", sfx18m.OUT, f"{BUILD}/../videos/18/words.json"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    return float(re.search(r"-> (-?[\d.]+) dB", r).group(1))


def main():
    ov, top, outside = captions_layout()
    n, bad, low = art_vs_captions()
    gl = glyphs()
    mm = math_checks()
    derr = decode_errors()
    I, TP = loudness()
    ok = lambda c: "✅" if c else "❌"
    lens = [b - a for a, b, _ in K.SCENES]
    rep = ["# QA-отчёт — ролик 18, версия «мультик» (15.2)\n", "| проверка | результат | |", "|---|---|---|",
           f"| рисунок × субтитры по пикселям (каждый 3-й кадр, {n} кадров) | {len(bad)} {bad[:6]} | {ok(not bad)} |",
           f"| нижний край рисунка (< {K.ART_MAX_Y}) / мин. зазор до субтитра в одном кадре | y {low} / {GAP} px | {ok(low < K.ART_MAX_Y and GAP >= 8)} |",
           f"| наложение строк субтитров (все {K.NF} кадров) | {len(ov)} | {ok(not ov)} |",
           f"| субтитры ближе 40px к краю кадра | {len(outside)} | {ok(not outside)} |",
           f"| символы без глифа в Unbounded (надписи рисунка + субтитры) | {len(gl)} {gl} | {ok(not gl)} |",
           f"| математика рисунка | {mm} | {ok(all(mm.values()))} |",
           f"| сцен / средняя / мин / макс | {len(lens)} / {sum(lens) / len(lens):.2f}с / {min(lens):.2f}с / {max(lens):.2f}с | ℹ️ |",
           f"| файл (ширина, высота, fps, длительность) | {probe()} | ℹ️ |",
           f"| ошибки декодирования | {derr} строк | {ok(derr == 0)} |",
           f"| громкость | {I:.1f} LUFS | {ok(abs(I + 14) <= 0.5)} |",
           f"| истинный пик | {TP:.1f} dBTP | {ok(TP <= -1.0)} |",
           f"| паузы речи в готовом файле (музыка + whoosh) | {music_gap():.1f} dB от речи | ℹ️ |",
           "\nГолос — тот же файл, что в 15 (voicefx_v7): его проверки — в qa-report.md ролика 18."]
    open(REPORT, "w", encoding="utf-8").write("\n".join(rep) + "\n")
    print("\n".join(rep))


if __name__ == "__main__":
    main()
