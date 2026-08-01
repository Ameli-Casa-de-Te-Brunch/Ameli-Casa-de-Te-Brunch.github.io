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
- **Dominio propio** (`menu.ameli.com.ar` o similar) y su DNS.
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

El sitio muestra **3 idiomas: español, inglés, portugués** (el turismo real
de Malargüe). Francés e italiano tienen columnas propias en el maestro —
podés seguir completándolas si querés, pero el validador no las exige ni el
sitio las muestra.

| Querés cambiar... | Hoja | Columna |
|---|---|---|
| Nombre o descripción de un producto (ES/EN/PT) | `01_Menú_Multilingüe` | Nombre: D-F · Descripción: I-K |
| Si un producto está activo / destacado / recomendado / nuevo | `02_Productos_MASTER` | J, K, L, M, N |
| Categorías, orden en el menú, si una categoría se muestra | `03_Categorías` | — |
| Precios (de venta) | `04_Precios` | D (precio local) |
| Temperatura (para el filtro "algo calentito/fresco") y formato de servicio | `05_Gastronomía` | D, E |
| Fotos de producto | `10_Multimedia_SEO` | C (URL imagen principal) — si está vacío, se muestra el patrón botánico en vez de una foto rota |
| WhatsApp, Instagram, dirección, URL del QR | `13_Configuración` | B |

### Hojas en uso vs. hojas sin usar

El pipeline lee **7 hojas**: `01`, `02`, `03`, `04`, `05`, `10`, `13`. Un
producto nuevo necesita fila en esas 7 (mismo ID en cada una), y el ID tiene
que seguir el formato de los que ya existen (3 letras + 3 números, ej.
`TYT008`).

Las hojas `06_Ingredientes`, `07_Alérgenos_Dietas`, `08_Personalización`,
`09_Ingeniería_Menú`, `11_Canales_QR` y `12_Estadísticas` **existen en el
maestro pero el pipeline no las lee ni el validador las exige**. Quedan ahí
para cuando se retomen (ver "Fuera de alcance por ahora" y la sección legal
sobre alérgenos más abajo) — no son "pendientes rotos", son simplemente
hojas que hoy no alimentan el sitio.

### Si ves errores de `#REF!` en los desplegables del Excel

La hoja oculta `99_Listas` (de donde salen los rangos con nombre que arman
los desplegables de las hojas 02/05/07/08) puede romperse al guardar desde
Excel. El validador te avisa si detecta un rango roto, pero **no bloquea la
publicación** — el pipeline lee valores de celda directamente, nunca los
rangos con nombre, así que un `#REF!` ahí no afecta el sitio. Es un
problema del Excel para quien lo edita, no del menú publicado.

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
  dos tipos de letra (`Cormorant Garamond`, `Karla`) en `.woff2`, subset
  `latin` (cubre todos los acentos de ES/EN/PT). Antes, cada visitante le
  mandaba su IP a Google solo por cargar la tipografía; ahora no sale
  ningún request a un tercero para eso, y además carga más rápido en 3G.
  Las dos tienen licencia **SIL Open Font License 1.1** (libre para uso
  comercial) — el texto de la licencia de cada familia viaja junto a los
  archivos (`OFL-CormorantGaramond.txt`, `OFL-Karla.txt`), como exige la
  licencia.
- **El mapa nunca fue un embed.** El botón "Cómo llegar" siempre fue un
  link `<a href>` a Google Maps que solo se activa si la persona lo toca —
  no hay ningún iframe cargando de fondo. Se deja documentado acá porque
  es fácil asumir lo contrario.

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
- **Sin rastreo.** Cero cookies, cero `localStorage`/`sessionStorage`, cero
  analytics, cero píxeles. Auditado directamente en el HTML generado: no
  queda ningún request ni ningún guardado de datos del visitante — el único
  uso de `localStorage` que existió (para no dejar votar dos veces desde el
  mismo dispositivo) se fue junto con todo el sistema de votos en la Fase 2.

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
