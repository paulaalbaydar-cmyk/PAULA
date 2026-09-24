"""Genera un post nuevo con Claude, buscando noticias actuales en la web."""
from __future__ import annotations

import json
import os
import re
from datetime import date

import anthropic

from .config import NEWS_TOPICS, TIP_AUDIENCES

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-5")

SYSTEM = """Eres el community manager de SOLAREIA, una consultoría energética independiente en España.
Solareia no trabaja para ninguna comercializadora: asesora a particulares, pymes, hostelería y restaurantes
para pagar menos por la luz y el gas, gestiona tarifas, trámites, instalaciones de autoconsumo y su seguimiento.

Tono: cercano, claro y profesional. Explica el impacto práctico en euros para el cliente, sin alarmismo ni jerga
innecesaria. Siempre en español de España. Nunca inventes cifras: todo dato numérico debe salir de una fuente
fiable y reciente que hayas consultado (BOE, CNMC, OMIE, REE, IDAE, MITECO, OCU, medios económicos o del sector).
No menciones ni recomiendes comercializadoras concretas. Termina con una llamada a la acción suave para contactar
con Solareia (revisión de factura / estudio gratuito y sin compromiso)."""

FORMAT = """Devuelve SOLO un objeto JSON válido (sin texto antes ni después, sin ```), con esta forma exacta:
{
  "categoria": "luz|gas|impuestos|renovables|autoconsumo|empresas|hogar",
  "imagen": {
    "etiqueta": "Noticia · Luz"  (o "Consejo · Empresas", etc., máx. 24 caracteres),
    "titular": "titular impactante de máx. 80 caracteres",
    "destacado": "palabra o cifra del titular a resaltar en dorado (debe aparecer literalmente en el titular)",
    "puntos": [{"titulo": "máx. 30 caracteres", "texto": "máx. 70 caracteres"}]  (2 a 4 puntos),
    "fuente": "medio u organismo, mes año"  (vacío si es un consejo sin datos externos),
    "cta": "llamada a la acción de máx. 40 caracteres"
  },
  "textos": {
    "linkedin": "800-1300 caracteres, profesional, con gancho inicial, datos, qué significa para empresas/hogares, CTA, 'Fuente: ...' y 3-5 hashtags al final",
    "facebook": "400-700 caracteres, cercano, algún emoji, CTA y 3-4 hashtags",
    "instagram": "400-700 caracteres, frases cortas con emojis, CTA a escribir por mensaje directo y 8-12 hashtags en minúscula al final"
  },
  "fuentes": ["URL 1", "URL 2"]
}"""


def build_prompt(tipo: str, today: date, recent_titles: list[str], rotation: int) -> str:
    recent = "\n".join(f"- {t}" for t in recent_titles) or "- (ninguna)"
    if tipo == "noticia":
        topic = NEWS_TOPICS[rotation % len(NEWS_TOPICS)]
        task = (
            f"Hoy es {today.isoformat()}. Busca en la web las noticias más relevantes de los últimos 7 días en España "
            f"sobre el sector energético. Prioriza este tema: {topic}; si no hay nada relevante, elige otra noticia "
            "importante de luz, gas, impuestos o renovables (subidas o bajadas de precio, nuevos impuestos o cambios "
            "fiscales, peajes, ayudas, cambios normativos). Elige UNA noticia que interese a los clientes de Solareia "
            "y crea un post explicando qué ha pasado y cómo les afecta."
        )
    else:
        audience = TIP_AUDIENCES[rotation % len(TIP_AUDIENCES)]
        task = (
            f"Hoy es {today.isoformat()}. Crea un post de CONSEJO práctico de ahorro energético dirigido a {audience}. "
            "Puede tratar sobre luz, gas, eficiencia, autoconsumo/renovables, potencia contratada, tarifas, "
            "horarios de consumo, ayudas vigentes, etc. Busca en la web datos actuales (precios, normativa o ayudas "
            "vigentes) que den valor y actualidad al consejo, y adapta el consejo a la época del año."
        )
    return (
        f"{task}\n\nNo repitas estos temas ya publicados recientemente:\n{recent}\n\n{FORMAT}"
    )


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"La respuesta no contiene JSON: {text[:300]}")
    return json.loads(text[start : end + 1])


def validate(post: dict) -> None:
    img, txt = post["imagen"], post["textos"]
    for k in ("etiqueta", "titular", "puntos"):
        if not img.get(k):
            raise ValueError(f"Falta imagen.{k}")
    for net in ("linkedin", "facebook", "instagram"):
        if not txt.get(net):
            raise ValueError(f"Falta el texto de {net}")
    if len(txt["linkedin"]) > 3000:
        raise ValueError("Texto de LinkedIn > 3000 caracteres")
    if len(txt["instagram"]) > 2200 or txt["instagram"].count("#") > 30:
        raise ValueError("Texto de Instagram demasiado largo o con más de 30 hashtags")
    if img.get("destacado") and img["destacado"] not in img["titular"]:
        img["destacado"] = None


def generate_post(tipo: str, today: date, recent_titles: list[str], rotation: int) -> dict:
    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": build_prompt(tipo, today, recent_titles, rotation)}]
    tools = [
        {
            "type": "web_search_20260209",
            "name": "web_search",
            "max_uses": 8,
            "user_location": {"type": "approximate", "country": "ES", "timezone": "Europe/Madrid"},
        }
    ]
    for _ in range(5):  # reanuda si el servidor pausa el turno (pause_turn)
        with client.beta.messages.stream(
            model=MODEL,
            max_tokens=32000,
            system=SYSTEM,
            thinking={"type": "adaptive"},
            output_config={"effort": "high"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            tools=tools,
            messages=messages,
        ) as stream:
            response = stream.get_final_message()
        if response.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": response.content})
            continue
        break
    if response.stop_reason == "refusal":
        raise RuntimeError("El modelo rechazó la petición")
    text = "".join(b.text for b in response.content if b.type == "text")
    post = _extract_json(text)
    validate(post)
    post["tipo"] = tipo
    return post
