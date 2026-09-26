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
| Google Sheets — hoja de disponibilidad | Estado "agotado/últimas porciones" por producto, editable desde el celular | Cuenta institucional (propietaria) + dueño (editor, acceso de respaldo) + personal del local |
| Apps Script (vinculado a la hoja de disponibilidad) | Avisa a GitHub cuando cambia una celda de disponibilidad | Cuenta institucional `ameli.casadete@gmail.com` (vive en Google, no en este repo) |
| Excel maestro (`Ameli_Menu_Maestro_V*.xlsx`, en OneDrive) | Fuente real de productos, precios, alérgenos, config | Dueño |

## Credenciales activas hoy

### `GITHUB_TOKEN_ACTIONS` (único PAT vigente, confirmado 25/09/2026)

- **Tipo**: fine-grained personal access token de GitHub.
- **Alcance**: resource owner `Ameli-Casa-de-Te-Brunch`, un solo
  repositorio (`Ameli-Casa-de-Te-Brunch.github.io`), permisos Actions
  (read/write) + Metadata (read-only, obligatorio y automático) — sin
  Contents, sin Workflows, sin permisos organizacionales adicionales.
- **Vencimiento**: 24/12/2026.
- **Dónde vive**: Propiedad de script `GITHUB_TOKEN_ACTIONS` en el Apps
  Script productivo, bajo la cuenta institucional
  `ameli.casadete@gmail.com`.
- **Para qué se usa**: única función de aviso en el código productivo
  confirmado — `avisarGitHubViaActions()` dispara el workflow vía
  `workflow_dispatch` sobre `deploy.yml`, rama `main`. El código
  productivo confirmado por inspección directa el 24/09/2026 **no
  contiene** `avisarGitHub()` (legacy), `resetearAgotadosDiario()` ni
  `corregirDisponibilidadUnaVez()` — solo `_esEnteroPositivo`,
  `_debeDispararPorRango`, `alCambiarDisponibilidad`, `_faltaToken`,
  `_evaluarRespuestaGitHub` y `avisarGitHubViaActions`.
- **Estado: CONFIRMADO por inspección directa y prueba real** (ya no es
  una correlación reportada). Prueba realizada el 25/09/2026 ~15:31
  GMT-3: ejecución manual de `avisarGitHubViaActions` desde la cuenta
  institucional → GitHub respondió 200 → corrida "Build y publicar menú"
  completada con éxito (evento manual/`workflow_dispatch`, rama `main`,
  ~36s). No repetir esta prueba salvo evidencia concreta de un problema.
- **Trigger institucional confirmado**: un único activador instalable —
  hoja de cálculo, al editar, función `alCambiarDisponibilidad`,
  propietario la cuenta institucional. El activador personal anterior fue
  eliminado.
- **Rotación de este PAT (25/09/2026)**: este es el PAT que reemplaza al
  que usaba antes esta misma propiedad de script (nombre con el que
  figuraba en GitHub: `ameli-actions-2026-09`, vencía 12/10/2026). Ese PAT
  anterior fue **revocado** el 25/09/2026, con confirmación explícita del
  dueño inmediatamente antes de eliminarlo, una vez confirmado que el
  reemplazo ya estaba en uso real (prueba de arriba). Verificado después:
  en la cuenta de GitHub solo queda `GITHUB_TOKEN_ACTIONS`.
- **Procedimiento de renovación** (antes del 24/12/2026): generar un
  nuevo fine-grained PAT desde la cuenta institucional con el mismo
  alcance mínimo (Actions read/write, Metadata read-only automático, sin
  Contents/Workflows/permisos de organización), cargarlo en la propiedad
  de script `GITHUB_TOKEN_ACTIONS`, probar con una edición real de
  disponibilidad, y recién después revocar el PAT que se reemplaza.
- **Responsable institucional**: `ameli.casadete@gmail.com`.
- **Rollback**: hoy no queda ningún PAT de respaldo activo (el anterior
  ya fue revocado) — si `GITHUB_TOKEN_ACTIONS` fallara, hay que generar
  uno nuevo de inmediato con el mismo procedimiento de arriba.

### Propiedad de script `GITHUB_TOKEN` (legacy — estado sin confirmar)

- El código productivo confirmado no tiene ninguna función que la use
  (no existe `avisarGitHub()` en el proyecto productivo). Si la propiedad
  en sí todavía existe en Apps Script no se verificó en este cierre — no
  se inspeccionaron las Propiedades del script más allá de
  `GITHUB_TOKEN_ACTIONS`. Si existe, queda huérfana (sin llamador) y es
  candidata a eliminarse la próxima vez que alguien abra el proyecto con
  intención de limpiarlo — no se tocó en este cierre.

### `repository_dispatch` — mecanismo legacy, ausente del código pero no del workflow

- El código productivo de Apps Script confirmado **no llama a
  `repository_dispatch` en ningún lado** — el único mecanismo de aviso es
  `workflow_dispatch` vía `avisarGitHubViaActions()`.
- `.github/workflows/deploy.yml` **sigue aceptando** `repository_dispatch`
  (tipo `actualizar-disponibilidad`) como disparador disponible — no se
  quitó en este cierre (retirarlo es una simplificación de
  infraestructura a evaluar aparte, no una corrección de un error). Se
  deja documentada la discrepancia: el camino sigue existiendo en el
  workflow, pero nada en el código productivo confirmado lo dispara hoy.

### `DISPONIBILIDAD_CSV_URL`

- **Tipo**: repo variable de GitHub Actions (Settings → Secrets and
  variables → Actions → **Variables**, no *Secrets*).
- **Por qué variable y no secreto**: es la URL de una hoja de Google
  Sheets "publicada en la web" — pública por diseño de Google en cuanto
  se publica, no es información sensible en sí misma.
- **Para qué se usa**: `build/aplicar_disponibilidad.py`, paso "Aplicar
  disponibilidad en vivo" del workflow.
- **Estado**: sin cambios en esta fase. Existencia y apunte al mismo gid
  reconfirmados el 25/09/2026 (sin reproducir la URL acá).

## Propiedad de la hoja de disponibilidad (confirmado 25/09/2026)

- **Propietaria**: cuenta institucional `ameli.casadete@gmail.com`
  (transferencia ya aceptada).
- **Editor**: `nacho.asoto03@gmail.com` (acceso de respaldo/recuperación,
  decisión deliberada — no un descuido).
- **Acceso general**: restringido.
- El Spreadsheet ID, el gid de la pestaña y el ID del proyecto de Apps
  Script **no se documentan en este archivo público** — quedan
  registrados solo en el paquete de cierre interno correspondiente, fuera
  de este repositorio.

## Qué se hizo en este cierre (25/09/2026)

- Se confirmó por inspección directa del dueño (no solo por correlación)
  qué función atiende el trigger real y qué activadores existen.
- Se rotó `GITHUB_TOKEN_ACTIONS` (PAT nuevo con el mismo alcance mínimo) y
  se probó con una ejecución real antes de tocar el anterior.
- Se revocó el PAT anterior (visible en GitHub como
  `ameli-actions-2026-09`) con confirmación explícita del dueño
  inmediatamente antes de eliminarlo.
- Se confirmó la transferencia de propiedad de la hoja de disponibilidad
  a la cuenta institucional.

## Qué NO se tocó en este cierre (a propósito)

- No se modificó el código de Apps Script (se solo inspeccionó).
- No se tocó el activador institucional ya creado.
- No se tocaron secrets ni variables de GitHub Actions.
- No se avanzó con WIF ni con la migración a Google Sheets privado.
- No se quitó `repository_dispatch` de `deploy.yml` (ver nota arriba).

**Importante — dos cosas distintas que no hay que confundir:**
- **Este repositorio (código y workflow) no fue el que roté ni revoqué
  ningún PAT** — eso pasó del lado de la cuenta de GitHub del dueño
  (Settings → Developer settings → Fine-grained tokens), no en un commit
  de este repo.
- **La propiedad de la hoja de disponibilidad y el activador institucional
  se confirmaron/ajustaron directamente en Google**, fuera de este
  repositorio y fuera de cualquier diff — este documento solo registra el
  resultado.

## Antes de cualquier cambio futuro sobre estas credenciales

1. Renovar `GITHUB_TOKEN_ACTIONS` antes de que venza (24/12/2026): generar
   el reemplazo, probarlo con una edición real, y solo después revocar el
   que se reemplaza — mismo procedimiento que se siguió el 25/09/2026.
2. Si en algún momento se abre el proyecto de Apps Script para limpieza,
   confirmar si la propiedad `GITHUB_TOKEN` (legacy) sigue existiendo y,
   si no tiene ningún llamador, eliminarla.
3. Antes de retirar `repository_dispatch` de `deploy.yml`, confirmar que
   ningún mecanismo (ni siquiera uno de respaldo) dependa todavía de él.
4. Cualquier secret o variable nueva se documenta acá (nombre, alcance,
   para qué, quién lo puede ver, vencimiento) el mismo día que se crea.
