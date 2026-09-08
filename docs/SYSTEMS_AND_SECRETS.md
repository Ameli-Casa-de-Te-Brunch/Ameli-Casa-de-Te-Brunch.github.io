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
- **Estado del trigger real: POR VERIFICAR.** Este documento se basa en
  lo conversado sobre el mecanismo, no en una inspección directa del
  Apps Script real (vive en la cuenta de Google del dueño, sin acceso
  desde acá). Que `alCambiarDisponibilidad` siga llamando a
  `avisarGitHub()` (y no a `avisarGitHubViaActions()`) es lo asumido,
  no lo confirmado — hay que abrir el editor de Apps Script y mirar el
  cuerpo real de esa función antes de dar esto por hecho.
- **Mientras el trigger real no se verifique**: se conserva como
  rollback temporal, no se renueva, revoca ni modifica durante esta
  fase.

### `GITHUB_TOKEN_ACTIONS` (PAT nuevo)

- **Tipo**: fine-grained personal access token de GitHub.
- **Alcance**: un solo repositorio, permiso Actions: write únicamente
  (más acotado que el anterior — no tiene Contents).
- **Dónde vive**: Propiedad de script `GITHUB_TOKEN_ACTIONS` en el mismo
  Apps Script.
- **Para qué se usa**: la función `avisarGitHubViaActions()` (agregada
  junto a `avisarGitHub()`, no en reemplazo) dispara el workflow vía
  `workflow_dispatch`.
- **Estado confirmado**: creado y probado manualmente con éxito — GitHub
  respondió HTTP 204 y el workflow terminó bien. Esto sí es un hecho
  reportado directamente, no una suposición.
- **Estado del trigger real: POR VERIFICAR** (mismo motivo que arriba —
  sin inspección directa del Apps Script desde acá). Que este mecanismo
  todavía NO sea el que dispara el trigger real de edición de la hoja es
  lo asumido según lo conversado, no algo confirmado mirando el código
  real. El cutover (verificar/cambiar ese trigger, y recién ahí evaluar
  revocar el PAT anterior) queda para después de esta fase — no se toca
  Apps Script durante Fase C1.

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
