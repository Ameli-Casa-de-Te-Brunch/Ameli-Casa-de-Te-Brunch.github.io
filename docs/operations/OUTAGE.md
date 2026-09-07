# El sitio no se actualiza o no carga

## Quién puede hacerlo

Cualquiera puede hacer el diagnóstico inicial (pasos 1-3). Corregir el
problema de fondo generalmente necesita al dueño (acceso al Excel) o a
quien mantiene el código (acceso a GitHub/Apps Script).

## Qué sistema se modifica

Ninguno en el diagnóstico. La corrección depende de dónde esté el
problema (ver abajo).

## Pasos exactos (diagnóstico)

1. **¿El sitio carga, pero con datos viejos?**
   Entrá a GitHub → pestaña **Actions** del repositorio → mirá la corrida
   más reciente.
   - Si dice ✅ verde: el sitio se publicó bien, puede ser solo caché del
     navegador — refrescá con Ctrl+Shift+R (o el equivalente en el
     celular) antes de asumir que algo está roto.
   - Si dice ❌ rojo: abrí esa corrida y mirá qué paso falló (el nombre
     del paso ya dice qué se estaba haciendo). Ver la lista de causas
     típicas más abajo.

2. **¿El sitio no carga directamente (error del navegador)?**
   Puede ser un problema de GitHub Pages en sí (raro, y no depende de
   este repo) o de conexión. Probá desde otra red/dispositivo antes de
   asumir que es del sitio.

3. **Causas típicas de una corrida ❌ y qué significan:**
   - *Falla en "Ejecutar pruebas automáticas" o "Validar data/menu.json"*:
     algo en el propio `data/menu.json` committeado quedó inconsistente
     (no debería pasar si `build.py --publicar` se usó normalmente — si
     pasa, avisá a quien mantiene el código, no lo intentes arreglar
     editando el JSON a mano en GitHub).
   - *Falla en "Aplicar disponibilidad en vivo"*: la hoja de
     disponibilidad tiene un dato que no se pudo confiar (un valor mal
     escrito en la columna Disponibilidad, un producto sin fila, etc.) —
     **esto es justamente lo esperado**: el sitio sigue mostrando la
     última versión publicada con éxito, no algo roto a medias. Solución:
     revisar la hoja de disponibilidad y corregir la fila que causó el
     error (el mensaje del paso dice cuál).

## Cómo verificar el resultado

Después de cualquier corrección, esperá a que una corrida nueva de
Actions termine en ✅, después refrescá el sitio en el navegador (con
Ctrl+Shift+R) y confirmá.

## Cuándo detenerse

- Si no identificás la causa en los pasos de arriba, no sigas
  experimentando cambios en el Excel, la hoja de disponibilidad o
  GitHub — avisá a quien mantiene el código con el link exacto de la
  corrida de Actions que falló.
- Nunca "solucionar" un ❌ borrando o re-ejecutando a ciegas sin haber
  leído qué paso falló y por qué.

## Cómo volver atrás

Si el problema lo causó el último commit publicado (`git log --oneline`
para verlo), usá `git revert <hash>` y `git push origin main` — nunca
`git reset --hard` sobre `main`. Ver `ROLLBACK.md` para el detalle
completo.

## Qué nunca copiar en capturas, logs o GitHub

- El contenido completo del log de un paso fallido puede incluir texto
  de la hoja de disponibilidad si algo salió mal en la validación — el
  código está escrito para nunca imprimir la URL completa ni el
  contenido crudo de la hoja, pero si ves algo que parece un link
  completo de Google Sheets en un log, no lo compartas en un issue
  público de GitHub; compartilo solo en privado con quien mantiene el
  código.
