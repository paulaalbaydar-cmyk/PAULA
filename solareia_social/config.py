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
MARK_PATH = ASSETS_DIR / "logo-mark.png"  # isotipo, se usa como ilustración

# Identidad de wearesolareia.com / tarifasluzbaratas.com (variables --sl-* de estilo-solareia.css)
BRAND = {
    "name": "SOLAREIA",
    "tagline": "Energy consulting",
    "bg": "#014044",
    "brand_2": "#025A5F",
    "mint": "#8CFFB9",
    "accent": "#60C495",
    "text": "#FFFFFF",
    "text_soft": "#D9E1E2",
    "text_muted": "#A3B6B2",
    "sun_from": "#FFAA00",
    "sun_to": "#E8F31A",
    "ink": "#001516",
    "email": "info@wearesolareia.com",
    "web": os.getenv("SOLAREIA_WEB", "wearesolareia.com"),
    "instagram": "@solareiaconsulting",
}

# Tamaño de imagen: 4:5 vertical, válido para Instagram, Facebook y LinkedIn
IMAGE_SIZE = (1080, 1350)

# Calendario: día de la semana (0=lunes) -> tipo de publicación
# Martes = consejo o servicio (se alternan), jueves = noticia del sector (si no hay novedad contrastada, otro consejo)
SCHEDULE = {1: "consejo", 3: "noticia"}
TUESDAY_ROTATION = ["consejo", "servicio"]

# Rotación de temas para que el contenido sea variado
NEWS_TOPICS = [
    "precio de la luz (PVPC, mercado mayorista, previsiones)",
    "gas natural (TUR, precios, mercado)",
    "impuestos y regulación (IVA, impuesto eléctrico, peajes y cargos CNMC, BOE)",
    "energías renovables y autoconsumo (ayudas, normativa, récords, almacenamiento)",
    "novedad internacional explicada en lenguaje sencillo (AIE, UE, mercados)",
]
TIP_TOPICS = [
    "qué revisar antes de aceptar una oferta de luz o gas",
    "cómo saber si cambiar el horario de consumo te puede ayudar",
    "qué mirar en la factura cuando llega una renovación",
    "potencia contratada: cómo saber si es la adecuada",
    "hábitos de consumo y eficiencia según la época del año",
    "dudas frecuentes sobre la factura de la luz o el gas",
    "autoconsumo solar: qué valorar antes de instalar",
]
TIP_AUDIENCES = ["hogares", "pequeños negocios y empresas"]

# Servicios de Solareia (fuente: dossier de empresas de Solareia en Canva)
SERVICES = [
    "Pack 360 Solareia: auditoría energética, soluciones personalizadas, gestión integral de todos los suministros "
    "y seguimiento continuo, con un único interlocutor",
    "instalación de placas solares y autoconsumo (estudio, instalación, trámites y compensación de excedentes)",
    "puntos de recarga para vehículos eléctricos (viviendas, garajes comunitarios, empresas, hoteles y restaurantes)",
    "optimización de tarifas y cambio de comercializadora (trabajamos con decenas de comercializadoras y "
    "buscamos la mejor para cada cliente)",
    "trámites de suministro sin complicaciones: cambios de titularidad, altas nuevas de luz y gas en inmuebles vacíos "
    "o de nueva construcción y gestión de incidencias con distribuidoras y comercializadoras",
    "eficiencia energética y certificados energéticos",
]

NETWORKS = ("linkedin", "facebook", "instagram")


def enabled_networks() -> list[str]:
    """Redes activas. Se pueden limitar con NETWORKS=linkedin,facebook."""
    raw = os.getenv("NETWORKS", ",".join(NETWORKS))
    return [n.strip() for n in raw.split(",") if n.strip() in NETWORKS]
