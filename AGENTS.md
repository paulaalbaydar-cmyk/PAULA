# AGENTS.md · Redes sociales de Solareia

Guía para cualquier agente de código (Codex, Claude Code…) que trabaje en este repositorio. Léela entera antes de
tocar nada. El proyecto se desarrolla entre varios agentes y Paula (Solareia) valida el resultado.

## Qué es

Automatización que publica **2 veces por semana** en las redes de Solareia:

- LinkedIn: página de empresa de Solareia
- Facebook: página de Solareia
- Instagram: @solareiaconsulting

Solareia es una **consultoría energética independiente** (wearesolareia.com, tarifasluzbaratas.com). Lema:
"Nos ocupamos de tu energía para que tú te ocupes de lo importante". Contacto: info@wearesolareia.com ·
627 60 51 78.

## Calendario y tipos de post

| Día | Tipo | Notas |
|---|---|---|
| Martes 09:17 (Madrid) | `consejo` o `servicio`, alternos | Se preparan con antelación en `content/queue/` |
| Jueves 09:17 (Madrid) | `noticia` (sección "Actualidad") | Se redacta el **miércoles** y **solo se publica si Paula la aprueba** en la issue de GitHub |

Cada post es un **carrusel de 3 imágenes 1080×1350** y lleva un texto distinto para cada red.

## Pautas editoriales (decididas por Paula; no las cambies sin que lo pida)

1. **Consejos y servicios venden el servicio.** Revisar contratos, extras, potencias o tarifas es un engorro para
   el cliente: el post plantea el problema y presenta a Solareia como quien lo hace por él ("te lo revisamos",
   "nos encargamos"). Nunca "revisa tú tu contrato". La última diapositiva explica cómo ayuda Solareia y lleva una
   llamada a contactar.
2. **LinkedIn es otro público:** empresarios y profesionales del sector. Actualidad con la lectura de Solareia y
   captación de clientes de empresa. Si el carrusel de Instagram/Facebook va para hogares, LinkedIn lleva su propio
   carrusel para empresas (`diapositivas_linkedin`).
3. **Instagram y Facebook:** hogares y pequeños negocios, tono cercano, pregunta o invitación a escribir.
4. **Veracidad:** fuente original y fecha en cada noticia; no presentar noticias antiguas como nuevas; no inventar
   cifras; no prometer porcentajes ni importes de ahorro sin estudio; no decir que el servicio es gratuito
   (pendiente de confirmar); no mencionar comercializadoras concretas.
5. Todos los textos cierran con `📩 info@wearesolareia.com · 📞 627 60 51 78` y llevan `#Solareia`.

Servicios de Solareia (fuente: dossier de empresas en Canva): Pack 360 (auditoría energética, soluciones
personalizadas, gestión integral, seguimiento continuo), cambio de comercializadora y optimización de tarifas,
cambios de titularidad, altas nuevas, gestión de incidencias, eficiencia y certificados energéticos, energías
renovables / placas solares y puntos de recarga de vehículos eléctricos.

## Identidad visual (no inventar otra)

Tomada de wearesolareia.com, tarifasluzbaratas.com y de los carruseles que Paula aprobó como referencia:

- Fondo petróleo liso `#014044`, acento menta `#8CFFB9`, texto blanco / `#D9E1E2`, secundario `#A3B6B2`.
- Logo oficial `assets/logo.png` (arriba a la izquierda) e isotipo `assets/logo-mark.png`.
- Sección (CONSEJOS / SERVICIOS / ACTUALIDAD) arriba a la derecha, espaciada, entre dos líneas menta.
- Titulares en MAYÚSCULAS con **Outfit** ExtraBold: primera parte blanca y final (`destacado`) en menta.
- Texto en **Roboto**. Números grandes 01/02 en menta con línea vertical. Contador `1 / 3`.
- Pie: "Desliza y guarda esta guía →" en la portada y el email en el resto; barra menta con icono de guardar para
  la llamada a la acción.
- ⚠️ El Brand Kit "SOLAREIA" de Canva tiene colores antiguos (azul marino y dorado): **no usarlo**.

## Estructura

```
solareia_social/
  config.py      marca, calendario, temas de rotación, lista de servicios
  render.py      carruseles con Pillow (diapositivas: portada, lista, datos) y ajuste de imágenes propias a 4:5
  generate.py    redacción con la API de Claude + búsqueda web (prompt editorial y validación del JSON)
  publishers.py  LinkedIn (Posts API, multiImage), Facebook (Graph API, varias fotos), Instagram (carrusel)
  main.py        CLI: publish, generate, prepare-news, set-issue, preview
content/queue/      posts pendientes (JSON) y "temas reservados" (JSON solo con fecha, tipo y tema)
content/published/  histórico: JSON con IDs de cada red + imágenes publicadas
.github/workflows/  publicar-redes (mar/jue), preparar-borradores (domingo), preparar-noticia (miércoles)
```

Formato de un post: ver cualquier JSON de `content/queue/`. Campos clave: `id`, `fecha`, `tipo`, `seccion`,
`titulo`, `diapositivas`, `diapositivas_linkedin` (opcional), `textos.{linkedin,facebook,instagram}`, `fuentes`,
`imagenes`/`imagenes_linkedin` (opcional, imágenes propias en `content/queue/`), `requiere_aprobacion` + `issue`
(noticias).

## Comandos

```bash
pip install -r requirements.txt
python -m solareia_social.main preview                          # renderiza la cola en previews/ (no se sube)
python -m solareia_social.main publish --dry-run --date 2026-09-29
python -m pyflakes solareia_social                              # debe salir limpio
```

`generate`, `prepare-news` y la publicación real necesitan secretos (ver README). No hay tests automáticos: antes
de subir cambios, ejecuta `preview` y **mira las imágenes** (textos cortados, solapes, acentos) y un `publish
--dry-run`. Para probar los publicadores sin red, simula `requests` con `unittest.mock`.

## Reglas de colaboración entre agentes

- Trabaja en una rama propia (`codex/...` o `claude/...`) y abre un PR contra la rama por defecto; no subas directamente a ella.
- Antes de empezar, lee el historial reciente (`git log`) y la sección "Estado" de abajo; al terminar, actualízala.
- No cambies el formato JSON de los posts sin actualizar `render.py`, `generate.py`, `main.py` y este archivo.
- No subas `previews/`, `issue.md` ni secretos. Las claves solo van en los secretos de GitHub Actions.
- Mensajes de commit y textos en español.
- Cualquier cambio de contenido publicado lo valida Paula.

## Estado (actualizado el 24/09/2026, tras la validación)

Hecho:
- Automatización completa (generación, carruseles, publicación en las 3 redes, reintentos, histórico).
- Contenido del 29/09 al 10/11 en `content/queue/` (consejos, servicios y temas reservados para las noticias).
- Validación previa de las noticias de los jueves mediante issues de GitHub.
- Página de revisión para Paula (artifact de claude.ai) con las vistas previas por red.

Pendiente:
- [x] Paula ha validado todos los carruseles y textos de la cola en las tres redes (campo `validado` en cada JSON).
      Paula quiere validar las noticias antes de publicarlas (`NOTICIAS_REVISION=true`).
- [ ] Paula configura los secretos de Meta (en curso, con Claude in Chrome: sigue `docs/configurar-meta.md`),
      LinkedIn y Claude (pasos en el README).
- [x] La rama `claude/solareia-social-content-automation-kzsjz0` es hoy la rama por defecto del repositorio (la única),
      así que los workflows programados ya se ejecutan desde ella. Si se crea `main`, hay que hacerla la rama por defecto.
- [ ] Primera prueba con "Solo probar" y después primera publicación real.
- [ ] Confirmar con Paula: si el estudio o revisión es gratuito, si la instalación de placas y cargadores se hace
      con instaladores colaboradores y si el Pack 360 se ofrece también a particulares.
- [ ] Opcional: fotos o iconos 3D como los de sus diseños de referencia (la plantilla actual es solo tipográfica).
