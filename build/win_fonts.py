"""Windows: замена SF Pro Expanded Black (macOS) в движке субтитров v3.

captions.wide() на Windows открыл бы Onest и не нашёл бы оси Width — текст вышел бы узким обычным.
Выбор автора ролика (2026-09-24, ПРАВИЛА-МОНТАЖА.md): Unbounded Black (OFL, кириллица), wght 900.
Импортировать ДО создания Captions: `import win_fonts` в render<N>.py / sfx<N>.py.
"""
import os
from PIL import ImageFont
import captions

FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "Unbounded.ttf")
_cache = {}


def wide(size):
    if size not in _cache:
        f = ImageFont.truetype(FONT, size)
        f.set_variation_by_axes([900])
        _cache[size] = f
    return _cache[size]


if not os.path.exists("/System/Library/Fonts/SFNS.ttf"):
    captions.wide = wide
