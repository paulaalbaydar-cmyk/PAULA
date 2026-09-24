"""Punto de entrada.

  python -m solareia_social.main publish [--dry-run] [--force] [--date AAAA-MM-DD]
  python -m solareia_social.main generate [--count 2]
  python -m solareia_social.main preview   # renderiza las imágenes de la cola en previews/
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import PUBLISHED_DIR, QUEUE_DIR, ROOT, SCHEDULE, enabled_networks
from .render import fit_to_feed, render_post

MADRID = ZoneInfo("Europe/Madrid")
NEWS_MAX_AGE_DAYS = 7  # una noticia en cola que se quedó sin publicar más de 7 días se descarta


def today_madrid() -> date:
    return datetime.now(MADRID).date()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _save(post: dict, path: Path) -> None:
    path.write_text(json.dumps(post, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def queued() -> list[Path]:
    return sorted(QUEUE_DIR.glob("*.json"))


def published() -> list[dict]:
    return [_load(p) for p in sorted(PUBLISHED_DIR.glob("*.json"))]


def recent_titles(n: int = 15) -> list[str]:
    posts = published()[-n:] + [_load(p) for p in queued()]
    return [p["imagen"]["titular"] for p in posts]


def rotation_for(tipo: str) -> int:
    return sum(1 for p in published() if p.get("tipo") == tipo) + sum(
        1 for p in queued() if _load(p).get("tipo") == tipo
    )


def new_post(tipo: str, day: date) -> dict:
    from .generate import generate_post  # import diferido: solo hace falta con la API de Claude

    post = generate_post(tipo, day, recent_titles(), rotation_for(tipo))
    slug = "".join(c if c.isalnum() else "-" for c in post.get("categoria", tipo).lower()).strip("-")
    post["id"] = f"{day.isoformat()}-{tipo}-{slug}"
    post["fecha"] = day.isoformat()
    post["generado"] = datetime.now(MADRID).isoformat(timespec="seconds")
    return post


def prepare_image(post: dict, queue_json: Path | None, out: Path) -> Path:
    """Usa la imagen diseñada (p. ej. exportada de Canva) si existe; si no, genera la plantilla."""
    custom = post.get("imagen_archivo")
    if custom and queue_json is not None and (queue_json.parent / custom).exists():
        return fit_to_feed(queue_json.parent / custom, out)
    return render_post(post["imagen"], out)


def publish_post(post: dict, image: Path, dry_run: bool) -> bool:
    from . import publishers as pub

    results = post.setdefault("publicaciones", {})
    ok = True
    fb_photo_id = results.get("facebook", {}).get("photo_id")
    for net in enabled_networks():
        if results.get(net, {}).get("ok"):
            print(f"[{net}] ya publicado, se omite")
            continue
        text = post["textos"][net]
        if dry_run:
            print(f"\n===== {net.upper()} (dry-run) =====\n{text}\n")
            continue
        try:
            if net == "linkedin":
                res = pub.publish_linkedin(text, image, post["imagen"]["titular"])
            elif net == "facebook":
                res = pub.publish_facebook(text, image)
                fb_photo_id = res["photo_id"]
            else:
                if not fb_photo_id:  # Instagram necesita una URL pública: se sube la foto a FB sin publicarla
                    fb_photo_id = pub.publish_facebook(text, image, published=False)["photo_id"]
                res = pub.publish_instagram(text, pub.facebook_photo_url(fb_photo_id))
            results[net] = {"ok": True, **res, "fecha": datetime.now(MADRID).isoformat(timespec="seconds")}
            print(f"[{net}] publicado: {res}")
        except Exception as exc:  # seguimos con el resto de redes
            ok = False
            results[net] = {"ok": False, "error": str(exc)[:500]}
            print(f"[{net}] ERROR: {exc}", file=sys.stderr)
    return ok


def cmd_publish(args) -> int:
    day = date.fromisoformat(args.date) if args.date else today_madrid()
    tipo = SCHEDULE.get(day.weekday())
    if tipo is None and not args.force:
        print(f"{day}: hoy no toca publicar (días programados: martes y jueves).")
        return 0
    tipo = tipo or "noticia"

    # 1) Primer post pendiente de la cola cuya fecha ya haya llegado
    queue_json, post = None, None
    for path in queued():
        candidate = _load(path)
        cday = date.fromisoformat(candidate["fecha"])
        if cday > day:
            continue
        if candidate.get("tipo") == "noticia" and (day - cday).days > NEWS_MAX_AGE_DAYS:
            print(f"Noticia caducada, se descarta: {path.name}")
            candidate["estado"] = "descartado (noticia caducada)"
            if not args.dry_run:
                _save(candidate, PUBLISHED_DIR / path.name)
                path.unlink()
            continue
        queue_json, post = path, candidate
        break

    # 2) Si no hay nada en cola, se genera al momento con noticias frescas
    if post is None:
        print(f"Cola vacía: generando un post de tipo '{tipo}' con Claude…")
        post = new_post(tipo, day)

    image = PUBLISHED_DIR / f"{post['id']}.jpg"
    if args.dry_run:
        image = ROOT / "previews" / f"{post['id']}.jpg"
    prepare_image(post, queue_json, image)
    print(f"Post: {post['id']} — {post['imagen']['titular']}\nImagen: {image}")

    ok = publish_post(post, image, args.dry_run)
    if args.dry_run:
        return 0

    if ok:
        post["estado"] = "publicado"
        _save(post, PUBLISHED_DIR / f"{post['id']}.json")
        if queue_json:
            custom = post.get("imagen_archivo")
            if custom and (QUEUE_DIR / custom).exists():
                (QUEUE_DIR / custom).unlink()
            queue_json.unlink()
        return 0

    # Fallo parcial: se guarda en la cola con el estado para reintentar solo las redes que fallaron
    post["estado"] = "pendiente de reintento"
    target = queue_json or QUEUE_DIR / f"{post['id']}.json"
    shutil.move(image, QUEUE_DIR / image.name)
    post["imagen_archivo"] = image.name
    _save(post, target)
    return 1


def next_slots(start: date, count: int) -> list[tuple[date, str]]:
    slots, d = [], start
    while len(slots) < count:
        d += timedelta(days=1)
        if d.weekday() in SCHEDULE:
            slots.append((d, SCHEDULE[d.weekday()]))
    return slots


def cmd_generate(args) -> int:
    last = max([date.fromisoformat(_load(p)["fecha"]) for p in queued()] + [today_madrid()])
    for day, tipo in next_slots(last, args.count):
        post = new_post(tipo, day)
        _save(post, QUEUE_DIR / f"{post['id']}.json")
        print(f"Borrador creado: {post['id']} — {post['imagen']['titular']}")
    return 0


def cmd_preview(args) -> int:
    out_dir = ROOT / "previews"
    for path in queued():
        post = _load(path)
        out = prepare_image(post, path, out_dir / f"{post['id']}.jpg")
        print(out)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Automatización de redes sociales de Solareia")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("publish", help="Publica el post que toca hoy")
    p.add_argument("--dry-run", action="store_true", help="No publica; muestra textos y genera la imagen")
    p.add_argument("--force", action="store_true", help="Publica aunque hoy no sea martes/jueves")
    p.add_argument("--date", help="Fecha a simular (AAAA-MM-DD)")
    p.set_defaults(func=cmd_publish)
    g = sub.add_parser("generate", help="Crea borradores en la cola para los próximos días de publicación")
    g.add_argument("--count", type=int, default=2)
    g.set_defaults(func=cmd_generate)
    v = sub.add_parser("preview", help="Genera las imágenes de la cola en previews/")
    v.set_defaults(func=cmd_preview)
    args = parser.parse_args(argv)
    PUBLISHED_DIR.mkdir(parents=True, exist_ok=True)
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
