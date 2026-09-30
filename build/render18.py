"""Сборка ролика 18 — «Треугольник держит мост / инженер-конструктор». Речь не резана — резы только по картинке.

Основа — render15.py (ролик 15, чат C). Отличия ролика 18:
- исходник 720x1280 HEVC (28.09/vid28.09 (13).MP4), локация «офис» — затемняющий GRADE (§2); кадр по месту
  как у ролика 9 (та же съёмка, лицо на ~20px правее) -> FRAMINGS ролика 9 со сдвигом A2; hflip как у 9/15;
- §4 «Графики и модели»: два чертежа-модели "model" (свои функции, по образцу diagrams_v1.eratosthenes):
  rigid — квадрат на шарнирах под толчком складывается в ромб (стороны не меняются), треугольник держит форму;
  pythagoras — прямоугольный треугольник 3-4-5 (катеты 3 и 4, гипотенуза 5): 3² + 4² = 5², sin A = 3/5;
- §4 «Анимации-акценты»: панч-зум, пружинка, маркер, штамп (реализация — из render15/anim13);
- временные файлы в build/assets/18/ (§0).

  python render18.py                  — полный рендер немого видео -> assets/18/_video_18.mp4 (звук — sfx18.py)
  python render18.py snap t1 t2 ...   — только кадры на заданных секундах -> assets/18/_snap18_<t>.png
"""
import os, sys, subprocess, math
import numpy as np
import cv2
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import *
import win_fonts  # noqa: F401 — Unbounded Black вместо SF Pro Expanded (до создания Captions)
from storyboard18 import SHOTS, CAPS, SLOTS, DUR, LABELS, NUMS

BUILD = os.path.dirname(os.path.abspath(__file__))
VIDEO_NUM = 18
SRC = f"{BUILD}/../videos/{VIDEO_NUM}/source.mov"
VIDEO_DIR = os.path.dirname(SRC)
TMPD = f"{BUILD}/assets/{VIDEO_NUM}"
A1 = f"{TMPD}/aroll_{VIDEO_NUM}_A1.mp4"
A2 = f"{TMPD}/aroll_{VIDEO_NUM}_A2.mp4"
VID = f"{TMPD}/_video_{VIDEO_NUM}.mp4"   # немое видео — его берут sfx18.py и qa18.py (§6, урок ролика 7)

# §2: локация «офис» (как ролик 9) — затемняющий GRADE
GRADE = ("eq=gamma=1.08:contrast=1.04:saturation=1.10,colorbalance=rm=0.04:gm=0.008:bm=-0.03,"
         "curves=all='0/0 0.45/0.45 0.70/0.62 1/0.84',unsharp=5:5:0.30")
# 720x1280 после hflip: кадр как у ролика 9 (кадр 17с сверен наложением рамок), лицо правее на ~20px -> A2 сдвинут
FRAMINGS = {"A1": (700, 1110, 20, 138), "A2": (540, 857, 132, 247)}
HFLIP = True

CX, CY, R_A_ = CARD_A[0], CARD_A[1], R_A
CW, CH = CARD_A[2], CARD_A[3]
NF = int(round(DUR * FPS))


def prep_aroll():
    for name, out in (("A1", A1), ("A2", A2)):
        if os.path.exists(out):
            continue
        w, h, x, y = FRAMINGS[name]
        vf = ("hflip," if HFLIP else "") + f"crop={w}:{h}:{x}:{y},scale={CW}:{CH}:flags=lanczos,{GRADE}"
        part = out.replace(".mp4", ".part.mp4")   # урок ролика 25: недописанный A-roll не должен считаться готовым
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", SRC,
                        "-vf", vf, "-an", "-c:v", "libx264", "-crf", "14",
                        "-preset", "medium", "-pix_fmt", "yuv420p", part], check=True)
        os.replace(part, out)
        print("готово:", out)


BX, BY, BW, BH = CARD_B
STOCK_DIR = f"{VIDEO_DIR}/stock"
STOCK_PREP_DIR = f"{STOCK_DIR}/prepared"


def prep_stock():
    """Каждая видео-вставка -> карточка B 858x620, кроп до 1.385:1, 30 fps. Без притемнения."""
    os.makedirs(STOCK_PREP_DIR, exist_ok=True)
    out = {}
    for i, (t0, t1, kind, prm) in enumerate(SHOTS):
        if kind != "stock":
            continue
        src = f"{STOCK_DIR}/stock_{prm['clip']}.mp4"
        cx = prm.get("cx", 0.5)
        dst = f"{STOCK_PREP_DIR}/sb_{i}_{prm['clip']}_{prm.get('ss', 0)}_{cx}.mp4"
        if not os.path.exists(dst):
            vf = (f"crop='min(iw,ih*1.3839)':'min(ih,iw/1.3839)':'(iw-ow)*{cx}':'(ih-oh)/2',"
                  f"scale={BW}:{BH}:flags=lanczos,fps=30")
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                            "-ss", str(prm.get("ss", 0)), "-t", f"{t1 - t0 + 0.3:.3f}",
                            "-i", src, "-vf", vf, "-an", "-c:v", "libx264", "-crf", "15",
                            "-preset", "medium", "-pix_fmt", "yuv420p", dst + ".part.mp4"], check=True)
            os.replace(dst + ".part.mp4", dst)
            print("готово:", dst)
        out[i] = dst
    return out


# Субтитры v3: общий движок captions.py (капс, одна фраза внизу, слова всплывают, тень)
from captions import Captions, num_item, label_item, wide

# предлоги/союзы, которые не оставляем в конце строки (уроки START-HERE: ролики 21, 22, 25, 27, 29)
PREP = {"В", "ВО", "НА", "К", "С", "СО", "ЗА", "ИЗ", "ИЗ-ЗА", "ПО", "О", "ОБ", "У", "И", "А", "НЕ", "НО",
        "ПРО", "ДЛЯ", "БЕЗ", "ПОД", "НАД", "ПРИ", "ОТ", "ДО"}


class Captions8(Captions):
    """Субтитры v3 (общий движок captions.py) + перенос ролика 8: «/» — принудительный разрыв строки,
    иначе одна строка, если влезает, или самое ровное 2-строчное разбиение без висячего предлога."""

    def _word_times(self, i):
        t0, t1, runs, slot = self.caps[i]
        n = sum(1 for (txt, k, sz) in runs for w in txt.split() if w != "/")
        ws = [w["start"] for w in self.words if t0 - 0.001 <= w["start"] < t1]   # words_cap точные: без окна −0.06
        assert len(ws) == n, (runs, ws)          # тайминги строго свои (words_cap.json из storyboard13)
        return [max(t0, x) for x in ws]

    def _fit(self, words, avail):
        forced = [k for k, w in enumerate(words) if w[0] == "/"]
        ws = [w for w in words if w[0] != "/"]
        sz = 62
        while True:
            f = wide(sz)
            sp = f.getlength(" ")
            wid = lambda ln: sum(f.getlength(x[0]) for x in ln) + sp * (len(ln) - 1)
            if forced:
                k = forced[0]
                cands = [(0, [ws[:k], ws[k:]])]
            else:
                cands = [(0, [ws])] if wid(ws) <= avail else []
                for k in range(1, len(ws)):
                    a, b = ws[:k], ws[k:]
                    hang = (a[-1][0] in PREP) + (len(a) == 1 and len(a[0][0]) <= 2) + (len(b) == 1 and len(b[0][0]) <= 2)
                    cands.append((1 + 1000 * hang + abs(wid(a) - wid(b)) / 1000, [a, b]))
            ok = [c for c in cands if all(wid(ln) <= avail for ln in c[1])]
            if ok and (min(ok)[0] < 1000 or sz <= 56):
                return f, sz, min(ok, key=lambda c: c[0])[1]
            if sz <= 30:
                return f, sz, cands[0][1]
            sz -= 2


CAP = Captions8(CAPS, SHOTS, DUR, f"{VIDEO_DIR}/words_cap.json")


def _is_insert(kind):
    return kind == "stock"


def label_for(t, kind):
    for t0, t1, text in LABELS:
        if t0 <= t < t1 and _is_insert(kind):
            return [label_item(text, (540, BY + BH + 46), 40, opacity=min(1.0, (t - t0) / 0.30))]
    return []


_GRID = {}


def grid_frame(t):
    """Сетка R4 с медленным дрейфом (фаза квантуется, кэш)."""
    ph = round(t * 0.35, 2)
    if ph in _GRID:
        return _GRID[ph]
    img = grid_canvas(CW, CH, phase=ph, alpha=int(255 * 0.40))
    card = Image.new("RGBA", (CW, CH), (0, 0, 0, 255))
    card.alpha_composite(img)
    card.putalpha(rounded_mask(CW, CH, R_A_))
    _GRID.clear()
    _GRID[ph] = card
    return card


def numw_layer(t, t0):
    """Число на сетке: белое R5a (поп 80мс) или синее R5b (0.38с, оверщут). Графика выше y≈1400,
    ниже — зона субтитров (y 1500)."""
    prm = NUMS[t0]
    lt = t - t0
    size = prm.get("size", 200)
    ncy = CY + CH // 2 - 90
    T = num_item(t, t0 + 0.05, prm["digits"], (CX + CW // 2, ncy), size, prm.get("blue", False),
                 max_w=CW - 120)
    if lt >= 0.25 and prm.get("sub"):
        lsz = min(50, int(50 * (CW - 120) / wide(50).getlength(prm["sub"].upper())))
        T.append(label_item(prm["sub"], (CX + CW // 2, ncy + int(size * 0.62) + 50), lsz,
                            opacity=0.35 + 0.65 * ease_out(min(1.0, (lt - 0.25) / 0.4))))
    return grid_frame(t), T


# ---------------------------------------------------------------- зум внутри карточки
ZOOM_FACE = 1.10
ZOOM_STOCK = 1.06
FACE_FOCUS = (0.5, 0.43)


def _zoom_plan():
    plan, nf, ns = {}, 0, 0
    for i, (t0, t1, kind, prm) in enumerate(SHOTS):
        if kind in ("A1", "A2"):
            plan[i] = (ZOOM_FACE, nf % 2 == 0, FACE_FOCUS); nf += 1
        elif kind == "stock":
            plan[i] = (ZOOM_STOCK, ns % 2 == 1, (0.5, 0.5)); ns += 1
    return plan


ZOOM = _zoom_plan()


def zoom_at(i, t):
    zmax, zin, _ = ZOOM[i]
    t0, t1 = SHOTS[i][0], SHOTS[i][1]
    p = min(1.0, max(0.0, (t - t0) / (t1 - t0)))
    e = 0.5 - 0.5 * math.cos(math.pi * p)
    return 1 + (zmax - 1) * (e if zin else 1 - e)


def zoom_img(img, z, focus):
    if z <= 1.0005:
        return img
    h, w = img.shape[:2]
    cw, ch = w / z, h / z
    cx = min(max(w * focus[0], cw / 2), w - cw / 2)
    cy = min(max(h * focus[1], ch / 2), h - ch / 2)
    M = np.array([[z, 0, -(cx - cw / 2) * z], [0, z, -(cy - ch / 2) * z]], np.float32)
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)


# ---------------------------------------------------------------- кадр
class Sources:
    def __init__(self):
        prep_aroll()
        self.stock = prep_stock()
        self.caps = {"A1": cv2.VideoCapture(A1), "A2": cv2.VideoCapture(A2)}
        self.pos = {"A1": -1, "A2": -1}
        self.scap = {i: cv2.VideoCapture(p) for i, p in self.stock.items()}
        self.spos = {i: -1 for i in self.stock}
        self.last = {}

    def _read(self, cap, key, pos, want):
        if want < pos[key]:
            cap.set(cv2.CAP_PROP_POS_FRAMES, want); pos[key] = want - 1
        while pos[key] < want:
            if not cap.grab():
                break
            pos[key] += 1
            self.last.pop(key, None)
        if key not in self.last:
            ok, img = cap.retrieve()
            self.last[key] = img if ok else None
        return self.last[key]

    def face(self, kind, f):
        return self._read(self.caps[kind], kind, self.pos, f)

    def stock_frame(self, i, lf):
        return self._read(self.scap[i], i, self.spos, lf)


MASK_A = rounded_mask(CW, CH, R_A_)
MASK_B = rounded_mask(BW, BH, R_B)


def frame(src, f):
    t = f / FPS
    si = next((i for i, s in enumerate(SHOTS) if s[0] <= t < s[1]), len(SHOTS) - 1)
    t0, t1, kind, prm = SHOTS[si]
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    titems = []
    if kind in ("A1", "A2"):
        img = src.face(kind, f)
        if img is None:
            img = np.zeros((CH, CW, 3), np.uint8)
        img = zoom_img(img, zoom_at(si, t), ZOOM[si][2])
        canvas.paste(Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)), (CX, CY), MASK_A)
    elif kind == "stock":
        img = src.stock_frame(si, int(round((t - t0) * FPS)))
        if img is not None:
            img = zoom_img(img, zoom_at(si, t), ZOOM[si][2])
            canvas.paste(Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)), (BX, BY), MASK_B)
    elif kind == "numw":
        g, titems = numw_layer(t, t0)
        canvas.alpha_composite(g, (CX, CY))
    elif kind == "model":                          # чертёж-модель (ПРАВИЛА §4 «Графики и модели»)
        canvas.alpha_composite(grid_frame(t), (CX, CY))
        canvas.alpha_composite(model_layer(t, t0, prm["fn"]), (CX, CY))
    items = titems + label_for(t, kind)
    if items:
        canvas.alpha_composite(text_layer((W, H), items))
    cl = CAP.layer(t)
    if cl is not None:
        canvas.alpha_composite(cl)
    return canvas.convert("RGB")



# ---------------------------------------------------------------- §4 «Графики и модели» (diagrams_v1, только чтение)
import diagrams_v1 as D
from storyboard18 import PUNCH, BOUNCE, UNDERLINE, STAMP, NUMS as _NUMS

# Модели ролика 18 — свои функции по образцу D.eratosthenes (модуль diagrams_v1 только читаем).
def _dot(d, P, r=11, col=D.WHITE):
    d.ellipse(D._s([P[0] - r, P[1] - r, P[0] + r, P[1] + r]), fill=col + (255,))


def _arrow(d, a, b, col=D.RED, w=7):
    d.line(D._s([a, b]), fill=col + (255,), width=w * D.SS)
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    for s_ in (-1, 1):
        q = (b[0] - 26 * math.cos(ang + s_ * 0.5), b[1] - 26 * math.sin(ang + s_ * 0.5))
        d.line(D._s([b, q]), fill=col + (255,), width=w * D.SS)


RIGID_SQ = (170, 560, 330)            # квадрат: левый нижний угол (x, y), сторона
RIGID_TR = (245, 1080, 380)           # треугольник равносторонний: левый конец основания, сторона
RIGID_PHI = 60                        # до какого угла складывается квадрат (стороны не меняются -> ромб)


def rigid_square(t, t0):
    """Вершины квадрата/ромба в момент t: боковые стороны поворачиваются 90° -> 60° (длина та же — ромб)."""
    x0, yb, a = RIGID_SQ
    phi = 90 - (90 - RIGID_PHI) * D._p(t, t0 + 1.0, 0.7)
    dx, dy = a * math.cos(math.radians(phi)), a * math.sin(math.radians(phi))
    return [(x0, yb), (x0 + a, yb), (x0 + a + dx, yb - dy), (x0 + dx, yb - dy)], phi


def rigid_triangle():
    x0, yb, a = RIGID_TR
    return [(x0, yb), (x0 + a, yb), (x0 + a / 2, yb - a * math.sqrt(3) / 2)]


def rigid(t, t0):
    """«Квадрат можно сплющить в ромб, треугольник держит форму»: рамки на шарнирах (точки в вершинах).
    0.0 квадрат; 0.3 треугольник; 0.9 толчок вбок по верху квадрата — 1.0…1.7 он складывается в ромб, угол 90°→60°
    (подпись — текущее значение); 2.0 такой же толчок в вершину треугольника — он не двигается; 2.45 контур бирюзой."""
    im, d = D._canvas()
    P, phi = rigid_square(t, t0)
    p = D._p(t, t0, 0.5)
    if p > 0:
        D._polyline_part(d, P + [P[0]], p, D.WHITE + (240,), 6)
        if p >= 1.0:
            for Q in P:
                _dot(d, Q)
            al = D._p(t, t0 + 0.5, 0.3)                           # угол у левого нижнего шарнира
            d.line(D._s(D._arc_pts(P[0], 62, -phi, 0, 30)), fill=D.BLUE + (int(255 * al),), width=5 * D.SS)
            m = math.radians(phi / 2)
            D._text(d, (P[0][0] + 118 * math.cos(m), P[0][1] - 118 * math.sin(m)), f"{int(round(phi))}°", 40,
                    fill=D.BLUE, alpha=al)
    a = D._p(t, t0 + 0.9, 0.2)                                    # толчок по верхней стороне
    if a > 0 and t < t0 + 2.0:
        y = P[3][1] - 55
        _arrow(d, (P[3][0] + 20, y), (P[3][0] + 20 + 180 * a, y))
    T = rigid_triangle()
    p = D._p(t, t0 + 0.3, 0.5)
    if p > 0:
        col = D.TEAL if t >= t0 + 2.45 else D.WHITE
        D._polyline_part(d, T + [T[0]], p, col + (240,), 6)
        if p >= 1.0:
            for Q in T:
                _dot(d, Q)
    a = D._p(t, t0 + 2.0, 0.2)                                    # толчок в вершину — треугольник стоит
    if a > 0:
        push = 14 * math.sin(math.pi * min(1.0, max(0.0, (t - t0 - 2.2) / 0.3)))
        ax, ay = T[2]
        _arrow(d, (ax - 210, ay), (ax - 210 + (185 + push) * a, ay))
    return D._done(im)


PY_A, PY_B, PY_C = (125, 700), (685, 700), (685, 280)      # катеты 560 = 4·140 и 420 = 3·140, гипотенуза 700 = 5·140


def pythagoras(t, t0):
    """Школьная геометрия на одном чертеже: прямоугольный треугольник ABC (∠B = 90°), катеты 3 и 4, гипотенуза 5.
    0.0 треугольник; 0.4 вершины A, B, C; 0.6 прямой угол; 1.1 длины сторон; 1.7 угол A (≈36,87°);
    2.3 sin A = BC/AC = 3/5; 2.9 3² + 4² = 5² (9 + 16 = 25)."""
    im, d = D._canvas()
    A, B, C = PY_A, PY_B, PY_C
    p = D._p(t, t0, 0.6)
    if p > 0:
        D._polyline_part(d, [A, B, C, A], p, D.WHITE + (240,), 6)
    al = D._p(t, t0 + 0.4, 0.3)
    for s_, xy in (("A", (A[0] - 45, A[1] + 30)), ("B", (B[0] + 45, B[1] + 30)), ("C", (C[0] + 45, C[1] - 25))):
        D._text(d, xy, s_, 40, alpha=al)
    al = D._p(t, t0 + 0.6, 0.25)
    if al > 0:
        k = 36
        d.line(D._s([(B[0] - k, B[1]), (B[0] - k, B[1] - k), (B[0], B[1] - k)]), fill=D.WHITE + (int(230 * al),),
               width=4 * D.SS)
    al = D._p(t, t0 + 1.1, 0.3)
    mid = ((A[0] + C[0]) / 2, (A[1] + C[1]) / 2)
    for s_, xy in (("4", ((A[0] + B[0]) / 2, A[1] + 50)), ("3", (B[0] + 50, (B[1] + C[1]) / 2)),
                   ("5", (mid[0] - 0.6 * 55, mid[1] - 0.8 * 55))):
        D._text(d, xy, s_, 46, alpha=al)
    al = D._p(t, t0 + 1.7, 0.35)
    if al > 0:
        ang = math.degrees(math.atan2(C[1] - A[1], C[0] - A[0]))   # −36.87°
        d.line(D._s(D._arc_pts(A, 95, ang * al, 0, 30)), fill=D.BLUE + (255,), width=6 * D.SS)
    D._text(d, (435, 880), "sin A = 3/5", 56, fill=D.WHITE, alpha=D._p(t, t0 + 2.3, 0.3))
    D._text(d, (435, 1010), "3² + 4² = 5²", 66, fill=D.BLUE, alpha=D._p(t, t0 + 2.9, 0.3))
    return D._done(im)


MODELS = {"rigid": rigid, "pythagoras": pythagoras}


def model_layer(t, t0, fn):
    return MODELS[fn](t, t0)


# ---------------------------------------------------------------- §4 «Анимации-акценты» (как anim13.py)
_num_item0 = num_item


def num_item(t, t0, text, xy, size, blue=False, max_w=None):          # noqa: F811 — счётчик 0→N
    for s0, prm in _NUMS.items():
        if prm.get("count") and abs(t0 - (s0 + 0.05)) < 1e-6:
            digits = "".join(ch for ch in text if ch.isdigit())
            p = min(1.0, max(0.0, (t - s0 - 0.05) / 0.55))
            v = int(round(int(digits) * ease_out(p)))
            size = min(size, int(size * max_w / wide(size).getlength(text))) if max_w else size
            items = _num_item0(t, t0, text.replace(digits, str(v), 1), xy, size, blue, None)
            for it in items:
                it.pop("reveal", None)
            return items
    return _num_item0(t, t0, text, xy, size, blue, max_w)


_zoom_at0 = zoom_at


def zoom_at(i, t):                                                     # noqa: F811 — панч-зум
    z = _zoom_at0(i, t)
    for tp, up, down, k in PUNCH:
        if tp <= t < tp + up:
            z *= 1 + k * ease_out((t - tp) / up)
        elif tp + up <= t < tp + up + down:
            z *= 1 + k * (1 - ease_out((t - tp - up) / down))
    return z


import captions as _C
from PIL import ImageDraw as _Draw, ImageFilter as _Filter


def _affine(lay, scale, angle, center, dx=0.0, dy=0.0):
    if abs(scale - 1) < 1e-3 and abs(angle) < 1e-3 and not dx and not dy:
        return lay
    cx, cy = center
    a = math.radians(angle)
    ca, sa = math.cos(a) / scale, math.sin(a) / scale
    coef = (ca, sa, cx - ca * (cx + dx) - sa * (cy + dy), -sa, ca, cy + sa * (cx + dx) - ca * (cy + dy))
    return lay.transform(lay.size, Image.AFFINE, coef, resample=Image.BICUBIC)


def caption_layer(t):
    i = CAP._active(t)
    if i is None:
        return None
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for it in CAP.lay[i]:
        lt = t - it["t_word"]
        if lt < 0:
            continue
        lay = _C.shadowed_layer([{k: v for k, v in it.items() if k != "t_word"}])
        b = it["font"].getbbox(it["text"], anchor="ls")
        cx, cy = it["xy"][0] + (b[0] + b[2]) / 2, it["xy"][1] + (b[1] + b[3]) / 2
        if it["text"] in STAMP:                                          # штамп
            p = min(1.0, lt / 0.12)
            sh = 0.0
            if 0.12 <= lt < 0.27:
                sh = 3 * math.sin((lt - 0.12) / 0.15 * 4 * math.pi) * (1 - (lt - 0.12) / 0.15)
            lay = _affine(lay, 1.8 - 0.8 * ease_out(p), -6 * (1 - ease_out(p)), (cx, cy), dx=sh)
            if p < 1:
                lay.putalpha(lay.split()[3].point(lambda v: int(v * min(1, 0.4 + p))))
        else:
            p = min(1.0, lt / _C.POP_DUR)
            if p < 1.0:                                                  # штатное всплытие v3
                e = ease_out(p)
                lay = lay.transform(lay.size, Image.AFFINE, (1, 0, 0, 0, 1, -int(round(_C.POP_DY * (1 - e)))))
                r = _C.POP_BLUR * (1 - e)
                if r > 0.3:
                    lay = lay.filter(_Filter.GaussianBlur(r))
                lay = lay.copy()
                lay.putalpha(lay.split()[3].point(lambda v: int(v * e)))
            elif it["text"] in BOUNCE and lt < _C.POP_DUR + 0.30:        # прыжок 22px без масштаба
                q = (lt - _C.POP_DUR) / 0.30
                lay = _affine(lay, 1.0, 0, (cx, cy), dy=-22 * math.sin(math.pi * q))
        out.alpha_composite(lay)
        if it["text"] in UNDERLINE and lt >= _C.POP_DUR:                 # маркер
            q = min(1.0, (lt - _C.POP_DUR) / 0.25)
            x0, x1 = it["xy"][0] + b[0] - 6, it["xy"][0] + b[2] + 6
            y = it["xy"][1] + 16
            xs = np.linspace(x0, x0 + (x1 - x0) * ease_out(q), 40)
            ys = y + 3 * np.sin((xs - x0) / 38) - 4 * (xs - x0) / (x1 - x0)
            dr = _Draw.Draw(out)
            pts = list(zip(xs, ys))
            dr.line([(x + 3, yy + 4) for x, yy in pts], fill=(0, 0, 0, 150), width=9, joint="curve")
            dr.line(pts, fill=it["fill"] + (255,), width=9, joint="curve")
            for x, yy in (pts[0], pts[-1]):
                dr.ellipse((x - 4.5, yy - 4.5, x + 4.5, yy + 4.5), fill=it["fill"] + (255,))
    return out


CAP.layer = caption_layer

def main():
    src = Sources()
    tmp = f"{TMPD}/_video_{VIDEO_NUM}.part.mp4"
    fin = VID
    ff = subprocess.Popen(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", tmp],
        stdin=subprocess.PIPE)
    for f in range(NF):
        ff.stdin.write(frame(src, f).tobytes())
        if f % 150 == 0:
            print(f"  кадр {f}/{NF}  ({f / FPS:5.1f}s)", flush=True)
    ff.stdin.close(); ff.wait()
    os.replace(tmp, fin)
    print("видео:", fin)


def snaps(ts):
    src = Sources()
    for t in ts:
        f = int(round(float(t) * FPS))
        frame(src, f).save(f"{TMPD}/_snap18_{float(t):05.2f}.png")
    print("кадры:", len(ts))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "snap":
        snaps(sys.argv[2:])
    else:
        main()
