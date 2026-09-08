# Línea base de seguridad — menú de Amelí

Estado de esta línea base: cierre técnico Fase C1 (rama
`cierre-tecnico-menu`, sin publicar todavía). Describe lo que HOY protege
al sitio, no un plan a futuro — para lo que queda deliberadamente
pospuesto, ver la sección final.

## Permisos del workflow (mínimo privilegio por job)

`.github/workflows/deploy.yml` ya no da los mismos permisos a los dos
jobs -- cada uno tiene solo lo que necesita:

| Job | `contents` | `pages` | `id-token` | Por qué |
|---|---|---|---|---|
| `build` | `read` | — | — | Descarga y procesa la hoja de disponibilidad, corre pruebas, renderiza -- nunca publica. No tiene ningún motivo para poder escribir nada. |
| `deploy` | — | `write` | `write` | El único paso que efectivamente publica (`actions/deploy-pages`) -- no hace checkout, no necesita `contents` en absoluto. |

Ningún otro job existe hoy. Si se agrega uno nuevo, arranca sin permisos
de escritura salvo que se justifique acá, en esta misma tabla.

## Cabeceras y política de contenido

- **CSP** (`build/render.py`, `_csp_meta`): `default-src 'none'`, con
  `script-src 'self' '<hash del script inline>'` (el hash se recalcula en
  cada build, nunca `'unsafe-inline'`), `style-src 'self'`,
  `font-src 'self'`, `img-src 'self'`, `connect-src 'none'`,
  `frame-ancestors 'none'`, `base-uri 'none'`, `form-action 'none'`. Va
  como `<meta>` porque GitHub Pages no permite mandar cabeceras HTTP
  propias — **`frame-ancestors` no tiene ningún efecto real entregado
  así** (el navegador lo ignora fuera de una respuesta HTTP). Es una
  limitación conocida y aceptada de este hosting, no un descuido; nunca
  se presenta como protección real contra clickjacking.
- **Referrer**: `<meta name="referrer" content="no-referrer">` — no se
  manda ningún referrer al navegar a un link externo.
- **Enlaces externos**: todo `target="_blank"` lleva
  `rel="noopener noreferrer"` (verificado por
  `tests/test_render.py::TestEnlacesExternosSeguros`).
- **`_safe_json`**: escapa `</` en el JSON embebido para que un texto del
  Excel con `</script>` literal no pueda cerrar el `<script>` del
  template antes de tiempo.

## Validación de entradas (no confiar en que el maestro siempre tenga lo
esperado)

- **URLs** (`build/extract_common.py::url_https_valida`): exige `https`,
  usa `hostname` (no `netloc`, así se ignora cualquier
  `usuario@host` engañoso), y exige coincidencia exacta o subdominio real
  contra una allowlist explícita por campo (`DOMINIOS_MENU`,
  `DOMINIOS_GOOGLE`, `DOMINIOS_TRIPADVISOR`, `DOMINIOS_DISPONIBILIDAD`) —
  nunca un fragmento de texto como `"tripadvisor."`. Cualquier otro
  esquema (`http:`, `javascript:`, `data:`) queda rechazado directamente
  por el chequeo de esquema.
- **WhatsApp** (`whatsapp_valido`): normaliza a solo dígitos y exige 8 a
  15 dígitos — un número fuera de rango se descarta (queda ausente del
  sitio) en vez de publicar un link `wa.me` roto.
- **Instagram**: handle validado por regex (`[A-Za-z0-9._]{1,30}`).
- Pruebas positivas y negativas de todo esto en
  `tests/test_extract_common.py`.

## Disponibilidad en vivo (el dato que más cambia, sin supervisión humana
directa en cada edición)

`build/aplicar_disponibilidad.py` reescribió su modelo de confianza:

- Valores de la hoja limitados a una lista cerrada (vacío, `Disponible`,
  `Agotado por hoy`, `No disponible temporalmente`, `Últimas porciones`)
  — cualquier otro texto es un error, no se interpreta silenciosamente
  como disponible.
- Integridad de filas en modo estricto (el que usa CI siempre, sin forma
  de desactivarlo desde afuera): ID duplicado, fila sin ID con un
  estado, ID desconocido, o un producto activo sin ninguna fila en la
  hoja → todos son errores explícitos. Una fila ausente nunca se
  interpreta como "disponible".
- Tamaño máximo de descarga: 1 MB (`TAMANO_MAXIMO_BYTES`).
- Redirecciones restringidas: solo se sigue una redirección hacia
  `docs.google.com` o el host real de contenido de Google Sheets
  (`*.googleusercontent.com` — comprobado en vivo contra la hoja real:
  Google redirige el CSV publicado ahí, es su comportamiento normal).
  Cualquier otro destino corta la descarga.
- **Nunca se imprime la URL completa ni el contenido de la hoja en
  logs** — los mensajes de error solo nombran filas/IDs/valores
  puntuales, o el tipo de excepción de red (nunca `str(excepción)`, que
  en algunos casos de `urllib` incluye la URL).
- **Fallo seguro real**: en GitHub Actions esto corre en modo estricto
  siempre. Si algo de lo anterior falla, el paso corta el job ANTES de
  renderizar — el `deploy` (que depende de `build`) nunca corre, y
  GitHub Pages conserva la última versión publicada con éxito. Nunca se
  publica con datos de disponibilidad no confiables.
- Localmente (`build.py`, uso del dueño en su PC) el modo por defecto
  sigue siendo NO estricto (para no romper una vista previa por una hoja
  de prueba incompleta) — pero avisa por consola cuando corre así, y
  `--disponibilidad-estricta` permite probar el modo estricto antes de
  confiar en él.

## data/menu.json: qué puede y no puede contener

`build/validate_json_publico.py` es un control independiente del
Excel/Sheets que corre en CI antes de renderizar:

- Estructura y tipos esperados en cada nivel (`cats`, `prods`, `precios`,
  `config`).
- Campos de producto y de config limitados exactamente a los públicos
  (`extract_common.CAMPOS_PROD_PUBLICOS` / `CAMPOS_CONFIG_PUBLICOS`) —
  cualquier campo interno (costos, ingredientes, `_fila`, `_meta`,
  `disponibilidad_csv_url`, tasas de cambio) es un error si aparece acá.
- IDs únicos, categorías existentes, códigos de disponibilidad válidos,
  ninguna entrada de precio huérfana.
- Ningún marcador de plantilla (`__ALGO__`) sin reemplazar.
- No fija que "tienen que ser 51 productos" — reporta el conteo actual y
  valida coherencia de referencias, para que agregar/sacar productos
  nunca rompa este control por un número hardcodeado.

## Dirección postal: no inventar lo que no existe

El JSON-LD (`build/render.py::_jsonld`) usa `addressLocality` y
`addressRegion` a partir de la dirección real ("Malargüe, Mendoza,
Argentina"), y **nunca incluye `streetAddress`** porque no existe calle
ni altura confirmadas en ningún lado del maestro — se omite esa clave en
vez de inventarla o de asignarle el valor equivocado (bug corregido en
esta fase: antes ponía "Malargüe" como si fuera la calle).

## Pruebas automáticas

`tests/` (stdlib `unittest`, sin dependencias, corre en CI sin instalar
nada) cubre: URLs válidas y maliciosas, WhatsApp/Instagram, integridad
completa de disponibilidad (valor desconocido, ID duplicado/faltante/
adicional, CSV vacío/demasiado grande, fallo de descarga sin filtrar la
URL), el JSON público (incluida una corrida contra el
`data/menu.json` real committeado), el JSON-LD, render sin placeholders,
CSP presente, y ausencia de campos internos/secretos en el HTML
generado.

## Bloqueo externo explícito: la hoja real tiene datos inválidos hoy

La hoja de disponibilidad real (no una hoja de prueba) tiene, al momento
de escribir esto, el texto literal `Disponibilidad` cargado en la columna
de estado para los productos `BLE001`–`BLE004` -- un dato inválido, no
algo introducido por este cierre técnico. **No se modificó la hoja** (fuera
de alcance de esta fase). Esto significa que, con el modo estricto ya
implementado acá, **una publicación real usando este código fallaría hoy**
hasta que el dueño corrija esas 4 filas en la hoja real (dejarlas vacías o
escribir `Disponible`). No se debe hacer una prueba productiva ni una
publicación con el nuevo modo estricto mientras esas filas sigan así.

## Qué queda deliberadamente fuera de esta fase

No se tocó, no se creó ni se planea acá:
- Workload Identity Federation (WIF) / migración de credenciales.
- Migración completa a Google Sheets privado (OIDC).
- Sesión de 180 minutos.
- Dominio propio para el menú (sigue en
  `ameli-casa-de-te-brunch.github.io`).
- Cualquier cambio a Apps Script, PATs, secrets o variables de GitHub —
  ver `SYSTEMS_AND_SECRETS.md` para el inventario de lo que ya existe.

Este documento describe la línea base que quedó después de Fase C1 —
actualizarlo cuando cambie cualquiera de los puntos de arriba.
