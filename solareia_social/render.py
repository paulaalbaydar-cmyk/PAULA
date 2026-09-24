"""Genera la imagen del post con la identidad visual de Solareia (Pillow)."""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .config import BRAND, FONTS_DIR, IMAGE_SIZE, LOGO_PATH

W, H = IMAGE_SIZE
MARGIN = 80
TOP_BAR = 100
FOOTER_H = 230


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf"
    return ImageFont.truetype(str(FONTS_DIR / name), size)


def _text_w(draw: ImageDraw.ImageDraw, text: str, font) -> float:
    return draw.textlength(text, font=font)


def _wrap_rich(draw, runs, max_width):
    """Parte en líneas una lista de (texto, font, color) respetando el ancho.

    Devuelve una lista de líneas; cada línea es una lista de (texto, font, color).
    """
    words = []
    for text, font, color in runs:
        for i, w in enumerate(text.split(" ")):
            if w == "":
                continue
            words.append((w, font, color))
    lines, current, width = [], [], 0.0
    for word, font, color in words:
        space = _text_w(draw, " ", font) if current else 0
        ww = _text_w(draw, word, font)
        if current and width + space + ww > max_width:
            lines.append(current)
            current, width = [], 0.0
            space = 0
        current.append((word, font, color))
        width += space + ww
    if current:
        lines.append(current)
    return lines


def _draw_lines(draw, lines, x, y, line_height):
    for line in lines:
        cx = x
        for i, (word, font, color) in enumerate(line):
            if i:
                cx += _text_w(draw, " ", font)
            draw.text((cx, y), word, font=font, fill=color)
            cx += _text_w(draw, word, font)
        y += line_height
    return y


def _headline_runs(titular: str, destacado: str | None, font):
    navy, gold = BRAND["navy"], BRAND["gold"]
    if destacado and destacado in titular:
        before, after = titular.split(destacado, 1)
        return [(before, font, navy), (destacado, font, gold), (after, font, navy)]
    return [(titular, font, navy)]


def _draw_sun(draw, cx, cy, r, color):
    """Isotipo sencillo tipo sol (se usa si no hay assets/logo.png)."""
    draw.ellipse((cx - r * 0.42, cy - r * 0.42, cx + r * 0.42, cy + r * 0.42), fill=color)
    for i in range(16):
        a = 2 * math.pi * i / 16
        r1, r2 = r * 0.58, r * (0.95 if i % 2 == 0 else 0.8)
        draw.line(
            (cx + r1 * math.cos(a), cy + r1 * math.sin(a), cx + r2 * math.cos(a), cy + r2 * math.sin(a)),
            fill=color,
            width=max(3, int(r * 0.09)),
        )


def render_post(imagen: dict, out_path: Path) -> Path:
    """Dibuja la tarjeta del post.

    imagen = {
      "etiqueta": "NOTICIA · GAS",
      "titular": "La TUR del gas podría subir un 54% el 1 de octubre",
      "destacado": "54%",                    # opcional, se pinta en dorado
      "puntos": [{"titulo": "Precio", "texto": "de 4,12 a 6,95 cént/kWh"}],
      "fuente": "OCU, sept. 2026",           # opcional
      "cta": "¿Te afecta? Te lo revisamos gratis"
    }
    """
    img = Image.new("RGB", (W, H), BRAND["cream"])
    d = ImageDraw.Draw(img)
    navy, gold, white = BRAND["navy"], BRAND["gold"], BRAND["white"]
    content_w = W - 2 * MARGIN

    # Barra superior con etiqueta
    d.rectangle((0, 0, W, TOP_BAR), fill=navy)
    d.rectangle((MARGIN, 38, MARGIN + 24, 62), fill=gold)
    d.text((MARGIN + 42, 34), imagen.get("etiqueta", "").upper(), font=_font(30, True), fill=white)

    # Titular: reduce el tamaño hasta que quepa en el espacio disponible
    max_head_h = 440
    for size in range(88, 46, -4):
        f = _font(size, True)
        lines = _wrap_rich(d, _headline_runs(imagen["titular"], imagen.get("destacado"), f), content_w)
        lh = int(size * 1.15)
        if len(lines) * lh <= max_head_h:
            break
    y = _draw_lines(d, lines, MARGIN, TOP_BAR + 70, lh) + 30
    d.line((MARGIN, y, W - MARGIN, y), fill=BRAND["line"], width=3)
    y += 40

    # Puntos clave con barra dorada lateral
    puntos = imagen.get("puntos", [])[:5]
    fuente = imagen.get("fuente")
    bottom_limit = H - FOOTER_H - (70 if fuente else 30)
    for size in range(36, 22, -2):
        fb, fr = _font(size, True), _font(size)
        lh = int(size * 1.35)
        blocks = []
        for p in puntos:
            runs = []
            if p.get("titulo"):
                t = p["titulo"].strip().rstrip(":.")
                runs.append((t + ("." if t.isdigit() else ":"), fb, navy))
            runs.append((p.get("texto", ""), fr, navy))
            blocks.append(_wrap_rich(d, runs, content_w - 50))
        gap = int(size * 0.9)
        total = sum(len(b) * lh for b in blocks) + gap * max(0, len(blocks) - 1)
        if y + total <= bottom_limit:
            break
    for b in blocks:
        h = len(b) * lh
        d.rectangle((MARGIN, y + 4, MARGIN + 10, y + h - 4), fill=gold)
        _draw_lines(d, b, MARGIN + 40, y, lh)
        y += h + gap

    if fuente:
        d.text((MARGIN, H - FOOTER_H - 55), f"Fuente: {fuente}", font=_font(24), fill="#5B6B80")

    # Pie de marca
    top = H - FOOTER_H
    d.rectangle((0, top, W, H), fill=navy)
    if LOGO_PATH.exists():
        logo = Image.open(LOGO_PATH).convert("RGBA")
        logo.thumbnail((420, 110))
        img.paste(logo, ((W - logo.width) // 2, top + 22), logo)
    else:
        name_f = _font(50, True)
        name = " ".join(BRAND["name"])  # S O L A R E I A, como el logotipo espaciado
        name_w = _text_w(d, name, name_f)
        block_w = 90 + 24 + name_w
        x0 = (W - block_w) / 2
        _draw_sun(d, x0 + 45, top + 70, 45, gold)
        d.text((x0 + 114, top + 32), name, font=name_f, fill=white)
        d.text((x0 + 116, top + 92), BRAND["tagline"].upper(), font=_font(17), fill=gold)
    d.line((MARGIN, top + 140, W - MARGIN, top + 140), fill="#2C4A6E", width=2)
    cta = imagen.get("cta") or "Te ayudamos a ahorrar en tu factura"
    cta_runs = [(cta + " ·", _font(32), white), (BRAND["name"], _font(32, True), gold)]
    cta_lines = _wrap_rich(d, cta_runs, content_w)
    line = cta_lines[0]
    lw = sum(_text_w(d, w, f) for w, f, _ in line) + _text_w(d, " ", _font(32)) * (len(line) - 1)
    _draw_lines(d, [line], (W - lw) / 2, top + 162, 40)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "JPEG", quality=92)
    return out_path


def fit_to_feed(src: Path, out_path: Path) -> Path:
    """Adapta una imagen (p. ej. exportada de Canva a 3:4) al formato 4:5 JPEG.

    Instagram solo acepta relaciones de aspecto entre 4:5 y 1.91:1, así que las
    imágenes más altas se reescalan y se rellenan los laterales prolongando el
    color del borde (queda invisible con fondos lisos).
    """
    im = Image.open(src).convert("RGB")
    ratio = im.width / im.height
    if abs(ratio - W / H) < 0.01:
        im = im.resize((W, H), Image.LANCZOS)
    elif ratio < W / H:  # más alta que 4:5
        nh = H
        nw = round(im.width * H / im.height)
        im = im.resize((nw, nh), Image.LANCZOS)
        canvas = Image.new("RGB", (W, H))
        left = (W - nw) // 2
        canvas.paste(im.crop((0, 0, 1, nh)).resize((left, nh)), (0, 0))
        canvas.paste(im.crop((nw - 1, 0, nw, nh)).resize((W - left - nw, nh)), (left + nw, 0))
        canvas.paste(im, (left, 0))
        im = canvas
    else:  # más ancha: se recorta al centro
        nw = round(im.height * W / H)
        x = (im.width - nw) // 2
        im = im.crop((x, 0, x + nw, im.height)).resize((W, H), Image.LANCZOS)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    im.save(out_path, "JPEG", quality=92)
    return out_path
