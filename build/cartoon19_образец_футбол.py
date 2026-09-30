"""Ролик 19, версия «мультик с фото» (16.4) — без лица, всё на экране — анимация + фото автора.
Слова автора (2026-09-30): «теперь голос норм - добавляй больше анимация как ролик 15 и добавь мои фото - добавь в
инстуркции если ролик без лица - то анимация и фото со мной должны быть».

Образец — build/cartoon18.py (15.2/15.3): вспомогательные функции (Pen, face, person, sticker, polaroid, avatar, world,
dust, check, cross, heart, sparkle, card, bulb…) скопированы оттуда без изменений (только PHOTO_DIR/TMPD — ролик 19).
Звук — тот же, что 16.3 (voicefx_v6 + подмес на скачке, song3 с 0:00, master_v2) — sfx19m.py. Слова и тайминги —
words.json 16.2. Субтитры v3 и акценты — render19.Captions19 (пружинка «АНАЛИТИКОВ», маркер «МАТЕМАТИКИ»,
штамп «ПРОБНОЕ»), зона «графика» (базовая линия y 1500); рисунок — только выше y 1370. Проверки — qa19m.py.
Математика буквальная: угол на ворота 2·atan(3.66/11) = 36.8° ≈ 37° и 14.6° ≈ 15° (размеры FIFA, assert);
3 из 10 = 30 % (шкала ровно 0.3); P(A) = m/n, (a+b+c)/3, y = kx + b; счётчик 0 → 1 000.
Фото автора (вырезки — «Фото/Вырезанные», копии в videos/19/photos): стикер 8883 в начале, полароид 8876
на стене отдела, стикер 9325 в «профессии на стыке», стикер 9338 у доски, «палец вверх» 9340 в финале.

  python cartoon19.py                 — рендер немого видео -> assets/19/_cartoon_19.mp4
  python cartoon19.py snap t1 t2 ...  — отдельные кадры -> assets/19/_cart19_<t>.png
"""
import os, sys, math, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render19 as R            # субтитры v3 + акценты ролика 19 (Captions19)
import captions as C
from style import W, H, FPS, grid_canvas, ease_out
from storyboard19 import CAPS, DUR, COUNTER_T

BUILD = os.path.dirname(os.path.abspath(__file__))
TMPD = f"{BUILD}/assets/19"
VID = f"{TMPD}/_cartoon_19.mp4"
PHOTO_DIR = f"{BUILD}/../videos/19/photos"
NF = int(round(DUR * FPS))
SS = 2
ART_MAX_Y = 1360                # рисунок только выше: верх 2-строчной фразы ≈ 1370 → зазор ≥ 8 px (при 1370 газон давал 1 px)

WHITE = (255, 255, 255); BLUE = (91, 124, 255); TEAL = (45, 225, 194); RED = (255, 59, 48)
SUN = (255, 214, 90); INK = (24, 24, 34); SKIN = (255, 206, 165); GREY = (150, 152, 165)
DARK = (40, 44, 62); HAIR = (110, 72, 44); CHALK = (236, 236, 226); CHALK_Y = (255, 228, 120)
GRASS = (34, 120, 72); GRASS2 = (40, 138, 82); BOARD = (34, 78, 58)

SCENES = [(0.00, 3.75, "buy"), (3.75, 5.28, "scout"), (5.28, 6.85, "analyst"), (6.85, 9.37, "pressure"),
          (9.37, 11.78, "pass"), (11.78, 14.60, "goal"), (14.60, 16.00, "europe"), (16.00, 17.93, "dept"),
          (17.93, 20.80, "liverpool"), (20.80, 21.90, "physicist"), (21.90, 25.05, "trophy"),
          (25.05, 29.05, "profession"), (29.05, 33.60, "school"), (33.60, 37.45, "kid"),
          (37.45, 40.06, "strength"), (40.06, 41.90, "cta"), (41.90, DUR, "lesson")]
SHOTS_M = [(a, b, "scene", {}) for a, b, _ in SCENES]     # для субтитров: всё — зона «графика» (y 1500)
CAPM = R.Captions19(CAPS, SHOTS_M, DUR, f"{BUILD}/../videos/19/words_cap.json")


# ================================================================ из cartoon18.py (без изменений)
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



# ================================================================ ролик 19: свои предметы и персонажи
def grass(pn, y0, a=1.0):
    """Газон с полосами покоса от y0 до низа зоны рисунка."""
    pn.rrect((-20, y0, W + 20, 1400), 0, fill=GRASS, a=a)
    for k in range(0, 12, 2):
        pn.rrect((-20 + k * 100, y0, 80 + k * 100, 1400), 0, fill=GRASS2, a=a)
    pn.line([(-20, y0 + 26), (W + 20, y0 + 26)], WHITE, 6, a * 0.8, caps=False)


def ball(pn, c, r, rot=0.0, a=1.0, shadow=True):
    pn.circle(c, r, fill=WHITE, outline=INK, w=max(3, r * 0.08), a=a, shadow=shadow)
    pent = ngon(c, r * 0.36, 5, rot=-90 + math.degrees(rot))
    pn.poly(pent, fill=INK, a=a)
    for p in pent:
        ang = math.atan2(p[1] - c[1], p[0] - c[0])
        pn.line([p, (c[0] + r * 0.97 * math.cos(ang), c[1] + r * 0.97 * math.sin(ang))], INK, max(2, r * 0.07), a)


def human(pn, x, yf, hh, t, shirt=TEAL, hair=HAIR, arm="idle", mood="happy", look=(0, 0), a=1.0, k=1.0,
          glasses=False, coat=False, num=None, jump=0.0, arm_l="idle"):
    """Человечек (по образцу person из cartoon18): футболка цвета shirt, номер, халат учёного, очки, прыжок."""
    if a <= 0.01 or k <= 0.01:
        return None
    H_ = hh * k
    yf = yf - jump
    bob = 5 * math.sin(t * 3.1) * k
    X = lambda u: x + u * H_
    Y = lambda v: yf - v * H_ + (bob if v > 0.3 else 0)
    for sx in (-1, 1):                                             # ноги
        pn.line([(X(sx * 0.07), Y(0.33)), (X(sx * 0.09), Y(0.02))], DARK, 0.075 * H_, a)
        pn.line([(X(sx * 0.09), Y(0.02)), (X(sx * 0.16), Y(0.02))], INK, 0.06 * H_, a)
    if coat:
        pn.rrect((X(-0.20), Y(0.64), X(0.20), Y(0.20)), 0.08 * H_, fill=WHITE, outline=GREY, w=3, a=a, shadow=True)
        pn.rrect((X(-0.07), Y(0.62), X(0.07), Y(0.30)), 0.03 * H_, fill=shirt, a=a)
    else:
        pn.rrect((X(-0.17), Y(0.64), X(0.17), Y(0.28)), 0.08 * H_, fill=shirt, outline=WHITE, w=4, a=a, shadow=True)
    if num:
        pn.text((X(0), Y(0.47)), num, 0.13 * H_, WHITE, a=a)
    sleeve = WHITE if coat else shirt
    sh_l, sh_r = (X(-0.16), Y(0.58)), (X(0.16), Y(0.58))
    hands = {"idle": lambda s: (X(s * 0.25), Y(0.38)), "up": lambda s: (X(s * 0.30), Y(0.86)),
             "point": lambda s: (X(s * 0.44), Y(0.74)), "hold": lambda s: (X(s * 0.12), Y(0.50))}
    if arm == "wave":
        ang = math.radians(-60 + 22 * math.sin(t * 9))
        hr_ = (sh_r[0] + 0.26 * H_ * math.cos(ang), sh_r[1] + 0.26 * H_ * math.sin(ang))
    else:
        hr_ = hands[arm](1)
    hl_ = hands[arm_l](-1)
    for sh, hd in ((sh_l, hl_), (sh_r, hr_)):
        pn.line([sh, hd], sleeve, 0.07 * H_, a)
        pn.circle(hd, 0.04 * H_, fill=SKIN, a=a)
    hc, hr = (X(0.0), Y(0.79)), 0.155 * H_
    pn.circle(hc, hr, fill=SKIN, outline=WHITE, w=4, a=a, shadow=True)
    hairp = arcp((hc[0], hc[1] - hr * 0.1), hr * 1.06, 190, 350, 30)
    pn.poly(hairp + [(hc[0], hc[1] - hr * 0.55)], fill=hair, a=a)
    fc, fs = (hc[0], hc[1] + hr * 0.18), hr * 1.3
    face(pn, fc, fs, mood, t, look, a)
    if glasses:
        for sx in (-1, 1):
            pn.circle((fc[0] + sx * 0.28 * fs, fc[1] - 0.10 * fs), 0.2 * fs, outline=INK, w=0.035 * fs, a=a)
        pn.line([(fc[0] - 0.08 * fs, fc[1] - 0.12 * fs), (fc[0] + 0.08 * fs, fc[1] - 0.12 * fs)], INK, 0.03 * fs, a)
    return hc, hr, hr_


def mortarboard(pn, top, u):
    if u <= 0:
        return
    cap = [(top[0] - 95 * u, top[1] - 8 * u), (top[0], top[1] - 48 * u), (top[0] + 95 * u, top[1] - 8 * u),
           (top[0], top[1] + 28 * u)]
    pn.poly(cap, fill=INK, outline=WHITE, w=4, shadow=True)
    pn.line([(top[0], top[1] - 10 * u), (top[0] + 72 * u, top[1] + 10 * u), (top[0] + 72 * u, top[1] + 62 * u)], SUN, 5)
    pn.circle((top[0] + 72 * u, top[1] + 66 * u), 9 * u, fill=SUN)


def mini_pitch(pn, box, t, a=1.0, seed=0, dots=6):
    """Экран с матчем: поле и бегающие точки двух команд."""
    x0, y0, x1, y1 = box
    pn.rrect(box, 12, fill=GRASS, a=a)
    pn.line([((x0 + x1) / 2, y0 + 6), ((x0 + x1) / 2, y1 - 6)], WHITE, 3, a * 0.8, caps=False)
    r = min(x1 - x0, y1 - y0) * 0.16
    pn.circle(((x0 + x1) / 2, (y0 + y1) / 2), r, outline=WHITE, w=3, a=a * 0.8)
    for i in range(dots):
        u = 0.5 + 0.38 * math.sin(t * (1.3 + 0.2 * i) + i * 2.1 + seed)
        v = 0.5 + 0.34 * math.cos(t * (1.1 + 0.15 * i) + i * 1.3 + seed)
        pn.circle((lerp(x0, x1, u), lerp(y0, y1, v)), max(3, r * 0.22), fill=TEAL if i % 2 else RED, a=a)


def monitor(pn, box, t, a=1.0, seed=0, chart=0.0, k=1.0):
    """Монитор на стене: матч или (chart > 0) график, растущий вверх."""
    if k <= 0.01 or a <= 0.01:
        return
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    b = [cx + (box[0] - cx) * k, cy + (box[1] - cy) * k, cx + (box[2] - cx) * k, cy + (box[3] - cy) * k]
    pn.rrect(b, 16 * k, fill=DARK, outline=WHITE, w=5, a=a, shadow=True)
    inner = (b[0] + 14 * k, b[1] + 14 * k, b[2] - 14 * k, b[3] - 14 * k)
    if chart <= 0:
        mini_pitch(pn, inner, t, a, seed)
        return
    pn.rrect(inner, 10 * k, fill=(26, 30, 46), a=a)
    n = 7
    pts = []
    for i in range(n):
        base = 0.25 + 0.12 * math.sin(i * 1.7 + seed) + 0.5 * chart * i / (n - 1)
        pts.append((lerp(inner[0] + 12, inner[2] - 12, i / (n - 1)), lerp(inner[3] - 12, inner[1] + 12, base)))
    pn.line(part(pts, cl(0.3 + chart)), TEAL, 6 * k, a)
    for p in pts[:1 + int(cl(0.3 + chart) * (n - 1))]:
        pn.circle(p, 7 * k, fill=WHITE, a=a)


def trophy(pn, c, s, a=1.0):
    """Кубок: чаша, ручки, ножка, подставка. s — высота."""
    if s <= 0.01 or a <= 0.01:
        return
    x, y = c
    bowl =[(x - 0.32 * s, y - 0.5 * s), (x + 0.32 * s, y - 0.5 * s)] + \
           [(x + 0.32 * s * math.cos(math.radians(u)), y - 0.5 * s + 0.36 * s * math.sin(math.radians(u)))
            for u in range(0, 181, 10)]
    for sx in (-1, 1):
        pn.arc((x + sx * 0.33 * s, y - 0.36 * s), 0.13 * s, -90 if sx > 0 else 90, 90 if sx > 0 else 270, SUN,
               0.05 * s, a)
    pn.poly(bowl, fill=SUN, outline=WHITE, w=4, a=a, shadow=True)
    pn.rrect((x - 0.05 * s, y - 0.16 * s, x + 0.05 * s, y + 0.1 * s), 4, fill=SUN, a=a)
    pn.rrect((x - 0.22 * s, y + 0.1 * s, x + 0.22 * s, y + 0.22 * s), 8, fill=(200, 150, 60), outline=WHITE, w=4,
             a=a, shadow=True)
    pn.line([(x - 0.18 * s, y - 0.42 * s), (x - 0.1 * s, y - 0.2 * s)], WHITE, 0.03 * s, a * 0.7)


def stadium(pn, c, s, flag=(BLUE, WHITE), a=1.0, t=0.0):
    """Стадион сбоку-сверху: чаша трибун, поле, мачты со светом, флаг клуба (две полосы, без эмблем)."""
    if s <= 0.01 or a <= 0.01:
        return
    x, y = c
    for sx in (-1, 1):                                              # мачты освещения
        mx = x + sx * 0.46 * s
        pn.line([(mx, y + 0.05 * s), (mx, y - 0.55 * s)], GREY, 0.02 * s, a)
        on = 0.6 + 0.4 * math.sin(t * 6 + sx)
        pn.rrect((mx - 0.07 * s, y - 0.62 * s, mx + 0.07 * s, y - 0.53 * s), 4, fill=SUN, a=a * on)
    outer = [(x + 0.5 * s * math.cos(math.radians(u)), y + 0.24 * s * math.sin(math.radians(u))) for u in range(0, 360, 8)]
    inner = [(x + 0.34 * s * math.cos(math.radians(u)), y + 0.14 * s * math.sin(math.radians(u))) for u in range(0, 360, 8)]
    pn.poly(outer, fill=(60, 66, 96), outline=WHITE, w=4, a=a, shadow=True)
    pn.poly(inner, fill=GRASS2, outline=WHITE, w=3, a=a)
    pn.line([(x, y - 0.13 * s), (x, y + 0.13 * s)], WHITE, 2, a * 0.8, caps=False)
    fx, fy = x, y - 0.22 * s                                       # флаг
    pn.line([(fx, fy), (fx, fy - 0.42 * s)], WHITE, 4, a)
    wv = 6 * math.sin(t * 5)
    for i, col in enumerate(flag):
        y0 = fy - 0.42 * s + i * 0.08 * s
        pn.poly([(fx, y0), (fx + 0.26 * s, y0 + wv), (fx + 0.26 * s, y0 + 0.08 * s + wv), (fx, y0 + 0.08 * s)],
                fill=col, a=a)


def dice(pn, c, s, rot, a=1.0):
    pts = [(c[0] + s * 0.5 * math.cos(math.radians(rot + 45 + 90 * k)) * 1.414,
            c[1] + s * 0.5 * math.sin(math.radians(rot + 45 + 90 * k)) * 1.414) for k in range(4)]
    pn.poly(pts, fill=WHITE, outline=INK, w=5, a=a, shadow=True)
    for du, dv in ((0, 0), (-0.25, -0.25), (0.25, 0.25), (-0.25, 0.25), (0.25, -0.25)):
        ang = math.radians(rot)
        px = c[0] + s * (du * math.cos(ang) - dv * math.sin(ang))
        py = c[1] + s * (du * math.sin(ang) + dv * math.cos(ang))
        pn.circle((px, py), s * 0.08, fill=INK, a=a)


def tile(pn, c, s, a=1.0):
    pn.rrect((c[0] - s / 2, c[1] - s / 2, c[0] + s / 2, c[1] + s / 2), 26, fill=(30, 34, 52), outline=WHITE, w=5,
             a=a, shadow=True)


def bars_icon(pn, c, s, grow, a=1.0):
    x0, y0 = c[0] - 0.36 * s, c[1] + 0.32 * s
    pn.line([(x0, c[1] - 0.36 * s), (x0, y0), (c[0] + 0.38 * s, y0)], WHITE, 5, a)
    for i, (h, col) in enumerate(((0.35, BLUE), (0.6, TEAL), (0.45, BLUE), (0.62, TEAL))):
        hh = h * s * cl(grow * 1.6 - i * 0.2)
        bx = x0 + 0.06 * s + i * 0.17 * s
        if hh > 8 and s > 20:
            pn.rrect((bx, y0 - hh, bx + 0.12 * s, y0 - 3), 6, fill=col, a=a)


def graph_icon(pn, c, s, frac, a=1.0):
    x0, y0 = c[0] - 0.36 * s, c[1] + 0.32 * s
    pn.line([(x0, c[1] - 0.36 * s), (x0, y0), (c[0] + 0.38 * s, y0)], WHITE, 5, a)
    pts = [(x0 + 0.05 * s + 0.66 * s * u, y0 - 0.08 * s - 0.55 * s * u) for u in np.linspace(0, 1, 12)]
    pn.line(part(pts, frac), RED, 7, a)
    if frac > 0.05:
        pn.circle(part(pts, frac)[-1], 9, fill=WHITE, a=a)


def confetti(pn, t, t0, n=36, a=1.0):
    if t < t0:
        return
    cols = (SUN, TEAL, BLUE, RED, WHITE)
    for i in range(n):
        x = (i * 97 + 40 * math.sin(t * 2 + i)) % W
        y = 120 + ((t - t0) * (260 + 40 * (i % 5)) + i * 53) % 1250
        ang = t * 4 + i
        d = (12 * math.cos(ang), 6 * math.sin(ang))
        pn.line([(x - d[0], y - d[1]), (x + d[0], y + d[1])], cols[i % 5], 8, a * 0.9)


def speed_lines(pn, c, s, t, a=1.0):
    for k in range(3):
        y = c[1] - s * 0.4 + k * s * 0.4
        x0 = c[0] + 10 * math.sin(t * 20 + k)
        pn.line([(x0, y), (x0 + s * (0.8 - 0.2 * k), y)], WHITE, 6, a * 0.7)


# ---------------------------------------------------------------- математика модели (буквальная, проверяется qa19m)
GOAL_HALF = 7.32 / 2


def view_angle(x, y):
    """Угол (°), под которым из точки (x; y) м видны ворота шириной 7.32 м (x — вдоль линии ворот от центра)."""
    return math.degrees(abs(math.atan2(GOAL_HALF - x, y) - math.atan2(-GOAL_HALF - x, y)))


PT_A, PT_B = (0.0, 11.0), (-14.0, 18.0)
ANG_A, ANG_B = view_angle(*PT_A), view_angle(*PT_B)
assert abs(ANG_A - 2 * math.degrees(math.atan(3.66 / 11))) < 1e-9 and round(ANG_A) == 37 and round(ANG_B) == 15
LOSS = (3, 10)                                                     # «3 из 10» → шкала ровно 0.3
MATH = {"угол с пенальти 37°": round(ANG_A) == 37, "угол с (−14; 18) м 15°": round(ANG_B) == 15,
        "3 из 10 = 30 %": abs(LOSS[0] / LOSS[1] - 0.30) < 1e-12}
GRAPH_TEXTS = ["10", "7", "9", "€ ?", "ГОЛЫ", "f(x)", "1", "1 000", "МАТЧЕЙ", "3 ИЗ 10", "= 30 %", "!",
               "УГОЛ НА ВОРОТА", f"{round(ANG_A)}°", f"{round(ANG_B)}°", f"{round(ANG_A)}° > {round(ANG_B)}°",
               "PhD", "x²", "P(A) = m / n", "(a + b + c) / 3", "y = kx + b", "ПН ВТ СР ЧТ ПТ СБ ВС", "0123456789"]


# ---------------------------------------------------------------- сцены (t — абсолютное время ролика)
def sc_buy(pn, t):
    """0.00–3.75 «Футбольные клубы покупают игроков не по голам, а по формулам»."""
    world(pn, t, 1080)
    grass(pn, 1080)
    k = back(t, -0.3, 0.5)                                         # первый кадр уже с игроком
    human(pn, 360, 1345, 720, t, TEAL, num="10", arm="wave" if t > 0.6 else "idle", k=k)
    ball(pn, (520, 1300), 46 * k, t * 1.5)
    if t >= 1.27:                                                  # «покупают» — ценник качается
        u = back(t, 1.27, 0.45)
        sw = 8 * math.sin((t - 1.27) * 5) * (1 - pp(t, 1.27, 2.0))
        pn.line([(640, 190), (790 + sw, 290)], WHITE, 4, cl(u))
        card(pn, (790 + sw, 340), "€ ?", u, 1, 250, 110, 54)
    if t >= 2.32:                                                  # «не по голам»
        u = back(t, 2.32, 0.35)
        card(pn, (790, 580), "ГОЛЫ", u, 1, 270, 100, 46)
        ball(pn, (600, 580), 34 * u, t)
        if t >= 2.54:
            cross(pn, (790, 580), 95, RED, 1, eo(t, 2.54, 0.2), 16)
    if t >= 3.03:                                                  # «а по формулам»
        u = back(t, 3.03, 0.4)
        pn.rrect((790 - 175 * u, 830 - 72 * u, 790 + 175 * u, 830 + 72 * u), 28 * u, fill=TEAL, shadow=True)
        pn.text((790, 834), "f(x)", 76 * u, INK, shadow=False)
        check(pn, (955, 760), 38, SUN, 1, eo(t, 3.36, 0.25))
        for i in range(3):
            sparkle(pn, (640 + 120 * i, 950 + 20 * (i % 2)), 20 * eo(t, 3.3 + 0.08 * i, 0.2), SUN)
    if t >= 0.35:                                                  # автор — стикер
        pn.paste(sticker("IMG_8883", 500), 880, 1395, k=back(t, 0.35, 0.45))


def sc_scout(pn, t):
    """3.75–5.28 «Скаут видит одну игру»."""
    for i in range(6):                                             # трибуна с болельщиками
        y = 200 + i * 95
        pn.rrect((-20, y, W + 20, y + 70), 8, fill=(44, 50, 76))
        for j in range(12):
            x = 40 + j * 90 + (i % 2) * 45
            pn.circle((x, y + 18 - 6 * abs(math.sin(t * 4 + i + j))), 18, fill=(70 + 20 * (j % 3), 78, 110))
    grass(pn, 1000)
    r = human(pn, 300, 1345, 660, t, (120, 92, 64), arm="hold", arm_l="hold", mood="happy", look=(1, 0),
              k=back(t, 3.78, 0.4))
    if r:
        hc, hr, _ = r
        for sx in (-1, 1):                                         # бинокль
            pn.circle((hc[0] + sx * 0.36 * hr, hc[1] + 0.05 * hr), 0.3 * hr, fill=INK, outline=WHITE, w=4)
    k = back(t, 3.9, 0.4)
    monitor(pn, (540, 300, 1030, 700), t, k=k)
    if t >= 4.62:                                                  # «одну» — бейдж «1»
        u = back(t, 4.62, 0.35)
        pn.circle((1000, 310), 56 * u, fill=SUN, shadow=True)
        pn.text((1000, 314), "1", 64 * u, INK, shadow=False)


def sc_analyst(pn, t):
    """5.28–6.85 «аналитик видит тысячи» — стена экранов растёт, счётчик матчей 0 → 1 000."""
    pn.rrect((-20, 1180, W + 20, 1400), 0, fill=(46, 42, 40))
    r = human(pn, 210, 1345, 600, t, BLUE, arm="hold", glasses=True, mood="surprised" if t > 6.17 else "happy",
              look=(1, -0.4), k=back(t, 5.3, 0.4))
    if r:                                                          # ноутбук
        pn.rrect((110, 1010, 320, 1070), 10, fill=GREY, outline=WHITE, w=4, shadow=True)
    X0, Y0, X1, Y1 = 420, 170, 1050, 820
    if t < 5.84:
        grid = [(1, 1, 0.0)]
    elif t < 6.17:
        grid = [(2, 2, 5.84)]
    else:
        grid = [(6, 5, 6.17)]
    cols, rows, t0 = grid[0]
    cw, ch = (X1 - X0) / cols, (Y1 - Y0) / rows
    for j in range(rows):
        for i in range(cols):
            n = j * cols + i
            k = back(t, max(5.3, t0) + 0.01 * n, 0.3) if t0 else back(t, 5.35, 0.35)
            box = (X0 + i * cw + 6, Y0 + j * ch + 6, X0 + (i + 1) * cw - 6, Y0 + (j + 1) * ch - 6)
            monitor(pn, box, t + n, k=k, seed=n) if cols < 6 else _small_screen(pn, box, t, n, k)
    c0, cd = COUNTER_T
    n = int(round(1000 * eo(t, c0, cd))) if t >= c0 else 0
    txt = f"{n:,}".replace(",", " ")
    sz = 150
    while C.wide(sz).getlength("1 000") > 600:
        sz -= 4
    pn.text((740, 990), txt, sz, BLUE)
    pn.text((740, 1120), "МАТЧЕЙ", 54, WHITE)


def _small_screen(pn, box, t, n, k):
    if k <= 0.01:
        return
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    b = [cx + (box[0] - cx) * k, cy + (box[1] - cy) * k, cx + (box[2] - cx) * k, cy + (box[3] - cy) * k]
    pn.rrect(b, 6, fill=GRASS, outline=WHITE, w=2)
    for i in range(2):
        u = 0.5 + 0.35 * math.sin(t * 2 + n + i * 2)
        pn.circle((lerp(b[0], b[2], u), lerp(b[1], b[3], 0.3 + 0.4 * i)), 4, fill=TEAL if i else RED)


def sc_pressure(pn, t):
    """6.85–9.37 «Как часто игрок теряет мяч под давлением»: защитник прессингует, мяч отлетает; 3 из 10 = 30 %."""
    world(pn, t, 900, sun_=False)
    grass(pn, 900)
    lost = t >= 7.86
    human(pn, 380, 1345, 640, t, TEAL, num="7", mood="worried" if t > 7.5 else "happy", look=(1, 0),
          k=back(t, 6.87, 0.4))
    dx = lerp(1180, 730, eo(t, 7.12, 0.7))
    human(pn, dx, 1345, 640, t, RED, num="4", arm="point" if t > 7.6 else "idle", mood="proud", look=(-1, 0))
    if 7.1 < t < 7.9:
        speed_lines(pn, (dx + 120, 1000), 170, t)
    if not lost:
        ball(pn, (540, 1300), 44, t * 3)
    else:
        u = eo(t, 7.86, 0.7)
        p = (lerp(540, 1000, u), lerp(1300, 760, u) - 260 * math.sin(math.pi * u))
        ball(pn, p, 44, t * 9)
        pn.text((470, 540), "!", 120 * back(t, 7.9, 0.3), RED)
    if t >= 8.46:                                                  # статистика потерь
        u = back(t, 8.46, 0.4)
        a = cl(u * 2)
        pn.rrect((110, 210, 970, 440), 34, fill=DARK, outline=(90, 96, 124), w=5, a=a, shadow=True)
        pn.poly([(360, 440), (420, 440), (380, 500)], fill=DARK, a=a)
        pn.text((320, 300), f"{LOSS[0]} ИЗ {LOSS[1]}", 64, WHITE, a=a)
        pn.rrect((560, 272, 920, 322), 25, fill=(70, 72, 90), a=a)
        f = LOSS[0] / LOSS[1] * eo(t, 8.6, 0.45)
        if f > 0.01:
            pn.rrect((560, 272, 560 + 360 * f, 322), 25, fill=RED, a=a)
        pn.text((740, 380), "= 30 %", 48, RED, a=a * eo(t, 8.9, 0.2))


PASS_PTS = [(540, 1170), (270, 880), (720, 640), (560, 360)]
PASS_T = [9.80, 10.28, 10.66]


def sc_pass(pn, t):
    """9.37–11.78 «Сколько опасных моментов создаёт его пас»: вид сверху, передачи к воротам, звёздочки-моменты."""
    a = eo(t, 9.37, 0.3)
    pn.rrect((60, 170, 1020, 1350), 20, fill=GRASS, a=a)
    for k in range(0, 12, 2):
        pn.rrect((60, 170 + k * 98, 1020, 170 + (k + 1) * 98), 0, fill=GRASS2, a=a)
    lc = WHITE
    pn.rrect((60, 170, 1020, 1350), 20, outline=lc, w=5, a=a)
    pn.rrect((280, 170, 800, 420), 0, outline=lc, w=5, a=a)
    pn.rrect((420, 170, 660, 250), 0, outline=lc, w=5, a=a)
    pn.rrect((470, 140, 610, 170), 4, fill=WHITE, a=a)
    pn.arc((540, 1350), 130, 180, 360, lc, 5, a)
    for i, (x, y) in enumerate(((300, 520), (780, 820), (430, 700), (650, 1000))):     # соперники
        pn.circle((x + 20 * math.sin(t * 2 + i), y + 12 * math.cos(t * 1.7 + i)), 26, fill=RED, outline=WHITE, w=4, a=a)
    for i, p in enumerate(PASS_PTS):                                                    # своя команда
        pn.circle((p[0] + 8 * math.sin(t * 2.4 + i), p[1]), 30, fill=TEAL, outline=WHITE, w=4, a=a, shadow=True)
    bp = PASS_PTS[0]
    stars = 0
    for i, t0 in enumerate(PASS_T):
        u = eo(t, t0, 0.35)
        if u > 0:
            arrow(pn, PASS_PTS[i], lerp2(PASS_PTS[i], PASS_PTS[i + 1], u * 0.88), SUN, 10, 1, 30)
            bp = lerp2(PASS_PTS[i], PASS_PTS[i + 1], u)
            if u >= 1:
                stars += 1
    ball(pn, (bp[0] + 32, bp[1] - 20), 20, t * 6, shadow=False)
    for i in range(stars):                                                              # «опасный момент»
        p = PASS_PTS[i + 1]
        sparkle(pn, (p[0] + 60, p[1] - 60), 34 * back(t, PASS_T[i] + 0.35, 0.3), SUN)
    if t >= 11.09:
        u = back(t, 11.09, 0.35)
        pn.circle((700, 300), 52 * u, fill=RED, shadow=True)
        pn.text((700, 304), "!", 70 * u, WHITE, shadow=False)


G_PXM, G_X, G_Y = 22.0, 540, 290


def _GP(x, y):
    return (G_X + G_PXM * x, G_Y + G_PXM * y)


def sc_goal(pn, t):
    """11.78–14.60 «С какой вероятностью удар с этой точки становится голом»: модель угла на ворота (FIFA)."""
    pn.rrect((-20, 150, W + 20, 1400), 0, fill=GRASS)
    for k in range(0, 14, 2):
        pn.rrect((-20, 150 + k * 90, W + 20, 150 + (k + 1) * 90), 0, fill=GRASS2)
    a = eo(t, 11.78, 0.35)
    lc = WHITE
    pn.line([(20, G_Y), (W - 20, G_Y)], lc, 6, a)
    x0, y0 = _GP(-20.16, 0); x1, y1 = _GP(20.16, 16.5)
    pn.rrect((x0, y0, x1, y1), 0, outline=lc, w=6, a=a)
    x0, y0 = _GP(-9.16, 0); x1, y1 = _GP(9.16, 5.5)
    pn.rrect((x0, y0, x1, y1), 0, outline=lc, w=6, a=a)
    cx, cy = _GP(0, 11)
    th = math.degrees(math.acos((16.5 - 11) / 9.15))
    pn.arc((cx, cy), 9.15 * G_PXM, 90 - th, 90 + th, lc, 6, a)
    gx0, gy0 = _GP(-GOAL_HALF, -2.0); gx1, _ = _GP(GOAL_HALF, 0)
    pn.rrect((gx0, gy0, gx1, G_Y), 4, fill=(200, 210, 230), outline=WHITE, w=7, a=a)
    for i in range(1, 8):                                           # сетка ворот
        xx = lerp(gx0, gx1, i / 8)
        pn.line([(xx, gy0), (xx, G_Y)], (150, 160, 180), 2, a, caps=False)
    kx = G_X + 50 * math.sin(t * 3)                                 # вратарь
    tri_char(pn, (kx, G_Y - 10), 70 * a, t, SUN, "worried", (0, 1))
    for pt, t0, col, lab in ((PT_A, 12.20, TEAL, f"{round(ANG_A)}°"), (PT_B, 13.20, RED, f"{round(ANG_B)}°")):
        if t < t0:
            continue
        p = _GP(*pt)
        u = eo(t, t0 + 0.1, 0.35)
        l, r_ = _GP(-GOAL_HALF, 0), _GP(GOAL_HALF, 0)
        L, Rr = lerp2(p, l, u), lerp2(p, r_, u)
        pn.poly([p, L, Rr], fill=col + (110,))
        pn.line([L, p, Rr], col, 6)
        ball(pn, p, 22 * back(t, t0, 0.3), t * 2)
        pos = (p[0] + 120, p[1] + 10) if pt == PT_A else (p[0], p[1] + 80)
        pn.text(pos, lab, 60, col, a=eo(t, t0 + 0.3, 0.2))
    pn.text((540, 860), "УГОЛ НА ВОРОТА", 50, WHITE, a=a)
    if t >= 13.96:
        u = back(t, 13.96, 0.4)
        pn.text((320, 1030), f"{round(ANG_A)}°", 130 * u, TEAL)
        pn.text((540, 1030), ">", 110 * u, WHITE)
        pn.text((760, 1030), f"{round(ANG_B)}°", 130 * u, RED)


def sc_europe(pn, t):
    """14.60–16.00 «У ведущих европейских» — стадионы разных клубов вырастают на холмах."""
    world(pn, t, 1100)
    grass(pn, 1100)
    for (x, y, s, fl, t0) in ((250, 900, 330, (BLUE, WHITE), 14.79), (560, 760, 380, (RED, WHITE), 14.92),
                              (860, 920, 330, (SUN, BLUE), 15.37)):
        stadium(pn, (x, y), s * back(t, t0, 0.45), fl, t=t)
        if t >= t0 + 0.3:
            sparkle(pn, (x + 0.35 * s, y - 0.45 * s), 22 * (0.7 + 0.3 * math.sin(t * 8 + x)), SUN)


def sc_dept(pn, t):
    """16.00–17.93 «клубов есть целый отдел аналитиков» — трое аналитиков, мониторы с графиками, фото автора на стене."""
    pn.rrect((-20, 150, W + 20, 1180), 0, fill=(34, 38, 58))
    pn.rrect((-20, 1180, W + 20, 1400), 0, fill=(52, 46, 44))
    if t >= 16.10:                                                  # полароид автора на стене
        u = back(t, 16.10, 0.45)
        pn.paste(polaroid("IMG_8876", 230, (0.05, 0.0, 0.95, 0.62)), 930, 460, k=u, rot=-7)
        pn.circle((930, 190), 12 * cl(u), fill=RED)
    flash = eo(t, 17.10, 0.35)
    for i, (x, t0) in enumerate(((190, 16.04), (500, 16.37), (810, 16.54))):
        k = back(t, t0, 0.4)
        monitor(pn, (x - 140, 520, x + 140, 740), t, seed=i, chart=0.1 + 0.9 * flash, k=k)
        human(pn, x, 1345, 520, t, (BLUE, TEAL, (140, 110, 220))[i], arm="hold", glasses=i != 1,
              mood="proud" if flash > 0.5 else "happy", look=(0, -1), k=k)
        if k > 0.5:
            pn.rrect((x - 90, 1080, x + 90, 1130), 8, fill=GREY, outline=WHITE, w=3)
        if flash > 0:
            sparkle(pn, (x + 120, 500), 26 * flash * (0.7 + 0.3 * math.sin(t * 9 + i)), SUN)


def _skyline(pn, y, t):
    for i in range(12):
        x = i * 95 - 20
        h = 160 + 90 * ((i * 5) % 4)
        pn.rrect((x, y - h, x + 80, y), 4, fill=(38, 44, 68))
        for j in range(int(h / 50)):
            if (i + j + int(t * 2)) % 3:
                pn.rrect((x + 18, y - h + 20 + j * 50, x + 34, y - h + 36 + j * 50), 2, fill=SUN, a=0.5)


def sc_liverpool(pn, t):
    """17.93–20.80 «В Ливерпуле такой отдел годами возглавлял не бывший футболист»."""
    world(pn, t, 1100, sun_=False)
    _skyline(pn, 1100, t)
    grass(pn, 1100)
    stadium(pn, (540, 820), 560 * back(t, 17.95, 0.5), (RED, WHITE), t=t)
    if t >= 19.32:                                                  # «годами» — листаются страницы календаря
        u = back(t, 19.32, 0.35)
        x0, y0 = 780, 180
        pn.rrect((x0, y0, x0 + 240 * u, y0 + 230 * u), 16, fill=WHITE, shadow=True)
        pn.rrect((x0, y0, x0 + 240 * u, y0 + 56 * u), 16, fill=RED)
        n = int((t - 19.32) / 0.1)
        fl = ((t - 19.32) / 0.1) % 1
        for j in range(3):
            pn.line([(x0 + 30, y0 + 100 + j * 40), (x0 + 210 * u, y0 + 100 + j * 40)], GREY, 6, u)
        if t < 20.2:
            pn.poly([(x0, y0 + 56), (x0 + 240, y0 + 56), (x0 + 240, y0 + 56 + 170 * (1 - fl)), (x0, y0 + 56 + 170 * (1 - fl))],
                    fill=(235, 235, 240), a=0.9 * u)
    if t >= 19.93:                                                  # «не бывший футболист»
        human(pn, 250, 1345, 560, t, TEAL, num="9", mood="worried" if t > 20.4 else "happy",
              k=back(t, 19.93, 0.35))
        ball(pn, (380, 1305), 36, t)
        if t >= 20.40:
            cross(pn, (250, 1040), 190, RED, 1, eo(t, 20.40, 0.25), 22)


def _atom(pn, c, R_, t, a=1.0):
    for k in range(3):
        ang = math.radians(60 * k)
        pts = []
        for i in range(61):
            u = 2 * math.pi * i / 60
            x, y = R_ * math.cos(u), R_ * 0.36 * math.sin(u)
            pts.append((c[0] + x * math.cos(ang) - y * math.sin(ang), c[1] + x * math.sin(ang) + y * math.cos(ang)))
        pn.line(pts, WHITE, 5, a * 0.8, caps=False)
        u = 2 * math.pi * (1.3 * t + k / 3)
        x, y = R_ * math.cos(u), R_ * 0.36 * math.sin(u)
        pn.circle((c[0] + x * math.cos(ang) - y * math.sin(ang), c[1] + x * math.sin(ang) + y * math.cos(ang)),
                  18, fill=TEAL, a=a)
    pn.circle(c, 44 * (1 + 0.15 * math.sin(t * 8)), fill=BLUE, outline=WHITE, w=4, a=a, shadow=True)


def sc_physicist(pn, t):
    """20.80–21.90 «а доктор физики» — учёный в халате, атом, шапочка PhD."""
    world(pn, t, 1180, sun_=False, birds=False)
    pn.rrect((-20, 1180, W + 20, 1400), 0, fill=(46, 42, 40))
    k = back(t, 20.82, 0.4)
    r = human(pn, 300, 1345, 720, t, BLUE, arm="point", coat=True, glasses=True, mood="proud", look=(1, -0.5), k=k)
    _atom(pn, (760, 560), 250 * back(t, 20.9, 0.5), t)
    if r and t >= 21.37:
        hc, hr, _ = r
        mortarboard(pn, (hc[0], hc[1] - hr * 0.95), back(t, 21.37, 0.35))
        pn.text((760, 930), "PhD", 120 * back(t, 21.37, 0.4), SUN)


def sc_trophy(pn, t):
    """21.90–25.05 «И клуб выиграл Лигу чемпионов и чемпионат Англии» — два кубка, конфетти, прыжки."""
    world(pn, t, 1120, sun_=False)
    grass(pn, 1120)
    confetti(pn, t, 22.47)
    jump = 70 * abs(math.sin((t - 22.5) * 6)) if t > 22.5 else 0
    human(pn, 540, 1345, 600, t, TEAL, num="10", arm="up" if t > 22.5 else "idle", arm_l="up" if t > 22.5 else "idle",
          mood="proud" if t > 22.5 else "happy", jump=jump, k=back(t, 21.92, 0.4))
    trophy(pn, (230, 760), 380 * back(t, 22.47, 0.45))
    trophy(pn, (850, 760), 380 * back(t, 23.80, 0.45))
    for i, (x, t0) in enumerate(((230, 22.8), (850, 24.1))):
        if t >= t0:
            sparkle(pn, (x + 150, 460), 30 * (0.7 + 0.3 * math.sin(t * 9 + i)), WHITE)


def sc_profession(pn, t):
    """25.05–29.05 «Спортивная аналитика — профессия на стыке любви к игре и математики» — пазл из двух половин."""
    world(pn, t, 1200, birds=False)
    if 25.85 <= t < 27.3:                                           # мысль автора — график
        a = eo(t, 25.85, 0.3) * (1 - pp(t, 27.0, 0.3))
        for i, (x, y, r) in enumerate(((600, 860, 18), (650, 790, 28))):
            pn.circle((x, y), r, fill=WHITE, a=a)
        pn.rrect((560, 420, 980, 740), 60, fill=WHITE, a=a, shadow=True)
        graph_icon(pn, (770, 590), 280, eo(t, 26.0, 0.8), a)
    if t >= 27.16:                                                  # пазл: слева игра, справа математика
        u = eo(t, 27.16, 0.45)
        lx = lerp(-400, 110, u); rx = lerp(1480, 540, u)
        pn.rrect((lx, 250, lx + 430, 640), 30, fill=TEAL, outline=WHITE, w=6, shadow=True)
        pn.circle((lx + 430, 445), 62, fill=TEAL)
        pn.rrect((rx, 250, rx + 430, 640), 30, fill=BLUE, outline=WHITE, w=6, shadow=True)
        pn.circle((rx, 445), 66, fill=DARK)
        pn.circle((lx + 430, 445), 60, fill=TEAL)
        if t >= 27.67:
            k2 = back(t, 27.67, 0.4)
            heart(pn, (lx + 200, 420), 110 * k2 * (1 + 0.06 * math.sin(t * 8)), RED)
            ball(pn, (lx + 290, 540), 52 * k2, t * 2)
        if t >= 28.40:
            pn.text((rx + 230, 445), "x²", 150 * back(t, 28.40, 0.4), WHITE)
        if u >= 1:
            for i in range(4):
                sparkle(pn, (540 + 30 * math.cos(i * 1.6), 250 + 395 * (i % 2)), 26 * eo(t, 27.62 + 0.06 * i, 0.2), SUN)
    pn.paste(sticker("IMG_9325", 600), 300 if t >= 27.16 else 380, 1395, k=back(t, 25.1, 0.45))


SCHOOL_F = [("P(A) = m / n", 32.05), ("(a + b + c) / 3", 32.35), ("y = kx + b", 32.60)]


def sc_school(pn, t):
    """29.05–33.60 «Вероятность, статистика, работа с графиками — ровно то, что есть в школьной программе»."""
    fly = eo(t, 31.76, 0.45)
    for i, (x, t0) in enumerate(((210, 29.34), (540, 29.94), (870, 30.42))):
        if t < t0:
            continue
        k = back(t, t0, 0.4)
        c = lerp2((x, 400), (300 + 120 * i, 860), fly)
        s = 270 * k * (1 - 0.7 * fly)
        a = 1 - pp(t, 32.0, 0.25)
        if a <= 0:
            continue
        tile(pn, c, s, a)
        if i == 0:
            dice(pn, c, s * 0.5, 25 * math.sin((t - t0) * 6) * (1 - pp(t, t0, 0.8)), a)
        elif i == 1:
            bars_icon(pn, c, s * 0.8, eo(t, t0, 0.6), a)
        else:
            graph_icon(pn, c, s * 0.8, eo(t, t0, 1.0), a)
    if t >= 31.76:                                                  # школьная доска
        u = back(t, 31.76, 0.45)
        y0 = lerp(1400, 620, u)
        pn.rrect((70, y0, 760, y0 + 600), 18, fill=BOARD, outline=(140, 96, 56), w=14, shadow=True)
        for j, (fml, t0) in enumerate(SCHOOL_F):
            if t >= t0:
                n = int(round(len(fml) * pp(t, t0, 0.35)))
                pn.text((110, y0 + 130 + j * 170), fml[:n], 60, CHALK, anchor="lm", shadow=False)
    if t >= 31.90:
        pn.paste(sticker("IMG_9338", 640), 900, 1395, k=back(t, 31.90, 0.45))


def sc_kid(pn, t):
    """33.60–37.45 «Если ваш ребёнок живёт футболом — это отличный повод полюбить математику»."""
    world(pn, t, 1100)
    grass(pn, 1100)
    r = human(pn, 330, 1345, 640, t, TEAL, arm="up", arm_l="up", mood="happy", look=(0, -1),
              k=back(t, 33.62, 0.45))
    if r:
        hc, hr, _ = r
        by = hc[1] - hr - 60 - 190 * abs(math.sin((t - 33.6) * 3.2))
        ball(pn, (hc[0], by), 50, t * 5)
    if t >= 36.01:
        bulb(pn, (800, 300), 70 * back(t, 36.01, 0.35), eo(t, 36.1, 0.25))
    if t >= 36.27:
        k = back(t, 36.27, 0.45)
        c = (780, 720)
        heart(pn, c, 200 * k * (1 + 0.06 * math.sin((t - 36.3) * 8)), RED)
        ang = (t - 36.27) * 3
        ball(pn, (c[0] + 260 * math.cos(ang) * k, c[1] + 120 * math.sin(ang) * k), 36 * k, t * 4)
        if t >= 36.66:
            pn.text((c[0], c[1] - 10), "x²", 110 * back(t, 36.66, 0.35), WHITE)


def _gear(pn, c, r, rot, col=GREY):
    pts = []
    for i in range(32):
        rr = r if (i // 2) % 2 == 0 else r * 0.78
        ang = math.radians(rot + i * 360 / 32)
        pts.append((c[0] + rr * math.cos(ang), c[1] + rr * math.sin(ang)))
    pn.poly(pts, fill=col, outline=WHITE, w=4)
    pn.circle(c, r * 0.3, fill=DARK)


def sc_strength(pn, t):
    """37.45–40.06 «Если хотите превратить его увлечение в сильную сторону» — машина превращает мяч в звезду-медаль."""
    world(pn, t, 1100, birds=False)
    grass(pn, 1100)
    proud = t >= 39.5
    human(pn, 200, 1345, 600, t, TEAL, arm="up" if proud else "idle", mood="proud" if proud else "happy",
          look=(1, 0), k=back(t, 37.47, 0.4))
    k = back(t, 37.6, 0.45)
    shake = 6 * math.sin(t * 40) if 38.74 <= t < 39.2 else 0
    mx, my = 560 + shake, 760
    pn.rrect((mx - 150 * k, my - 150 * k, mx + 150 * k, my + 170 * k), 26, fill=BLUE, outline=WHITE, w=6, shadow=True)
    pn.poly([(mx - 110 * k, my - 150 * k), (mx + 110 * k, my - 150 * k), (mx + 40 * k, my - 230 * k),
             (mx - 40 * k, my - 230 * k)][::-1], fill=GREY, outline=WHITE, w=4)
    if k > 0.3:
        _gear(pn, (mx - 45, my + 20), 60 * k, t * 180)
        _gear(pn, (mx + 60, my + 70), 42 * k, -t * 240, SUN)
    if t < 38.18:
        ball(pn, (330, 1300), 40, t * 2)
    elif t < 38.56:
        u = eo(t, 38.18, 0.38)
        ball(pn, (lerp(330, mx, u), lerp(1300, my - 250, u) - 300 * math.sin(math.pi * u)), 40, t * 8)
    if t >= 39.22:                                                  # «сильную» — звезда-медаль вылетает
        u = eo(t, 39.22, 0.4)
        c = lerp2((mx + 150, my), (860, 420), u)
        s = 130 * back(t, 39.22, 0.45)
        star = [(c[0] + (s if i % 2 == 0 else s * 0.45) * math.cos(math.radians(-90 + 36 * i)),
                 c[1] + (s if i % 2 == 0 else s * 0.45) * math.sin(math.radians(-90 + 36 * i))) for i in range(10)]
        pn.poly(star, fill=SUN, outline=WHITE, w=5, shadow=True)
    if t >= 39.50:                                                  # «сторону» — шкала силы
        f = eo(t, 39.5, 0.45)
        pn.rrect((930, 620, 1000, 1180), 30, fill=(60, 64, 86), outline=WHITE, w=4)
        pn.rrect((936, 1174 - 548 * f, 994, 1174), 26, fill=TEAL)


def sc_cta(pn, t):
    """40.06–41.90 «Напишите в комментариях слово „пробное“» — окно комментариев (текст «ПРОБНОЕ» не дублируем, §3)."""
    world(pn, t, 1250, birds=False)
    k = back(t, 40.08, 0.45)
    if k <= 0:
        return
    box = (110, 190, 970, 1060)
    c = (540, 620)
    bx = [lerp(c[0], box[0], k), lerp(c[1], box[1], k), lerp(c[0], box[2], k), lerp(c[1], box[3], k)]
    pn.rrect(bx, 36, fill=(26, 28, 42), outline=(90, 96, 124), w=5, shadow=True)
    if k < 0.97:
        return
    for i, y in enumerate((280, 420, 560)):
        a = eo(t, 40.15 + 0.1 * i, 0.25)
        pn.circle((200, y + 22), 36, fill=(90, 96, 124), a=a)
        pn.rrect((265, y, 265 + 480 - 90 * i, y + 24), 12, fill=(80, 86, 112), a=a)
        pn.rrect((265, y + 40, 265 + 330 + 60 * i, y + 64), 12, fill=(60, 64, 86), a=a)
    pn.rrect((150, 930, 800, 1010), 40, fill=(40, 44, 62), outline=(90, 96, 124), w=3)
    if t < 41.36:
        if (t * 2) % 1 < 0.6:
            pn.line([(195, 950), (195, 990)], WHITE, 4)
        if t >= 40.60:
            for i in range(3):
                pn.circle((250 + 34 * i, 970 - 8 * max(0.0, math.sin(t * 9 - i))), 9, fill=GREY)
    pul = 1 + 0.08 * math.sin((t - 40.6) * 8) if 40.6 < t < 41.4 else 1
    pn.circle((880, 970), 48 * pul, fill=BLUE, shadow=True)
    pn.poly([(858, 945), (910, 970), (858, 995), (868, 970)], fill=WHITE)
    if t >= 41.36:                                                  # комментарий отправлен — улетает вверх в ленту
        u = back(t, 41.36, 0.4)
        y = lerp(930, 700, u)
        pn.rrect((150, y, 930, y + 150), 30, fill=(36, 60, 130), outline=BLUE, w=4, a=cl(u * 2), shadow=True)
        pn.circle((225, y + 75), 42, fill=TEAL, a=cl(u * 2))
        pn.rrect((295, y + 50, 560, y + 100), 16, fill=RED, a=cl(u * 2))      # слово-кодовое — плашкой без букв
        heart(pn, (860, y + 110), 38 * back(t, 41.6, 0.35), RED)


CAL_DAY = 9


def sc_lesson(pn, t):
    """41.90–44.72 «Запишу его на первое занятие» — календарь, день с галочкой, автор — «палец вверх»."""
    world(pn, t, 1250, birds=False)
    k = back(t, 41.92, 0.45)
    x0, y0, x1, y1 = 90, 200, 800, 1040
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    b = (lerp(cx, x0, k), lerp(cy, y0, k), lerp(cx, x1, k), lerp(cy, y1, k))
    pn.rrect(b, 34, fill=(30, 33, 48), outline=(90, 96, 124), w=5, shadow=True)
    if k >= 0.97:
        pn.rrect((x0, y0, x1, y0 + 110), 34, fill=BLUE)
        pn.rrect((x0, y0 + 60, x1, y0 + 110), 0, fill=BLUE)
        for i in range(2):                                          # кольца календаря
            pn.rrect((250 + 300 * i, y0 - 30, 270 + 300 * i, y0 + 40), 10, fill=GREY, outline=WHITE, w=3)
        for j, wd in enumerate(("ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС")):
            pn.text((150 + 98 * j, y0 + 160), wd, 28, GREY, shadow=False)
        for day in range(1, 31):
            row, col = (day - 1) // 7, (day - 1) % 7
            a = eo(t, 42.0 + 0.06 * row, 0.2)
            p = (150 + 98 * col, y0 + 260 + 118 * row)
            if day == CAL_DAY and t >= 42.72:
                pn.circle(p, 50 * back(t, 42.72, 0.35), fill=TEAL, shadow=True)
                if t >= 43.00:
                    pn.line(part([(p[0] - 22, p[1] + 2), (p[0] - 6, p[1] + 18), (p[0] + 24, p[1] - 16)],
                                     eo(t, 43.0, 0.3)), INK, 9)
                    continue
            pn.text(p, str(day), 34, WHITE, a=a, shadow=False)
    if t >= 42.20:
        pn.paste(sticker("IMG_9340", 560, (0, 0, 1, 0.72)), 880, 1395, k=back(t, 42.20, 0.45))
    for i in range(3):
        sparkle(pn, (820 + 70 * i, 300 + 50 * (i % 2)), 22 * eo(t, 43.2 + 0.12 * i, 0.2) * (0.7 + 0.3 * math.sin(t * 9 + i)),
                SUN)


FN = {"buy": sc_buy, "scout": sc_scout, "analyst": sc_analyst, "pressure": sc_pressure, "pass": sc_pass,
      "goal": sc_goal, "europe": sc_europe, "dept": sc_dept, "liverpool": sc_liverpool, "physicist": sc_physicist,
      "trophy": sc_trophy, "profession": sc_profession, "school": sc_school, "kid": sc_kid, "strength": sc_strength,
      "cta": sc_cta, "lesson": sc_lesson}


def scene_at(t):
    for a, b, n in SCENES:
        if a <= t < b:
            return a, b, n
    return SCENES[-1]


def art(t, qa=False):
    a, b, n = scene_at(t)
    pn = Pen(t, qa)
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


def snaps(ts):
    for t in ts:
        frame(int(round(float(t) * FPS))).save(f"{TMPD}/_cart19_{float(t):05.2f}.png")
    print("кадры:", len(ts))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "snap":
        snaps(sys.argv[2:])
    else:
        main()
