# Calendario de temas desde Google Sheets

Con esto, mover o agregar fechas de un tema (Halloween, Navidad, etc.) se hace
editando una pestaña de la planilla, sin tocar el repositorio. El circuito es el
mismo que ya usa la disponibilidad ("agotado por hoy").

Cómo funciona por dentro: `build/aplicar_calendario.py` lee la pestaña
publicada (CSV), la valida con las mismas reglas que `data/calendario.json` y,
si está bien, la usa para armar el sitio. Si tiene errores, **no se aplica
nada**: el sitio se publica igual con el último calendario válido del
repositorio, y la corrida de GitHub queda en rojo para que te llegue el mail
de aviso y lo corrijas. Un calendario roto nunca frena un "agotado por hoy".

## Armado, una sola vez (lo hace quien administra la planilla)

1. **Pestaña nueva.** En la planilla de disponibilidad (cuenta institucional),
   agregar una pestaña llamada `Calendario`.
2. **Cargar la plantilla.** Pegar estas dos filas en la pestaña (la primera es el
   encabezado y la segunda el evento de Halloween y Día de los Muertos de este
   año; si se pega todo en la celda A1 y Sheets lo deja en una sola columna:
   Datos > Dividir texto en columnas > coma). Un test del repo verifica que esta
   plantilla sea siempre válida:

   ```csv
   id,tipo,tema,desde,hasta,prioridad,activo,nota
   encantada-2026,tema,encantada,2026-10-19,2026-11-02,10,Sí,Halloween y Día de los Muertos
   ```

   Las columnas son:

   | Columna | Obligatoria | Qué va |
   |---|---|---|
   | `tipo` | sí | hoy solo `tema` |
   | `tema` | sí | hoy solo `encantada` (cada tema nuevo se suma en el código) |
   | `desde` / `hasta` | sí | fechas **AAAA-MM-DD**, ambas incluidas |
   | `prioridad` | no | 0 a 100; si dos eventos se pisan gana el mayor |
   | `activo` | no | vacío o `Sí` = vale, `No` = se ignora la fila (sirve para apagar sin borrar) |
   | `id` | no | si queda vacío se arma solo (`fila-N`) |
   | `nota` | no | texto para las personas; no se publica |

3. **Fechas como texto.** Seleccionar las columnas `desde` y `hasta` y
   Formato > Número > **Texto sin formato**, *antes* de escribir las fechas. Si
   no, Sheets las convierte a `19/10/2026` y el sitio las rechaza (por eso el
   formato es estricto: `10/11` podría ser 10 de noviembre o 11 de octubre).
4. **Listas desplegables** (Datos > Validación de datos > Menú desplegable):
   `tipo` con `tema`; `tema` con `encantada`; `activo` con `Sí, No`.
5. **Publicar solo esa pestaña.** Archivo > Compartir > Publicar en la Web >
   elegir la pestaña `Calendario` y el formato "Valores separados por comas
   (.csv)" > Publicar. Copiar el enlace. Solo se publica esa pestaña (las demás
   no), y solo contiene fechas y nombres de temas, nada sensible.
6. **Guardar el enlace en GitHub.** Repositorio > Settings > Secrets and
   variables > Actions > pestaña **Variables** > New repository variable:
   nombre `CALENDARIO_CSV_URL`, valor el enlace. Es una variable, no un secreto
   (el enlace es público por diseño al publicar). No lo pegues en chats ni en
   documentos.
7. **Que se publique solo al editar.** El Apps Script de la planilla hoy
   dispara el deploy solo cuando se edita la disponibilidad. Para que también
   dispare al editar la pestaña `Calendario`, en la función que atiende la
   edición (`alCambiarDisponibilidad`), al principio, agregar:

   ```js
   if (e && e.range && e.range.getSheet().getName() === 'Calendario') {
     avisarGitHubViaActions();   // la misma función que ya se usa para el deploy
     return;
   }
   ```

   Antes de pegarlo hay que revisarlo contra el código real que está en Apps
   Script (esta guía no lo ve). Sin este paso el calendario igual funciona: se
   aplica en el próximo deploy (cualquier cambio de disponibilidad o un push), o
   al instante con Actions > "Build y publicar menú" > Run workflow.

## Uso diario

- Editar la pestaña, esperar uno o dos minutos y listo. Para confirmar, en
  GitHub > Actions > última corrida > job `build` > paso "Aplicar calendario de
  temas": debe decir `N evento(s) aplicados desde la hoja`.
- Para ver un tema antes de que empiece: `?tema=encantada` al final de la
  dirección.
- Si llega el mail de GitHub "avisar-calendario falló": una fila tiene un error.
  El paso "Aplicar calendario" del job `build` dice el **número de fila** y qué
  campo (nunca copia el contenido de la celda). El sitio sigue funcionando con
  el calendario anterior.

## Seguridad

- Quien puede editar la planilla controla qué tema se muestra en el sitio
  público, pero solo dentro de lo que el validador acepta: temas que existen,
  fechas reales y campos conocidos. No puede inyectar texto ni código en las
  páginas.
- La URL del CSV solo se descarga si es `https://docs.google.com/...`, con
  redirecciones limitadas a los dominios de Google, tope de 1 MB y sin
  reproducir nunca la URL ni el contenido en los logs.
- Mantener el acceso de edición de la planilla restringido, como hoy.
