# Sistemas y credenciales — inventario (solo nombres y metadatos, nunca
valores)

Este documento nunca contiene el valor de ningún token, contraseña ni URL
completa de una hoja privada. Si en algún momento alguien pega un valor
real acá por error, hay que rotarlo/revocarlo como si se hubiera filtrado
— nunca simplemente borrar la línea y seguir.

## Sistemas involucrados

| Sistema | Para qué | Quién tiene acceso |
|---|---|---|
| GitHub — repositorio del menú | Código, `data/menu.json`, GitHub Actions, GitHub Pages | Quien mantiene el código |
| GitHub Pages | Hosting del sitio publicado | (automático, vía Actions) |
| Google Sheets — hoja de disponibilidad | Estado "agotado/últimas porciones" por producto, editable desde el celular | Personal del local + dueño |
| Apps Script (vinculado a la hoja de disponibilidad) | Avisa a GitHub cuando cambia una celda de disponibilidad | Dueño (vive en su cuenta de Google, no en este repo) |
| Excel maestro (`Ameli_Menu_Maestro_V*.xlsx`, en OneDrive) | Fuente real de productos, precios, alérgenos, config | Dueño |

## Credenciales activas hoy

### `GITHUB_TOKEN` (PAT anterior)

- **Tipo**: fine-grained personal access token de GitHub.
- **Alcance**: organización como resource owner, un solo repositorio,
  permisos Contents + Actions (read/write).
- **Dónde vive**: Propiedad de script `GITHUB_TOKEN` en el Apps Script de
  la hoja de disponibilidad.
- **Para qué se usa**: `avisarGitHub()` en Apps Script dispara
  `repository_dispatch` (`event_type: actualizar-disponibilidad`).
- **Estado del trigger real: POR VERIFICAR (inspección directa
  pendiente), pero con evidencia reportada/observada en contra de que
  este siga siendo el mecanismo activo.** Este documento se basa en lo
  reportado por el dueño, no en una inspección directa del Apps Script
  real (vive en su cuenta de Google, sin acceso desde acá). Lo
  reportado/observado: cuatro ediciones manuales de disponibilidad
  (corrección de `BLE001`–`BLE004`) produjeron cuatro ejecuciones
  exitosas de `alCambiarDisponibilidad` del lado de Apps Script, que
  coinciden exactamente en cantidad con cuatro ejecuciones
  `workflow_dispatch` (no `repository_dispatch`) observadas sobre `main`
  en GitHub Actions. Eso es consistente con que `alCambiarDisponibilidad`
  ya esté llamando a `avisarGitHubViaActions()` (ver más abajo) en lugar
  de a `avisarGitHub()` -- pero sigue siendo una correlación
  reportada/observada, no una confirmación directa leyendo el cuerpo real
  de esa función en el editor de Apps Script.
- **Mientras el trigger real no se verifique con inspección directa**: se
  conserva como rollback temporal, no se renueva, revoca ni modifica
  durante esta fase.

### `GITHUB_TOKEN_ACTIONS` (PAT nuevo)

- **Tipo**: fine-grained personal access token de GitHub.
- **Alcance**: un solo repositorio, permiso Actions: write únicamente
  (más acotado que el anterior — no tiene Contents).
- **Dónde vive**: Propiedad de script `GITHUB_TOKEN_ACTIONS` en el mismo
  Apps Script.
- **Para qué se usa**: la función `avisarGitHubViaActions()` (agregada
  junto a `avisarGitHub()`, no en reemplazo) dispara el workflow vía
  `workflow_dispatch`.
- **Estado confirmado**: creado y probado manualmente con éxito — al
  ejecutarlo a mano una vez como prueba, GitHub respondió HTTP 204 y el
  workflow terminó bien. Esto es un hecho reportado directamente, no una
  suposición.
- **Estado del trigger real: POR VERIFICAR con inspección directa**, pero
  ya NO se puede asumir sin más que esté desconectado del trigger real de
  edición de la hoja (mismo motivo que arriba — sin inspección directa
  del Apps Script desde acá). Lo reportado/observado: cuatro correcciones
  manuales de disponibilidad (`BLE001`–`BLE004`) coincidieron exactamente
  con cuatro ejecuciones `workflow_dispatch` sobre `main`, y con cuatro
  ejecuciones exitosas de `alCambiarDisponibilidad` del lado de Apps
  Script — consistente con que `avisarGitHubViaActions()` (y por lo tanto
  este PAT) ya sea el mecanismo activo, no solo un mecanismo probado
  manualmente una vez. Sigue siendo una correlación reportada/observada,
  no una lectura directa del código real de Apps Script: el cutover
  formal (confirmar esto abriendo el editor de Apps Script, y recién ahí
  evaluar revocar el PAT anterior) queda para después de esta fase — no
  se toca Apps Script durante Fase C1.

### `DISPONIBILIDAD_CSV_URL`

- **Tipo**: repo variable de GitHub Actions (Settings → Secrets and
  variables → Actions → **Variables**, no *Secrets*).
- **Por qué variable y no secreto**: es la URL de una hoja de Google
  Sheets "publicada en la web" — pública por diseño de Google en cuanto
  se publica, no es información sensible en sí misma.
- **Para qué se usa**: `build/aplicar_disponibilidad.py`, paso "Aplicar
  disponibilidad en vivo" del workflow.
- **Estado**: sin cambios en esta fase.

## Qué NO se tocó en Fase C1 (a propósito)

- No se creó, canceló ni renovó ningún PAT.
- No se modificó Apps Script (ni `avisarGitHub()`, ni
  `avisarGitHubViaActions()`, ni ningún trigger).
- No se tocaron secrets ni variables de GitHub.
- No se avanzó con WIF ni con la migración a Google Sheets privado.

**Importante — dos cosas distintas que no hay que confundir:**
- **Esta PR (el código de este repositorio) no modificó Apps Script, PATs,
  secrets ni variables de GitHub** — nada de eso cambió por un commit de
  esta rama.
- **El estado real de la hoja de disponibilidad sí fue corregido
  externamente durante la preparación de esta fase** (la columna de
  `Disponibilidad` sobrescrita con su propio encabezado, ver
  `docs/SECURITY_BASELINE.md`) — un ajuste hecho por el dueño directamente
  en Google Sheets, fuera de este repositorio y fuera del diff de esta
  PR, no una consecuencia de ningún cambio de código de acá.

## Antes de cualquier cambio futuro sobre estas credenciales

1. **Abrir el editor de Apps Script real y confirmar con los propios
   ojos** qué función llama hoy `alCambiarDisponibilidad` -- no asumirlo
   de esta conversación. Recién con eso confirmado, verificar que el
   mecanismo nuevo (`GITHUB_TOKEN_ACTIONS` + `avisarGitHubViaActions()`)
   esté realmente conectado a ese trigger y probado con una edición real
   del personal, no solo con la prueba manual ya hecha.
2. Solo entonces evaluar revocar `GITHUB_TOKEN` (el anterior) — nunca
   antes de tener el reemplazo probado en producción.
3. Cualquier secret o variable nueva se documenta acá (nombre, alcance,
   para qué, quién lo puede ver) el mismo día que se crea.
