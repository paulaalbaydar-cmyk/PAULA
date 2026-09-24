# Solareia · Redes sociales automáticas

> Proyecto compartido entre agentes (Claude Code y Codex): el contexto completo y el estado están en
> [`AGENTS.md`](AGENTS.md).

Publica **2 veces por semana** (martes y jueves) en:

- **LinkedIn**: página de empresa de Solareia
- **Facebook**: página de Solareia
- **Instagram**: @solareiaconsulting

Calendario editorial:

| Día | Tipo | Contenido |
|---|---|---|
| Martes | **Consejo** o **Servicio** (se alternan) | Consejo: plantea un problema o duda (tarifas, renovaciones, potencia, horarios…) y muestra cómo Solareia se encarga de ello. Servicio: Pack 360, placas solares y autoconsumo, puntos de recarga, cambios de comercializadora, trámites, eficiencia… |
| Jueves | **Actualidad** | Novedad de luz, gas, impuestos o renovables de esa semana, con la fuente original. Si no hay una novedad contrastada, se publica un consejo |

Cada publicación es un **carrusel de 3 imágenes** y lleva un texto adaptado a cada red:

- **LinkedIn**: público de empresarios y profesionales del sector. Actualidad con la lectura de Solareia y
  captación de clientes de empresa. Cuando el carrusel de Instagram/Facebook va para hogares, LinkedIn lleva
  su propio carrusel para empresas (`diapositivas_linkedin`).
- **Instagram**: ejemplos cotidianos, texto breve e invitación a guardar el carrusel.
- **Facebook**: texto cercano y explicativo para hogares y pequeños negocios, con una pregunta.

Reglas que sigue la IA al redactar: en los consejos y servicios, **Solareia hace el trabajo por el cliente**
("te lo revisamos", "nos encargamos") y cada carrusel acaba con cómo le ayudamos y una llamada a contactar;
comprobar la fuente y la fecha de cada noticia, distinguir previsiones de resultados, no inventar cifras ni
prometer ahorros sin estudio, no decir que el servicio es gratuito, no mencionar comercializadoras y cerrar con
`📩 info@wearesolareia.com · 📞 627 60 51 78`.

## Cómo funciona

```
Domingo ─────► "Preparar el consejo de la semana": Claude redacta el post del martes (consejo o servicio)
                si no hay ninguno preparado, y lo deja en content/queue/ para revisarlo
Martes 09:17 ► publica el post del martes en LinkedIn, Facebook e Instagram
Miércoles ───► "Preparar la noticia del jueves": Claude redacta la noticia y abre una issue en GitHub con
                el carrusel y los textos (te llega un email)
Jueves 09:17 ► si la aprobaste, se publica; si no, no sale
```

**Para aprobar una noticia:** en la issue, añade la etiqueta `aprobado` o escribe un comentario que empiece por
**ok** o **aprobado**. Solo cuenta la aprobación del propietario del repositorio. Si quieres cambios, edita el
JSON enlazado en la issue antes del jueves. Para que las noticias se publiquen sin validar, crea la variable
`NOTICIAS_REVISION` con el valor `false`.

- En la cola puede haber posts completos o **temas reservados** (JSON con `fecha`, `tipo` y `tema`), que se
  redactan con la información más reciente.
- Una noticia que se retrasa más de 3 días ya no se publica.
- Si una red falla, las demás se publican igualmente y al relanzar solo se reintentan las que fallaron.
  GitHub te avisa por email si algo falla.
- Todo lo publicado queda en `content/published/` (textos, imágenes e ID de cada publicación).

### Diseño de las imágenes

Estilo de los carruseles creados con ChatGPT y colores de wearesolareia.com / tarifasluzbaratas.com:
fondo petróleo `#014044`, menta `#8CFFB9`, logo oficial arriba a la izquierda, sección (CONSEJOS /
ACTUALIDAD) arriba a la derecha, titulares en mayúsculas blanco + menta con **Outfit**, texto en **Roboto**,
números grandes 01/02, contador `1 / 3`, "Desliza y guarda esta guía →" y barra menta para guardar.

Tres tipos de diapositiva: `portada`, `lista` (puntos numerados) y `datos` (cifras grandes con fuente).

Si para un post prefieres tus propias imágenes (por ejemplo, las que te hizo ChatGPT con fotos e iconos 3D),
súbelas a `content/queue/` y añade al JSON del post `"imagenes": ["foto-1.jpg", "foto-2.jpg", "foto-3.jpg"]`.
Se ajustan solas al formato 4:5 que exige Instagram.

## Contenido preparado (29/09 – 29/10, más dos extra)

| Fecha | Tipo | Post |
|---|---|---|
| Mar 29/09 | Consejo | ¿Te han ofrecido una nueva tarifa de luz? Te la revisamos |
| Jue 01/10 | Actualidad | Revisión de la TUR del gas (se redacta ese día con el precio oficial) |
| Mar 06/10 | Servicio | Pack 360: nos ocupamos de toda tu energía |
| Jue 08/10 | Actualidad | Balance del precio de la luz de septiembre y previsión |
| Mar 13/10 | Consejo | ¿Tu empresa paga potencia que no usa? Te lo revisamos |
| Jue 15/10 | Actualidad | Renovables y autoconsumo |
| Mar 20/10 | Servicio | Placas solares: del estudio a los trámites |
| Jue 22/10 | Actualidad | Regulación y costes (peajes, impuestos, CNMC, BOE) |
| Mar 27/10 | Servicio | Puntos de recarga para coche eléctrico |
| Jue 29/10 | Actualidad | Novedad internacional y efecto en España este invierno |
| Mar 03/11 | Consejo | ¿Te compensa poner la lavadora de noche? |
| Mar 10/11 | Consejo | ¿Tu negocio va a consumir más electricidad? |

Los jueves son temas reservados: la noticia se redacta ese mismo día para que sea actual.

## Puesta en marcha (una sola vez)

### 1. Secretos del repositorio

En GitHub: **Settings → Secrets and variables → Actions → New repository secret**

| Secreto | Qué es |
|---|---|
| `ANTHROPIC_API_KEY` | Clave de la API de Claude (console.anthropic.com) para generar contenido nuevo |
| `META_PAGE_ACCESS_TOKEN` | Token de acceso de página **de larga duración** de la página de Facebook de Solareia |
| `FACEBOOK_PAGE_ID` | ID numérico de la página de Facebook |
| `INSTAGRAM_ACCOUNT_ID` | ID de la cuenta profesional de Instagram vinculada a la página (`solareiaconsulting`) |
| `LINKEDIN_ACCESS_TOKEN` | Token OAuth de LinkedIn con permiso `w_organization_social` |
| `LINKEDIN_ORG_ID` | ID numérico de la página de empresa de LinkedIn (sale en la URL del panel de administrador) |
| `LINKEDIN_REFRESH_TOKEN`, `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET` | Opcionales: si LinkedIn te da un refresh token, el token se renueva solo |

Si quieres empezar solo con algunas redes, crea la **variable** (no secreto) `NETWORKS`, por ejemplo
`facebook,instagram`.

### 2. Meta (Facebook + Instagram)

1. La cuenta de Instagram `solareiaconsulting` tiene que ser **profesional** (empresa o creador) y estar
   **vinculada a la página de Facebook** de Solareia.
2. En [developers.facebook.com](https://developers.facebook.com) crea una app de tipo *Business* y añade los
   productos *Facebook Login for Business* e *Instagram Graph API*.
3. En el **Graph API Explorer** genera un token de usuario con los permisos: `pages_show_list`,
   `pages_read_engagement`, `pages_manage_posts`, `instagram_basic`, `instagram_content_publish`, `business_management`.
4. Conviértelo en token de larga duración (herramienta *Access Token Debugger → Extend*) y pide
   `GET /me/accounts`: el `access_token` de la página de Solareia es el **token de página**, que no caduca.
   Ese es `META_PAGE_ACCESS_TOKEN`, y el `id` es `FACEBOOK_PAGE_ID`.
5. `GET /{FACEBOOK_PAGE_ID}?fields=instagram_business_account` devuelve el `INSTAGRAM_ACCOUNT_ID`.

> Como la app solo publica en páginas que administras tú, basta con el modo desarrollo. Si Meta pide
> verificación del negocio, se hace desde el Business Manager.

### 3. LinkedIn

1. En [linkedin.com/developers](https://www.linkedin.com/developers/apps) crea una app asociada a la página de
   Solareia y verifica la app desde la página (un administrador de la página tiene que aprobarla).
2. Solicita el producto **Community Management API** (da el permiso `w_organization_social`).
3. Con el *OAuth token generator* de la propia web de desarrolladores genera un token con `w_organization_social`,
   usando una cuenta que sea **administradora** de la página → `LINKEDIN_ACCESS_TOKEN`.
4. Los tokens de LinkedIn caducan a los **60 días**. Si tu app recibe refresh token, rellena los tres secretos
   opcionales y se renovará solo; si no, pon un recordatorio para regenerarlo cada ~55 días.

### 4. Activar

1. Fusiona esta rama en la rama principal del repositorio: GitHub solo ejecuta los workflows programados desde la rama por defecto.
2. Prueba en **Actions → Publicar en redes → Run workflow** con *Solo probar* marcado: verás los textos en el
   log y la imagen en *Artifacts → vista-previa*.
3. Cuando todo esté bien, lánzalo sin *Solo probar* (y con *force* si no es martes ni jueves) para una
   primera publicación real, o espera al próximo martes.

## Uso diario

- **Revisar o editar un post**: edita el JSON en `content/queue/` desde GitHub antes del martes o el jueves.
  Los textos de cada red están en `textos`; lo que sale en la imagen, en `imagen`.
- **Añadir un post propio**: copia uno de los JSON de la cola y cambia `id`, `fecha`, diapositivas y textos.
- **Reservar un tema**: crea un JSON solo con `id`, `fecha`, `tipo` y `tema`; se redactará ese día.
- **Pausar la automatización**: Actions → el workflow → *Disable workflow*.
- **En local**:

```bash
pip install -r requirements.txt
python -m solareia_social.main preview                   # carruseles de la cola en previews/
python -m solareia_social.main publish --dry-run --force # simulación, no publica nada
python -m solareia_social.main generate                  # consejo de la próxima semana (necesita ANTHROPIC_API_KEY)
```

## Coste aproximado

- GitHub Actions: gratis. Cada ejecución tarda unos 2 minutos.
- API de Claude: unos 0,30-0,60 € por post generado (incluye la búsqueda web), unos 3-5 € al mes.

## Alternativa: Metricool

Si prefieres ver y programar todo desde Metricool (como proponía ChatGPT), la parte de publicación se puede
cambiar para que envíe cada carrusel a tu calendario de Metricool en lugar de usar directamente las APIs de
Meta y LinkedIn. Así solo hace falta conectar las tres redes en Metricool y una clave de su API (disponible en
los planes de pago; LinkedIn no está en el plan gratuito).
- APIs de Meta y LinkedIn: gratis.
