# `url_base` del menú para la arquitectura unificada

**Estado actualizado (2026-09-11): el cambio de código YA está aplicado**
en `build/extract_common.py` (sin commitear, en la rama
`integracion-web-menu`) y **verificado end-to-end** con datos de prueba
en memoria — ver sección 2. **Lo único que sigue sin tocar es la celda
real de Google Sheets** (sección 1): eso no se modifica sin tu
autorización explícita, tal como se pidió.

## Qué lo dispara

Al unificar la web institucional y el menú en un único artefacto de
GitHub Pages (ver `build_unificado.py` en la raíz del repo), el menú deja
de vivir en la raíz de `https://ameli-casa-de-te-brunch.github.io/` y pasa
a vivir en `https://amelicasadete.com.ar/menu/`. Los assets del menú
(CSS/JS/fuentes/imágenes) usan rutas relativas y ya funcionaban bien
anidados en `/menu/` sin tocar nada. Lo que dependía de `config.url_base`
(el `<link rel="canonical">`, el JSON-LD `Restaurant.url`/`image`, y
`dist/menu/{robots.txt,sitemap.xml}`) seguía apuntando al dominio viejo
hasta este cambio.

## 1. Propiedad/dato pendiente (fuera de este repo, NO tocado)

| Dónde | Qué | Valor actual | Valor propuesto |
|---|---|---|---|
| Google Sheets, columna/celda **"URL base del menú"** (la misma hoja de configuración que ya alimenta `whatsapp`/`instagram`/`direccion`/etc.) | Dato de config, no secreto | `https://ameli-casa-de-te-brunch.github.io/` | `https://amelicasadete.com.ar/menu` |

No es un secret ni un token — es un dato de configuración público, igual
que el número de WhatsApp o el handle de Instagram que ya vive en esa
misma hoja. Aun así, no se toca sin tu autorización porque es una
propiedad real de un sistema en producción.

## 2. Cambio de código -- APLICADO y verificado

Archivo: `build/extract_common.py` (working tree, sin commitear). El
diff real (contra el `main`/`cierre-tecnico-menu` reales):

```diff
-DOMINIO_URL_BASE = "ameli-casa-de-te-brunch.github.io"
+DOMINIO_URL_BASE_NUEVO = "amelicasadete.com.ar"
+RUTA_URL_BASE_NUEVO = "/menu"
+DOMINIO_URL_BASE_VIEJO = "ameli-casa-de-te-brunch.github.io"


 def url_base_valida(valor) -> bool:
     """Acepta EXACTAMENTE una de dos formas (con o sin "/" final):
     "https://amelicasadete.com.ar/menu" -- la arquitectura unificada
     real -- o "https://ameli-casa-de-te-brunch.github.io" -- rollback
     al repo separado. [...]"""
     ...
-    if (partes.hostname or "").lower() != DOMINIO_URL_BASE:
-        return False
     ...
-    if partes.path not in ("", "/"):
-        return False
     ...
+    host = (partes.hostname or "").lower()
+    if host == DOMINIO_URL_BASE_NUEVO:
+        return partes.path in (RUTA_URL_BASE_NUEVO, RUTA_URL_BASE_NUEVO + "/")
+    if host == DOMINIO_URL_BASE_VIEJO:
+        return partes.path in ("", "/")
+    return False
```

(diff resumido -- el real y completo se obtiene con
`git diff -- build/extract_common.py` en la rama `integracion-web-menu`.)

**Pruebas agregadas** en `tests/test_extract_common.py`
(`test_positivas_dominio_propio_unificado`,
`test_negativas_dominio_propio_con_path_incorrecto`) — suite completa del
menú: **158/158 OK** (antes: 156).

**Verificación end-to-end sin tocar `data/menu.json` real:** se generó una
copia en memoria de `data/menu.json` con `config.url_base` puesto en
`https://amelicasadete.com.ar/menu`, y se llamó a `render()` y
`_escribir_seo_estatico()` reales (el código de producción, sin
modificar) contra esa copia. Resultado:

```
canonical:  https://amelicasadete.com.ar/menu/
og:url:     https://amelicasadete.com.ar/menu/
jsonld url: https://amelicasadete.com.ar/menu/
jsonld image: https://amelicasadete.com.ar/menu/assets/img/og-image.jpg
robots.txt: Sitemap: https://amelicasadete.com.ar/menu/sitemap.xml
sitemap.xml <loc>: https://amelicasadete.com.ar/menu/
```

Los cinco lugares pedidos (canonical, og:url, JSON-LD, robots, sitemap)
generan exactamente `https://amelicasadete.com.ar/menu/`. El archivo real
`data/menu.json` del repo **no fue tocado** — la prueba corrió sobre una
copia temporal, nunca escrita a disco fuera de un directorio `tempfile`.

## 3. Alcance mínimo (qué NO cambia)

- **Apps Script real: sin cambios.** El disparo de disponibilidad
  (`repository_dispatch`, tipo `actualizar-disponibilidad`) sigue
  apuntando a este mismo repositorio
  (`Ameli-Casa-de-Te-Brunch/Ameli-Casa-de-Te-Brunch.github.io`) porque la
  unificación se hizo agregando `web/` y `build_unificado.py` ACÁ, no
  moviendo el pipeline del menú a otro repo. El PAT/token que usa Apps
  Script para ese disparo no necesita ningún permiso nuevo ni ningún
  cambio de alcance.
- **`.github/workflows/deploy.yml` / `test-rama.yml`**: cambios ya
  aplicados también al working tree (ver `git diff` de esos archivos) --
  ver detalle en el informe de esta tarea. Sin commitear.
- **Ningún secret ni repository variable nuevo.** `DISPONIBILIDAD_CSV_URL`
  sigue siendo la única variable que el workflow ya usaba.
- **La hoja de disponibilidad en vivo, el Excel maestro, y el resto de
  la config de Sheets: sin cambios** — solo la celda puntual de arriba
  queda pendiente.

## 4. Antes de publicar esto de verdad

1. Confirmar con Ignacio el valor final exacto (`https://amelicasadete.com.ar/menu`,
   sin barra final, para que coincida con el criterio de esta propuesta).
2. Actualizar la celda "URL base del menú" en la hoja de Sheets real.
3. Volver a correr el pipeline de publicación local de Ignacio
   (`python build.py --publicar` o equivalente) para que
   `data/menu.json` quede con el `config.url_base` nuevo -- recién ahí el
   build real (no la prueba en memoria de arriba) produce las URLs
   correctas.
4. Commitear `build/extract_common.py` y los workflows (revisión/PR
   propios, no junto con este cierre técnico) antes de fusionar a `main`.

Hasta que esos 4 pasos se hagan, el `data/menu.json` COMMITEADO real
sigue con `config.url_base` apuntando al dominio viejo -- confirmado
arriba que es exactamente el único motivo por el que el menú publicado
seguiría anunciando `https://ameli-casa-de-te-brunch.github.io/` en vez
de `https://amelicasadete.com.ar/menu/`. El código ya está listo para el
día que el dato cambie.
