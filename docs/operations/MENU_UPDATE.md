# Agregar, editar o dar de baja un producto del menú

## Quién puede hacerlo

El dueño (o quien tenga el Excel maestro `Ameli_Menu_Maestro_V*.xlsx` en su
PC, vía OneDrive). Requiere tener Python instalado y este repositorio
clonado — no es un procedimiento para hacer desde el celular.

## Qué sistema se modifica

El Excel maestro (fuera del repo, en OneDrive) primero. Después,
`data/menu.json` de este repositorio, y `main` en GitHub al publicar.

## Pasos exactos

1. Abrí el Excel maestro y editá la hoja `Productos` (nombre, categoría,
   descripción en los 5 idiomas, precio, alérgenos, etc.) o `Categorías`.
   Un producto nuevo necesita un ID con formato 3 letras + 3 números
   (ej. `TYT008`) que no se repita con ninguno existente.
2. Guardá el Excel.
3. En una terminal, dentro de la carpeta del repositorio:
   ```
   python build.py --dry-run
   ```
   Este dry-run común valida el Excel maestro y el documento público
   (`data/menu.json`) **sin acceso de red** — no consulta la hoja de
   disponibilidad en vivo, solo lo que ya está en el Excel. Si aparece
   algún `[ERROR]`, corregilo en el Excel y repetí este paso hasta que
   diga "0 error(es)".
4. Cuando el dry-run esté limpio, corré:
   ```
   python build.py
   ```
   Esto genera `data/menu.json` y `dist/index.html` en tu PC (todavía no
   publica nada).
5. Revisá `dist/index.html` abriéndolo en el navegador (doble clic, o
   `python -m http.server 8000` dentro de `dist/`) para confirmar que se
   ve bien.
6. **Antes de preparar una publicación**, corré el preflight adicional:
   ```
   python build.py --dry-run --disponibilidad-estricta
   ```
   A diferencia del dry-run del paso 3, este exige que la URL de
   disponibilidad esté configurada y consulta/valida de verdad la hoja
   real, en el mismo modo estricto que usa la publicación real en GitHub
   Actions — pero tampoco escribe ningún archivo. Sirve para confirmar
   que la hoja de disponibilidad está en un estado válido antes de
   publicar, sin depender de que el workflow lo descubra recién en CI.
   Si cualquiera de los dos dry-runs (paso 3 o este) falla, no continúes
   a los pasos siguientes hasta corregirlo.
7. Recién ahí, para publicar de verdad:
   ```
   python build.py --publicar
   ```
   Te va a mostrar exactamente qué archivo (`data/menu.json`) va a subir y
   va a pedir que escribas `si` para confirmar. Sin esa confirmación no
   pasa nada.

## Cómo verificar el resultado

Después de publicar: primero confirmá en GitHub, pestaña **Actions**, que
la corrida terminó en ✅ (el workflow en sí tarda ~1-2 minutos). Eso
confirma que se publicó, no que ya se ve -- GitHub Pages sirve detrás de
una caché pública que puede tardar varios minutos más en mostrar la
versión nueva. Recién después abrí
`https://ameli-casa-de-te-brunch.github.io/` con un refresco forzado
(Ctrl+Shift+R) y revisá el producto nuevo/editado en su categoría; si no
lo ves, probá desde otro dispositivo o red antes de asumir que algo
falló.

## Cuándo detenerse

- Si cualquiera de los dos dry-runs (el común del paso 3, o el
  `--disponibilidad-estricta` del paso 6) marca un `[ERROR]`: no continúes
  a los pasos siguientes hasta corregirlo. Los `[AVISO]` no bloquean, pero
  conviene leerlos.
- Si `--publicar` te muestra un diff que no esperabas (cambios en
  productos que no tocaste): no confirmes con `si` — revisá primero si
  guardaste una versión vieja del Excel por error.

## Cómo volver atrás

Si ya publicaste un cambio con un error:
```
git log --oneline -- data/menu.json      # ver el commit anterior
git revert <hash-del-commit-que-rompió>
git push origin main
```
`git revert` crea un commit nuevo que deshace el anterior, sin borrar
historial. **Nunca uses `git reset --hard` sobre `main`** — reescribe
historia que ya está publicada y puede complicar futuras publicaciones.

## Qué nunca copiar en capturas, logs o GitHub

- Nada de la hoja `Productos - Backoffice` (ingredientes, costos,
  personalización) — es información interna que nunca se publica.
- Las 12 columnas de costo/ingrediente ni el origen propio/tercerizado
  del Excel.
