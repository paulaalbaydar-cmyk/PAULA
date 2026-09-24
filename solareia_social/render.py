"""Genera la imagen del post con la identidad visual de Solareia (Pillow)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .config import BRAND, FONTS_DIR, IMAGE_SIZE, LOGO_PATH

W, H = IMAGE_SIZE
MARGIN = 80

FONTS = {
    "display": "Outfit-ExtraBold.ttf",
    "display_semi": "Outfit-SemiBold.ttf",
    "body": "Roboto-Regular.ttf",
    "body_bold": "Roboto-Bold.ttf",
}


def _font(size: int, kind: str = "body") -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS_DIR / FONTS[kind]), size)


def _text_w(draw: ImageDraw.ImageDraw, text: str, font) -> float:
    return draw.textlength(text, font=font)


def _rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def _wrap_rich(draw, runs, max_width):
    """Parte en líneas una lista de (texto, font, color) respetando el ancho.

    Devuelve una lista de líneas; cada línea es una lista de (texto, font, color).
    """
    words = []
    for text, font, color in runs:
        for w in text.split(" "):
            if w:
                words.append((w, font, color))
    lines, current, width = [], [], 0.0
    for word, font, color in words:
        space = _text_w(draw, " ", font) if current else 0
        ww = _text_w(draw, word, font)
        if current and width + space + ww > max_width:
            lines.append(current)
            current, width, space = [], 0.0, 0
        current.append((word, font, color))
        width += space + ww
    if current:
        lines.append(current)
    return lines


def _line_w(draw, line) -> float:
    return sum(_text_w(draw, w, f) for w, f, _ in line) + sum(_text_w(draw, " ", f) for _, f, _ in line[1:])


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
    white, mint = BRAND["text"], BRAND["mint"]
    if destacado and destacado in titular:
        before, after = titular.split(destacado, 1)
        return [(before, font, white), (destacado, font, mint), (after, font, white)]
    return [(titular, font, white)]


def _background() -> Image.Image:
    """Degradado petróleo (#001516 → #014044) con un halo menta suave, como en la web."""
    top, bottom = _rgb(BRAND["bg_top"]), _rgb(BRAND["bg_bottom"])
    grad = Image.new("RGB", (1, H))
    for y in range(H):
        t = y / (H - 1)
        grad.putpixel((0, y), tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)))
    img = grad.resize((W, H))
    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).ellipse((W - 520, -300, W + 380, 560), fill=70)
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    img.paste(Image.new("RGB", (W, H), BRAND["accent"]), (0, 0), glow)
    return img


def _sun_gradient(size: tuple[int, int]) -> Image.Image:
    a, b = _rgb(BRAND["sun_from"]), _rgb(BRAND["sun_to"])
    grad = Image.new("RGB", (size[0], 1))
    for x in range(size[0]):
        t = x / max(1, size[0] - 1)
        grad.putpixel((x, 0), tuple(round(p + (q - p) * t) for p, q in zip(a, b)))
    return grad.resize(size)


def render_post(imagen: dict, out_path: Path) -> Path:
    """Dibuja la tarjeta del post con la identidad de wearesolareia.com.

    imagen = {
      "etiqueta": "Noticia · Gas",
      "titular": "La TUR del gas podría subir un 54% el 1 de octubre",
      "destacado": "54%",                    # opcional, se pinta en menta
      "puntos": [{"titulo": "Precio", "texto": "de 4,12 a 6,95 cént/kWh"}],
      "fuente": "OCU, sept. 2026",           # opcional
      "cta": "¿Te afecta? Te lo revisamos gratis"
    }
    """
    img = _background()
    d = ImageDraw.Draw(img, "RGBA")
    mint, white = BRAND["mint"], BRAND["text"]
    content_w = W - 2 * MARGIN

    # Cabecera: logo a la izquierda, etiqueta en píldora menta a la derecha
    logo = Image.open(LOGO_PATH).convert("RGBA")
    logo.thumbnail((330, 100), Image.LANCZOS)
    img.paste(logo, (MARGIN, 64), logo)
    tag = imagen.get("etiqueta", "").upper()
    tag_f = _font(26, "display_semi")
    tw = _text_w(d, tag, tag_f)
    x1 = W - MARGIN
    x0 = x1 - tw - 56
    d.rounded_rectangle((x0, 78, x1, 136), radius=29, fill=mint)
    d.text((x0 + 28, 107), tag, font=tag_f, fill=BRAND["ink"], anchor="lm")

    # Titular: reduce el tamaño hasta que quepa
    y = 250
    for size in range(96, 50, -4):
        f = _font(size, "display")
        lines = _wrap_rich(d, _headline_runs(imagen["titular"], imagen.get("destacado"), f), content_w)
        lh = int(size * 1.1)
        if len(lines) * lh <= 420:
            break
    y = _draw_lines(d, lines, MARGIN, y, lh) + 28
    d.rounded_rectangle((MARGIN, y, MARGIN + 120, y + 8), radius=4, fill=mint)
    y += 56

    # Puntos clave en tarjetas translúcidas
    puntos = imagen.get("puntos", [])[:5]
    fuente = imagen.get("fuente")
    cta_top = H - 190
    bottom_limit = cta_top - (70 if fuente else 40)
    pad = 26
    for size in range(34, 22, -2):
        fb, fr = _font(size, "body_bold"), _font(size, "body")
        lh = int(size * 1.3)
        blocks = []
        for p in puntos:
            runs = []
            if p.get("titulo"):
                t = p["titulo"].strip().rstrip(":.")
                runs.append((t + ("." if t.isdigit() else ":"), fb, mint))
            runs.append((p.get("texto", ""), fr, BRAND["text_soft"]))
            blocks.append(_wrap_rich(d, runs, content_w - 2 * pad - 20))
        gap = 18
        total = sum(len(b) * lh + 2 * pad for b in blocks) + gap * max(0, len(blocks) - 1)
        if y + total <= bottom_limit:
            break
    for b in blocks:
        h = len(b) * lh + 2 * pad
        d.rounded_rectangle((MARGIN, y, W - MARGIN, y + h), radius=22, fill=(255, 255, 255, 16),
                            outline=(140, 255, 185, 60), width=2)
        d.rounded_rectangle((MARGIN + pad, y + pad + 4, MARGIN + pad + 6, y + h - pad - 4), radius=3, fill=mint)
        _draw_lines(d, b, MARGIN + pad + 26, y + pad - 2, lh)
        y += h + gap

    if fuente:
        d.text((MARGIN, cta_top - 52), f"Fuente: {fuente}", font=_font(24), fill=BRAND["text_muted"])

    # Llamada a la acción con el degradado amarillo de la web
    cta = imagen.get("cta") or "Te ayudamos a ahorrar en tu factura"
    for cta_size in range(34, 20, -2):
        cta_f = _font(cta_size, "display_semi")
        if _text_w(d, cta, cta_f) + 90 <= content_w:
            break
    cw = min(_text_w(d, cta, cta_f) + 90, content_w)
    ch = 84
    cx0 = (W - cw) / 2
    mask = Image.new("L", (int(cw), ch), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, int(cw) - 1, ch - 1), radius=ch // 2, fill=255)
    img.paste(_sun_gradient((int(cw), ch)), (int(cx0), cta_top), mask)
    d.text((W / 2, cta_top + ch / 2), cta, font=cta_f, fill=BRAND["ink"], anchor="mm")
    contact = f"{BRAND['web']}  ·  {BRAND['instagram']}"
    d.text((W / 2, H - 58), contact, font=_font(26), fill=BRAND["text_muted"], anchor="mm")

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
