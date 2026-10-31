# Diseño combinado "capítulos" (portada y menú)

Desde 2026-10-14 la portada y el menú comparten un mismo lenguaje visual:
encabezado mínimo con el logotipo al centro, portada a pantalla completa con
leyendas sobre la foto, capítulos que alternan
claro y oscuro (con las curvas de nivel), números grandes en la colección de tés
y los destacados del menú, y una barra de pedido fija abajo.

## Cómo se prende y se apaga

Todo el diseño cuelga de un atributo en la etiqueta `<html>` de los dos templates:

```html
<html lang="es" data-estilo="capitulos">
```

- `web/templates/index.template.html` (portada)
- `templates/menu.template.html` (menú)

**Rollback sin revertir código:** sacar `data-estilo="capitulos"` de los dos
templates y publicar. Sin el atributo, los estilos nuevos no se aplican y las
piezas nuevas (`.barra-pedido`, `.sticker`) quedan ocultas. El botón
flotante de WhatsApp vuelve solo.

**Rollback completo:** revertir el merge del PR (un solo commit).

## Dónde está el código

| Qué | Dónde |
|---|---|
| Estilos de la portada | bloque `DISEÑO COMBINADO "capítulos"` al final de `web/assets/css/site.css` |
| Estilos del menú | el mismo bloque al final de `assets/css/menu.css` |
| Textos de la barra de pedido del menú (5 idiomas) | `UI.barraPedido` en `assets/js/menu.js` |
| Tests | `tests/test_estilo_combinado.py` |

## Reglas que no hay que romper

- **Dos tonos de base** (verde oscuro y crema/blanco) y **un solo acento** (salvia). El calafate queda para detalles chicos.
- **El logotipo es el de la marca** (Amelí en versalitas), no una versión nueva.
- Formas del resto del sitio: botones píldora, tarjetas redondeadas.
- Los `:hover` van dentro de `@media (hover:hover) and (pointer:fine)` (en el celular quedaban pegados).
- Las bandas a todo el ancho se hacen con `box-shadow` + `clip-path`; **nunca** con capas más anchas que la pantalla (`inset` negativo): agrandan el viewport en el celular.
- La cinta se sacó del todo el 2026-10-31 (no gustó).
- Las alturas fijas salen de `--alto-encabezado` y `--alto-barra`, no de números sueltos.
- La leyenda sobre la foto necesita fondo ≥ 62 % para cumplir el contraste.
- Al cambiar CSS, subir el `?v=` del `<link>` en el template (si no, el navegador usa la versión en caché).
- Textos nuevos del menú: en los 5 idiomas (`es`, `en`, `pt`, `fr`, `it`).

## Pendientes conocidos

- La barra de pedido de la portada dice solo "Hacé tu pedido por WhatsApp". "Retiralo en Amelí" queda fuera hasta que se confirme el servicio.
- Accesibilidad (2026-10-14, rama `accesibilidad-2026-10-14`, `tests/test_accesibilidad.py`): enlace "Saltar al menú" y un único `<main>`; anillo de foco salvia/blanco sobre fondos oscuros; chips, categorías y buscador de 44 px o más; selector de idioma con `aria-current` (sin roles listbox); con texto A+/A++ el menú pasa a una columna y los encabezados de menú y portada ponen el logotipo en fila (ambos escriben `data-afs` en `<html>`); "Reducir movimiento" conserva los fundidos de 150 ms. El único objetivo bajo 44 px es el enlace "Más información" dentro de una frase (excepción de enlace en línea de WCAG 2.5.8).
- La 404 y la página de información alimentaria no usan este diseño.
