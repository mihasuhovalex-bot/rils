"""Ролик 18, версия «мультик» (15.2) — без лица, только голос; всё на экране — анимация (твоё, 2026-09-30:
«сделаем без видео — только голос — все анимации на тебе, прям чуть ли не мультик, очень красиво»).

Звук — тот же голос ролика 18 (voicefx_v7, выбор автора для офиса) и та же музыка (song3 с 0:50) — sfx18m.py.
Субтитры v3 и акценты (пружинка «отменить», маркер «наизусть», штамп «пробное») — как в render18 (зона «графика»,
базовая линия y 1500). Весь рисунок — только выше y 1370 (ниже — субтитры), проверка — qa18m.py.
Стиль бренда: чёрный фон + сетка «тетрадь», белые контуры, синий #5B7CFF / бирюза / красный, солнце — жёлтый,
шрифт Unbounded (в нём нет греческих букв — только латиница, «²», «°», «×»). Математика буквальная:
ромб — те же стороны, угол подписан тем, что нарисован; 3-4-5 с прямым углом; 1 200 × 1,5 = 1 800 (на экране
ошибка «180» — это и есть «ошибка в расчёте»); транспортир — подпись = нарисованный угол.

С 15.3 (твоё, 2026-09-30: «добавлю фотки мои, попробуй их запихнуть… чуть человечности») — фото автора как стикеры:
вырезанная фигура (rembg, videos/18/photos/*_cut.png) с белой обводкой и тенью — в начале, у ошибки в расчёте, у доски
и в финале; карточка-полароид в сцене с поездом; лицо автора — аватарка комментария.

  python cartoon18.py                 — рендер немого видео -> assets/18/_cartoon_18.mp4
  python cartoon18.py snap t1 t2 ...  — отдельные кадры -> assets/18/_cart18_<t>.png
"""
import os, sys, math, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render18 as R            # субтитры v3 + акценты ролика 18 (Captions8, caption_layer)
import captions as C
from style import W, H, FPS, grid_canvas, ease_out
from storyboard18 import CAPS, DUR

BUILD = os.path.dirname(os.path.abspath(__file__))
TMPD = f"{BUILD}/assets/18"
VID = f"{TMPD}/_cartoon_18p.mp4"          # 15.3 (с фото); 15.2 — _cartoon_18.mp4
PHOTO_DIR = f"{BUILD}/../videos/18/photos"
NF = int(round(DUR * FPS))
SS = 2
ART_MAX_Y = 1370                # рисунок только выше (субтитры: базовая линия 1500, верх 2-строчной фразы ≈ 1378)

WHITE = (255, 255, 255); BLUE = (91, 124, 255); TEAL = (45, 225, 194); RED = (255, 59, 48)
SUN = (255, 214, 90); INK = (24, 24, 34); SKIN = (255, 206, 165); GREY = (150, 152, 165)
DARK = (40, 44, 62); HAIR = (110, 72, 44); CHALK = (236, 236, 226); CHALK_Y = (255, 228, 120)

SCENES = [(0.00, 4.25, "bridge"), (4.25, 8.55, "hero"), (8.55, 12.15, "rigid"), (12.15, 16.17, "train"),
          (16.17, 22.12, "engineer"), (22.12, 24.86, "weather"), (24.86, 28.00, "undo"),
          (28.00, 31.77, "master"), (31.77, 37.58, "board"), (37.58, 40.70, "forget"),
          (40.70, 44.23, "kid"), (44.23, DUR, "cta")]
SHOTS_M = [(a, b, "scene", {}) for a, b, _ in SCENES]     # для субтитров: всё — зона «графика» (y 1500)

CAPM = R.Captions8(CAPS, SHOTS_M, DUR, f"{BUILD}/../videos/18/words_cap.json")
R.CAP = CAPM                     # caption_layer render18 берёт субтитры из R.CAP
CAPM.layer = R.caption_layer


# ---------------------------------------------------------------- время и геометрия
def cl(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def pp(t, t0, d):
    return cl((t - t0) / d)


def eo(t, t0, d):
    return ease_out(pp(t, t0, d))


def back(t, t0, d, k=1.9):
    """ease-out с перелётом (пружинка появления)."""
    p = pp(t, t0, d)
    if p <= 0:
        return 0.0
    q = p - 1
    return 1 + (k + 1) * q ** 3 + k * q ** 2


def lerp(a, b, u):
    return a + (b - a) * u


def lerp2(p, q, u):
    return (lerp(p[0], q[0], u), lerp(p[1], q[1], u))


def sc(pts, c, k):
    return [(c[0] + (x - c[0]) * k, c[1] + (y - c[1]) * k) for x, y in pts]


def mv(pts, dx, dy):
    return [(x + dx, y + dy) for x, y in pts]


def arcp(c, r, a0, a1, n=40):
    return [(c[0] + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             c[1] + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def part(pts, frac):
    """Ломаная до доли frac своей длины."""
    if frac >= 1:
        return list(pts)
    if frac <= 0 or len(pts) < 2:
        return pts[:1]
    L = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    goal, acc, out = sum(L) * frac, 0.0, [pts[0]]
    for (a, b), l in zip(zip(pts, pts[1:]), L):
        if acc + l >= goal:
            out.append(lerp2(a, b, (goal - acc) / l if l else 0))
            return out
        out.append(b)
        acc += l
    return out


def tri_pts(c, side, rot=0.0):
    r = side / math.sqrt(3)
    return [(c[0] + r * math.cos(math.radians(a + rot)), c[1] + r * math.sin(math.radians(a + rot)))
            for a in (-90, 30, 150)]


def ngon(c, r, n, rot=-90):
    return [(c[0] + r * math.cos(math.radians(rot + 360 * k / n)), c[1] + r * math.sin(math.radians(rot + 360 * k / n)))
            for k in range(n)]


def centroid(pts):
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


# ---------------------------------------------------------------- фон и «кисть»
_BG = {}


def bg(t):
    ph = round(t * 0.35, 2)
    if ph not in _BG:
        _BG.clear()
        base = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        base.alpha_composite(grid_canvas(W, H, phase=ph, alpha=int(255 * 0.30)))
        _BG[ph] = base.convert("RGB").resize((W * SS, H * SS), Image.BILINEAR)
    return _BG[ph]


def rgba(col, a):
    base = col[3] if len(col) == 4 else 255
    return tuple(col[:3]) + (int(max(0.0, min(1.0, a)) * base),)


class Pen:
    """Рисование в суперсэмплинге с камерой (zoom вокруг center). qa=True — прозрачный слой (для проверок)."""

    def __init__(self, t, qa=False, zoom=1.0, center=(540, 760)):
        self.qa, self.z, self.c = qa, zoom, center
        if qa:
            self.im = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
            self.d = ImageDraw.Draw(self.im)
        else:
            self.im = bg(t).copy()
            self.d = ImageDraw.Draw(self.im, "RGBA")

    def P(self, p):
        return ((self.c[0] + (p[0] - self.c[0]) * self.z) * SS, (self.c[1] + (p[1] - self.c[1]) * self.z) * SS)

    def w(self, w):
        return max(1, int(round(w * self.z * SS)))

    def line(self, pts, col, w=6, a=1.0, caps=True):
        if a <= 0.01 or len(pts) < 2:
            return
        P = [self.P(p) for p in pts]
        c, ww = rgba(col, a), self.w(w)
        self.d.line(P, fill=c, width=ww, joint="curve")
        if caps:
            r = ww / 2
            for q in (P[0], P[-1]):
                self.d.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], fill=c)

    def poly(self, pts, fill=None, outline=None, w=6, a=1.0, shadow=False):
        if a <= 0.01:
            return
        if shadow:
            self.d.polygon([self.P(p) for p in mv(pts, 9, 11)], fill=(0, 0, 0, int(120 * a)))
        if fill:
            self.d.polygon([self.P(p) for p in pts], fill=rgba(fill, a))
        if outline:
            self.line(list(pts) + [pts[0], pts[1]], outline, w, a, caps=False)

    def circle(self, c, r, fill=None, outline=None, w=6, a=1.0, shadow=False):
        if a <= 0.01 or r <= 0:
            return
        if shadow:
            q = self.P((c[0] + 8, c[1] + 10)); rr = r * self.z * SS
            self.d.ellipse([q[0] - rr, q[1] - rr, q[0] + rr, q[1] + rr], fill=(0, 0, 0, int(120 * a)))
        q, rr = self.P(c), r * self.z * SS
        self.d.ellipse([q[0] - rr, q[1] - rr, q[0] + rr, q[1] + rr], fill=rgba(fill, a) if fill else None,
                       outline=rgba(outline, a) if outline else None, width=self.w(w) if outline else 0)

    def rrect(self, box, r, fill=None, outline=None, w=5, a=1.0, shadow=False):
        if a <= 0.01:
            return
        x0, y0, x1, y1 = box
        if shadow:
            p0, p1 = self.P((x0 + 9, y0 + 11)), self.P((x1 + 9, y1 + 11))
            self.d.rounded_rectangle([p0, p1], radius=r * self.z * SS, fill=(0, 0, 0, int(120 * a)))
        p0, p1 = self.P((x0, y0)), self.P((x1, y1))
        self.d.rounded_rectangle([p0, p1], radius=r * self.z * SS, fill=rgba(fill, a) if fill else None,
                                 outline=rgba(outline, a) if outline else None, width=self.w(w) if outline else 0)

    def arc(self, c, r, a0, a1, col, w=6, a=1.0):
        self.line(arcp(c, r, a0, a1, max(8, int(abs(a1 - a0) / 4))), col, w, a)

    def text(self, xy, s, size, col=WHITE, anchor="mm", a=1.0, shadow=True):
        if a <= 0.01 or not s:
            return
        f = C.wide(max(6, int(size * self.z * SS)))
        q = self.P(xy)
        if shadow:
            self.d.text((q[0] + 3 * SS * self.z, q[1] + 4 * SS * self.z), s, font=f, anchor=anchor,
                        fill=(0, 0, 0, int(150 * a)))
        self.d.text(q, s, font=f, anchor=anchor, fill=rgba(col, a))

    def _comp(self, im, pos):
        if self.qa:
            lay = Image.new("RGBA", self.im.size, (0, 0, 0, 0))
            lay.paste(im, pos, im)
            self.im.alpha_composite(lay)
        else:
            self.im.paste(im, pos, im)

    def paste(self, img, cx, ybot, k=1.0, rot=0.0, a=1.0, shadow=True):
        """Вставить готовую картинку (стикер/полароид, уже в двойном разрешении): низ по центру в (cx, ybot)."""
        if k <= 0.02 or a <= 0.01:
            return
        z = self.z * k
        im = img if abs(z - 1) < 1e-3 else img.resize((max(1, int(img.width * z)), max(1, int(img.height * z))),
                                                      Image.BILINEAR)
        if abs(rot) > 0.2:
            im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
        px, py = self.P((cx, ybot))
        x, y = int(px - im.width / 2), int(py - im.height)
        al = im.split()[3]
        if a < 1:
            al = al.point(lambda v: int(v * a))
        if shadow:
            sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
            sh.putalpha(al.point(lambda v: int(v * 0.45)))
            self._comp(sh, (x + 9 * SS, y + 11 * SS))
        im2 = im.copy()
        im2.putalpha(al)
        self._comp(im2, (x, y))

    def done(self, t):
        y = ART_MAX_Y * SS                          # всё ниже — зона субтитров: вернуть фон
        if self.qa:
            self.im.paste((0, 0, 0, 0), (0, y, W * SS, H * SS))
            return self.im.resize((W, H), Image.LANCZOS)
        self.im.paste(bg(t).crop((0, y, W * SS, H * SS)), (0, y))
        return self.im.resize((W, H), Image.LANCZOS)


# ---------------------------------------------------------------- персонажи и предметы
def face(pn, c, s, mood="happy", t=0.0, look=(0.0, 0.0), a=1.0, wink=False):
    """Мордочка: глаза с бликом, зрачки смотрят в look (−1…1), рот по настроению. s — масштаб (ширина ≈ s)."""
    ex, ey, r = 0.28 * s, -0.10 * s, 0.14 * s
    blink = (t % 3.4) < 0.11
    for k, sx in enumerate((-1, 1)):
        e = (c[0] + sx * ex, c[1] + ey)
        if mood == "dizzy":
            for d0 in (45, 135):
                u = (math.cos(math.radians(d0)) * r * 0.8, math.sin(math.radians(d0)) * r * 0.8)
                pn.line([(e[0] - u[0], e[1] - u[1]), (e[0] + u[0], e[1] + u[1])], INK, 0.07 * s, a)
        elif blink or (wink and sx == 1):
            pn.line([(e[0] - r * 0.8, e[1]), (e[0] + r * 0.8, e[1])], INK, 0.06 * s, a)
        else:
            rr = r * (1.25 if mood == "surprised" else 1.0)
            pn.circle(e, rr, fill=WHITE, a=a)
            pc = (e[0] + look[0] * rr * 0.45, e[1] + look[1] * rr * 0.45)
            pn.circle(pc, rr * 0.52, fill=INK, a=a)
            pn.circle((pc[0] - rr * 0.18, pc[1] - rr * 0.2), rr * 0.16, fill=WHITE, a=a)
        if mood in ("proud", "worried"):
            lift = 1 if mood == "proud" else -1
            y = e[1] - r * 1.5
            pn.line([(e[0] - r, y + sx * lift * r * 0.35), (e[0] + r, y - sx * lift * r * 0.35)], INK, 0.05 * s, a)
    my, mw = c[1] + 0.20 * s, 0.24 * s
    if mood in ("happy", "proud"):
        k = 0.55 if mood == "happy" else 0.35
        pts = [(c[0] + u * mw, my + k * mw * (1 - u * u)) for u in np.linspace(-1, 1, 16)]
        if mood == "proud":
            pts = [(x + 0.04 * s, y - (x - c[0]) * 0.18) for x, y in pts]
        pn.line(pts, INK, 0.06 * s, a)
    elif mood == "surprised":
        pn.circle((c[0], my + 0.04 * s), 0.08 * s, fill=INK, a=a)
    else:                                                        # worried / dizzy — волнистый рот
        pts = [(c[0] + u * mw, my + 0.05 * s * math.sin(u * 3 * math.pi + t * 10 * (mood == "dizzy")))
               for u in np.linspace(-1, 1, 20)]
        pn.line(pts, INK, 0.05 * s, a)


def tri_char(pn, c, side, t, fill=TEAL, mood="happy", look=(0, 0), a=1.0, wink=False, rot=0.0, outline=WHITE):
    pts = tri_pts(c, side, rot)
    pn.poly(pts, fill=fill, outline=outline, w=max(4, side * 0.022), a=a, shadow=True)
    face(pn, (c[0], c[1] + side * 0.05), side * 0.55, mood, t, look, a, wink)
    return pts


def poly_char(pn, pts, t, fill=BLUE, mood="happy", look=(0, 0), a=1.0, s=None, hinges=False):
    pn.poly(pts, fill=fill, outline=WHITE, w=7, a=a, shadow=True)
    cc = centroid(pts)
    s = s or 0.5 * math.dist(pts[0], pts[1])
    face(pn, cc, s, mood, t, look, a)
    if hinges:
        for p in pts:
            pn.circle(p, 13, fill=WHITE, a=a)
            pn.circle(p, 5, fill=INK, a=a)


def arrow(pn, a_, b_, col=RED, w=12, a=1.0, head=34):
    if a <= 0.01:
        return
    ang = math.atan2(b_[1] - a_[1], b_[0] - a_[0])
    bb = (b_[0] - head * 0.5 * math.cos(ang), b_[1] - head * 0.5 * math.sin(ang))
    pn.line([a_, bb], col, w, a)
    tip = [b_, (b_[0] - head * math.cos(ang - 0.45), b_[1] - head * math.sin(ang - 0.45)),
           (b_[0] - head * math.cos(ang + 0.45), b_[1] - head * math.sin(ang + 0.45))]
    pn.poly(tip, fill=col, a=a)


def sparkle(pn, c, r, col=WHITE, a=1.0):
    if r <= 0 or a <= 0.01:
        return
    pts = []
    for k in range(8):
        rr = r if k % 2 == 0 else r * 0.3
        ang = math.radians(-90 + 45 * k)
        pts.append((c[0] + rr * math.cos(ang), c[1] + rr * math.sin(ang)))
    pn.poly(pts, fill=col, a=a)


def check(pn, c, s, col=TEAL, a=1.0, frac=1.0, disc=True):
    if disc:
        pn.circle(c, s, fill=col, a=a, shadow=True)
        col2 = WHITE
    else:
        col2 = col
    pts = [(c[0] - 0.45 * s, c[1] + 0.02 * s), (c[0] - 0.12 * s, c[1] + 0.32 * s), (c[0] + 0.48 * s, c[1] - 0.3 * s)]
    pn.line(part(pts, frac), col2, 0.16 * s, a)


def cross(pn, c, s, col=RED, a=1.0, frac=1.0, w=16):
    pn.line(part([(c[0] - s, c[1] - s), (c[0] + s, c[1] + s)], cl(frac * 2)), col, w, a)
    if frac > 0.5:
        pn.line(part([(c[0] + s, c[1] - s), (c[0] - s, c[1] + s)], cl(frac * 2 - 1)), col, w, a)


def heart(pn, c, s, col=RED, a=1.0):
    pts = []
    for u in np.linspace(0, 2 * math.pi, 60):
        x = 16 * math.sin(u) ** 3
        y = -(13 * math.cos(u) - 5 * math.cos(2 * u) - 2 * math.cos(3 * u) - math.cos(4 * u))
        pts.append((c[0] + x * s / 16, c[1] + y * s / 16))
    pn.poly(pts, fill=col, a=a, shadow=True)


def person(pn, x, yf, hh, t, kind="engineer", arm="idle", mood="happy", look=(0, 0), a=1.0, k=1.0):
    """Человечек: инженер (каска, синяя рубашка) или ребёнок (волосы, бирюзовая футболка). hh — рост, k — масштаб
    появления (растёт от ступней)."""
    if a <= 0.01 or k <= 0.01:
        return
    H_ = hh * k
    shirt = BLUE if kind == "engineer" else TEAL
    bob = 5 * math.sin(t * 3.1) * k
    X = lambda u: x + u * H_
    Y = lambda v: yf - v * H_ + (bob if v > 0.3 else 0)
    for sx in (-1, 1):                                           # ноги
        pn.line([(X(sx * 0.07), Y(0.33)), (X(sx * 0.09), Y(0.02))], DARK, 0.075 * H_, a)
        pn.line([(X(sx * 0.09), Y(0.02)), (X(sx * 0.16), Y(0.02))], DARK, 0.06 * H_, a)
    pn.rrect((X(-0.17), Y(0.64), X(0.17), Y(0.28)), 0.08 * H_, fill=shirt, outline=WHITE, w=4, a=a, shadow=True)
    if kind == "engineer":                                       # светоотражающие полосы жилета
        for v in (0.46, 0.38):
            pn.line([(X(-0.16), Y(v)), (X(0.16), Y(v))], SUN, 0.02 * H_, a * 0.9, caps=False)
    sh_l, sh_r = (X(-0.16), Y(0.58)), (X(0.16), Y(0.58))
    pn.line([sh_l, (X(-0.25), Y(0.38))], shirt, 0.07 * H_, a)
    pn.circle((X(-0.25), Y(0.38)), 0.04 * H_, fill=SKIN, a=a)
    if arm == "point":
        hand = (X(0.44), Y(0.74))
    elif arm == "wave":
        ang = math.radians(-60 + 22 * math.sin(t * 9))
        hand = (sh_r[0] + 0.26 * H_ * math.cos(ang), sh_r[1] + 0.26 * H_ * math.sin(ang))
    elif arm == "up":
        hand = (X(0.30), Y(0.86))
    else:
        hand = (X(0.25), Y(0.38))
    pn.line([sh_r, hand], shirt, 0.07 * H_, a)
    pn.circle(hand, 0.04 * H_, fill=SKIN, a=a)
    hc, hr = (X(0.0), Y(0.79)), 0.155 * H_
    pn.circle(hc, hr, fill=SKIN, outline=WHITE, w=4, a=a, shadow=True)
    if kind == "engineer":                                       # каска
        dome = arcp((hc[0], hc[1] - hr * 0.25), hr * 1.08, 180, 360, 30)
        pn.poly(dome, fill=SUN, outline=WHITE, w=4, a=a)
        pn.line([(hc[0] - hr * 1.3, hc[1] - hr * 0.25), (hc[0] + hr * 1.3, hc[1] - hr * 0.25)], SUN, 0.05 * H_, a)
        face(pn, (hc[0], hc[1] + hr * 0.25), hr * 1.25, mood, t, look, a)
    else:                                                        # волосы
        hair = arcp((hc[0], hc[1] - hr * 0.1), hr * 1.06, 190, 350, 30)
        pn.poly(hair + [(hc[0], hc[1] - hr * 0.55)], fill=HAIR, a=a)
        face(pn, (hc[0], hc[1] + hr * 0.18), hr * 1.3, mood, t, look, a)
    return hc, hr


def truss(x0, x1, yd, h, n):
    bw = (x1 - x0) / n
    B = [(x0 + i * bw, yd) for i in range(n + 1)]
    T = [(x0 + (i + 0.5) * bw, yd - h) for i in range(n)]
    zig = []
    for i in range(n):
        zig += [B[i], T[i]]
    zig.append(B[n])
    ups = [(B[i], T[i], B[i + 1]) for i in range(n)]
    downs = [(T[i], B[i + 1], T[i + 1]) for i in range(n - 1)]
    return B, T, zig, ups, downs


def river(pn, y0, y1, t, a=1.0):
    pn.rrect((-20, y0, W + 20, y1), 0, fill=(20, 34, 84), a=0.9 * a)
    for k in range(4):
        y = y0 + 34 + k * (y1 - y0 - 50) / 3.2
        pts = [(x, y + 9 * math.sin(x / 70 + t * 2.4 + k * 1.3)) for x in range(-40, W + 60, 24)]
        pn.line(pts, (110, 145, 255), 4, a * 0.55)


def piers(pn, xs, yd, ybot, a=1.0):
    for x in xs:
        pn.rrect((x - 36, yd + 20, x + 36, ybot), 8, fill=(56, 60, 82), outline=WHITE, w=4, a=a)


def bridge(pn, x0, x1, yd, h, n, frac=1.0, lit=None, a=1.0, col=WHITE, w=9, deck=True, members=True):
    B, T, zig, ups, downs = truss(x0, x1, yd, h, n)
    if deck:
        pn.rrect((x0 - 16, yd - 4, x1 + 16, yd + 22), 6, fill=DARK, outline=col, w=4, a=a * cl(frac * 4))
    if not members:
        return B, T
    if lit:
        for i, tr in enumerate(ups):
            v = lit(i, "up")
            if v > 0:
                pn.poly(list(tr), fill=TEAL, a=a * 0.55 * v)
        for i, tr in enumerate(downs):
            v = lit(i, "down")
            if v > 0:
                pn.poly(list(tr), fill=TEAL, a=a * 0.35 * v)
    paths = [zig, T]
    L = [sum(math.dist(p, q) for p, q in zip(pp_, pp_[1:])) for pp_ in paths]
    goal = frac * sum(L)
    for pth, l in zip(paths, L):
        f = cl(goal / l) if l else 1
        if f > 0:
            pn.line(part(pth, f), col, w, a)
        goal -= l
    if frac >= 1:
        for p in B + T:
            pn.circle(p, w * 0.9, fill=col, a=a)
    return B, T


def train(pn, xf, yd, t, nw=5, a=1.0):
    """Поезд едет вправо, xf — нос локомотива. Колёса крутятся по пройденному пути."""
    y_b = yd - 30
    spin = xf / 15.0
    cars = [("loco", xf - 210, xf)]
    x = xf - 224
    for k in range(nw):
        cars.append(("wag", x - 150, x))
        x -= 164
    for kind, a0, a1 in cars:
        if a1 < -60 or a0 > W + 60:
            continue
        if kind == "loco":
            body = [(a0, y_b), (a0, y_b - 118), (a1 - 58, y_b - 118), (a1, y_b - 60), (a1, y_b)]
            pn.poly(body, fill=RED, outline=WHITE, w=5, a=a, shadow=True)
            pn.rrect((a1 - 118, y_b - 104, a1 - 66, y_b - 66), 8, fill=(190, 225, 255), a=a)
            pn.line([(a0 + 20, y_b - 40), (a1 - 20, y_b - 40)], WHITE, 5, a * 0.8)
        else:
            pn.rrect((a0, y_b - 86, a1, y_b), 10, fill=(70, 92, 170), outline=WHITE, w=5, a=a, shadow=True)
            bumps = [(a0 + 12 + i * 21, y_b - 86 - 10 * abs(math.sin(i * 1.7))) for i in range(7)]
            pn.poly([(a0 + 6, y_b - 84)] + bumps + [(a1 - 6, y_b - 84)], fill=(35, 38, 52), a=a)
        for wx in ((a0 + 32, a1 - 32) if kind == "wag" else (a0 + 36, a0 + 96, a1 - 70)):
            c = (wx, yd - 16)
            pn.circle(c, 15, fill=INK, outline=WHITE, w=3, a=a)
            pn.line([(c[0] - 11 * math.cos(spin), c[1] - 11 * math.sin(spin)),
                     (c[0] + 11 * math.cos(spin), c[1] + 11 * math.sin(spin))], WHITE, 3, a)
    return [(a0 + a1) / 2 for _, a0, a1 in cars]


def snowflake(pn, c, r, rot, a=1.0, col=(200, 225, 255)):
    for k in range(6):
        ang = math.radians(rot + 60 * k)
        tip = (c[0] + r * math.cos(ang), c[1] + r * math.sin(ang))
        pn.line([c, tip], col, r * 0.12, a)
        for u in (0.45, 0.72):
            m = lerp2(c, tip, u)
            for s_ in (-1, 1):
                b = math.radians(rot + 60 * k + s_ * 42)
                pn.line([m, (m[0] + r * 0.26 * math.cos(b), m[1] + r * 0.26 * math.sin(b))], col, r * 0.09, a)


def sun(pn, c, r, rot, a=1.0):
    for k in range(12):
        ang = math.radians(rot + 30 * k)
        pn.line([(c[0] + r * 1.25 * math.cos(ang), c[1] + r * 1.25 * math.sin(ang)),
                 (c[0] + r * 1.6 * math.cos(ang), c[1] + r * 1.6 * math.sin(ang))], SUN, r * 0.13, a)
    pn.circle(c, r, fill=SUN, a=a, shadow=True)
    face(pn, (c[0], c[1] + r * 0.08), r * 1.1, "happy", 0.5, (0, 0), a)


def wind(pn, c, s, t, a=1.0):
    for k, (dy, ln) in enumerate(((-0.5, 1.5), (0.05, 1.9), (0.6, 1.3))):
        x0 = c[0] - s * ln / 2 + 12 * math.sin(t * 4 + k)
        y = c[1] + dy * s
        pts = [(x0 + u * s * ln, y + 6 * math.sin(u * 6 + t * 5)) for u in np.linspace(0, 1, 16)]
        curl = arcp((pts[-1][0], pts[-1][1] - s * 0.18), s * 0.18, 90, -200, 16)
        pn.line(pts + curl, WHITE, s * 0.085, a)


def cursor(pn, p, s=1.0, a=1.0):
    pts = [(0, 0), (0, 58), (15, 45), (26, 68), (37, 63), (26, 41), (46, 41)]
    pn.poly([(p[0] + x * s, p[1] + y * s) for x, y in pts], fill=WHITE, outline=INK, w=4, a=a, shadow=True)


def bulb(pn, c, r, on, a=1.0):
    if on > 0:
        for k in range(10):
            ang = math.radians(-90 + 36 * k)
            pn.line([(c[0] + r * 1.35 * math.cos(ang), c[1] + r * 1.35 * math.sin(ang)),
                     (c[0] + r * (1.35 + 0.5 * on) * math.cos(ang), c[1] + r * (1.35 + 0.5 * on) * math.sin(ang))],
                    SUN, r * 0.12, a * on)
    glass = tuple(int(lerp(g, s_, on)) for g, s_ in zip((90, 94, 110), SUN))
    pn.circle(c, r, fill=glass, outline=WHITE, w=5, a=a, shadow=True)
    pn.rrect((c[0] - r * 0.45, c[1] + r * 0.85, c[0] + r * 0.45, c[1] + r * 1.35), 6, fill=GREY, outline=WHITE,
             w=3, a=a)
    if on > 0.5:
        pn.line([(c[0] - r * 0.35, c[1] - r * 0.1), (c[0] - r * 0.1, c[1] - r * 0.45)], WHITE, r * 0.12, a)


def chalk(pn, pts, col=CHALK, w=7, a=1.0):
    pn.line(pts, col, w, a * 0.92)
    jit = [(x + 1.6 * math.sin(i * 2.3), y + 1.6 * math.cos(i * 1.7)) for i, (x, y) in enumerate(pts)]
    pn.line(jit, col, max(2, w * 0.45), a * 0.35)


def card(pn, c, text, k=1.0, a=1.0, w_=270, h_=92, size=34):
    if k <= 0.01 or a <= 0.01:
        return
    x, y = c
    pn.rrect((x - w_ / 2 * k, y - h_ / 2 * k, x + w_ / 2 * k, y + h_ / 2 * k), 18 * k, fill=WHITE, a=a, shadow=True)
    pn.text((x, y + 2 * k), text, size * k, INK, a=a, shadow=False)


# ---------------------------------------------------------------- фото автора: стикеры, полароид, аватарка
_STK = {}


def sticker(name, h, crop=(0, 0, 1, 1)):
    """Вырезанная фигура высотой h (px кадра) с белой обводкой — «наклейка». Кэш."""
    key = ("s", name, int(h), crop)
    if key not in _STK:
        c = Image.open(f"{PHOTO_DIR}/{name}_cut.png").convert("RGBA")
        w0, h0 = c.size
        c = c.crop((int(crop[0] * w0), int(crop[1] * h0), int(crop[2] * w0), int(crop[3] * h0)))
        hh = int(h * SS)
        c = c.resize((max(1, int(c.width * hh / c.height)), hh), Image.LANCZOS)
        pad = 14 * SS
        base = Image.new("RGBA", (c.width + 2 * pad, c.height + 2 * pad), (0, 0, 0, 0))
        base.alpha_composite(c, (pad, pad))
        edge = base.split()[3].filter(ImageFilter.MaxFilter(10 * SS + 1))
        white = Image.new("RGBA", base.size, (255, 255, 255, 0))
        white.putalpha(edge)
        white.alpha_composite(base)
        _STK[key] = white
    return _STK[key]


def polaroid(name, w, crop):
    """Карточка-полароид шириной w: фото (crop — доли исходника) в белой рамке."""
    key = ("p", name, int(w), crop)
    if key not in _STK:
        im = ImageOps.exif_transpose(Image.open(f"{PHOTO_DIR}/{name}.jpeg")).convert("RGB")
        w0, h0 = im.size
        im = im.crop((int(crop[0] * w0), int(crop[1] * h0), int(crop[2] * w0), int(crop[3] * h0)))
        m, mb = 14 * SS, 50 * SS
        iw = int(w * SS) - 2 * m
        im = im.resize((iw, int(im.height * iw / im.width)), Image.LANCZOS)
        cardi = Image.new("RGBA", (iw + 2 * m, im.height + m + mb), (250, 250, 246, 255))
        cardi.paste(im, (m, m))
        _STK[key] = cardi
    return _STK[key]


def avatar(name, r, box):
    """Круглая аватарка радиуса r из вырезанного фото (box — квадрат в пикселях файла *_cut.png) на бирюзовом."""
    key = ("a", name, int(r), box)
    if key not in _STK:
        c = Image.open(f"{PHOTO_DIR}/{name}_cut.png").convert("RGBA").crop(box)
        d_ = int(2 * r * SS)
        c = c.resize((d_, d_), Image.LANCZOS)
        disc = Image.new("RGBA", (d_, d_), TEAL + (255,))
        disc.alpha_composite(c)
        mask = Image.new("L", (d_ * 2, d_ * 2), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, d_ * 2 - 1, d_ * 2 - 1), fill=255)
        disc.putalpha(mask.resize((d_, d_), Image.LANCZOS))
        _STK[key] = disc
    return _STK[key]


def cloud(pn, c, s, a=1.0, col=(44, 49, 70)):
    for dx, dy, r in ((-0.55, 0.12, 0.42), (-0.1, -0.12, 0.58), (0.45, 0.05, 0.46), (0.05, 0.22, 0.4)):
        pn.circle((c[0] + dx * s, c[1] + dy * s), r * s, fill=col, a=a)
    pn.rrect((c[0] - 0.85 * s, c[1] + 0.05 * s, c[0] + 0.85 * s, c[1] + 0.5 * s), 0.22 * s, fill=col, a=a)


def world(pn, t, horizon, a=1.0, sun_=True, birds=True):
    """Фон «улицы»: облака, солнце, птицы, холмы дальнего берега (тёмные, чтобы не спорить с главным)."""
    for k, (x0, y, s) in enumerate(((120, 250, 110), (640, 190, 80), (980, 330, 95))):
        x = (x0 + t * (10 + 4 * k)) % 1400 - 160
        cloud(pn, (x, y), s, a)
    if sun_:
        c = (880, 300)
        for k in range(10):
            ang = math.radians(t * 12 + 36 * k)
            pn.line([(c[0] + 72 * math.cos(ang), c[1] + 72 * math.sin(ang)),
                     (c[0] + 95 * math.cos(ang), c[1] + 95 * math.sin(ang))], SUN, 8, a * 0.8)
        pn.circle(c, 56, fill=SUN, a=a)
    if birds:
        for k in range(3):
            bx = (200 + 150 * k + t * 55) % 1300 - 110
            by = 420 + 40 * k + 10 * math.sin(t * 2 + k)
            fl = 12 * math.sin(t * 9 + k)
            pn.line([(bx - 22, by - fl), (bx, by), (bx + 22, by - fl)], (200, 205, 220), 4, a * 0.8)
    hy = lambda x: horizon - 70 - 55 * math.sin(x / 190 + 1.3) - 30 * math.sin(x / 83)
    hill = [(-20, horizon)] + [(x, hy(x)) for x in range(-20, W + 40, 30)] + [(W + 20, horizon)]
    pn.poly(hill, fill=(30, 36, 56), a=a)
    for k in range(9):                                              # домики-силуэты на холмах
        x = 60 + k * 118
        hh = 40 + 30 * ((k * 7) % 3)
        pn.rrect((x - 22, hy(x) - hh, x + 22, hy(x) + 8), 4, fill=(38, 45, 70), a=a)


def dust(pn, t):
    """Лёгкие частицы на всех сценах — «живой» кадр."""
    cols = (TEAL, BLUE, WHITE)
    for i in range(14):
        x = (i * 173 + 30 * math.sin(t * 0.6 + i)) % W
        y = 1330 - ((i * 211 + t * 28) % 1180)
        pn.circle((x, y), 3 + (i % 3) * 1.5, fill=cols[i % 3], a=0.22)


# ---------------------------------------------------------------- сцены (t — абсолютное время ролика)
BR = dict(x0=50, x1=1030, yd=960, h=300, n=7)        # мост первой сцены: центральный «вверх»-треугольник — x 540
_B1 = truss(BR["x0"], BR["x1"], BR["yd"], BR["h"], BR["n"])
HERO0 = centroid(_B1[3][3])                          # центроид треугольника, в который въезжает камера
HERO_ZOOM = 2.4
HERO_SIDE0 = math.dist(_B1[3][3][0], _B1[3][3][2]) * HERO_ZOOM


def cam_bridge(t):
    return 1 + (HERO_ZOOM - 1) * eo(t, 3.72, 0.53), HERO0


def sc_bridge(pn, t):
    """0.00–4.25 «Любой железнодорожный мост состоит из треугольников. И это не дизайн»."""
    world(pn, t, 1110, eo(t, 0.0, 0.5))
    river(pn, 1100, 1340, t, eo(t, 0.0, 0.4))
    piers(pn, (300, 780), BR["yd"], 1170, eo(t, 0.05, 0.4))
    order = [3, 2, 4, 1, 5, 0, 6]                                  # вспыхивают от центра к краям
    lit = lambda i, kind: eo(t, 2.12 + 0.07 * (order.index(i) if kind == "up" else order.index(min(i, 6)) + 0.5),
                             0.25) if t >= 2.12 else 0.0
    bridge(pn, frac=eo(t, 0.15, 1.5), lit=lit, **BR)
    B, T = _B1[0], _B1[1]
    for k, j in enumerate((1, 3, 5)):                              # «украшения» — и красный крест: «не дизайн»
        base = (T[j][0], T[j][1] - 62)
        s = back(t, 3.11 + 0.1 * k, 0.35)
        fall = pp(t, 3.78, 0.45)
        if s <= 0 or fall >= 1:
            continue
        cc = (base[0], base[1] + 520 * fall ** 2)
        spiral = [(cc[0] + 34 * s * (1 - u * 0.8) * math.cos(u * 9.5), cc[1] + 34 * s * (1 - u * 0.8) * math.sin(u * 9.5))
                  for u in np.linspace(0, 1, 40)]
        pn.line(spiral, (255, 150, 200), 6, 1 - fall)
        sparkle(pn, (cc[0] + 40 * s, cc[1] - 30 * s), 14 * s, (255, 150, 200), 1 - fall)
    if t >= 3.62:
        cross(pn, (T[3][0], T[3][1] - 62), 58, RED, 1 - pp(t, 3.95, 0.25), eo(t, 3.62, 0.18))
    if t < 3.3:                                                    # автор: крупно в первую полсекунды → в угол
        u = eo(t, 0.62, 0.5)
        out = pp(t, 2.95, 0.3)
        pn.paste(sticker("IMG_8876", 760), lerp(540, 850, u), 1395 + 520 * out ** 2,
                 k=back(t, 0.0, 0.3) * lerp(1.0, 0.53, u))
    if t >= 3.5:                                                   # центральный треугольник «оживает» перед сменой
        tr = _B1[3][3]
        pn.poly(list(tr), fill=TEAL, outline=WHITE, w=9, a=eo(t, 3.8, 0.3))


def sc_hero(pn, t):
    """4.25–8.55 «Треугольник — единственный многоугольник, который нельзя деформировать, не сломав сторону»."""
    u = eo(t, 4.25, 0.5)
    c = lerp2(HERO0, (540, 610), u)
    side = lerp(HERO_SIDE0, 560, u)
    c = (c[0], c[1] + 7 * math.sin(t * 3))
    mood = "happy"
    if 6.30 <= t < 7.45:
        mood = "proud"
    if 7.64 <= t < 8.25:
        mood = "worried"
    look = (0, 0)
    if 5.4 <= t < 6.2:
        look = (0, 1)
    pts = tri_pts(c, side)
    pn.poly(pts, fill=TEAL, outline=WHITE, w=10, shadow=True)
    if t < 4.41:
        for sx in (-1, 1):
            e = (c[0] + sx * 0.28 * side * 0.55, c[1] + side * 0.05 - 0.10 * side * 0.55)
            pn.line([(e[0] - 18, e[1]), (e[0] + 18, e[1])], INK, 5)
    else:
        face(pn, (c[0], c[1] + side * 0.05), side * 0.55 * (0.9 + 0.1 * back(t, 4.41, 0.3)), mood, t, look)
    for k in range(4):                                             # «единственный» — искры
        ang = math.radians(-60 + 80 * k)
        a = eo(t, 5.10 + 0.08 * k, 0.2) * (1 - pp(t, 6.0, 0.4))
        r = 30 * (0.7 + 0.3 * math.sin(t * 12 + k))
        sparkle(pn, (c[0] + 400 * math.cos(ang), c[1] + 340 * math.sin(ang)), r * 1.3, SUN, a)
    # «многоугольник» — другие фигуры; на «деформировать» они гнутся, треугольник — нет
    env = eo(t, 6.54, 0.25) * (1 - pp(t, 7.9, 0.4))
    shear = 0.42 * env * math.sin(2 * math.pi * 2.2 * (t - 6.54))
    for k, (x, n) in enumerate(((240, 4), (540, 5), (840, 6))):
        s = back(t, 5.40 + 0.12 * k, 0.4)
        if s <= 0:
            continue
        cc = (x, 1205)
        g = ngon(cc, 105 * s, n, -90 if n != 4 else -45)
        g = [(px + shear * (cc[1] - py) * (1 if k != 1 else -1), py) for px, py in g]
        poly_char(pn, g, t + k, fill=(68, 72, 96), mood="dizzy" if env > 0.3 else "happy", s=120 * s)
    if 6.30 <= t < 7.45:                                           # толкают — не поддаётся
        a = eo(t, 6.30, 0.2) * (1 - pp(t, 7.3, 0.15))
        push = 16 * abs(math.sin((t - 6.3) * 7))
        L, Rr = pts[2], pts[1]
        arrow(pn, (L[0] - 170 + push, L[1] - 50), (L[0] - 25 + push, L[1] - 50), RED, 15, a)
        arrow(pn, (Rr[0] + 170 - push, Rr[1] - 50), (Rr[0] + 25 - push, Rr[1] - 50), RED, 15, a)
    if 7.64 <= t < 8.4:                                            # «не сломав сторону» — трещина на стороне
        a = eo(t, 7.64, 0.12) * (1 - pp(t, 8.2, 0.2))
        p0, p1 = pts[0], pts[1]
        pn.line([p0, p1], RED, 12, a)
        m = lerp2(p0, p1, 0.5)
        nx, ny = (p1[1] - p0[1]) / side, -(p1[0] - p0[0]) / side
        zz = [(m[0] + nx * 40 * (-1 + 2 * i / 5) + (8 if i % 2 else -8) * (p1[0] - p0[0]) / side * 3,
               m[1] + ny * 40 * (-1 + 2 * i / 5) + (8 if i % 2 else -8) * (p1[1] - p0[1]) / side * 3) for i in range(6)]
        pn.line(zz, WHITE, 7, a)


def sc_rigid(pn, t):
    """8.55–12.15 «Квадрат можно сплющить в ромб. Треугольник держит форму» (стороны ромба = стороны квадрата)."""
    yb = 1020
    g = eo(t, 8.55, 0.3)
    pn.line([(50, yb + 6), (1030, yb + 6)], WHITE, 6, g)
    for x in range(70, 1030, 46):
        pn.line([(x, yb + 12), (x - 24, yb + 44)], WHITE, 3, g * 0.45)
    x0, a_ = 70, 360
    phi = 90 - 30 * eo(t, 9.55, 0.7)
    dx, dy = a_ * math.cos(math.radians(phi)), a_ * math.sin(math.radians(phi))
    sq = [(x0, yb), (x0 + a_, yb), (x0 + a_ + dx, yb - dy), (x0 + dx, yb - dy)]
    k = back(t, 8.62, 0.4)
    if k > 0:
        sqk = sc(sq, (x0 + a_ / 2, yb), k)
        mood = "happy" if t < 9.4 else ("surprised" if t < 9.9 else "dizzy")
        poly_char(pn, sqk, t, fill=BLUE, mood=mood, s=190 * k, hinges=True, look=(0.6, -0.3) if t > 9.2 else (0, 0))
        al = eo(t, 8.95, 0.3)
        if al > 0:
            pn.arc((x0, yb), 72, -phi, 0, WHITE, 6, al)
            m = math.radians(phi / 2)
            pn.text((x0 + 135 * math.cos(m), yb - 135 * math.sin(m) + 4), f"{int(round(phi))}°", 44, WHITE, a=al)
    a = eo(t, 9.25, 0.2) * (1 - pp(t, 10.3, 0.25))
    if a > 0:
        tl = sq[3]
        arrow(pn, (tl[0] - 20, tl[1] - 70), (tl[0] + 170, tl[1] - 70), RED, 13, a)
    tri = [(640, yb), (1030, yb), (835, yb - 390 * math.sqrt(3) / 2)]
    k2 = back(t, 8.85, 0.4)
    if k2 > 0:
        trk = sc(tri, (835, yb), k2)
        col = TEAL
        mood = "happy" if t < 11.0 else "proud"
        pn.poly(trk, fill=col, outline=WHITE, w=8, shadow=True)
        face(pn, (835, yb - 100 * k2), 200 * k2, mood, t, (-0.7, -0.2) if 10.5 < t < 11.0 else (0, 0),
             wink=11.3 < t < 11.6)
        for p in trk:
            pn.circle(p, 13, fill=WHITE)
            pn.circle(p, 5, fill=INK)
    a = eo(t, 10.55, 0.2) * (1 - pp(t, 11.5, 0.3))
    if a > 0:
        apex = tri[2]
        push = 14 * math.sin(math.pi * pp(t, 10.75, 0.3))
        arrow(pn, (apex[0] - 200 + push, apex[1]), (apex[0] - 28 + push, apex[1]), RED, 14, a)
    if t >= 11.54:
        check(pn, (960, 520), 66 * back(t, 11.54, 0.35), TEAL)
        for k3 in range(3):
            sparkle(pn, (700 + 110 * k3, 440 - 40 * (k3 % 2)), 22 * eo(t, 11.6 + 0.08 * k3, 0.2) *
                    (0.7 + 0.3 * math.sin(t * 10 + k3)), SUN)


TR = dict(x0=30, x1=1050, yd=930, h=300, n=7)


def sc_train(pn, t):
    """12.15–16.17 «Поезд в тысячи тонн, а конструкция не складывается»."""
    a = eo(t, 12.15, 0.3)
    world(pn, t, 1080, a)
    river(pn, 1075, 1340, t, a)
    piers(pn, (290, 790), TR["yd"], 1150, a)
    bridge(pn, frac=1.0, a=a, members=False, **TR)
    xf = lerp(-40, 1480, pp(t, 12.45, 3.7))
    mids = train(pn, xf, TR["yd"], t)
    order = [3, 2, 4, 1, 5, 0, 6]
    lit = lambda i, kind: eo(t, 14.94 + 0.07 * order.index(min(i, 6)), 0.25) if t >= 14.94 else 0.0
    bridge(pn, frac=1.0, a=a, lit=lit, deck=False, **TR)
    fa = eo(t, 13.9, 0.25) * (1 - pp(t, 15.3, 0.3))
    if fa > 0:                                                     # «тысячи тонн» — нагрузка вниз на пролёт
        for k, mx in enumerate(mids[1:5]):
            if 60 < mx < 1020:
                y0 = TR["yd"] - 300 - 170 + 12 * math.sin(t * 8 + k)
                arrow(pn, (mx, y0), (mx, TR["yd"] - 325), RED, 14, fa)
    if t >= 15.36:
        check(pn, (950, 450), 70 * back(t, 15.36, 0.35), TEAL)
    pn.paste(polaroid("IMG_8880", 290, (0.14, 0.2, 0.94, 0.95)), 205, 600, k=back(t, 12.5, 0.4),
             rot=6 + 2 * math.sin(t * 1.5))


def sc_engineer(pn, t):
    """16.17–22.12 инженер: балка на чертеже → нагрузка (гири, стрелка прибора) → угол (транспортир)."""
    k = back(t, 16.2, 0.45)
    arm = "point" if (17.5 < t < 18.7 or 20.5 < t < 22.1) else ("up" if 19.8 < t < 20.4 else "idle")
    mood = "surprised" if 19.1 < t < 19.8 else "happy"
    person(pn, 235, 1335, 700, t, "engineer", arm, mood, look=(0.8, -0.5), k=k)
    pk = back(t, 16.3, 0.45)
    if pk <= 0:
        return
    box = (430, 150, 1050, 770)
    c = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
    bx = [lerp(c[0], box[0], pk), lerp(c[1], box[1], pk), lerp(c[0], box[2], pk), lerp(c[1], box[3], pk)]
    pn.rrect(bx, 30, fill=(28, 52, 120), outline=(140, 170, 255), w=5, shadow=True)
    if pk < 0.98:
        return
    for x in range(460, 1040, 40):
        pn.line([(x, 165), (x, 755)], (120, 150, 240), 1, 0.35, caps=False)
    for y in range(180, 760, 40):
        pn.line([(445, y), (1035, y)], (120, 150, 240), 1, 0.35, caps=False)
    aA = 1 - pp(t, 18.75, 0.15)
    if aA > 0:                                                     # A: ферма на чертеже, «балка» мигает
        B, T = bridge(pn, 480, 1000, 620, 200, 5, frac=eo(t, 16.45, 0.9), a=aA, w=6, deck=False)
        if t >= 16.74:
            blink = 0.55 + 0.45 * math.sin((t - 16.74) * 14)
            pn.line([T[1], T[2]], SUN, 12, aA * blink)
            pn.line([B[2], B[3]], SUN, 12, aA * blink * eo(t, 17.0, 0.2))
    aB = eo(t, 18.8, 0.15) * (1 - pp(t, 20.45, 0.15))
    if aB > 0:                                                     # B: «какую нагрузку она выдержит»
        drops = [x for x in (19.14, 19.40, 19.62) if t >= x]
        sag = 5 * len(drops) * (1 + 0.3 * math.sin((t - 19.14) * 18) * math.exp(-(t - 19.14) * 5) if drops else 1)
        beam = [(x, 520 + sag * math.sin(math.pi * (x - 520) / 440)) for x in np.linspace(520, 960, 30)]
        pn.line(beam, (225, 230, 240), 20, aB)
        for x in (530, 950):
            pn.poly([(x, 534), (x - 26, 580), (x + 26, 580)], fill=GREY, outline=WHITE, w=3, a=aB)
        for k2, (x, tt) in enumerate(zip((620, 740, 860), (19.14, 19.40, 19.62))):
            if t < tt - 0.3:
                continue
            u = back(t, tt - 0.3, 0.4)
            ybot = 512 + sag * math.sin(math.pi * (x - 520) / 440)
            y = lerp(230, ybot, u)
            pn.rrect((x - 46, y - 62, x + 46, y), 10, fill=(70, 74, 96), outline=WHITE, w=4, a=aB, shadow=True)
            pn.text((x, y - 30), "10 т", 24, WHITE, a=aB)
        gc = (740, 715)                                            # прибор: стрелка в зелёную зону
        pn.arc(gc, 70, 180, 300, TEAL, 12, aB)
        pn.arc(gc, 70, 318, 360, RED, 12, aB)
        v = 0.25 * len(drops) * 0.85 + 0.15 * eo(t, 19.84, 0.3)
        ang = math.radians(180 + 180 * v)
        pn.line([gc, (gc[0] + 60 * math.cos(ang), gc[1] + 60 * math.sin(ang))], WHITE, 6, aB)
        pn.circle(gc, 9, fill=WHITE, a=aB)
        if t >= 19.95:
            check(pn, (890, 685), 38 * back(t, 19.95, 0.3), TEAL, aB)
    aC = eo(t, 20.45, 0.15)
    if aC > 0:                                                     # C: «под каким углом её поставить»
        pv, L, rp = (650, 690), 360, 190
        th = 45 * eo(t, 20.9, 0.7)
        pn.line([(455, 690), (1030, 690)], WHITE, 4, aC * 0.8)
        pn.arc(pv, rp, 180, 360, (170, 190, 255), 4, aC * 0.8)           # транспортир
        for d in range(0, 181, 15):
            r0 = rp - 16 if d % 45 else rp - 32
            ang = math.radians(-d)
            pn.line([(pv[0] + r0 * math.cos(ang), pv[1] + r0 * math.sin(ang)),
                     (pv[0] + rp * math.cos(ang), pv[1] + rp * math.sin(ang))], (170, 190, 255), 3, aC * 0.8)
        end = (pv[0] + L * math.cos(math.radians(-th)), pv[1] + L * math.sin(math.radians(-th)))
        pn.line([pv, end], (225, 230, 240), 20, aC)
        pn.circle(pv, 14, fill=WHITE, a=aC)
        if th > 1:
            pn.arc(pv, 105, -th, 0, SUN, 7, aC)
            m = math.radians(-th / 2)
            pn.text((pv[0] + 150 * math.cos(m) + 22, pv[1] + 150 * math.sin(m)), f"{int(round(th))}°", 40, SUN, a=aC)


WB = dict(x0=90, x1=990, yd=1000, h=240, n=5)


def sc_weather(pn, t):
    """22.12–24.86 «Что будет в мороз, в жару, при сильном ветре» — мост стоит."""
    a = eo(t, 22.12, 0.3)
    world(pn, t, 1120, a, sun_=False, birds=False)
    river(pn, 1115, 1340, t, a)
    piers(pn, (360, 720), WB["yd"], 1170, a)
    sway = 0 if t < 24.2 else 4 * math.sin((t - 24.2) * 14) * (1 - pp(t, 24.6, 0.25))
    bridge(pn, frac=1.0, a=a, **dict(WB, x0=WB["x0"] + sway, x1=WB["x1"] + sway))
    if t >= 22.97:                                                 # мороз
        k = back(t, 22.97, 0.4)
        snowflake(pn, (215, 420), 105 * k, t * 20)
        for i in range(34):
            x = (i * 97 + 40 * math.sin(t + i)) % 1080
            y = 160 + ((i * 151 + (t - 22.97) * 170) % 1150)
            if y < 1330:
                pn.circle((x, y), 5 + (i % 3) * 2, fill=(215, 230, 255), a=0.7 * eo(t, 22.97, 0.3))
    if t >= 23.55:                                                 # жара
        k = back(t, 23.55, 0.4)
        sun(pn, (540, 380), 95 * k, t * 25)
        for i in range(4):
            x = 260 + i * 180
            ys = np.linspace(760, 600, 12)
            off = (t - 23.55) * 60
            pts = [(x + 10 * math.sin(y / 18 + t * 6 + i), y - off % 40) for y in ys]
            pn.line(pts, SUN, 5, 0.55 * eo(t, 23.6, 0.3))
    if t >= 24.2:                                                  # ветер
        k = back(t, 24.2, 0.4)
        wind(pn, (860, 420), 140 * k, t)
        for i in range(6):
            x = -300 + ((t - 24.2) * 1500 + i * 260) % 1500
            y = 580 + i * 70
            pn.line([(x, y), (x + 180, y)], WHITE, 4, 0.5)


def sc_undo(pn, t):
    """24.86–28.00 «Ошибку в таком расчёте не исправишь кнопкой „отменить“». 1 200 × 1,5 = 1 800 — на экране «180»."""
    k = back(t, 24.9, 0.4)
    if k <= 0:
        return
    box = (90, 170, 990, 810)
    c = (540, 490)
    bx = [lerp(c[0], box[0], k), lerp(c[1], box[1], k), lerp(c[0], box[2], k), lerp(c[1], box[3], k)]
    pn.rrect(bx, 28, fill=(22, 25, 38), outline=(110, 118, 150), w=5, shadow=True)
    if k < 0.97:
        return
    for i, col in enumerate((RED, SUN, TEAL)):
        pn.circle((145 + 38 * i, 215), 12, fill=col)
    rows = [(25.09, 340, "нагрузка", "1 200 т"), (25.50, 490, "запас", "× 1,5"), (25.82, 640, "итого", "180 т")]
    for tt, y, lab, val in rows:
        p = pp(t, tt, 0.35)
        if p <= 0:
            continue
        pn.text((150, y), lab, 46, (170, 178, 205), anchor="lm", a=eo(t, tt, 0.2))
        s = val[: max(1, int(round(len(val) * p)))]
        pn.text((935, y), s, 62, WHITE, anchor="rm")
    if t >= 26.0:                                                  # ошибка: потерян ноль (должно быть 1 800 т)
        e = eo(t, 26.0, 0.3)
        pul = 1 + 0.06 * math.sin((t - 26) * 10) if t > 26.3 else 1
        pts = [(785 + 185 * pul * math.cos(u), 640 + 68 * pul * math.sin(u)) for u in np.linspace(-2.6, -2.6 + 2 * math.pi * e, 50)]
        pn.line(pts, RED, 7)
    kk = back(t, 26.19, 0.4)
    if kk > 0:                                                     # кнопка «отменить» (значок ↶, без подписи)
        press = 10 if 27.40 <= t < 27.56 else 0
        bad = eo(t, 27.55, 0.12)
        shake = 12 * math.sin((t - 27.55) * 40) * (1 - pp(t, 27.55, 0.4)) if t >= 27.55 else 0
        kc = (640 + shake, 1080 + press)
        kb = (kc[0] - 230 * kk, kc[1] - 140 * kk, kc[0] + 230 * kk, kc[1] + 140 * kk)
        fill = tuple(int(lerp(a_, b_, bad)) for a_, b_ in zip((52, 57, 80), (150, 30, 30)))
        pn.rrect(kb, 44 * kk, fill=fill, outline=WHITE, w=6, shadow=press == 0)
        arc = arcp((kc[0] + 12 * kk, kc[1] + 16 * kk), 74 * kk, 20, -200, 30)
        pn.line(arc, WHITE, 16 * kk)
        tip = arc[-1]
        pn.poly([(tip[0] - 30 * kk, tip[1] - 6 * kk), (tip[0] + 18 * kk, tip[1] - 26 * kk), (tip[0] + 6 * kk, tip[1] + 30 * kk)],
                fill=WHITE)
        if t >= 27.6:
            cross(pn, kc, 125, RED, 1.0, eo(t, 27.6, 0.2), 22)
    if t >= 26.0:                                                  # автор: «ой» — рука у виска
        rot = 4 * math.sin((t - 27.55) * 30) * (1 - pp(t, 27.55, 0.4)) if t >= 27.55 else 0
        pn.paste(sticker("IMG_9341", 450, (0, 0, 1, 0.8)), 190, 1395, k=back(t, 26.0, 0.4), rot=rot)
    if 26.48 <= t < 27.95:                                         # курсор летит к кнопке и жмёт
        u = eo(t, 26.48, 0.85)
        p = lerp2((1000, 1300), (670, 1100), u)
        cursor(pn, p, 1.5 - (0.14 if 27.40 <= t < 27.56 else 0))


def sc_master(pn, t):
    """28.00–31.77 «В конструкторы берут тех, кто по-настоящему понимает геометрию»."""
    k = back(t, 28.05, 0.45)
    mood = "proud" if t > 30.5 else "happy"
    hc = person(pn, 540, 1335, 740, t, "engineer", "wave" if 29.1 < t < 30.3 else "idle", mood, k=k)
    if t >= 29.07:
        check(pn, (880, 470), 95 * back(t, 29.07, 0.4), TEAL)
        for i in range(3):
            sparkle(pn, (780 + 90 * i, 330 - 30 * (i % 2)), 20 * eo(t, 29.2 + 0.08 * i, 0.2) *
                    (0.7 + 0.3 * math.sin(t * 9 + i)), SUN)
    if t >= 30.54 and hc:                                          # «геометрию» — фигуры на орбите вокруг головы
        c = hc[0]
        for i in range(4):
            s = back(t, 30.54 + 0.12 * i, 0.4)
            ang = (t - 30.54) * 1.7 + i * math.pi / 2
            p = (c[0] + 340 * math.cos(ang), c[1] - 60 + 190 * math.sin(ang))
            s *= 1.9
            if i == 0:
                pn.poly(tri_pts(p, 90 * s), fill=TEAL, outline=WHITE, w=6, shadow=True)
            elif i == 1:
                pn.circle(p, 42 * s, fill=BLUE, outline=WHITE, w=6, shadow=True)
                pn.line([p, (p[0] + 42 * s, p[1])], WHITE, 6)
                pn.circle(p, 6 * s, fill=WHITE)
            elif i == 2:
                pn.rrect((p[0] - 36 * s, p[1] - 36 * s, p[0] + 36 * s, p[1] + 36 * s), 6, fill=(68, 72, 96),
                         outline=WHITE, w=6, shadow=True)
            else:
                pn.line([(p[0] - 40 * s, p[1] + 25 * s), (p[0] + 40 * s, p[1] + 25 * s)], RED, 9)
                pn.line([(p[0] - 40 * s, p[1] + 25 * s), (p[0] + 20 * s, p[1] - 30 * s)], RED, 9)
                pn.arc((p[0] - 40 * s, p[1] + 25 * s), 34 * s, -43, 0, WHITE, 6)


PY_A, PY_B, PY_C = (150, 820), (630, 820), (630, 460)   # катеты 480 = 4·120 и 360 = 3·120, гипотенуза 600 = 5·120


def sc_board(pn, t):
    """31.77–37.58 школа: доска, мел; признаки, углы, синусы, теорема Пифагора (3-4-5)."""
    k = back(t, 31.8, 0.45)
    if k <= 0:
        return
    c = (540, 650)
    fr = [lerp(c[0], 40, k), lerp(c[1], 150, k), lerp(c[0], 1040, k), lerp(c[1], 1160, k)]
    pn.rrect(fr, 22, fill=(128, 84, 48), outline=WHITE, w=4, shadow=True)
    if k < 0.97:
        return
    pn.rrect((68, 178, 1012, 1132), 10, fill=(30, 66, 50))
    pn.rrect((90, 1132, 990, 1156), 6, fill=(150, 104, 64))
    pn.rrect((760, 1118, 830, 1132), 4, fill=CHALK)
    title = "ГЕОМЕТРИЯ"
    p = pp(t, 32.06, 1.1)
    if p > 0:
        pn.text((540, 265), title[: max(1, int(round(len(title) * p)))], 58, CHALK, a=0.95, shadow=False)
        if p >= 1:
            chalk(pn, [(300, 312), (780, 312)], CHALK_Y, 5, eo(t, 33.2, 0.3))
    A, B, C_ = PY_A, PY_B, PY_C
    fr_ = eo(t, 33.88, 0.6)
    if fr_ > 0:
        pts = part([A, B, C_, A], fr_)
        chalk(pn, pts, CHALK, 8)
        if fr_ < 1:                                                # мелок у кончика линии
            tip = pts[-1]
            pn.poly([(tip[0] + 4, tip[1] - 4), (tip[0] + 40, tip[1] - 40), (tip[0] + 52, tip[1] - 28), (tip[0] + 16, tip[1] + 8)],
                    fill=CHALK)
    al = eo(t, 34.15, 0.3)
    for s, xy in (("A", (A[0] - 42, A[1] + 28)), ("B", (B[0] + 42, B[1] + 28)), ("C", (C_[0] + 42, C_[1] - 22))):
        pn.text(xy, s, 40, CHALK, a=al, shadow=False)
    al = eo(t, 34.36, 0.25)
    if al > 0:
        chalk(pn, [(B[0] - 36, B[1]), (B[0] - 36, B[1] - 36), (B[0], B[1] - 36)], CHALK, 5, al)
    al = eo(t, 34.6, 0.3)
    mid = ((A[0] + C_[0]) / 2, (A[1] + C_[1]) / 2)
    for s, xy in (("4", ((A[0] + B[0]) / 2, A[1] + 48)), ("3", (B[0] + 48, (B[1] + C_[1]) / 2)),
                  ("5", (mid[0] - 0.6 * 52, mid[1] - 0.8 * 52))):
        pn.text(xy, s, 46, CHALK, a=al, shadow=False)
    al = eo(t, 35.36, 0.35)
    if al > 0:
        ang = math.degrees(math.atan2(C_[1] - A[1], C_[0] - A[0]))
        chalk(pn, arcp(A, 92, ang * al, 0, 24), CHALK_Y, 6)
    pn.text((400, 950), "sin A = 3/5", 54, CHALK, a=eo(t, 35.97, 0.3), shadow=False)
    pn.text((400, 1060), "3² + 4² = 5²", 60, CHALK_Y, a=eo(t, 36.58, 0.3), shadow=False)
    pn.paste(sticker("IMG_9337", 680), 890, 1395, k=back(t, 32.48, 0.45))      # автор — учитель у доски
    if t >= 36.9:
        for i in range(3):
            sparkle(pn, (120 + 270 * i, 1005 + 30 * (i % 2)), 18 * eo(t, 36.9 + 0.1 * i, 0.2) *
                    (0.7 + 0.3 * math.sin(t * 9 + i)), CHALK_Y)


CARDS = ["a² + b² = c²", "sin A = a/c", "180°", "S = ah/2"]
CARD_FROM = [(-230, 290), (1310, 330), (-230, 1080), (1310, 990)]
CARD_OUT = [(-260, 140), (1340, 230), (-260, 820), (1340, 760)]


def sc_forget(pn, t):
    """37.58–40.70 «Многие учат наизусть и сразу забывают»: формулы влетают в голову — и вылетают."""
    k = back(t, 37.62, 0.45)
    if k <= 0:
        return
    hc, hr = (540, 650), 205 * k
    ty = lerp(1420, 930, k)                                        # бюст вырастает снизу целиком, а не «полоской»
    hc = (540, ty - 280 * k)
    pn.rrect((540 - 250 * k, ty, 540 + 250 * k, 1420), 110 * k, fill=TEAL, outline=WHITE, w=5, shadow=True)
    pn.rrect((540 - 55 * k, ty - 100 * k, 540 + 55 * k, ty + 20 * k), 20 * k, fill=SKIN)
    pn.line([(540 - 80 * k, ty + 5), (540, ty + 80 * k), (540 + 80 * k, ty + 5)], WHITE, 7, 0.9 * cl(k))
    pn.circle(hc, hr, fill=SKIN, outline=WHITE, w=5, shadow=True)
    hair = arcp((hc[0], hc[1] - hr * 0.1), hr * 1.06, 190, 350, 30)
    pn.poly(hair + [(hc[0], hc[1] - hr * 0.55)], fill=HAIR)
    mood = "happy"
    if 38.9 <= t < 39.5:
        mood = "proud"
    if t >= 39.88:
        mood = "worried"
    look = (0, -1) if 38.6 < t < 39.4 else ((0.7, -0.6) if t > 39.6 else (0, 0))
    face(pn, (hc[0], hc[1] + hr * 0.18), hr * 1.3, mood, t, look)
    for i, (txt, p0, p1) in enumerate(zip(CARDS, CARD_FROM, CARD_OUT)):
        tin = 38.64 + 0.13 * i
        if t < tin:
            u0 = eo(t, 37.8 + 0.1 * i, 0.5)                          # сначала подлетают к краям кадра
            if u0 > 0:
                card(pn, lerp2(p0, (lerp(p0[0], hc[0], 0.62), p0[1]), u0), txt, 1.0, u0, 380, 118, 44)
            continue
        u = eo(t, tin, 0.45)
        start = (lerp(p0[0], hc[0], 0.62), p0[1])
        if t < 39.62:
            card(pn, lerp2(start, hc, u), txt, 1 - 0.75 * u, 1 - pp(t, tin + 0.35, 0.12), 380, 118, 44)
        else:
            v = eo(t, 39.62 + 0.08 * i, 0.6)
            card(pn, lerp2(hc, p1, v), txt, 0.3 + 0.7 * v, 1 - pp(t, 40.1 + 0.08 * i, 0.4), 380, 118, 44)
    if t >= 40.0:
        for i, (dx, dy) in enumerate(((-300, -170), (300, -210), (0, -310))):
            s = back(t, 40.0 + 0.1 * i, 0.35)
            pn.text((hc[0] + dx, hc[1] + dy + 6 * math.sin(t * 6 + i)), "?", 120 * s, BLUE)


def sc_kid(pn, t):
    """40.70–44.23 «Чтобы ваш ребёнок понимал геометрию, а не заучивал её»."""
    k = back(t, 40.75, 0.45)
    hc = person(pn, 330, 1335, 660, t, "kid", "up" if t > 42.5 else "idle", "proud" if t > 42.3 else "happy",
                look=(0.3, -1) if t > 42.1 else (0, 0), k=k)
    if not hc:
        return
    bc = (hc[0][0], hc[0][1] - hc[1] - 150)
    on = eo(t, 42.18, 0.25)
    if t >= 41.15:
        bulb(pn, bc, 74 * back(t, 41.15, 0.35), on)
    if t >= 42.54:                                                 # треугольники складываются в мост
        B, T, zig, ups, downs = truss(520, 1030, 560, 190, 3)
        for i, tr in enumerate(ups + downs):
            u = back(t, 42.54 + 0.1 * i, 0.45)
            cc = centroid(tr)
            fly = lerp2((cc[0] + 300, cc[1] - 250 + 100 * i), cc, u)
            pts = [(p[0] - cc[0] + fly[0], p[1] - cc[1] + fly[1]) for p in tr]
            pn.poly(pts, fill=TEAL if i < 3 else BLUE, outline=WHITE, w=5, a=cl(u * 2), shadow=True)
        if t >= 43.1:
            pn.line([(500, 570), (1050, 570)], WHITE, 12, eo(t, 43.1, 0.2))
    if t >= 43.34:                                                 # «а не заучивал» — зубрёжка: стопка карточек ✕
        a = 1 - pp(t, 43.95, 0.25)
        for i in range(3):
            card(pn, (830 + 8 * i, 1060 - 14 * i), "a² + b²", back(t, 43.34 + 0.05 * i, 0.3), a, 300, 100, 38)
        if t >= 43.55:
            cross(pn, (846, 1032), 110, RED, a, eo(t, 43.55, 0.2), 18)


def sc_cta(pn, t):
    """44.23–48.93 «Напишите в комментариях слово „пробное“ — и разберём это на первом занятии»."""
    k = back(t, 44.25, 0.45)
    if k <= 0:
        return
    box = (130, 190, 950, 870)
    c = (540, 530)
    bx = [lerp(c[0], box[0], k), lerp(c[1], box[1], k), lerp(c[0], box[2], k), lerp(c[1], box[3], k)]
    pn.rrect(bx, 36, fill=(26, 28, 42), outline=(90, 96, 124), w=5, shadow=True)
    if k < 0.97:
        return
    for i, y in enumerate((270, 390)):                             # чужие комментарии — без читаемого текста
        a = eo(t, 44.35 + 0.1 * i, 0.25)
        pn.circle((210, y + 20), 34, fill=(90, 96, 124), a=a)
        pn.rrect((270, y, 270 + 420 - 90 * i, y + 22), 11, fill=(80, 86, 112), a=a)
        pn.rrect((270, y + 36, 270 + 300 + 60 * i, y + 58), 11, fill=(60, 64, 86), a=a)
    pn.rrect((170, 760, 790, 840), 40, fill=(40, 44, 62), outline=(90, 96, 124), w=3)
    if t < 45.55 and (t * 2) % 1 < 0.6:
        pn.line([(215, 780), (215, 820)], WHITE, 4)
    pul = 1 + 0.08 * math.sin((t - 44.4) * 8) if 44.4 < t < 45.6 else 1
    pn.circle((865, 800), 46 * pul, fill=BLUE, shadow=True)
    pn.poly([(843, 775), (895, 800), (843, 825), (853, 800)], fill=WHITE)
    if 44.4 <= t < 45.55:                                          # «печатает…»
        for i in range(3):
            pn.circle((260 + 34 * i, 800 - 8 * max(0.0, math.sin(t * 9 - i))), 9, fill=GREY)
    if t >= 45.55:                                                 # ответ автора (его лицо на аватарке) + сердечко
        u = back(t, 45.55, 0.45)
        y = lerp(760, 530, u)
        pn.rrect((190, y - 10, 890, y + 150), 30, fill=(36, 60, 130), outline=BLUE, w=4, a=cl(u * 2), shadow=True)
        pn.circle((262, y + 70), 50, fill=WHITE, a=cl(u * 2))
        pn.paste(avatar("IMG_9340", 46, (180, 70, 640, 530)), 262, y + 116, a=cl(u * 2), shadow=False)
        pn.rrect((335, y + 40, 720, y + 64), 12, fill=(140, 165, 240), a=cl(u * 2))
        pn.rrect((335, y + 82, 600, y + 106), 12, fill=(100, 125, 210), a=cl(u * 2))
        if t >= 45.96:
            heart(pn, (820, y + 115), 40 * back(t, 45.96, 0.4) * (1 + 0.08 * math.sin((t - 46) * 7)), RED)
    if t >= 45.96:                                                 # автор: большой палец вверх
        pn.paste(sticker("IMG_9340", 520, (0, 0, 1, 0.72)), 800, 1395, k=back(t, 45.96, 0.45))
    if t >= 46.4:                                                  # талисман рядом
        s_ = back(t, 46.4, 0.45)
        c2 = (240, 1215 + 6 * math.sin(t * 5))
        pts = tri_char(pn, c2, 250 * s_, t, TEAL, "happy", (0.7, -0.3))
        if t >= 47.28:                                             # шапочка выпускника
            u = back(t, 47.28, 0.4)
            top = pts[0]
            cap = [(top[0] - 90 * u, top[1] - 10 * u), (top[0], top[1] - 45 * u), (top[0] + 90 * u, top[1] - 10 * u),
                   (top[0], top[1] + 25 * u)]
            pn.poly(cap, fill=INK, outline=WHITE, w=4, shadow=True)
            pn.line([(top[0], top[1] - 10 * u), (top[0] + 70 * u, top[1] + 10 * u), (top[0] + 70 * u, top[1] + 60 * u)],
                    SUN, 5)
            pn.circle((top[0] + 70 * u, top[1] + 64 * u), 9 * u, fill=SUN)
        for i in range(3):
            sparkle(pn, (400 + 70 * i, 1010 - 40 * (i % 2)), 18 * eo(t, 46.8 + 0.12 * i, 0.2) *
                    (0.7 + 0.3 * math.sin(t * 9 + i)), SUN)


FN = {"bridge": sc_bridge, "hero": sc_hero, "rigid": sc_rigid, "train": sc_train, "engineer": sc_engineer,
      "weather": sc_weather, "undo": sc_undo, "master": sc_master, "board": sc_board, "forget": sc_forget,
      "kid": sc_kid, "cta": sc_cta}


def scene_at(t):
    for a, b, n in SCENES:
        if a <= t < b:
            return a, b, n
    return SCENES[-1]


def art(t, qa=False):
    a, b, n = scene_at(t)
    z, c = cam_bridge(t) if n == "bridge" else (1.0, (540, 760))
    pn = Pen(t, qa, z, c)
    if not qa:
        dust(pn, t)
    FN[n](pn, t)
    return pn.done(t)


def frame(f):
    t = f / FPS
    im = art(t).convert("RGBA")
    cl_ = CAPM.layer(t)
    if cl_ is not None:
        im.alpha_composite(cl_)
    return im.convert("RGB")


def main():
    os.makedirs(TMPD, exist_ok=True)
    tmp = VID.replace(".mp4", ".part.mp4")
    ff = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "16",
                           "-preset", "medium", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
    for f in range(NF):
        ff.stdin.write(frame(f).tobytes())
        if f % 150 == 0:
            print(f"  кадр {f}/{NF}  ({f / FPS:5.1f}s)", flush=True)
    ff.stdin.close(); ff.wait()
    os.replace(tmp, VID)
    print("видео:", VID)


def patch(base, ranges):
    """Правка отдельных сцен без полного рендера: кадры из диапазонов [(t0, t1), …] рисуются заново, остальные
    берутся из готового base.mp4 (flat-графика, crf 15 — потерь не видно). Результат — VID."""
    import cv2
    cap = cv2.VideoCapture(base)
    tmp = VID.replace(".mp4", ".part.mp4")
    ff = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "15",
                           "-preset", "medium", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
    n = 0
    for f in range(NF):
        ok, im = cap.read()
        t = f / FPS
        if any(a <= t < b for a, b in ranges) or not ok:
            fr = np.asarray(frame(f)); n += 1
        else:
            fr = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
        ff.stdin.write(fr.tobytes())
        if f % 150 == 0:
            print(f"  кадр {f}/{NF}  (перерисовано {n})", flush=True)
    ff.stdin.close(); ff.wait(); cap.release()
    os.replace(tmp, VID)
    print("видео:", VID, "перерисовано кадров:", n)


def snaps(ts):
    for t in ts:
        frame(int(round(float(t) * FPS))).save(f"{TMPD}/_cart18_{float(t):05.2f}.png")
    print("кадры:", len(ts))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "snap":
        snaps(sys.argv[2:])
    elif len(sys.argv) > 1 and sys.argv[1] == "patch":       # patch <base.mp4> 0-4.25 12.15-16.17 …
        patch(sys.argv[2], [tuple(float(x) for x in r.split("-")) for r in sys.argv[3:]])
    else:
        main()
