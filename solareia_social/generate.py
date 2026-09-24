"""Genera un post nuevo (textos + carrusel) con Claude, buscando información actual en la web."""
from __future__ import annotations

import json
import os
import re
from datetime import date

import anthropic

from .config import NEWS_TOPICS, SERVICES, TIP_AUDIENCES, TIP_TOPICS

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-5")

SYSTEM = """Eres el equipo de contenidos de SOLAREIA, una consultoría energética independiente en España
(wearesolareia.com, info@wearesolareia.com). Solareia no trabaja para ninguna comercializadora: ayuda a hogares,
pymes, hostelería y pequeños negocios a entender y pagar menos por la luz y el gas, y gestiona tarifas, trámites,
autoconsumo y renovables. Lema: "Nos ocupamos de tu energía para que tú te ocupes de lo importante".

Reglas editoriales:
- Español de España, tono cercano, claro y directo, sin alarmismo.
- Noticias: comprueba la fuente original y la fecha; distingue previsiones de resultados; explica qué significa para
  los clientes de Solareia. Nunca presentes una noticia antigua como nueva.
- Consejos: el objetivo es que el cliente quiera contactar con Solareia. Revisar contratos, letra pequeña, extras,
  potencias o tarifas es un engorro para el cliente: plantea el problema o la duda, muestra lo que hay que revisar
  (y lo complicado o laborioso que es) y presenta a Solareia como quien lo hace por él. NUNCA le mandes hacer el trabajo
  ("revisa tu contrato", "compara tú"): en su lugar, "te lo revisamos", "nos encargamos", "déjalo en nuestras manos".
  El carrusel termina siempre con una diapositiva de cómo ayuda Solareia (pasos: nos envías tu factura / analizamos /
  te proponemos y lo gestionamos) y una llamada a contactar.
- Servicios: presenta un servicio de Solareia desde el problema del cliente (el engorro, el coste, la duda) y lo que
  Solareia hace por él; el carrusel explica qué incluye y cómo se trabaja, y termina con una llamada a contactar.
  No inventes precios, plazos, garantías, subvenciones ni cifras del servicio.
- Comprueba con fuentes oficiales (CNMC, BOE, IDAE, MITECO, REE, OMIE) cualquier afirmación técnica o normativa.
- No inventes cifras. No prometas porcentajes ni importes de ahorro sin un estudio del suministro. No digas que el
  servicio es gratuito.
- No menciones ni recomiendes comercializadoras concretas.
- LinkedIn es otro público: empresarios y profesionales del sector energético y de empresa. Tono profesional, de tú a
  tú entre profesionales, con la lectura experta de Solareia sobre la actualidad y su impacto en los costes y decisiones
  de las empresas (industria, hostelería, comercios, comunidades, administradores de fincas, promotoras). El objetivo es
  captar clientes de empresa: cierra invitando a solicitar una revisión de los suministros de su empresa y con una
  pregunta que abra conversación entre profesionales.
- Instagram: ejemplos cotidianos para hogares y pequeños negocios, texto breve, invita a guardar el carrusel y a
  escribir por mensaje directo.
- Facebook: texto cercano y explicativo para hogares y pequeños negocios, con una pregunta o invitación a escribir.
- Todos los textos terminan con "📩 info@wearesolareia.com · 📞 627 60 51 78" antes de los hashtags e incluyen #Solareia."""

FORMAT = """Devuelve SOLO un objeto JSON válido (sin texto antes ni después, sin ```), con esta forma:
{
  "tipo": "noticia" | "consejo" | "servicio",
  "categoria": "luz|gas|impuestos|renovables|autoconsumo|tarifas|factura|empresas|hogar",
  "seccion": "Actualidad" (noticias) | "Consejos" (consejos) | "Servicios" (servicios),
  "titulo": "título interno del post, máx. 80 caracteres",
  "diapositivas": [
    {"tipo": "portada", "titular": "máx. 45 caracteres, en forma de pregunta o afirmación potente",
     "destacado": "final del titular que se pinta en menta (debe ser el final literal del titular)",
     "subtitulo": "máx. 45 caracteres", "texto": "máx. 60 caracteres",
     "fuente": "solo en noticias: 'Organismo · DD/MM/AAAA'"},
    {"tipo": "lista", "titular": "máx. 30 caracteres", "destacado": "final literal del titular",
     "items": [{"titulo": "máx. 35 caracteres", "texto": "máx. 45 caracteres"}]  (2 items),
     "cta": "solo en la última diapositiva, máx. 38 caracteres"},
    {"tipo": "datos", "titular": "máx. 30 caracteres", "destacado": "final literal del titular",
     "datos": [{"valor": "23 %", "etiqueta": "máx. 20 caracteres"}] (1 o 2 cifras verificadas),
     "subtitulo": "máx. 45 caracteres", "texto": "máx. 120 caracteres", "fuente": "Organismo · DD/MM/AAAA"}
  ],
  "diapositivas_linkedin": [ ...mismo formato... ]  (SOLO si el carrusel principal va dirigido a hogares: versión para
    empresas, con la misma estructura y la última diapositiva enfocada a captar clientes de empresa; si el carrusel
    principal ya sirve para empresas, omite este campo),
  "textos": {"linkedin": "700-1300 caracteres", "facebook": "400-800 caracteres", "instagram": "300-700 caracteres"},
  "fuentes": ["URL de la fuente original", "..."]
}
El carrusel tiene 3 diapositivas: una "portada" y dos más de tipo "lista" o "datos" (usa "datos" solo con cifras
verificadas). Numera los items de forma continua entre diapositivas (01, 02 en la segunda; 03, 04 en la tercera)
añadiendo "num" a cada item. La última diapositiva es "cómo te ayudamos" (tipo "lista" con los pasos de Solareia)
y lleva "cta" (p. ej. "Envíanos tu factura y lo revisamos")."""


def build_prompt(tipo: str, today: date, recent: list[str], rotation: int, tema: str | None) -> str:
    recent_txt = "\n".join(f"- {t}" for t in recent) or "- (ninguno)"
    if tipo == "noticia":
        foco = tema or NEWS_TOPICS[rotation % len(NEWS_TOPICS)]
        task = (
            f"Hoy es {today.isoformat()}. Busca en la web novedades energéticas publicadas en los últimos 7 días que "
            f"afecten a hogares o empresas en España. Tema preferente: {foco}. Si no encuentras una novedad relevante "
            "y contrastada, NO fuerces la noticia: crea en su lugar un consejo práctico (tipo 'consejo')."
        )
    elif tipo == "servicio":
        foco = tema or SERVICES[rotation % len(SERVICES)]
        task = (
            f"Hoy es {today.isoformat()}. Crea un post de SERVICIO de Solareia sobre: {foco}. "
            "Dirígelo a hogares y pequeños negocios en Instagram y Facebook, y a empresas en LinkedIn "
            "(con 'diapositivas_linkedin' propias si el enfoque cambia). Si citas normativa o ayudas, compruébalas."
        )
    else:
        foco = tema or TIP_TOPICS[rotation % len(TIP_TOPICS)]
        audience = TIP_AUDIENCES[rotation % len(TIP_AUDIENCES)]
        task = (
            f"Hoy es {today.isoformat()}. Crea un post de CONSEJO para {audience} sobre: {foco}. "
            "Busca la información oficial y vigente que lo respalde y adáptalo a la época del año. Recuerda: muestra "
            "por qué es un engorro hacerlo solo y cómo Solareia se encarga de ello."
        )
    return f"{task}\n\nNo repitas estos temas publicados o programados recientemente:\n{recent_txt}\n\n{FORMAT}"


def _extract_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"La respuesta no contiene JSON: {text[:300]}")
    return json.loads(text[start : end + 1])


def validate(post: dict) -> None:
    slides = post.get("diapositivas") or []
    if not 1 <= len(slides) <= 10:
        raise ValueError("El carrusel debe tener entre 1 y 10 diapositivas")
    for s in slides + (post.get("diapositivas_linkedin") or []):
        if s.get("tipo") not in ("portada", "lista", "datos") or not s.get("titular"):
            raise ValueError(f"Diapositiva no válida: {s}")
        dest = s.get("destacado")
        if dest and not s["titular"].upper().endswith(dest.upper()) and dest.upper() not in s["titular"].upper():
            s["destacado"] = None
    txt = post.get("textos", {})
    for net in ("linkedin", "facebook", "instagram"):
        if not txt.get(net):
            raise ValueError(f"Falta el texto de {net}")
    if len(txt["linkedin"]) > 3000:
        raise ValueError("Texto de LinkedIn > 3000 caracteres")
    if len(txt["instagram"]) > 2200 or txt["instagram"].count("#") > 30:
        raise ValueError("Texto de Instagram demasiado largo o con más de 30 hashtags")
    if post.get("tipo") not in ("noticia", "consejo", "servicio"):
        raise ValueError("tipo debe ser 'noticia', 'consejo' o 'servicio'")


def generate_post(tipo: str, today: date, recent: list[str], rotation: int, tema: str | None = None) -> dict:
    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": build_prompt(tipo, today, recent, rotation, tema)}]
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
        if response.stop_reason != "pause_turn":
            break
        messages.append({"role": "assistant", "content": response.content})
    if response.stop_reason == "refusal":
        raise RuntimeError("El modelo rechazó la petición")
    text = "".join(b.text for b in response.content if b.type == "text")
    post = _extract_json(text)
    validate(post)
    return post
