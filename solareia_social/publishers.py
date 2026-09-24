"""Publicación en LinkedIn (página de empresa), Facebook (página) e Instagram (cuenta profesional)."""
from __future__ import annotations

import os
import re
import time
from pathlib import Path

import requests

GRAPH_VERSION = os.getenv("META_GRAPH_VERSION", "v24.0")
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


def publish_linkedin(text: str, image: Path, title: str) -> dict:
    token = _linkedin_token()
    org = _env("LINKEDIN_ORG_ID")
    author = org if org.startswith("urn:") else f"urn:li:organization:{org}"
    headers = {
        "Authorization": f"Bearer {token}",
        "LinkedIn-Version": LINKEDIN_VERSION,
        "X-Restli-Protocol-Version": "2.0.0",
    }
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
    body = {
        "author": author,
        "commentary": linkedin_commentary(text),
        "visibility": "PUBLIC",
        "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [], "thirdPartyDistributionChannels": []},
        "content": {"media": {"title": title[:200], "id": init["image"]}},
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    resp = _check(
        requests.post("https://api.linkedin.com/rest/posts", json=body, headers=headers, timeout=TIMEOUT),
        "LinkedIn crear post",
    )
    return {"id": resp.headers.get("x-restli-id")}


# ---------------------------------------------------------------- Facebook

def publish_facebook(text: str, image: Path, published: bool = True) -> dict:
    page_id, token = _env("FACEBOOK_PAGE_ID"), _env("META_PAGE_ACCESS_TOKEN")
    with image.open("rb") as fh:
        resp = _check(
            requests.post(
                f"{GRAPH}/{page_id}/photos",
                data={"message": text, "access_token": token, "published": str(published).lower()},
                files={"source": (image.name, fh, "image/jpeg")},
                timeout=TIMEOUT,
            ),
            "Facebook subir foto",
        ).json()
    return {"id": resp.get("post_id") or resp.get("id"), "photo_id": resp["id"]}


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

def publish_instagram(text: str, image_url: str) -> dict:
    ig_id, token = _env("INSTAGRAM_ACCOUNT_ID"), _env("META_PAGE_ACCESS_TOKEN")
    container = _check(
        requests.post(
            f"{GRAPH}/{ig_id}/media",
            data={"image_url": image_url, "caption": text, "access_token": token},
            timeout=TIMEOUT,
        ),
        "Instagram crear contenedor",
    ).json()["id"]
    for _ in range(30):
        status = _check(
            requests.get(
                f"{GRAPH}/{container}", params={"fields": "status_code", "access_token": token}, timeout=TIMEOUT
            ),
            "Instagram estado del contenedor",
        ).json().get("status_code")
        if status == "FINISHED":
            break
        if status in ("ERROR", "EXPIRED"):
            raise PublishError(f"Instagram: el contenedor terminó en estado {status}")
        time.sleep(5)
    resp = _check(
        requests.post(
            f"{GRAPH}/{ig_id}/media_publish",
            data={"creation_id": container, "access_token": token},
            timeout=TIMEOUT,
        ),
        "Instagram publicar",
    ).json()
    return {"id": resp["id"]}
