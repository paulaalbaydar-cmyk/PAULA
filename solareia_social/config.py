"""Configuración central: marca, rutas y calendario editorial."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUEUE_DIR = ROOT / "content" / "queue"
PUBLISHED_DIR = ROOT / "content" / "published"
ASSETS_DIR = ROOT / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
LOGO_PATH = ASSETS_DIR / "logo.png"  # logo completo para fondo oscuro (menta + blanco)

# Identidad de wearesolareia.com / tarifasluzbaratas.com (variables --sl-* de estilo-solareia.css)
BRAND = {
    "name": "SOLAREIA",
    "tagline": "Energy consulting",
    "bg_top": "#001516",
    "bg_bottom": "#014044",
    "brand_2": "#025A5F",
    "mint": "#8CFFB9",
    "accent": "#60C495",
    "text": "#FFFFFF",
    "text_soft": "#D9E1E2",
    "text_muted": "#A3B6B2",
    "sun_from": "#FFAA00",
    "sun_to": "#E8F31A",
    "ink": "#001516",
    "web": os.getenv("SOLAREIA_WEB", "wearesolareia.com"),
    "instagram": "@solareiaconsulting",
}

# Tamaño de imagen: 4:5 vertical, válido para Instagram, Facebook y LinkedIn
IMAGE_SIZE = (1080, 1350)

# Calendario: día de la semana (0=lunes) -> tipo de publicación
# Martes = noticia del sector, jueves = consejo de ahorro
SCHEDULE = {1: "noticia", 3: "consejo"}

# Rotación de temas para que el contenido sea variado
NEWS_TOPICS = [
    "precio de la luz (PVPC, mercado mayorista, previsiones)",
    "gas natural (TUR, precios, mercado)",
    "impuestos y regulación (IVA, impuesto eléctrico, peajes y cargos CNMC, BOE)",
    "energías renovables y autoconsumo (ayudas, normativa, récords, baterías)",
]
TIP_AUDIENCES = ["particulares (hogares)", "empresas, pymes y hostelería"]

NETWORKS = ("linkedin", "facebook", "instagram")


def enabled_networks() -> list[str]:
    """Redes activas. Se pueden limitar con NETWORKS=linkedin,facebook."""
    raw = os.getenv("NETWORKS", ",".join(NETWORKS))
    return [n.strip() for n in raw.split(",") if n.strip() in NETWORKS]
