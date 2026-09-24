# Configurar las claves de Meta (Facebook + Instagram)

Guía para el agente que lo haga en el navegador de Paula (Claude in Chrome) o para Paula. **Nunca** escribas
tokens, contraseñas ni códigos en el chat, en commits ni en archivos: solo en los secretos de GitHub.

## Punto de partida (24/09/2026)

- Instagram @solareiaconsulting ya es cuenta profesional y está vinculada a la página de Facebook de Solareia. ✅
- Paula tiene cuenta de desarrolladora en developers.facebook.com. ✅
- Hay dos apps "solareia redes" (IDs 1905042623802599 y 1729243871704590) creadas **sin casos de uso**
  (Tipo: Ninguno). No sirven: archívalas (Mis aplicaciones → ··· → Archivar).
- Se empezó una tercera app con los casos de uso correctos, pero al conectar el portfolio empresarial
  "Solareia" Meta pidió verificación de dispositivo ("Se requiere verificación") y no dejó terminar.

## Pasos

1. **Crear la app** en developers.facebook.com → Mis aplicaciones → Crear aplicación.
   - Nombre `Solareia Redes`, email de Paula.
   - Casos de uso (filtro "Todo"): marcar **solo** "Administrar mensajes y contenido en Instagram" y
     "Administra todo en tu página". No marcar "Crea una aplicación sin un caso de uso" ni "Otro".
   - Portfolio empresarial: "Solareia". Si vuelve a salir "Se requiere verificación", que Paula complete la
     verificación en business.facebook.com; si no es posible, elegir **"Aún no quiero conectar un portfolio
     empresarial"** (no hace falta para publicar en sus propias cuentas).
   - Crear aplicación. Debe quedar en modo desarrollo.
2. **Token de usuario** en https://developers.facebook.com/tools/explorer/ :
   - App de Meta: la nueva "Solareia Redes".
   - Permisos: `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `instagram_basic`,
     `instagram_content_publish`, `business_management`.
   - Generate Access Token → Paula acepta y marca la página Solareia y la cuenta @solareiaconsulting.
3. **Ampliar el token** en https://developers.facebook.com/tools/debug/accesstoken/ → Depurar →
   "Ampliar token de acceso".
4. En el Explorador, con el token ampliado: `GET me/accounts` → en el bloque de Solareia:
   `id` = **FACEBOOK_PAGE_ID**, `access_token` = **META_PAGE_ACCESS_TOKEN** (el Depurador debe decir
   "Caduca: Nunca").
5. `GET {FACEBOOK_PAGE_ID}?fields=instagram_business_account` → `id` = **INSTAGRAM_ACCOUNT_ID**.
6. **GitHub** → https://github.com/paulaalbaydar-cmyk/PAULA/settings/secrets/actions → New repository secret:
   `META_PAGE_ACCESS_TOKEN`, `FACEBOOK_PAGE_ID`, `INSTAGRAM_ACCOUNT_ID`.
   Pestaña Variables → New repository variable: `NETWORKS` = `facebook,instagram` (hasta tener LinkedIn).
7. **Comprobar**: https://github.com/paulaalbaydar-cmyk/PAULA/actions → "Publicar en redes (martes y jueves)" →
   Run workflow → marcar **"Solo comprobar la conexión con las redes"** → Run. Deben salir tres ✅.
