# Solareia · Redes sociales automáticas

Publica **2 veces por semana** (martes y jueves) en:

- **LinkedIn**: página de empresa de Solareia
- **Facebook**: página de Solareia
- **Instagram**: @solareiaconsulting

Calendario editorial:

| Día | Tipo | Temas (rotan) |
|---|---|---|
| Martes | **Noticia del sector** | precio de la luz, gas, impuestos y regulación (IVA, impuesto eléctrico, peajes CNMC), renovables y autoconsumo |
| Jueves | **Consejo de ahorro** | alterna entre particulares (hogares) y empresas, pymes y hostelería |

## Cómo funciona

```
Domingo 18:07 ─► "Preparar borradores": Claude busca noticias recientes y deja los
                  posts del martes y el jueves en content/queue/ (se pueden revisar o editar)
Martes/jueves ─► "Publicar en redes": coge el post que toca de la cola, prepara la
  09:17            imagen 1080×1350 y lo publica en LinkedIn, Facebook e Instagram
```

- Si la cola está vacía, el post se genera en el momento con noticias de ese día.
- Una noticia que lleva más de 7 días en la cola sin publicarse se descarta (ya no es actualidad).
- Si una red falla, las demás se publican igualmente. El post se queda en la cola con el error y al volver
  a lanzar el workflow **solo se reintentan las redes que fallaron** (no se duplica nada). GitHub te avisa
  por email cuando un workflow falla.
- Todo lo publicado queda guardado en `content/published/` (texto, imagen e ID de cada red).

### Imágenes

1. **Diseño propio (Canva)**: si en `content/queue/` hay una imagen con el nombre indicado en
   `imagen_archivo`, se usa esa. Las de 3:4 que exporta Canva se ajustan automáticamente a 4:5, el formato
   máximo que admite Instagram.
2. **Plantilla automática**: si no hay imagen, se genera una con los colores del Brand Kit de Solareia
   (azul `#143254`, dorado `#D1952C`, fondo crema). Si subes el logo como `assets/logo.png` (PNG con
   fondo transparente, en blanco o dorado), se pondrá en el pie.

## Primeros posts ya preparados

| Fecha | Post | Diseño en Canva |
|---|---|---|
| Mar 29/09 | Noticia · Gas: la TUR podría subir un 54% el 1 de octubre | https://canva.link/kd40s0y2ttyt914 |
| Jue 01/10 | Noticia · Luz: baja un 19% en septiembre, pero es el septiembre más caro en 4 años | https://canva.link/6y4hrxtocvlp6aw |
| Mar 06/10 | Consejo · Empresas: ¿pagas potencia que no usas? | https://canva.link/wrdv9e7os7xvvha |
| Jue 08/10 | Consejo · Hogar: 5 claves para que el otoño no dispare tu factura | https://canva.link/nknmmopfrf12u9g |

Para usar los diseños de Canva, descarga cada uno como **JPG** y súbelo a `content/queue/` con el nombre de
la columna `imagen_archivo` del JSON (por ejemplo `2026-09-29-gas-tur.jpg`). Si no los subes, se usará la
plantilla automática.

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
- **Añadir un post propio**: copia uno de los JSON de la cola, cambia `id`, `fecha` y los textos.
- **Pausar la automatización**: Actions → el workflow → *Disable workflow*.
- **En local**:

```bash
pip install -r requirements.txt
python -m solareia_social.main preview                   # imágenes de la cola en previews/
python -m solareia_social.main publish --dry-run --force # simulación, no publica nada
python -m solareia_social.main generate --count 2        # borradores nuevos (necesita ANTHROPIC_API_KEY)
```

## Coste aproximado

- GitHub Actions: gratis. Cada ejecución tarda unos 2 minutos.
- API de Claude: unos 0,30-0,60 € por post generado (incluye la búsqueda web), unos 3-5 € al mes.
- APIs de Meta y LinkedIn: gratis.
