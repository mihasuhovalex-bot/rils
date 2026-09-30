"""Графики и чертежи-модели на сетке карточки A — с 2026-09-28 (твоё: «графики строить, модели чертить»).
Общий модуль: в параллельной работе только читать (меняет чат A). ПРАВИЛА-МОНТАЖА.md §4 «Графики и модели».

Перекрывает запрет гайда «максимум число + подпись» — с защитой от бага, из-за которого он появился
(графика наезжала на субтитры): всё рисуется в координатах карточки A (870×1380) только в ЗОНЕ ГРАФИКИ
x 60…810, y 60…1130 (абсолютно y ≤ 1368 < 1400), субтитры — внизу (y 1500); пересечение проверять
`overlap_px(layer, subtitle_layer)` — норма 0. Математика буквальная: фигуры замкнуты, оси подписаны.
Стиль: белые линии 4px, акцент синий #5B7CFF / бирюза / красный, шрифт Unbounded (captions.wide), без свечения.
Анимация входа ease-out, элементы каскадом; всё детерминировано от t (seek-safe).

    import diagrams_v1 as D
    layer = D.line_chart(t, t0, pts, box=(110, 160, 790, 900), x_label="годы", y_label="₽", end_label="×3")
    layer = D.bar_chart(t, t0, values=[3, 5, 9], labels=["2020", "2022", "2024"])
    layer = D.eratosthenes(t, t0)           # модель: Земля, Сиена/Александрия, параллельные лучи, палка, 7°
    canvas.alpha_composite(layer, (CARD_A[0], CARD_A[1]))
"""
import math
import numpy as np
from PIL import Image, ImageDraw

import win_fonts  # noqa: F401 — Unbounded вместо SF Pro
import captions
from style import CARD_A, ease_out

CW, CH = CARD_A[2], CARD_A[3]
SS = 2                                          # суперсэмплинг для гладких линий
WHITE = (255, 255, 255)
BLUE = (91, 124, 255)
TEAL = (45, 225, 194)
RED = (255, 59, 48)
ZONE = (60, 60, 810, 1130)                      # зона графики в координатах карточки


def _canvas():
    im = Image.new("RGBA", (CW * SS, CH * SS), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def _done(im):
    return im.resize((CW, CH), Image.LANCZOS)


def _p(t, t0, dur):
    return ease_out(min(1.0, max(0.0, (t - t0) / dur))) if t >= t0 else 0.0


def _s(v):
    """Координаты в суперсэмплинг: число, (x, y), [x0, y0, x1, y1] или список точек [(x, y), …]."""
    if isinstance(v, (list, tuple)):
        if v and isinstance(v[0], (list, tuple)):
            return [(p[0] * SS, p[1] * SS) for p in v]
        return [c * SS for c in v]
    return v * SS


def _text(d, xy, s, size, fill=WHITE, anchor="mm", alpha=1.0):
    if alpha <= 0:
        return
    f = captions.wide(size * SS)
    col = fill + (int(255 * alpha),)
    d.text((xy[0] * SS + 3 * SS, xy[1] * SS + 4 * SS), s, font=f, anchor=anchor, fill=(0, 0, 0, int(150 * alpha)))
    d.text(_s(xy), s, font=f, anchor=anchor, fill=col)


def _polyline_part(d, pts, frac, fill, width):
    """Нарисовать ломаную до доли frac её длины; вернуть точку «головы»."""
    segs = list(zip(pts, pts[1:]))
    lens = [math.dist(a, b) for a, b in segs]
    total, acc = sum(lens), 0.0
    target = total * frac
    head = pts[0]
    for (a, b), L in zip(segs, lens):
        if acc + L <= target:
            d.line(_s([a, b]), fill=fill, width=width * SS)
            head = b
        else:
            r = (target - acc) / L if L else 0
            head = (a[0] + (b[0] - a[0]) * r, a[1] + (b[1] - a[1]) * r)
            d.line(_s([a, head]), fill=fill, width=width * SS)
            break
        acc += L
    return head


def _axes(d, box, alpha, x_label=None, y_label=None):
    x0, y0, x1, y1 = box
    col = WHITE + (int(210 * alpha),)
    d.line(_s([(x0, y1), (x1, y1)]), fill=col, width=4 * SS)
    d.line(_s([(x0, y1), (x0, y0)]), fill=col, width=4 * SS)
    for (ax, ay), pts in (((x1, y1), [(x1 - 18, y1 - 10), (x1, y1), (x1 - 18, y1 + 10)]),
                          ((x0, y0), [(x0 - 10, y0 + 18), (x0, y0), (x0 + 10, y0 + 18)])):
        d.line(_s(pts), fill=col, width=4 * SS)
    if x_label:
        _text(d, (x1, y1 + 42), x_label, 30, anchor="rm", alpha=alpha)
    if y_label:
        _text(d, (x0 + 16, y0 - 8), y_label, 30, anchor="lb", alpha=alpha)


def line_chart(t, t0, pts, box=(110, 160, 790, 900), x_label=None, y_label=None, end_label=None,
               color=BLUE, dur=1.2):
    """Линия рисуется слева направо за dur; pts — данные (x, y) в любых единицах, масштабируются в box."""
    im, d = _canvas()
    a_ax = _p(t, t0, 0.25)
    _axes(d, box, a_ax, x_label, y_label)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    x0, y0, x1, y1 = box
    pad = 40
    mx = lambda x: x0 + pad + (x - min(xs)) / ((max(xs) - min(xs)) or 1) * (x1 - x0 - 2 * pad)
    my = lambda y: y1 - pad - (y - min(ys)) / ((max(ys) - min(ys)) or 1) * (y1 - y0 - 2 * pad)
    P = [(mx(x), my(y)) for x, y in pts]
    frac = _p(t, t0 + 0.2, dur)
    if frac > 0:
        head = _polyline_part(d, P, frac, color + (255,), 7)
        r = 12
        d.ellipse(_s([head[0] - r, head[1] - r, head[0] + r, head[1] + r]), fill=color + (255,))
    if end_label and frac >= 1.0:
        a = _p(t, t0 + 0.2 + dur, 0.25)
        _text(d, (P[-1][0], P[-1][1] - 60), end_label, 64, fill=color, alpha=a)
    return _done(im)


def bar_chart(t, t0, values, labels=None, box=(110, 200, 790, 900), color=BLUE, value_fmt="{:g}",
              highlight=None, stagger=0.09, dur=0.5):
    """Столбики растут каскадом; highlight — индекс столбика другим цветом (бирюза)."""
    im, d = _canvas()
    _axes(d, box, _p(t, t0, 0.25))
    x0, y0, x1, y1 = box
    n = len(values)
    slot = (x1 - x0 - 40) / n
    bw = slot * 0.62
    vmax = max(values) or 1
    for i, v in enumerate(values):
        p = _p(t, t0 + 0.2 + i * stagger, dur)
        h = (y1 - y0 - 80) * v / vmax * p
        cx = x0 + 20 + slot * (i + 0.5)
        col = (TEAL if i == highlight else color) + (255,)
        if h > 1:
            d.rounded_rectangle(_s([cx - bw / 2, y1 - h, cx + bw / 2, y1 - 2]), radius=10 * SS, fill=col)
        if p >= 1.0:
            _text(d, (cx, y1 - h - 34), value_fmt.format(v), 40, fill=col[:3], alpha=_p(t, t0 + 0.2 + i * stagger + dur, 0.2))
        if labels:
            _text(d, (cx, y1 + 40), labels[i], 30, alpha=_p(t, t0, 0.25))
    return _done(im)


def _arc_pts(c, r, a0, a1, steps=40):
    """Точки дуги окружности (углы в градусах, 0 = вправо, по часовой — вниз, как в PIL)."""
    return [(c[0] + r * math.cos(math.radians(a0 + (a1 - a0) * k / steps)),
             c[1] + r * math.sin(math.radians(a0 + (a1 - a0) * k / steps))) for k in range(steps + 1)]


def eratosthenes(t, t0, angle_draw=25, angle_label="7°"):
    """Модель Эратосфена по шагам (угол на чертеже преувеличен до angle_draw° для читаемости, подписан 7°):
    0.0 Земля; 0.5 центр и радиусы к Сиене и Александрии; 0.9 параллельные лучи солнца сверху (каждый
    кончается НА поверхности); 1.3 палка в Александрии, луч мимо её вершины падает на землю — тень;
    1.7 угол у палки и тот же угол в центре Земли (синие дуги, «7°»)."""
    im, d = _canvas()
    C, R = (435, 740), 300
    a = math.radians(angle_draw)
    S = (C[0], C[1] - R)                                           # Сиена — солнце в зените
    A = (C[0] + R * math.sin(a), C[1] - R * math.cos(a))           # Александрия
    L = 110                                                        # длина палки
    T = (A[0] + L * math.sin(a), A[1] - L * math.cos(a))           # вершина палки (по радиусу наружу)
    ground_y = lambda x: C[1] - math.sqrt(max(0.0, R * R - (x - C[0]) ** 2))
    SUN = (255, 214, 90)
    # 1. Земля
    p = _p(t, t0, 0.6)
    if p > 0:
        d.line(_s(_arc_pts(C, R, -90, -90 + 360 * p, 90)), fill=WHITE + (235,), width=5 * SS)
    # 2. центр и радиусы
    p = _p(t, t0 + 0.5, 0.35)
    if p > 0:
        r = 9
        d.ellipse(_s([C[0] - r, C[1] - r, C[0] + r, C[1] + r]), fill=WHITE + (255,))
        for Q in (S, A):
            d.line(_s([C, (C[0] + (Q[0] - C[0]) * p, C[1] + (Q[1] - C[1]) * p)]), fill=WHITE + (170,), width=3 * SS)
        _text(d, (S[0], 150), "сиена", 26, anchor="mm", alpha=p)                # подписи — над своими лучами
        _text(d, (T[0] + 10, 150), "александрия", 26, anchor="mm", alpha=p)
    # 3. параллельные лучи сверху: к Сиене (по радиусу), мимо вершины палки (до земли — тень), и третий слева
    rays = [S[0], T[0], C[0] - 170]
    p = _p(t, t0 + 0.9, 0.4)
    if p > 0:
        for x in rays:
            y0, y1 = 170, ground_y(x)
            y = y0 + (y1 - y0) * p
            d.line(_s([(x, y0), (x, y)]), fill=SUN + (230,), width=4 * SS)
            d.line(_s([(x - 12, y - 18), (x, y), (x + 12, y - 18)]), fill=SUN + (230,), width=4 * SS)
        _text(d, (rays[2], 105), "лучи солнца", 26, fill=SUN, anchor="mm", alpha=p)
    # 4. палка и тень (от основания палки до точки, куда падает луч мимо её вершины)
    p = _p(t, t0 + 1.3, 0.3)
    if p > 0:
        top = (A[0] + (T[0] - A[0]) * p, A[1] + (T[1] - A[1]) * p)
        d.line(_s([A, top]), fill=WHITE + (255,), width=8 * SS)
        if p >= 1.0:
            sh_x = T[0]
            ang0 = math.degrees(math.atan2(A[1] - C[1], A[0] - C[0]))
            ang1 = math.degrees(math.atan2(ground_y(sh_x) - C[1], sh_x - C[0]))
            d.line(_s(_arc_pts(C, R, ang0, ang1, 12)), fill=(170, 170, 170, 255), width=10 * SS)
    # 5. углы: у вершины палки (между палкой и лучом) и в центре (между радиусами) — равны
    p = _p(t, t0 + 1.7, 0.4)
    if p > 0:
        col = BLUE + (255,)
        stick_dir = math.degrees(math.atan2(A[1] - T[1], A[0] - T[0]))      # от вершины вниз к основанию
        d.line(_s(_arc_pts(T, 70, stick_dir, stick_dir + (90 - stick_dir) * p)), fill=col, width=6 * SS)
        rad_dir = math.degrees(math.atan2(A[1] - C[1], A[0] - C[0]))
        d.line(_s(_arc_pts(C, 120, -90, -90 + (rad_dir + 90) * p)), fill=col, width=6 * SS)
        if p >= 1.0:
            al = _p(t, t0 + 2.1, 0.25)
            _text(d, (T[0] + 70, T[1] + 95), angle_label, 46, fill=BLUE, alpha=al)
            _text(d, (C[0] + 45, C[1] - 165), angle_label, 46, fill=BLUE, alpha=al)
    return _done(im)


def outside_zone_px(graphic, thr=40):
    """Пиксели графики вне ZONE (в т.ч. за краем карточки). Норма — 0."""
    a = np.array(graphic.split()[3]) > thr
    x0, y0, x1, y1 = ZONE
    a[y0:y1, x0:x1] = False
    return int(a.sum())


def overlap_px(graphic, subtitles, thr=40):
    """Число общих пикселей (альфа > thr) слоя графики (размер карточки, будет сдвинут на CARD_A) и слоя
    субтитров (весь холст). Норма — 0."""
    g = np.array(graphic.split()[3]) > thr
    s = np.array(subtitles.split()[3])[CARD_A[1]:CARD_A[1] + CH, CARD_A[0]:CARD_A[0] + CW] > thr
    return int((g & s).sum())
