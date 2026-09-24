"""Publicación en LinkedIn (página de empresa), Facebook (página) e Instagram (cuenta profesional)."""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

import requests

GRAPH_VERSION = os.getenv("META_GRAPH_VERSION", "v25.0")
GRAPH = f"https://graph.facebook.com/{GRAPH_VERSION}"
LINKEDIN_VERSION = os.getenv("LINKEDIN_VERSION", "202608")
TIMEOUT = 60


class PublishError(RuntimeError):
    pass


def _check(resp: requests.Response, what: str) -> requests.Response:
    if resp.status_code >= 400:
        raise PublishError(f"{what}: HTTP {resp.status_code} {resp.text[:500]}")
    return resp


def _env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise PublishError(f"Falta el secreto {name}")
    return value


# ---------------------------------------------------------------- LinkedIn

_LITTLE_TEXT_RESERVED = re.compile(r"([\\|{}@\[\]()<>#*_~])")


def linkedin_commentary(text: str) -> str:
    """Escapa el texto al formato 'little text' de LinkedIn y convierte #hashtags."""
    out, last = [], 0
    for m in re.finditer(r"#(\w+)", text):
        out.append(_LITTLE_TEXT_RESERVED.sub(r"\\\1", text[last : m.start()]))
        out.append("{hashtag|\\#|" + m.group(1) + "}")
        last = m.end()
    out.append(_LITTLE_TEXT_RESERVED.sub(r"\\\1", text[last:]))
    return "".join(out)


def _linkedin_token() -> str:
    """Usa LINKEDIN_ACCESS_TOKEN o, si hay refresh token, obtiene uno nuevo."""
    refresh = os.getenv("LINKEDIN_REFRESH_TOKEN")
    if refresh and os.getenv("LINKEDIN_CLIENT_ID") and os.getenv("LINKEDIN_CLIENT_SECRET"):
        resp = requests.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh,
                "client_id": os.environ["LINKEDIN_CLIENT_ID"],
                "client_secret": os.environ["LINKEDIN_CLIENT_SECRET"],
            },
            timeout=TIMEOUT,
        )
        if resp.ok:
            return resp.json()["access_token"]
        print(f"[linkedin] No se pudo refrescar el token ({resp.status_code}); se usa LINKEDIN_ACCESS_TOKEN")
    return _env("LINKEDIN_ACCESS_TOKEN")


def _linkedin_upload(image: Path, author: str, token: str, headers: dict) -> str:
    init = _check(
        requests.post(
            "https://api.linkedin.com/rest/images?action=initializeUpload",
            json={"initializeUploadRequest": {"owner": author}},
            headers=headers,
            timeout=TIMEOUT,
        ),
        "LinkedIn initializeUpload",
    ).json()["value"]
    _check(
        requests.put(
            init["uploadUrl"],
            data=image.read_bytes(),
            headers={"Authorization": f"Bearer {token}"},
            timeout=TIMEOUT,
        ),
        "LinkedIn subida de imagen",
    )
    return init["image"]


def publish_linkedin(text: str, images: list[Path], title: str) -> dict:
    token = _linkedin_token()
    org = _env("LINKEDIN_ORG_ID")
    author = org if org.startswith("urn:") else f"urn:li:organization:{org}"
    headers = {
        "Authorization": f"Bearer {token}",
        "LinkedIn-Version": LINKEDIN_VERSION,
        "X-Restli-Protocol-Version": "2.0.0",
    }
    urns = [_linkedin_upload(img, author, token, headers) for img in images]
    if len(urns) == 1:
        content = {"media": {"title": title[:200], "id": urns[0]}}
    else:  # carrusel de imágenes (2 a 20)
        content = {"multiImage": {"images": [{"id": u, "altText": f"{title[:100]} ({i})"}
                                             for i, u in enumerate(urns, 1)]}}
    body = {
        "author": author,
        "commentary": linkedin_commentary(text),
        "visibility": "PUBLIC",
        "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [], "thirdPartyDistributionChannels": []},
        "content": content,
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    resp = _check(
        requests.post("https://api.linkedin.com/rest/posts", json=body, headers=headers, timeout=TIMEOUT),
        "LinkedIn crear post",
    )
    return {"id": resp.headers.get("x-restli-id")}


# ---------------------------------------------------------------- Facebook

def upload_facebook_photo(image: Path, published: bool = False, message: str | None = None) -> dict:
    page_id, token = _env("FACEBOOK_PAGE_ID"), _env("META_PAGE_ACCESS_TOKEN")
    data = {"access_token": token, "published": str(published).lower()}
    if message:
        data["message"] = message
    with image.open("rb") as fh:
        return _check(
            requests.post(
                f"{GRAPH}/{page_id}/photos",
                data=data,
                files={"source": (image.name, fh, "image/jpeg")},
                timeout=TIMEOUT,
            ),
            "Facebook subir foto",
        ).json()


def publish_facebook(text: str, images: list[Path]) -> dict:
    """Publica en la página. Con varias imágenes crea una publicación con todas las fotos."""
    if len(images) == 1:
        resp = upload_facebook_photo(images[0], published=True, message=text)
        return {"id": resp.get("post_id") or resp["id"], "photo_ids": [resp["id"]]}
    page_id, token = _env("FACEBOOK_PAGE_ID"), _env("META_PAGE_ACCESS_TOKEN")
    photo_ids = [upload_facebook_photo(img)["id"] for img in images]
    data = {"message": text, "access_token": token}
    for i, pid in enumerate(photo_ids):
        data[f"attached_media[{i}]"] = json.dumps({"media_fbid": pid})
    resp = _check(requests.post(f"{GRAPH}/{page_id}/feed", data=data, timeout=TIMEOUT), "Facebook publicar").json()
    return {"id": resp["id"], "photo_ids": photo_ids}


def facebook_photo_url(photo_id: str) -> str:
    """URL pública (CDN de Meta) de una foto de la página; Instagram la necesita para descargar la imagen."""
    token = _env("META_PAGE_ACCESS_TOKEN")
    data = _check(
        requests.get(f"{GRAPH}/{photo_id}", params={"fields": "images", "access_token": token}, timeout=TIMEOUT),
        "Facebook URL de la foto",
    ).json()
    images = sorted(data["images"], key=lambda i: i["width"], reverse=True)
    return images[0]["source"]


# ---------------------------------------------------------------- Instagram

def _ig_wait(container: str, token: str) -> None:
    for _ in range(36):
        status = _check(
            requests.get(
                f"{GRAPH}/{container}", params={"fields": "status_code", "access_token": token}, timeout=TIMEOUT
            ),
            "Instagram estado del contenedor",
        ).json().get("status_code")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            raise PublishError(f"Instagram: el contenedor terminó en estado {status}")
        time.sleep(5)
    raise PublishError("Instagram: el contenedor no terminó de procesarse a tiempo")


def publish_instagram(text: str, image_urls: list[str]) -> dict:
    """Publica una imagen o un carrusel (2 a 10 imágenes) a partir de URLs públicas."""
    ig_id, token = _env("INSTAGRAM_ACCOUNT_ID"), _env("META_PAGE_ACCESS_TOKEN")

    def create(data: dict) -> str:
        return _check(
            requests.post(f"{GRAPH}/{ig_id}/media", data={**data, "access_token": token}, timeout=TIMEOUT),
            "Instagram crear contenedor",
        ).json()["id"]

    if len(image_urls) == 1:
        container = create({"image_url": image_urls[0], "caption": text})
    else:
        children = [create({"image_url": url, "is_carousel_item": "true"}) for url in image_urls[:10]]
        for child in children:
            _ig_wait(child, token)
        container = create({"media_type": "CAROUSEL", "children": ",".join(children), "caption": text})
    _ig_wait(container, token)
    resp = _check(
        requests.post(
            f"{GRAPH}/{ig_id}/media_publish",
            data={"creation_id": container, "access_token": token},
            timeout=TIMEOUT,
        ),
        "Instagram publicar",
    ).json()
    return {"id": resp["id"]}


def check_meta() -> list[str]:
    """Comprueba las claves de Meta sin publicar nada. Devuelve líneas legibles con el resultado."""
    page_id, token = _env("FACEBOOK_PAGE_ID"), _env("META_PAGE_ACCESS_TOKEN")
    page = _check(
        requests.get(f"{GRAPH}/{page_id}", params={"fields": "name,instagram_business_account", "access_token": token},
                     timeout=TIMEOUT),
        "Facebook: no se puede leer la página (revisa FACEBOOK_PAGE_ID y META_PAGE_ACCESS_TOKEN)",
    ).json()
    out = [f"✅ Facebook: conectado a la página «{page.get('name')}»"]
    ig_expected = _env("INSTAGRAM_ACCOUNT_ID")
    ig_linked = (page.get("instagram_business_account") or {}).get("id")
    if ig_linked != ig_expected:
        out.append(f"⚠️ Instagram: la página tiene vinculada la cuenta {ig_linked}, pero INSTAGRAM_ACCOUNT_ID es "
                   f"{ig_expected}")
    ig = _check(
        requests.get(f"{GRAPH}/{ig_expected}", params={"fields": "username", "access_token": token}, timeout=TIMEOUT),
        "Instagram: no se puede leer la cuenta (revisa INSTAGRAM_ACCOUNT_ID y los permisos)",
    ).json()
    out.append(f"✅ Instagram: conectado a @{ig.get('username')}")
    limit = _check(
        requests.get(f"{GRAPH}/{ig_expected}/content_publishing_limit",
                     params={"fields": "quota_usage", "access_token": token}, timeout=TIMEOUT),
        "Instagram: falta el permiso de publicación (instagram_content_publish)",
    ).json()
    out.append(f"✅ Instagram: permiso de publicación activo (publicaciones en 24 h: "
               f"{(limit.get('data') or [{}])[0].get('quota_usage', 0)})")
    return out
