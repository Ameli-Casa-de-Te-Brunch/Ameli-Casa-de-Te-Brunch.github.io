# Volver atrás una publicación

## Quién puede hacerlo

Quien mantiene el código (necesita acceso de escritura al repositorio en
GitHub). No es un procedimiento para hacer desde el celular ni sin
experiencia con git.

## Qué sistema se modifica

La rama `main` del repositorio (un commit nuevo, nunca se borra
historia), y como consecuencia, el sitio publicado en GitHub Pages
después de que el workflow corra de nuevo.

## Pasos exactos

1. Identificá qué commit publicó el problema:
   ```
   git log --oneline -- data/menu.json
   ```
2. Confirmá que es el correcto viendo su contenido:
   ```
   git show <hash>
   ```
3. Revertilo (esto crea un commit NUEVO que deshace los cambios de ese
   commit puntual, sin tocar nada posterior ni reescribir historia):
   ```
   git revert <hash>
   ```
   Si git te abre un editor para el mensaje del commit de revert, dejá el
   mensaje por defecto y guardá/cerrá.
4. Publicá el revert:
   ```
   git push origin main
   ```
5. GitHub Actions va a reconstruir y publicar automáticamente en 1-2
   minutos.

## Cómo verificar el resultado

- Pestaña **Actions** en GitHub: la corrida nueva tiene que terminar en
  ✅.
- Abrí el sitio publicado y confirmá que volvió al estado esperado.

## Cuándo detenerse

- Si `git revert` marca un conflicto (pasa si hubo commits posteriores
  que tocaron las mismas líneas): no lo resuelvas a las apuradas.
  Pará y pedí ayuda antes de forzar nada.
- Nunca reviertas más de un commit a la vez sin verificar cada uno --
  revertir varios juntos puede deshacer cambios buenos junto con el malo.

## Qué NUNCA hacer para revertir

- **`git reset --hard`** sobre `main` (local o, peor, seguido de
  `push --force`): reescribe la historia que ya está publicada. Si
  alguien más tiene una copia del repo, sus próximos push van a chocar
  o van a reintroducir lo que se quiso sacar. `git revert` es siempre la
  opción segura porque solo agrega un commit, nunca borra ni reescribe.
- **`push --force` a `main`** por ningún motivo relacionado con esto.

## Qué nunca copiar en capturas, logs o GitHub

- Nada específico de este procedimiento en sí (son solo commits de
  código/datos públicos) — pero si el rollback es a raíz de un incidente
  de seguridad (credencial expuesta, etc.), ver `SECURITY_BASELINE.md`
  antes de describir el incidente en un commit message o en un issue
  público: nunca el valor de un token, ni una URL de la hoja de
  disponibilidad completa.
