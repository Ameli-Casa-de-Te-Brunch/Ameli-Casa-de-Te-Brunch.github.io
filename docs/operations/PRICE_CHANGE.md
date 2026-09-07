# Cambiar el precio de uno o varios productos

## Quién puede hacerlo

El dueño (o quien tenga el Excel maestro en su PC). Mismo requisito que
`MENU_UPDATE.md`: Python instalado y el repositorio clonado.

## Qué sistema se modifica

El Excel maestro primero, después `data/menu.json` de este repositorio y
`main` en GitHub al publicar. Los tipos de cambio (ARS/USD, ARS/EUR,
ARS/Real) también viven en el Excel, en el mismo bloque de configuración.

## Pasos exactos

1. Abrí el Excel maestro, hoja `Productos`.
2. Editá la columna de precio chico (o único) y, si el producto tiene dos
   tamaños, la columna de precio grande. No hace falta tocar nada más de
   esa fila.
3. Si también cambió el tipo de cambio de referencia, actualizalo en la
   hoja `Resumen y Configuración` (los campos "Tipo de cambio ARS/USD",
   "Tipo de cambio ARS/EUR", "Real") — esto afecta los precios
   equivalentes en otras monedas que se muestran en el sitio.
4. Guardá el Excel.
5. Corré, en orden, exactamente los mismos pasos 3 a 6 de
   `MENU_UPDATE.md` (`--dry-run` → revisar → `python build.py` →
   revisar `dist/` → `--publicar` con confirmación explícita).

## Cómo verificar el resultado

Después de publicar, abrí el sitio y confirmá el precio nuevo en la
tarjeta del producto, y — si cambiaste tipo de cambio — que el precio
equivalente en USD/EUR/Real también se vea correcto.

## Cuándo detenerse

- Si al correr `--dry-run` ves un `[AVISO]` de "está activo pero sin
  precio cargado" en un producto que no ibas a tocar: pará y revisá si
  se borró un valor sin querer antes de seguir.
- Un precio que quedó undefined/vacío no rompe el build (se publica sin
  precio visible, con aviso) — pero no es lo que se buscaba, así que
  conviene corregirlo antes de publicar.

## Cómo volver atrás

Igual que `MENU_UPDATE.md`: `git revert` sobre el commit que publicó el
precio equivocado, nunca `git reset --hard` sobre `main`.

## Qué nunca copiar en capturas, logs o GitHub

- El margen o costo de un producto (vive en `Productos - Backoffice`,
  nunca en `Productos` ni en `data/menu.json`) — si alguna vez ves un
  precio de costo mezclado con el de venta, es una señal de que algo se
  cargó en la hoja equivocada; no lo publiques así.
