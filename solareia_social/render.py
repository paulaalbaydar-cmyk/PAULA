"""Genera la imagen del post con la identidad visual de Solareia (Pillow)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .config import BRAND, FONTS_DIR, IMAGE_SIZE, LOGO_PATH, MARK_PATH

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
    titular = titular.upper()
    destacado = (destacado or "").upper()
    if destacado and destacado in titular:
        before, after = titular.split(destacado, 1)
        return [(before, font, white), (destacado, font, mint), (after, font, white)]
    return [(titular, font, white)]


def _spaced(draw, xy, text, font, fill, spacing, anchor_right=False):
    """Texto con espaciado entre letras (como CONSEJOS / ACTUALIDAD en los diseños)."""
    widths = [_text_w(draw, ch, font) for ch in text]
    total = sum(widths) + spacing * (len(text) - 1)
    x, y = xy
    if anchor_right:
        x -= total
    for ch, w in zip(text, widths):
        draw.text((x, y), ch, font=font, fill=fill)
        x += w + spacing
    return total


def _fit_headline(draw, titular, destacado, max_w, max_h, start=112, stop=56):
    """Ajusta el titular. Si la parte destacada va al final, empieza en línea nueva (como en los diseños)."""
    up, dest = titular.upper(), (destacado or "").upper()
    split_end = bool(dest) and up.endswith(dest) and up != dest
    for size in range(start, stop - 1, -4):
        f = _font(size, "display")
        if split_end:
            head = up[: -len(dest)].rstrip()
            lines = _wrap_rich(draw, [(head, f, BRAND["text"])], max_w) + _wrap_rich(
                draw, [(dest, f, BRAND["mint"])], max_w)
        else:
            lines = _wrap_rich(draw, _headline_runs(titular, destacado, f), max_w)
        lh = int(size * 1.02)
        if len(lines) * lh <= max_h and all(_line_w(draw, ln) <= max_w for ln in lines):
            return lines, lh
    return lines, lh


def _arrow(draw, x, y, color, length=34):
    draw.line((x, y, x + length, y), fill=color, width=4)
    draw.line((x + length - 13, y - 12, x + length, y), fill=color, width=4)
    draw.line((x + length - 13, y + 12, x + length, y), fill=color, width=4)


def _mark(size: int, opacity: int) -> Image.Image:
    """Isotipo (hoja + enchufe) en menta con la opacidad indicada, como ilustración."""
    mark = Image.open(MARK_PATH).convert("RGBA")
    alpha = mark.getchannel("A").point(lambda a: a * opacity // 255)
    tinted = Image.new("RGBA", mark.size, BRAND["mint"])
    tinted.putalpha(alpha)
    tinted.thumbnail((size, size), Image.LANCZOS)
    return tinted


def _base(seccion: str, pagina: tuple[int, int] | None, pie: str | None):
    img = Image.new("RGB", (W, H), BRAND["bg"])
    d = ImageDraw.Draw(img, "RGBA")
    logo = Image.open(LOGO_PATH).convert("RGBA")
    logo.thumbnail((400, 124), Image.LANCZOS)
    img.paste(logo, (MARGIN - 6, 70), logo)
    mint = BRAND["mint"]
    f = _font(30, "display_semi")
    label = seccion.upper()
    w = _spaced(d, (W - MARGIN, 112), label, f, mint, 7, anchor_right=True)
    d.line((W - MARGIN - w - 20, 92, W - MARGIN, 92), fill=mint, width=3)
    d.line((W - MARGIN - w - 20, 164, W - MARGIN, 164), fill=mint, width=3)
    foot_f = _font(30)
    pie = pie or BRAND["email"]
    arrow = pie.endswith("→")
    pie = pie.rstrip("→ ").rstrip()
    d.text((MARGIN, H - 72), pie, font=foot_f, fill=BRAND["text"], anchor="lm")
    if arrow:
        _arrow(d, MARGIN + _text_w(d, pie, foot_f) + 16, H - 72, BRAND["text"])
    if pagina and pagina[1] > 1:
        d.text((W - MARGIN, H - 72), f"{pagina[0]} / {pagina[1]}", font=_font(32, "body_bold"),
               fill=BRAND["text"], anchor="rm")
    return img, d


def _slide_portada(s, img, d):
    mark = _mark(400, 55)
    img.paste(mark, (W - MARGIN - mark.width + 30, H - mark.height - 130), mark)
    lines, lh = _fit_headline(d, s["titular"], s.get("destacado"), W - 2 * MARGIN, 560, start=136)
    y = _draw_lines(d, lines, MARGIN, 280, lh) + 24
    if s.get("subtitulo"):
        sub = _wrap_rich(d, [(s["subtitulo"], _font(58, "display_semi"), BRAND["text"])], W - 2 * MARGIN)
        y = _draw_lines(d, sub, MARGIN, y, 70) + 36
    d.rounded_rectangle((MARGIN, y, MARGIN + 130, y + 6), radius=3, fill=BRAND["mint"])
    y += 50
    if s.get("texto"):
        txt = _wrap_rich(d, [(s["texto"], _font(42), BRAND["text"])], W - 2 * MARGIN - 220)
        y = _draw_lines(d, txt, MARGIN, y, 56)
    if s.get("fuente"):
        d.text((MARGIN, y + 20), s["fuente"], font=_font(36, "display_semi"), fill=BRAND["mint"])


def _slide_lista(s, img, d):
    lines, lh = _fit_headline(d, s["titular"], s.get("destacado"), W - 2 * MARGIN, 300, start=128)
    y = _draw_lines(d, lines, MARGIN, 260, lh) + 50
    items = s.get("items", [])[:4]
    cta = s.get("cta")
    bottom = H - 150 - (160 if cta else 0)
    num_f = _font(170 if len(items) <= 2 else 120, "display")
    col = MARGIN + (_text_w(d, "00", num_f) + 50)
    text_w = W - MARGIN - col
    for size in range(58, 30, -2):
        tf, bf = _font(size, "display"), _font(int(size * 0.72))
        blocks = [
            (_wrap_rich(d, [(it.get("titulo", ""), tf, BRAND["text"])], text_w),
             _wrap_rich(d, [(it.get("texto", ""), bf, BRAND["text_soft"])], text_w) if it.get("texto") else [])
            for it in items
        ]
        tlh, blh = int(size * 1.15), int(size * 0.72 * 1.4)
        heights = [max(len(t) * tlh + len(b) * blh + 10, num_f.size) for t, b in blocks]
        if sum(heights) + 60 * (len(items) - 1) <= bottom - y:
            break
    y += max(0, (bottom - y - sum(heights) - 60 * (len(items) - 1)) / 2)
    for i, (it, (t, b), h) in enumerate(zip(items, blocks, heights)):
        if i:
            d.line((MARGIN, y - 30, W - MARGIN - 60, y - 30), fill=(140, 255, 185, 110), width=2)
        num = it.get("num") or f"{i + 1:02d}"
        d.text((MARGIN - 6, y + h / 2), num, font=num_f, fill=BRAND["mint"], anchor="lm")
        d.line((col - 28, y, col - 28, y + h), fill=(140, 255, 185, 140), width=2)
        ty = y + (h - (len(t) * tlh + len(b) * blh + 10)) / 2
        ty = _draw_lines(d, t, col, ty, tlh) + 10
        _draw_lines(d, b, col, ty, blh)
        y += h + 60
    if cta:
        top = H - 250
        d.rounded_rectangle((MARGIN, top, W - MARGIN, top + 100), radius=18, fill=BRAND["mint"])
        f = _font(40, "display_semi")
        tw = _text_w(d, cta, f)
        x = (W - tw - 80) / 2
        # icono marcador (guardar)
        bx, by = x, top + 30
        d.polygon([(bx, by), (bx + 30, by), (bx + 30, by + 42), (bx + 15, by + 30), (bx, by + 42)],
                  outline=BRAND["ink"], width=4)
        d.line((x + 58, top + 25, x + 58, top + 75), fill=BRAND["ink"], width=2)
        d.text((x + 80, top + 50), cta, font=f, fill=BRAND["ink"], anchor="lm")


def _slide_datos(s, img, d):
    lines, lh = _fit_headline(d, s["titular"], s.get("destacado"), W - 2 * MARGIN, 260, start=104)
    y = _draw_lines(d, lines, MARGIN, 250, lh) + 50
    datos = s.get("datos", [])[:2]
    col_w = (W - 2 * MARGIN) / max(1, len(datos))
    for size in range(200, 90, -10):
        vf = _font(size, "display")
        if all(_text_w(d, x["valor"], vf) <= col_w - 50 for x in datos):
            break
    lf = _font(48, "display")
    for i, x in enumerate(datos):
        cx = MARGIN + i * col_w + (40 if i else 0)
        d.text((cx, y), x["valor"], font=vf, fill=BRAND["mint"])
        d.text((cx, y + size * 1.02), x.get("etiqueta", ""), font=lf, fill=BRAND["text"])
        if i:
            d.line((MARGIN + i * col_w, y + 10, MARGIN + i * col_w, y + size + 70), fill=BRAND["mint"], width=3)
    y += size + 150
    if s.get("subtitulo"):
        sub = _wrap_rich(d, [(s["subtitulo"], _font(54, "display"), BRAND["text"])], W - 2 * MARGIN)
        y = _draw_lines(d, sub, MARGIN, y, 64) + 40
    if s.get("texto"):
        txt = _wrap_rich(d, [(s["texto"], _font(38), BRAND["text_soft"])], W - 2 * MARGIN)
        _draw_lines(d, txt, MARGIN, y, 52)


LAYOUTS = {"portada": _slide_portada, "lista": _slide_lista, "datos": _slide_datos}


def render_carousel(post: dict, out_dir: Path) -> list[Path]:
    """Genera las diapositivas del post (1080×1350 JPEG) al estilo de los diseños de Solareia.

    post["seccion"] = "Consejos" | "Actualidad"
    post["diapositivas"] = [
      {"tipo": "portada", "titular": "¿Vas a cambiar de tarifa de luz?", "destacado": "de tarifa de luz?",
       "subtitulo": "4 preguntas antes de contratar", "texto": "Compara con toda la información."},
      {"tipo": "lista", "titular": "El precio y los extras", "destacado": "y los extras",
       "items": [{"titulo": "¿Cuándo puede cambiar el precio?", "texto": "Revisa cómo se actualiza."}],
       "cta": "Guárdalo para tu próxima renovación"},
      {"tipo": "datos", "titular": "...", "datos": [{"valor": "23 %", "etiqueta": "Actualmente"}],
       "subtitulo": "...", "texto": "...", "fuente": "AIE · 22/09/2026"}
    ]
    """
    slides = post["diapositivas"]
    n = len(slides)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, s in enumerate(slides, 1):
        if i == 1 and n > 1:
            pie = s.get("pie") or "Desliza y guarda esta guía →"
        else:
            pie = s.get("pie") or (f"Fuente: {s['fuente']}" if s.get("fuente") and s["tipo"] != "portada" else None)
        img, d = _base(post.get("seccion", "Consejos"), (i, n), pie)
        LAYOUTS[s.get("tipo", "lista")](s, img, d)
        path = out_dir / f"{post['id']}-{i}.jpg"
        img.save(path, "JPEG", quality=92)
        paths.append(path)
    return paths


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
