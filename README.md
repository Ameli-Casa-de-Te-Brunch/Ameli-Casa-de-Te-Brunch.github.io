# Menú digital Amelí

Pipeline que genera el menú publicado en
**https://ameli-casa-de-te-brunch.github.io/** a partir de un único archivo:
el Excel maestro (`Ameli_Menu_Maestro_Vx.x.xlsx` — la versión más reciente
que tengas en tu carpeta de OneDrive; el pipeline la encuentra solo).

**Regla de oro: nunca se edita el sitio a mano.** Todo cambio entra por el
Excel. `dist/` (el HTML final) se genera solo — no está versionado en git
porque GitHub Actions lo reconstruye de cero en cada publicación.

**El Excel maestro no vive en este repo.** Tiene costos y márgenes por
producto, y este repo es público — ver la sección
["Qué es público y qué no"](#qué-es-público-y-qué-no) para el detalle y el
porqué. Vive en tu PC (con respaldo en OneDrive). Lo que sí está versionado
es `data/menu.json`, una copia derivada que solo tiene lo que el sitio
realmente publica.

## Fuera de alcance por ahora

Este repo es **solo el menú digital**. Lo siguiente está congelado a
propósito — no se retoma hasta resolver privacidad y hosting:

- **Sitio institucional** (una página de marca/presencia separada del menú).
- **Sistema de "me gusta" / votos** (backend Apps Script, contador en las
  tarjetas). Se sacó del sitio — ver más abajo por qué.
- **Dominio propio** (`amelicasadete.com.ar`) — todavía no comprado. El
  proyecto ya está preparado para esa migración (ver "Migración a dominio
  propio" más abajo); no hay nada que rehacer cuando se compre.
- **Sesión temporal de 180 minutos con backend** (Cloudflare Workers/
  Supabase/etc. + tokens firmados) — arquitectura documentada pero sin
  implementar (ver "Arquitectura futura: sesión de 180 minutos" más abajo).
  No confundir con un timer de JavaScript: eso no es lo que se pidió, y no
  se va a fingir que sí con un `setTimeout`.
- **Analytics** de cualquier tipo (visitas, escaneos de QR, etc.).

Si en algún momento se retoma alguno de estos puntos, que sea una decisión
explícita, no un agregado de paso.

## Instalación (una sola vez)

1. Instalar [Python 3](https://www.python.org/downloads/) (marcar "Add to PATH" durante la instalación en Windows).
2. Abrir una terminal en esta carpeta y correr:
   ```
   pip install openpyxl
   ```
3. El pipeline busca el Excel en, en este orden: el flag `--xlsx`, la
   variable de entorno `AMELI_XLSX_PATH`, un archivo `.env` en la raíz del
   repo (no se sube a git) con la línea `AMELI_XLSX_PATH=...`, o si ninguna
   de esas está, en la ubicación de OneDrive donde vive hoy. Si tu archivo
   está en esa ubicación no tenés que configurar nada.

## Cómo publicar un cambio

1. Editar el Excel maestro con Excel o Google Sheets.
2. Guardar el archivo.
3. Doble clic en **`menu.bat`** — valida y arma el sitio en tu PC (no publica
   todavía). Revisá que no haya `[ERROR]` en la salida.
4. Doble clic en **`publicar.bat`** — te muestra exactamente qué archivo va a
   subir (solo `data/menu.json`, nunca el Excel) y te pide que escribas
   `si` para confirmar. Recién ahí commitea y pushea.

A los 2-3 minutos de publicar, el cambio está visible en la URL de arriba —
GitHub Actions reconstruye el sitio solo a partir de `data/menu.json`.

Si el validador encuentra un error, **`menu.bat` no genera nada** y
**`publicar.bat` no tiene nada para subir**: corregís lo que te indica en el
Excel y volvés a correr `menu.bat`.

## Disponibilidad en vivo (sin tocar el Excel ni el código)

Esto es aparte del flujo de arriba, y a propósito: cambiar el precio o la
descripción de un producto sigue pasando por el Excel + `publicar.bat` (son
cambios que ameritan pensarlos). Pero "se terminó la Matilda" necesita
poder resolverse desde el celular, en segundos, sin este proyecto de por
medio — ver el detalle completo (y por qué se descartaron otras
arquitecturas) en `Disponibilidad_en_vivo_instrucciones` que te compartí.

**Cómo funciona:** una hoja de Google Sheets con una fila por producto
(`ID`, `Nombre`, `Disponibilidad`) que el personal edita desde el celular.
Un Apps Script avisa a GitHub cada vez que cambia una celda; GitHub Actions
reconstruye el sitio usando el `data/menu.json` ya commiteado (nunca toca
el Excel, nunca necesita verlo). Todos los demás datos del producto
(nombre, precio, descripción, alérgenos, fotos) siguen viniendo únicamente
del Excel — la hoja de Sheets solo pisa el campo `disp` de cada producto.

**Sobre los tiempos, con precisión:** el workflow de GitHub Actions en sí
tarda ~30-90 segundos en correr (build + deploy). Eso NO es lo mismo que
"el visitante ya ve el cambio" — GitHub Pages sirve detrás de una caché
pública (CDN) que en la práctica puede seguir mostrando la versión
anterior varios minutos más, incluso con el workflow ya terminado en ✅.
Para verificar un cambio: primero confirmá en la pestaña Actions que la
corrida terminó en ✅, y recién después probá el sitio con un refresco
forzado (Ctrl+Shift+R) o desde otro dispositivo/red antes de asumir que
algo no funcionó.

**Piezas del lado del código** (si hay que tocarlas de nuevo):
- `build/aplicar_disponibilidad.py` — lee la hoja publicada como CSV y
  parchea la disponibilidad, con integridad de filas estricta (ver
  `docs/SECURITY_BASELINE.md` y `docs/operations/SOLD_OUT.md`): valores
  desconocidos, IDs duplicados/desconocidos, filas sin ID con un estado, o
  un producto activo sin fila, hacen fallar el paso en vez de publicarse
  con datos no confiables. Si la URL simplemente no está configurada,
  eso no es un error — la disponibilidad en vivo sigue siendo opcional.
- `build.py` lo aplica en memoria en modo NO estricto por defecto (para
  que la vista previa local no se rompa por una hoja de prueba
  incompleta), usando la URL del Excel, campo "URL de disponibilidad
  (Google Sheets)" en *Resumen y Configuración*. `--disponibilidad-estricta`
  prueba localmente el mismo modo estricto que usa CI.
- `.github/workflows/deploy.yml` lo corre standalone, leyendo la URL de la
  **repo variable** `DISPONIBILIDAD_CSV_URL` (Settings → Secrets and
  variables → Actions → Variables — no es un secreto: una hoja "publicada
  en la web" ya es pública por diseño de Google, por eso va como variable
  y no como secret).
- El disparador es `repository_dispatch` con `event_type:
  actualizar-disponibilidad`, invocado por el Apps Script de la hoja — no
  por nada de este repo.

### Otras formas de correrlo

```
python build.py                # valida y arma dist/ en tu PC, no toca git
python build.py --dry-run      # solo revisa el Excel y te dice qué está mal
python build.py --publicar     # arma el sitio y ofrece publicar (pide "si")
python build.py --xlsx otra_version.xlsx
```

Para ver el resultado en tu PC: abrí `dist/index.html` con doble clic, o si
querés verlo como se va a ver online, corré `python -m http.server 8000`
dentro de `dist/` y entrá a `http://localhost:8000`.

## Qué hoja editar para cada cosa

Desde el maestro **V3.1** el archivo tiene **4 hojas**: `Resumen y
Configuración`, `Categorías`, `Productos` (nombre, descripción, precio,
alérgenos — lo esencial del menú) y `Productos - Backoffice` (ingredientes
y personalización, referencia interna que el sitio nunca lee).

El sitio muestra **los 5 idiomas trabajados: español, inglés, portugués,
francés e italiano**.

| Querés cambiar... | Hoja | Columna |
|---|---|---|
| Nombre o descripción de un producto (ES/EN/PT/FR/IT) | `Productos` | Nombre: D-H · Descripción: I-M |
| Si un producto está activo / destacado / recomendado / nuevo | `Productos` | N, O, P, Q, R |
| Categorías, orden alfabético, si una categoría se muestra | `Categorías` | — |
| Precios (de venta) — un solo precio, o "chico/grande" (té, café, blends) o "vaso/jarra" (batidos y jugos) | `Productos` | U (precio chico o único) · V (precio grande, solo si el producto tiene dos tamaños) |
| Alérgenos (15 banderas + estado de validación) | `Productos` | AF-AT (banderas) · AU (estado de validación) — no se publica nada de un producto hasta que su fila diga "Validado por cocina" o "Validado por proveedor" |
| Temperatura (para el filtro "algo calentito/fresco") y formato de servicio | `Productos` | X, Y |
| Fotos de producto | `Productos` | Z (ruta relativa propia, ej. `assets/img/tyt004.webp`) — nunca una URL externa: la CSP solo permite `img-src 'self'`, y `build/validate_json_publico.py` rechaza cualquier otra forma (URL externa, ruta absoluta, `..`). Si está vacío, se muestra un gradiente con la inicial del producto en vez de una foto rota |
| Opción de leche vegetal / sin lactosa en una bebida | `Productos - Backoffice` | columnas "Leche vegetal" / "Leche sin lactosa" (dentro de Personalización) — no es un producto aparte, es un agregado que se muestra en el detalle de la bebida correspondiente |
| WhatsApp, Instagram, dirección, URL del QR | `Resumen y Configuración` | columna Valor, bloque "Configuración del sitio" (filas 16-25) |
| Ingredientes, personalización — referencia interna | `Productos - Backoffice` | — (nada de esto lo lee el sitio, salvo leche vegetal/sin lactosa arriba) |

Un producto nuevo necesita una fila en `Productos` (y opcionalmente otra en
`Productos - Backoffice` si querés cargarle ingredientes), con un ID que
siga el formato de los que ya existen (3 letras + 3 números, ej. `TYT008`).

**"Adicionales" ya no es una categoría del menú.** Leche vegetal y leche
sin lactosa dejaron de ser productos propios (no tenía sentido pedirlos
solos) y pasaron a ser un agregado que se muestra en el detalle de cada
bebida que lleva leche.

### Alérgenos: cómo se valida y se publica

La validación es **por producto, no global**: cada fila de `Productos`
tiene su propia columna "Estado de validación (alérgenos)" (columna AU),
y esa fila puntual se publica con sus datos de alérgenos solo si ahí dice
**"Validado por cocina" o "Validado por proveedor"**. Un producto sin
validar no bloquea a los demás — cada uno se evalúa solo.

Estado actual: los 51 productos publicados hoy ya tienen su columna AU
validada (no quedan productos activos en "Pendiente"). Un producto nuevo
que se agregue sin completar esa columna se publica igual, simplemente
sin sus datos de alérgenos, hasta que se valide.

## Qué hacer si el validador se queja

El mensaje te dice tres cosas: **qué** pasa, en qué **hoja y fila**, y qué
**columna** corregir. Ejemplo:

```
[ERROR] Fila 51 (TYT004 · Red velvet): falta la descripción en portugués.
        Cargala en la hoja 01_Menú_Multilingüe, columna K.
```

- **`[ERROR]`**: bloquea la publicación. Hay que corregirlo sí o sí.
- **`[AVISO]`**: no bloquea nada, es solo para que lo tengas en el radar
  (ej. "este producto todavía no tiene precio cargado").

Después de corregir el Excel, volvé a correr `menu.bat` (o `python build.py
--dry-run` si solo querés revisar sin publicar todavía).

## Estructura del proyecto

```
(fuera del repo)  Ameli_Menu_Maestro_Vx.x.xlsx   ← fuente de verdad, en tu PC/OneDrive
                                                    (el pipeline usa el más reciente por fecha)
data/    menu.json                        ← derivado del Excel, SOLO campos públicos, versionado
build/   extract.py       xlsx -> data/menu.json (filtrado) + datos completos en memoria
         validate.py      reglas de calidad (IDs, traducciones, categorías, slugs, contacto)
         render.py        menu.json + template -> dist/index.html (copia assets/ también)
         config_local.py  resuelve dónde está el Excel en esta máquina
templates/menu.template.html              ← el HTML, separado de los datos
assets/fonts/                             ← Cormorant Garamond + Karla, self-hosteadas
assets/css/menu.css                       ← todo el CSS, external (no inline)
assets/js/menu.js                         ← toda la lógica de la página, external (no inline)
assets/img/                               ← favicon, apple-touch-icon, imagen de vista previa
                                             (og:image) — generados del logo, no son fotos de
                                             producto. Se regeneran a mano si el logo cambia
                                             (no forman parte del build automático).
dist/                                     ← generado, NO versionado en git
build.py                                  ← construir (extract -> validate -> render) y, si pedís, publicar
menu.bat / publicar.bat                   ← doble clic en Windows para cada paso
```

(El prompt original sugería una carpeta `template/` en singular; usé
`templates/` en plural simplemente porque ya existía así de una entrega
anterior — no hay ninguna razón funcional para el nombre, cambiarlo es
cosmético.)

## Decisiones de diseño

- **El Excel completo NO está versionado.** Tiene columnas de costo unitario
  y margen (hojas `04_Precios` y `09_Ingeniería_Menú`) que son información de
  negocio, no algo para un repo público. Vive en tu PC. `data/menu.json` es
  lo que sí se versiona: una proyección filtrada a mano en `extract.py`
  (función `datos_publicos()`) que solo puede contener nombre, descripción,
  categoría, badges, momentos, precio de venta y los datos de contacto — si
  alguna vez agregás un campo a esa función, pensalo dos veces antes de
  agregar algo que no debería ser público.
- **El equivalente en USD/EUR/BRL es una conversión fija, no una cotización
  en vivo.** Se calcula una sola vez, en `extract.py`, con la tasa que
  cargues a mano en "Tipo de cambio ARS/USD" / "ARS/EUR" / "Real" (hoja
  Resumen y Configuración) — queda fija hasta el próximo `python build.py`.
  La alternativa (pedirle la cotización a una API externa desde el
  navegador de cada visitante) se descartó a propósito: abriría
  `connect-src` a un tercero (hoy es `'none'`), y las APIs gratuitas de
  cotización dan el dólar "oficial", que en Argentina casi nunca es el que
  un turista termina pagando (blue/MEP/tarjeta) — mostrarlo podría
  confundir más que ayudar. USD se muestra en cualquier idioma si hay tasa
  cargada; EUR además solo en francés e italiano; BRL solo en portugués.
- **La ruta del Excel es configurable** (flag, variable de entorno, o
  `.env` gitignoreado) porque cada máquina donde esto se corra va a tenerlo
  en un lugar distinto.
- **GitHub Actions nunca ve el Excel.** El workflow de deploy solo lee
  `data/menu.json` (ya commiteado) y corre `render.py` — no instala
  `openpyxl` ni tiene forma de leer un Excel que no existe en el runner.
  Validar (`extract.py` + `validate.py`) pasa únicamente en tu PC.
- **`dist/` no está versionado.** El deploy reconstruye el HTML de cero en
  cada push a partir de `data/menu.json` — nunca lee lo que esté commiteado
  en `dist/`. Versionarlo era decorativo y agregaba la tentación de editarlo
  a mano por error.
- **Datos de contacto (WhatsApp, Instagram, dirección) salen siempre del
  Excel**, nunca hardcodeados en el HTML. Si falta alguno, el pipeline oculta
  el botón o enlace correspondiente en vez de publicar un link roto.
- **Construir y publicar son pasos separados.** `python build.py` (o
  `menu.bat`) solo valida y arma el sitio en tu PC — nunca toca git.
  Publicar requiere `--publicar` (o `publicar.bat`), que además te muestra
  el archivo exacto que va a subir y espera que escribas `si`. Nunca
  commitea nada que no haya listado antes.
- **Sin sistema de votos.** Existió un botón de "me gusta" con backend en
  Google Apps Script; se sacó por completo (ver "Fuera de alcance por
  ahora"). Obligaba a un endpoint público sin autenticación y a mantener
  claves — y como el voto es manipulable desde el navegador, tampoco iba a
  servir como dato real para decidir la carta.
- **Fuentes self-hosteadas, no Google Fonts.** `assets/fonts/` tiene los
  tres tipos de letra (`Cormorant Garamond`, `Karla`, `Montserrat`) en
  `.woff2`, subset `latin` (cubre todos los acentos de ES/EN/PT/FR/IT).
  Antes, cada visitante le mandaba su IP a Google solo por cargar la
  tipografía; ahora no sale ningún request a un tercero para eso, y además
  carga más rápido en 3G. Las tres tienen licencia **SIL Open Font License
  1.1** (libre para uso comercial) — el texto de la licencia de cada
  familia viaja junto a los archivos (`OFL-CormorantGaramond.txt`,
  `OFL-Karla.txt`, `OFL-Montserrat.txt`), como exige la licencia.
  `Montserrat` se suma para replicar la tipografía real del logo: "AMELÍ"
  usa `Cormorant Garamond` 600 (SemiBold) en mayúsculas con tracking
  chico; "CASA DE TÉ & BRUNCH" usa `Montserrat` 300 (Light) en mayúsculas
  con tracking más generoso — mismos pesos y tracking que especificó el
  dueño a partir del diseño original.
- **El mapa nunca fue un embed.** El botón "Cómo llegar" siempre fue un
  link `<a href>` a Google Maps que solo se activa si la persona lo toca —
  no hay ningún iframe cargando de fondo. Se deja documentado acá porque
  es fácil asumir lo contrario.

## Cabeceras de seguridad (Content-Security-Policy)

GitHub Pages sirve archivos estáticos: no hay forma de mandar cabeceras HTTP
propias (nada de `Content-Security-Policy` real, `X-Frame-Options`, etc.).
La única herramienta disponible es declarar la política por `<meta>` dentro
del `<head>` del HTML, que es lo que hace `render.py` en cada build.

La política queda así de restrictiva porque el sitio no necesita nada de
afuera — sin analytics, sin fuentes de Google, sin mapa embebido, sin
llamadas a ningún backend:

```
default-src 'none';
script-src 'self' 'sha256-<hash del script inline>';
style-src 'self';
font-src 'self';
img-src 'self';
connect-src 'none';
frame-ancestors 'none';
base-uri 'none';
form-action 'none';
```

- **`default-src 'none'`**: nada carga salvo lo que se permite explícitamente
  abajo. Cierra la puerta por defecto en vez de tener que acordarse de
  bloquear cada cosa nueva.
- **`frame-ancestors 'none'`**: nadie puede meter el menú en un `<iframe>`
  ajeno (protección contra clickjacking).
- **`connect-src 'none'`**: el sitio no llama a ningún backend — ni falta
  que hace, ni se va a agregar sin querer sin que esto lo bloquee primero.
- **CSS y JS son archivos externos** (`assets/css/menu.css`,
  `assets/js/menu.js`), no bloques `<style>`/`<script>` inline — así
  `style-src` puede ser `'self'` sin necesitar `'unsafe-inline'`.
- **Un solo `<script>` sigue siendo inline**, a propósito: los 4 datos que
  salen del Excel en cada build (`CATS`, `PRODS`, `PRECIOS`,
  `WSP_NUMBER`) tienen que viajar con el HTML. En vez de abrir
  `script-src` con `'unsafe-inline'` (lo que dejaría correr *cualquier*
  script inline que se cuele, ej. si algún día una descripción de producto
  trajera HTML raro), `render.py` calcula el hash SHA-256 exacto de ese
  bloque en cada build y lo declara en la CSP (`'sha256-...'`). Solo ese
  contenido exacto puede correr — nada más.
- **Nada de `unsafe-eval`**, como pidió el dueño del proyecto.

**Limitación real, no un bug:** `frame-ancestors` no tiene ningún efecto
cuando se declara por `<meta>` — el navegador lo ignora y lo dice por
consola ("ignored when delivered via a meta element"). Es una regla del
propio estándar de CSP, no algo que se pueda arreglar desde el HTML.
GitHub Pages no permite mandar cabeceras HTTP propias, así que **la
protección contra clickjacking no está activa en la práctica**, aunque la
política la declare. Se deja igual declarada porque no rompe nada y no
cuesta nada tenerla, pero hay que saber que es cosmética en este hosting.

**Una vuelta anterior de esto tenía un bug real**: la primera versión de la
CSP asumía que no había ningún estilo inline dinámico, pero el propio JS
del sitio sí los generaba (gradientes de los destacados, animación
escalonada de las tarjetas, el arrastre del panel de detalle) — la CSP los
bloqueaba en la práctica y rompía esas tres cosas. Se migraron todos a
clases CSS fijas (o cuantizadas, para el arrastre) y las fotos de producto
pasan de `background-image` a `<img>` real. Resultado actual, verificado
en el navegador: **cero errores de consola**, `style-src 'self'` sin
`'unsafe-inline'` en ningún lado.

## Cumplimiento legal (Argentina)

Esto no es asesoramiento legal — son reglas operativas para que el sitio no
publique algo riesgoso por accidente. Validar con fuentes oficiales antes de
cualquier decisión real.

- **Alérgenos.** La hoja `07_Alérgenos_Dietas` está toda en "Verificar" —
  nadie confirmó todavía qué producto tiene qué alérgeno con recetas y
  etiquetas reales. El pipeline **nunca leyó esa hoja** (no hay ícono ni
  afirmación de alérgeno en ningún lado del sitio hoy), y ahora además
  `validate.py` tiene una traba activa: si algún día se agrega un campo de
  alérgenos a un producto sin que la hoja esté 100% en "Validado" en la
  columna Q, **el build falla con error**, no con aviso. Probado con un caso
  simulado antes de este commit.
- **"Sin TACC".** El menú ya aclara que son productos tercerizados
  (`Producto tercerizado` / `Outsourced product` / `Produto terceirizado`,
  categoría `STC`) — no se le agregó la leyenda a ningún producto que no la
  tuviera antes, y no se va a agregar sin certificación real del proveedor.
- **Precios.** Se muestran en pesos (`$ X.XXX`) como precio final — el
  esquema de Monotributo del negocio no discrimina IVA. `validate.py` avisa
  (warning, no bloquea, porque hoy no hay ningún precio cargado todavía) si
  un producto activo se publica sin precio — ver la sección de arriba sobre
  qué hace el validador.
- **Sin rastreo.** Cero cookies, cero analytics, cero píxeles, cero request
  a terceros (`connect-src 'none'`, auditado en el HTML generado). El único
  uso de `localStorage` es para las preferencias de accesibilidad (tamaño
  de texto, contraste, idioma) — vive únicamente en el dispositivo del
  visitante, nunca sale de ahí, y no es tracking: no identifica a nadie ni
  se lee desde ningún lado más que el propio navegador.

## Qué es público y qué no

**Regla:** al sitio publicado solo sale lo que un cliente necesita para
elegir algo y venir — carta (nombres, descripciones, categorías), precios
de venta, fotos, horarios, dirección y contacto. Todo lo demás es interno
y nunca debe cruzar a `data/menu.json`, al HTML generado, ni a ningún commit.

**Nunca subir al repo (ni al Excel siquiera si algún día se lo versiona
de nuevo, ni a ningún archivo versionado):**
- El Excel maestro completo (`.xlsx`/`.xlsm`) — está en `.gitignore` a propósito.
- Costo unitario, margen, proveedor (hojas `04` más allá del precio de
  venta, `09`).
- Ingredientes internos, notas operativas, reglas de personalización
  (hojas `06`, `08`).
- Estadísticas de ventas o de tráfico interno (hoja `12`).
- Cualquier credencial, token o URL de backend con permisos de escritura,
  en texto plano, en cualquier archivo versionado. Van en secrets de GitHub
  Actions o en un archivo gitignoreado (`.env`) — hoy el sitio no tiene
  ningún backend propio (se sacó el sistema de votos), así que esto no
  aplica a nada actual, pero queda como regla para lo que venga.
- Capturas de pantalla, rutas locales (`C:\Users\...`), o cualquier dato
  personal que no sea el contacto de negocio de Amelí.

**Si tenés dudas sobre si algo puede publicarse:** no lo subas y preguntá
primero. Es mucho más fácil agregar un dato después que sacarlo de un repo
público una vez que salió.

## Migración a dominio propio

El sitio está armado para que comprar `amelicasadete.com.ar` sea un cambio
de configuración chico, no una reconstrucción. Todo lo que depende del
dominio sale de **una sola fuente**: el campo "URL base del menú" en la
hoja *Resumen y Configuración* del Excel. No hay ningún `github.io`
hardcodeado en el código — se verificó con una búsqueda completa del
repositorio. Todos los `href`/`src` de assets son rutas relativas
(`assets/css/menu.css`, no `/assets/css/menu.css`), así que funcionan igual
si el sitio se sirve desde la raíz de un dominio o desde un subpath como
`amelicasadete.com.ar/menu`.

**Qué ya usa esa URL base hoy** (todo se regenera solo con `python
build.py` una vez actualizado el campo): `og:url`, `og:image`,
`<link rel="canonical">`, el JSON-LD (Schema.org), `robots.txt` y
`sitemap.xml`.

### Pasos para cuando se compre el dominio

1. Configurar el dominio en GitHub Pages (Settings → Pages → Custom domain)
   apuntando a `amelicasadete.com.ar` — o, si se prefiere `/menu` como
   subpath, evaluar en ese momento si GitHub Pages custom domain soporta
   ese path o si conviene otro hosting (Cloudflare Pages/Netlify, ambos
   gratis en este volumen) sirviendo este mismo `dist/` bajo `/menu`.
2. Elegir canónico con o sin `www` y redirigir la variante secundaria.
3. Actualizar "URL base del menú" en el Excel con la URL definitiva.
4. Correr `python build.py --publicar` — esto ya regenera OG, canonical,
   JSON-LD, `robots.txt` y `sitemap.xml` con la URL nueva, sin tocar código.
5. Dar de alta la propiedad en Google Search Console, verificar por DNS,
   enviar el `sitemap.xml` nuevo.
6. Enlazar Google Business Profile al dominio definitivo.
7. Configurar correo (`hola@amelicasadete.com.ar` y las cuentas que
   correspondan) con SPF/DKIM/DMARC — recién en este momento, no antes.
8. Recién acá: generar el QR físico definitivo apuntando al dominio propio,
   e imprimirlo. No antes — el QR no debería tener que reimprimirse nunca
   más después de este punto, ni por cambios de precio, de menú, de fotos
   ni de hosting.
9. `ameli-casa-de-te-brunch.github.io` queda como infraestructura interna
   (GitHub Pages la sigue sirviendo) o como redirect al dominio nuevo, pero
   deja de ser la URL que ve un cliente.

## Arquitectura futura: sesión de 180 minutos

**Todavía no implementada a propósito** — se documenta acá para no
perder el diseño, pero no se construye hasta tener el dominio propio y
decidir el proveedor de backend. Un timer solo de JavaScript no cumple lo
pedido (se esquiva con un refresh) y no se va a fingir que sí.

**Flujo previsto:**

```
QR físico permanente (impreso una sola vez)
        │
        ▼
amelicasadete.com.ar/menu
        │
        ▼
backend / edge function (Cloudflare Workers, o equivalente)
        │  crea un token firmado con:
        │   - hora de creación
        │   - hora de expiración (creación + 180 min)
        │   - estado
        ▼
menú servido con el token válido en un header/cookie de sesión
        │
        ▼
cada carga verifica el token en el backend, nunca confía en el reloj
del navegador — un refresh no renueva ni esquiva la expiración
        │
        ▼
al vencer: pantalla "Tu visita al menú terminó", con los links
institucionales (Instagram, WhatsApp, ubicación, TripAdvisor) igual
accesibles — lo que expira es la carta, no el contacto con Amelí
```

**Por qué no es trivial** (para que quede claro por qué se dejó para una
fase aparte, no por pereza):
- Requiere un proveedor de cómputo real (Workers/Functions) — GitHub Pages
  sirve archivos estáticos, no puede emitir ni verificar tokens.
- Requiere un secreto de firma gestionado con cuidado — el primer secreto
  real que tendría este proyecto.
- Cambia el modelo de amenazas: pasa de "sitio estático sin backend" (lo
  que hoy simplifica enormemente la seguridad) a un sistema con su propio
  ciclo de vida, rotación de claves y superficie de ataque.
- Preferencias de accesibilidad e idioma deberían sobrevivir dentro de una
  misma sesión (ya lo hacen vía `localStorage`, que no depende de esto) pero
  no más allá de los 180 minutos ni de una visita a otra.

**Cuándo retomarlo:** cuando el dominio propio esté andando y haya decidido
el proveedor de backend. Hasta entonces, el sitio sigue siendo 100%
estático y sin esa dependencia.
