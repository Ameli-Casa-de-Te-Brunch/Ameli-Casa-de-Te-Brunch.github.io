# Productos (activo y etiquetas) desde Google Sheets

Con esto se prenden, apagan y etiquetan productos editando una pestaña de la
planilla, desde cualquier computadora, sin correr el build en la PC del dueño.
Son las mismas siete columnas que ya existen en el Excel maestro
(`Ameli_Menu_Maestro_V3.5/V3.6`, hoja "Productos"). Mismo circuito que la
disponibilidad, el calendario y los precios.

**Todo con la cuenta institucional de Google.** Iniciá sesión con ella antes de
abrir la planilla, publicar la pestaña o abrir Apps Script. Nada de esto va en la
cuenta personal.

## Qué hace cada columna

| Columna del Excel | En la hoja | Efecto en el menú |
|---|---|---|
| Producto activo | `activo` | `No` oculta el producto (y su precio). `Sí` lo deja como está. |
| Destacado editorial | `destacado` | Carrusel de destacados, panel grande de su categoría y etiqueta "Favorito de la casa". |
| Recomendado | `recomendado` | Etiqueta "Recomendado". |
| Más vendido | `mas_vendido` | Etiqueta "Lo más pedido". |
| Nuevo | `nuevo` | Etiqueta "Nuevo". |
| Edición limitada | `edicion_limitada` | **Todavía no tiene efecto** (tampoco en el Excel): se guarda pero no cambia nada de lo que se ve. |
| Etiqueta inicial | `etiqueta_inicial` | Texto corto (hasta 40 caracteres) en la ficha del producto, solo en español. |

Un producto muestra **una sola** de las cuatro etiquetas, en este orden de
prioridad: destacado, recomendado, más vendido, nuevo (los productos "Sin TACC"
conservan además su etiqueta propia). Por eso ponerle "Nuevo" a un producto que
ya es "Favorito" no cambia nada.

## Lo que la hoja NO puede hacer

**No puede publicar un producto que el Excel tiene en pausa.** El maestro tiene
130 productos: 51 publicados y 79 en pausa. A los 79 les falta el nombre o la
descripción en algún idioma (o el precio), y esos textos y traducciones se
completan y publican desde el Excel maestro; el repositorio es público y esos
textos no viajan por la hoja. Si en la hoja ponés `Sí` en `activo` a uno de esos
productos, no se publica nada: se informa (el job `avisar-hojas`) y el resto de la
hoja se aplica igual. La columna `estado` de la hoja explica por qué cada uno
está en pausa.

## Reglas

- **Cada fila es independiente**: una fila con un error no frena las demás
  (lo peor que puede pasar es una etiqueta equivocada, que se ve y se arregla).
  La corrida de GitHub queda en rojo después de publicar para que te enteres.
- **Frenan todo** (no se aplica nada): un encabezado con columnas que no existen,
  repetidas o faltantes, más de 500 filas, o **ocultar más de 15 productos de una
  vez** (un `No` pegado por error en toda la columna). Si es a propósito, se
  hace desde el Excel.
- `activo` no puede quedar vacío (tiene que decir `Sí` o `No`). En las demás
  columnas, vacío = `No`. Valen `Sí`, `si`, `SÍ`, `No`, `no`.
- La etiqueta inicial: hasta 40 caracteres, sin `< >` ni enlaces.
- Un producto publicado sin fila en la hoja se deja como está y se informa.
- La URL del CSV solo se descarga si es `https://docs.google.com/...`, con
  redirecciones limitadas a Google, tope de 1 MB, y los mensajes de error citan
  la fila (y el ID solo si ya está publicado), nunca el contenido de una celda.

## Armado, una sola vez

1. **Pestaña nueva.** En la planilla de la cuenta institucional (la misma de la
   disponibilidad, el calendario y los precios), agregar una pestaña llamada
   `Productos`.
2. **Cargar los 130 productos.** Importar `PLANTILLA_Productos.csv` (Archivo >
   Importar > Subir > "Insertar hoja(s) nueva(s)"; está en la carpeta de
   Documentos junto a la guía) o generarla con:

   ```
   python build/aplicar_productos.py --plantilla-desde-excel > productos.csv
   ```

   Trae una fila por producto con el valor de hoy de cada columna. `nombre`,
   `categoria`, `estado` y `nota` son solo para las personas: nunca se leen.
3. **Listas desplegables** (Datos > Validación de datos > Menú desplegable) en
   `activo`, `destacado`, `recomendado`, `mas_vendido`, `nuevo` y
   `edicion_limitada`: `Sí, No`.
4. **Proteger lo que no debe tocar cualquiera** (Datos > Proteger hojas y
   rangos): las columnas `id`, `nombre`, `categoria` y `estado`.
5. **Publicar solo esa pestaña** como CSV (Archivo > Compartir > Publicar en la
   Web > pestaña `Productos` > "Valores separados por comas (.csv)") y copiar el
   enlace. No expone nada nuevo: lo que dice la hoja ya es público en el menú.
6. **Guardar el enlace en GitHub** como variable de repositorio
   `PRODUCTOS_CSV_URL` (Settings > Secrets and variables > Actions > Variables).
   Es una variable, no un secreto.
7. **Que se publique solo al editar.** En el Apps Script de la planilla, sumar la
   pestaña `Productos` a la lista de hojas que disparan el deploy (como
   `Calendario` y `Precios`). Revisar contra el código real antes de pegar. Sin
   este paso funciona igual: se aplica en el próximo deploy, o al instante con
   Actions > "Build y publicar menú" > Run workflow.

## Uso diario

- Cambiar un `Sí`/`No`, esperar uno o dos minutos. Para confirmar: GitHub >
  Actions > última corrida > job `build` > paso "Aplicar productos": lista cada
  cambio.
- **Ver qué cambiaría sin publicar:**
  `PRODUCTOS_CSV_URL=<enlace> python build/aplicar_productos.py --comparar`
  (solo lectura).
- Si llega el mail "avisar-hojas falló": alguna fila no se aplicó. El paso dice
  qué fila y por qué; el resto sí se aplicó.

## El Excel maestro y la hoja

Mientras la hoja esté activa, **el menú publicado toma estas siete columnas de la
hoja** para los productos publicados. Cambiar una etiqueta solo en el Excel y
publicar desde la PC no se va a ver: cambiala en la hoja. Cuando se publica un
producto nuevo desde el Excel, hay que **agregar su fila a la hoja** (mientras no
esté, el aviso lo informa). `--plantilla-desde-excel` genera la lista completa
actualizada.

El contenido (nombres, descripciones, traducciones, alérgenos, imágenes), los
precios de costo y las recetas **siguen en el Excel maestro**, a propósito. Los
precios de venta tienen su propia pestaña (ver `PRECIOS_SHEETS.md`).
