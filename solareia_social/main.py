"""Punto de entrada.

  python -m solareia_social.main publish [--dry-run] [--force] [--date AAAA-MM-DD]
  python -m solareia_social.main generate          # prepara los consejos de la semana siguiente
  python -m solareia_social.main preview           # renderiza los carruseles de la cola en previews/
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import PUBLISHED_DIR, QUEUE_DIR, ROOT, SCHEDULE, TUESDAY_ROTATION, enabled_networks
from .render import fit_to_feed, render_carousel

MADRID = ZoneInfo("Europe/Madrid")
MAX_DELAY_DAYS = {"noticia": 3, "consejo": 30, "servicio": 30}  # una noticia retrasada más de 3 días ya no se publica


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
    return [p.get("titulo") or p.get("tema", "") for p in posts if p.get("titulo") or p.get("tema")]


def rotation_for(tipo: str) -> int:
    return sum(1 for p in published() if p.get("tipo") == tipo)


def slot_type(day: date) -> str | None:
    """Tipo de post que toca ese día. Los martes alternan consejo y servicio según lo último publicado."""
    tipo = SCHEDULE.get(day.weekday())
    if tipo != "consejo":
        return tipo
    previous = [p.get("tipo") for p in published() if p.get("tipo") in TUESDAY_ROTATION and p.get("estado") == "publicado"]
    previous += [_load(q).get("tipo") for q in queued() if _load(q)["fecha"] < day.isoformat()
                 and _load(q).get("tipo") in TUESDAY_ROTATION]
    if not previous:
        return TUESDAY_ROTATION[0]
    return TUESDAY_ROTATION[(TUESDAY_ROTATION.index(previous[-1]) + 1) % len(TUESDAY_ROTATION)]


def is_brief(post: dict) -> bool:
    """Un 'brief' es un hueco reservado en la cola con solo el tema: se redacta el mismo día."""
    return not post.get("diapositivas")


def new_post(tipo: str, day: date, tema: str | None = None, post_id: str | None = None) -> dict:
    from .generate import generate_post  # import diferido: solo hace falta con la API de Claude

    post = generate_post(tipo, day, recent_titles(), rotation_for(tipo), tema)
    slug = "".join(c if c.isalnum() else "-" for c in post.get("categoria", tipo).lower()).strip("-")
    post["id"] = post_id or f"{day.isoformat()}-{post['tipo']}-{slug}"
    post["fecha"] = day.isoformat()
    post["generado"] = datetime.now(MADRID).isoformat(timespec="seconds")
    return post


def prepare_images(post: dict, out_dir: Path) -> dict[str, list[Path]]:
    """Imágenes por red: 'default' (Instagram y Facebook) y 'linkedin'.

    LinkedIn usa su propio carrusel si el post trae "diapositivas_linkedin" (o "imagenes_linkedin");
    si no, comparte el de Instagram y Facebook. Las imágenes propias ("imagenes") tienen prioridad.
    """
    def build(img_key: str, slides_key: str, suffix: str) -> list[Path] | None:
        custom = [QUEUE_DIR / name for name in post.get(img_key, [])]
        if custom and all(p.exists() for p in custom):
            return [fit_to_feed(src, out_dir / f"{post['id']}{suffix}-{i}.jpg") for i, src in enumerate(custom, 1)]
        if post.get(slides_key):
            return render_carousel(post, out_dir, slides_key, suffix)
        return None

    default = build("imagenes", "diapositivas", "")
    linkedin = build("imagenes_linkedin", "diapositivas_linkedin", "-li") or default
    return {"default": default, "linkedin": linkedin}


def publish_post(post: dict, image_sets: dict[str, list[Path]], dry_run: bool) -> bool:
    from . import publishers as pub

    results = post.setdefault("publicaciones", {})
    ok = True
    photo_ids = results.get("facebook", {}).get("photo_ids")
    for net in enabled_networks():
        if results.get(net, {}).get("ok"):
            print(f"[{net}] ya publicado, se omite")
            continue
        text = post["textos"][net]
        images = image_sets["linkedin" if net == "linkedin" else "default"]
        if dry_run:
            print(f"\n===== {net.upper()} (dry-run, {len(images)} imágenes) =====\n{text}\n")
            continue
        try:
            if net == "linkedin":
                res = pub.publish_linkedin(text, images, post.get("titulo", ""))
            elif net == "facebook":
                res = pub.publish_facebook(text, images)
                photo_ids = res["photo_ids"]
            else:
                # Instagram descarga las imágenes desde una URL pública: se usan las fotos subidas a Facebook
                if not photo_ids or len(photo_ids) != len(images):
                    photo_ids = [pub.upload_facebook_photo(img)["id"] for img in images]
                res = pub.publish_instagram(text, [pub.facebook_photo_url(pid) for pid in photo_ids])
            results[net] = {"ok": True, **res, "fecha": datetime.now(MADRID).isoformat(timespec="seconds")}
            print(f"[{net}] publicado: {res}")
        except Exception as exc:  # seguimos con el resto de redes
            ok = False
            results[net] = {"ok": False, "error": str(exc)[:500]}
            print(f"[{net}] ERROR: {exc}", file=sys.stderr)
    return ok


def pick_from_queue(day: date, dry_run: bool):
    for path in queued():
        candidate = _load(path)
        cday = date.fromisoformat(candidate["fecha"])
        if cday > day:
            continue
        max_delay = MAX_DELAY_DAYS.get(candidate.get("tipo"), 30)
        if (day - cday).days > max_delay and not candidate.get("publicaciones"):
            print(f"Caducado, se descarta: {path.name}")
            candidate["estado"] = "descartado (caducado)"
            if not dry_run:
                _save(candidate, PUBLISHED_DIR / path.name)
                path.unlink()
            continue
        return path, candidate
    return None, None


def cmd_publish(args) -> int:
    day = date.fromisoformat(args.date) if args.date else today_madrid()
    tipo = slot_type(day)
    if tipo is None and not args.force:
        print(f"{day}: hoy no toca publicar (martes: consejo o servicio, jueves: noticia).")
        return 0
    tipo = tipo or "consejo"

    queue_json, post = pick_from_queue(day, args.dry_run)
    if post is not None and is_brief(post):
        print(f"Redactando el tema reservado para hoy: {post.get('tema')}")
        post = new_post(post.get("tipo", tipo), day, post.get("tema"), post.get("id"))
    elif post is None:
        print(f"Cola vacía: generando un post de tipo '{tipo}' con Claude…")
        post = new_post(tipo, day)

    out_dir = (ROOT / "previews") if args.dry_run else PUBLISHED_DIR
    image_sets = prepare_images(post, out_dir)
    for name, imgs in image_sets.items():
        print(f"Imágenes ({name}): {', '.join(str(i) for i in imgs)}")
    print(f"Post: {post['id']} — {post.get('titulo')}")

    ok = publish_post(post, image_sets, args.dry_run)
    if args.dry_run:
        return 0

    if ok:
        post["estado"] = "publicado"
        _save(post, PUBLISHED_DIR / f"{post['id']}.json")
        if queue_json:
            for name in post.get("imagenes", []) + post.get("imagenes_linkedin", []):
                (QUEUE_DIR / name).unlink(missing_ok=True)
            queue_json.unlink()
        return 0

    # Fallo parcial: se guarda en la cola con el estado para reintentar solo las redes que fallaron
    post["estado"] = "pendiente de reintento"
    for field, imgs in (("imagenes", image_sets["default"]), ("imagenes_linkedin", image_sets["linkedin"])):
        post[field] = []
        for img in imgs:
            target = QUEUE_DIR / img.name
            if img.exists() and img.resolve() != target.resolve():
                shutil.move(img, target)
            post[field].append(img.name)
    _save(post, queue_json or QUEUE_DIR / f"{post['id']}.json")
    return 1


def cmd_generate(args) -> int:
    """Prepara el consejo o servicio de los próximos 7 días si aún no tiene post en la cola.

    Las noticias no se preparan con antelación: se redactan el mismo jueves para que sean actuales.
    """
    start = today_madrid()
    taken = {_load(p)["fecha"] for p in queued()}
    for offset in range(1, 8):
        day = start + timedelta(days=offset)
        tipo = slot_type(day)
        if tipo not in TUESDAY_ROTATION or day.isoformat() in taken:
            continue
        post = new_post(tipo, day)
        _save(post, QUEUE_DIR / f"{post['id']}.json")
        print(f"Borrador creado: {post['id']} — {post.get('titulo')}")
    return 0


def cmd_preview(args) -> int:
    out_dir = ROOT / "previews"
    for path in queued():
        post = _load(path)
        if is_brief(post):
            print(f"{path.name}: tema reservado, se redactará el {post['fecha']} ({post.get('tema')})")
            continue
        for imgs in prepare_images(post, out_dir).values():
            for img in dict.fromkeys(imgs):
                print(img)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Automatización de redes sociales de Solareia")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("publish", help="Publica el post que toca hoy")
    p.add_argument("--dry-run", action="store_true", help="No publica; muestra textos y genera las imágenes")
    p.add_argument("--force", action="store_true", help="Publica aunque hoy no sea martes/jueves")
    p.add_argument("--date", help="Fecha a simular (AAAA-MM-DD)")
    p.set_defaults(func=cmd_publish)
    g = sub.add_parser("generate", help="Prepara los consejos de la próxima semana en la cola")
    g.set_defaults(func=cmd_generate)
    v = sub.add_parser("preview", help="Genera las imágenes de la cola en previews/")
    v.set_defaults(func=cmd_preview)
    args = parser.parse_args(argv)
    PUBLISHED_DIR.mkdir(parents=True, exist_ok=True)
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
