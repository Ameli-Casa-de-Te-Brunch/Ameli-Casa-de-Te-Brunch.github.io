# Menú digital Amelí

Pipeline que genera el menú publicado en
**https://ameli-casa-de-te-brunch.github.io/** a partir de un único archivo:
`data/Ameli_Menu_Maestro_V2.1.xlsx`.

**Regla de oro: nunca se edita el sitio a mano.** Todo cambio entra por el
Excel. `dist/` (el HTML final) se genera solo — no está versionado en git
porque GitHub Actions lo reconstruye de cero en cada publicación.

## Instalación (una sola vez)

1. Instalar [Python 3](https://www.python.org/downloads/) (marcar "Add to PATH" durante la instalación en Windows).
2. Abrir una terminal en esta carpeta y correr:
   ```
   pip install openpyxl
   ```

## Cómo publicar un cambio

1. Editar `data/Ameli_Menu_Maestro_V2.1.xlsx` con Excel o Google Sheets.
2. Guardar el archivo.
3. Doble clic en **`menu.bat`** (o, en una terminal, `python build.py`).

Eso valida el Excel, arma el sitio y lo publica solo (commit + push). A los
2-3 minutos el cambio está visible en la URL de arriba — GitHub Actions lo
reconstruye automáticamente.

Si el validador encuentra un error, **no se publica nada**: corregís lo que
te indica en el Excel y volvés a correr `menu.bat`.

### Otras formas de correrlo

```
python build.py --dry-run    # solo revisa el Excel y te dice qué está mal, no publica nada
python build.py --no-push    # arma el sitio en dist/ para verlo en tu PC, pero no lo publica
python build.py --xlsx otra_version.xlsx   # probar con otro archivo
```

Para ver el resultado en tu PC antes de publicar (con `--no-push` o
`--dry-run` fallido): abrí `dist/index.html` con doble clic, o si querés
verlo como se va a ver online, corré `python -m http.server 8000` dentro de
`dist/` y entrá a `http://localhost:8000`.

## Qué hoja editar para cada cosa

| Querés cambiar... | Hoja | Columna |
|---|---|---|
| Nombre o descripción de un producto (en cualquiera de los 5 idiomas) | `01_Menú_Multilingüe` | Nombre: D-H · Descripción: I-M |
| Si un producto está activo / destacado / recomendado / nuevo | `02_Productos_MASTER` | J, K, L, M, N |
| Categorías, orden en el menú, si una categoría se muestra | `03_Categorías` | — |
| Precios | `04_Precios` | D (precio local) |
| Temperatura (para el filtro "algo calentito/fresco") y formato de servicio | `05_Gastronomía` | D, E |
| Fotos de producto | `10_Multimedia_SEO` | C (URL imagen principal) — si está vacío, se muestra el patrón botánico en vez de una foto rota |
| WhatsApp, Instagram, dirección, URL del QR | `13_Configuración` | B |

Si agregás un producto nuevo, tiene que tener fila en **las 5 hojas** de
arriba (01, 02, 04, 05, 10) con el mismo ID, y el ID tiene que seguir el
formato de los que ya existen (3 letras + 3 números, ej. `TYT008`).

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
data/    Ameli_Menu_Maestro_V2.1.xlsx     ← fuente de verdad, versionada en git
build/   extract.py    xlsx -> dist/data.json
         validate.py   reglas de calidad (IDs, traducciones, categorías, slugs, contacto)
         render.py     data.json + template -> dist/index.html
templates/menu.template.html              ← el HTML, separado de los datos
backend/apps-script/                      ← backend del sistema de "me gusta" (Google Apps Script)
dist/                                     ← generado por build.py, NO versionado en git
build.py                                  ← el comando único: extract -> validate -> render -> publicar
menu.bat                                  ← doble clic para correr build.py en Windows
```

(El prompt original sugería una carpeta `template/` en singular; usé
`templates/` en plural simplemente porque ya existía así de una entrega
anterior — no hay ninguna razón funcional para el nombre, cambiarlo es
cosmético.)

## Decisiones de diseño

- **`dist/` no está versionado.** El deploy de GitHub Actions corre
  `python build.py` de cero en cada push y sube ese resultado — nunca lee lo
  que esté commiteado en `dist/`. Versionarlo era decorativo y agregaba la
  tentación de editarlo a mano por error.
- **El Excel completo sí está versionado**, aunque el repo es público. Hoy
  no tiene datos sensibles (se auditó). El día que se carguen costos o
  márgenes reales en `04_Precios` o `09_Ingeniería_Menú`, hay que revisar de
  nuevo esta decisión — probablemente separando esas hojas a otro lugar
  antes de que eso pase, no versionando el Excel completo con costos.
- **Datos de contacto (WhatsApp, Instagram, dirección) salen siempre del
  Excel**, nunca hardcodeados en el HTML. Si falta alguno, el pipeline oculta
  el botón o enlace correspondiente en vez de publicar un link roto.
- **`menu.bat` publica solo** (commit + push) cuando el Excel cambió y no
  hay errores de validación. Solo lo hace parado en la rama `main` — en
  cualquier otra rama, avisa y no toca nada, para no interferir con trabajo
  de desarrollo en curso.
