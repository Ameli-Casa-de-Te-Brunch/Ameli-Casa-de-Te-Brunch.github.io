# Precios desde Google Sheets

Con esto se cambia un precio (o el tipo de cambio de los equivalentes en otras
monedas) editando una pestaña de la planilla, desde cualquier computadora, sin
correr el build en la PC del dueño. Es el mismo circuito que ya usan la
disponibilidad ("agotado por hoy") y el calendario.

Cómo funciona: en cada publicación, `build/aplicar_precios.py` lee la pestaña
publicada (CSV), la valida y recalcula los precios de `data/menu.json` con las
mismas funciones que usa el extractor del Excel. Un precio mal cargado es peor
que un precio viejo, por eso **ante cualquier duda no se aplica nada**: el sitio
se publica igual con los precios que ya tenía, y la corrida de GitHub queda en
rojo (job `avisar-hojas`) para que llegue el mail de aviso. Un error de precios
nunca frena un "agotado por hoy".

## Qué se valida (todo o nada)

- **Todos** los productos con precio tienen que estar en la hoja, y ninguno
  desconocido. Una fila ausente nunca significa "dejar el precio como estaba".
- Cada precio es un número **entero** de pesos entre 500 y 200.000. Se aceptan
  `4800`, `4.800` y `$ 4.800`; no `4,8` ni `4800.50`.
- **No se puede agregar ni quitar un tamaño** (Chico/Grande, Vaso/Jarra) desde la
  hoja: eso cambia la estructura del menú y se hace desde el Excel maestro. El
  precio grande no puede ser menor que el chico.
- **Ningún precio puede cambiar más de 60 %** de una vez: frena un cero de más
  o de menos. Un ajuste real tan grande se hace desde el Excel maestro.
- Las tres filas de tipo de cambio (`TASA_USD`, `TASA_EUR`, `TASA_BRL`, cuántos
  pesos vale una unidad) tienen que estar y tener un valor razonable. Los
  equivalentes que muestra el menú ("≈ USD 11") son orientativos y se calculan
  siempre sobre el precio chico.
- La URL solo se descarga si es `https://docs.google.com/...`, con
  redirecciones limitadas a Google, tope de 1 MB, y los mensajes de error citan
  la fila y el ID del producto, **nunca** el contenido de una celda.

## Armado, una sola vez

**Todo con la cuenta institucional de Google.** Iniciá sesión con ella antes de abrir la planilla, publicar la pestaña o abrir Apps Script. Nada de esto va en la cuenta personal.

1. **Pestaña nueva.** En la planilla de disponibilidad, agregar una pestaña
   llamada `Precios`.
2. **Cargar los precios de hoy.** Importar `PLANTILLA_Precios.csv` (Archivo >
   Importar > Subir > "Insertar hoja(s) nueva(s)"; está en la carpeta de
   Documentos junto a la guía) o generarla con:

   ```
   python build/aplicar_precios.py --plantilla 1485 1715 289 > precios.csv
   ```

   (los tres números son los tipos de cambio USD, EUR y BRL de hoy). Trae una
   fila por producto (`id`, `nombre`, `categoria`, `precio_chico`,
   `precio_grande`, `nota`) y las tres filas `TASA_*`. `nombre`, `categoria` y
   `nota` son solo para las personas: nunca se leen ni se publican.
3. **Formato de números.** Seleccionar `precio_chico` y `precio_grande` y
   Formato > Número > **Número** (sin formato de moneda ni decimales).
4. **Proteger lo que no debe tocar cualquiera.** Datos > Proteger hojas y
   rangos: dejar editables solo las columnas `precio_chico`/`precio_grande` (y
   las filas `TASA_*` si querés que el local actualice el dólar), y proteger `id`.
   Si querés que solo vos cambies precios, proteger toda la pestaña.
5. **Publicar solo esa pestaña** como CSV (Archivo > Compartir > Publicar en la
   Web > pestaña `Precios` > "Valores separados por comas (.csv)") y copiar el
   enlace. Los precios ya son públicos en el menú, no se expone nada nuevo.
6. **Guardar el enlace en GitHub** como variable de repositorio
   `PRECIOS_CSV_URL` (Settings > Secrets and variables > Actions > Variables).
   Es una variable, no un secreto.
7. **Que se publique solo al editar.** En el Apps Script de la planilla, donde ya
   se dispara el deploy al editar la disponibilidad (y el calendario), sumar la
   pestaña `Precios` a la lista de hojas que disparan. Revisar contra el código
   real antes de pegar. Sin este paso funciona igual: se aplica en el próximo
   deploy, o al instante con Actions > "Build y publicar menú" > Run workflow.

## Uso diario

- Cambiar el número en `precio_chico`/`precio_grande`, esperar uno o dos
  minutos. Para confirmar: GitHub > Actions > última corrida > job `build` >
  paso "Aplicar precios": dice cuántos productos cambiaron.
- **Ver qué cambiaría sin publicar:**
  `PRECIOS_CSV_URL=<enlace> python build/aplicar_precios.py --comparar` (solo
  lectura).
- Si llega el mail "avisar-hojas falló": una fila tiene un error. El paso
  "Aplicar precios" dice qué fila y qué regla. El sitio sigue con los precios
  anteriores.

## El Excel maestro y los precios

Mientras la hoja de precios esté activa, **el sitio publicado toma los precios
de la hoja**, no del Excel. `data/menu.json` en el repositorio conserva los del
Excel como respaldo (la hoja se aplica sobre una copia en cada publicación; no se
commitea). Dos consecuencias:

- Si cambiás un precio en el Excel y lo publicás con `python build.py
  --publicar`, **no se va a ver** mientras la hoja diga otra cosa. Cambialo en la
  hoja.
- De vez en cuando conviene llevar los precios de la hoja de vuelta al Excel
  (`--comparar` muestra las diferencias) para que el costeo y el respaldo no
  queden desactualizados.

El costeo, los márgenes, las recetas, las descripciones, las traducciones y los
alérgenos **siguen en el Excel maestro**: no se pasan a la hoja a propósito
(5 idiomas y riesgo sanitario y legal).
