# Temas por calendario (Halloween, Navidad, etc.)

Un tema cambia colores, adornos y alguna animación suave de la web y del menú
durante unas fechas, y fuera de ellas el sitio vuelve solo al diseño original.
No hace falta republicar para que empiece o termine.

## Cómo funciona

1. `data/calendario.json` lista los eventos (tema, desde, hasta, prioridad).
2. Los dos builds (web y menú) validan ese archivo con `build/calendario.py` y
   lo embeben en la página como un bloque JSON de datos.
3. `assets/js/tema.js` (idéntico en `web/assets/js/` y `assets/js/`) mira la
   fecha de hoy **en Mendoza** y, si cae dentro de un evento, pone
   `<html data-tema="nombre">`.
4. `temas.css` de cada sitio solo tiene reglas bajo `html[data-tema="nombre"]`.
   Sin el atributo no se aplica ninguna: es el diseño original.

Las fechas son inclusivas: un tema "desde 2026-10-19 hasta 2026-11-02" empieza
a las 00:00 del 19/10 y termina a las 23:59 del 2/11, hora de Mendoza.
Si dos eventos se pisan gana el de mayor `prioridad`; si empatan, el que
empieza más tarde.

## Tareas comunes

**Agregar o mover fechas de un tema que ya existe.** Editar
`data/calendario.json` (un evento por ocurrencia, con `id` único como
`encantada-2027`), abrir un PR y mergear. El CI valida el archivo: una fecha
inválida, un tema que no existe o un campo desconocido hacen fallar el build
antes de publicar nada.

**Previsualizar antes de la fecha.** Agregar `?tema=encantada` al final de la
dirección (web o menú). Para ver el diseño normal aunque haya un tema activo:
`?tema=ninguno`.

**Apagar todo ya.** Poner `"activo": false` en `data/calendario.json`. Apaga
los temas y también la previsualización.

**Crear un tema nuevo.**
1. Agregar el CSS bajo `html[data-tema="nuevo"]:not([data-contraste="alto"])`
   en `web/assets/css/temas.css` y en `assets/css/temas.css`.
2. Los adornos van como SVG propios con nombre plano `tema-nuevo-*.svg` en
   `web/assets/img/` y `assets/img/` (nada de URLs externas ni `data:`, la CSP
   del sitio solo permite imágenes propias).
3. Agregar el id a `TEMAS_CONOCIDOS` en `build/calendario.py`.
4. Agregar el evento al calendario. Los tests de `tests/test_calendario.py`
   verifican que el tema tenga CSS en los dos sitios y que cumpla las reglas.

## Reglas de todo tema

- Solo colores (con los mismos tokens de `:root`), adornos y animaciones
  suaves. La estructura, los textos y los avisos de alérgenos no se tocan.
- En el **menú**: nada de animaciones y nada de fondos oscuros en la lectura
  de productos (los clientes dijeron que los tonos oscuros se leían mal en la
  mesa). El color va en acentos, títulos, chips y botones.
- Respetar el alto contraste y el movimiento reducido del panel de
  accesibilidad (el test lo exige).
- Derechos de autor: se toma inspiración de estéticas y tradiciones, nunca
  nombres, personajes, logos, fotogramas ni frases de películas o marcas
  (por ejemplo, las películas de Disney). Los libros de dominio público
  (como *Alicia en el país de las maravillas*, de Lewis Carroll) sí se pueden
  citar. Las tradiciones culturales (Día de los Muertos) se tratan con
  respeto, sin caricatura.
- Fechas de duelo o conmemoración (24 de marzo, 2 de abril): sin decoración.

## Qué no cubre todavía

- Las páginas de información alimentaria y el 404 no llevan tema (son páginas
  serias, con su propia política de seguridad).
- Tipos de evento previstos pero **no implementados**: `cierre`,
  `horario_especial` y `aviso` (hoy el cartel "Abierto/Cerrado" del menú no
  considera feriados).
- Hoy el calendario se edita en el repositorio. El plan acordado es leerlo
  desde una pestaña de Google Sheets, con el mismo circuito que ya usa la hoja
  de disponibilidad (el cambio dispara el build y el calendario se valida
  igual; si la hoja tiene un error se conserva el último calendario válido).
  Cambiar de Sheets a otra herramienta solo implica cambiar quién escribe
  `data/calendario.json`.
