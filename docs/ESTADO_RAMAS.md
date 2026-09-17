# Estado de ramas — ameli-menu

Última revisión: 2026-09-17. Objetivo: que nadie (yo, Ignacio, u otra línea de
trabajo tipo Codex) tenga que reconstruir esto de cero para saber qué rama es
"la buena" antes de tocar el repo.

## La única fuente de verdad

**`main`** (rastrea `origin/main`) es lo único que cuenta como estado real del
sitio publicado en `amelicasadete.com.ar`. Cualquier otra rama es, como mucho,
trabajo en curso — nunca se asume publicado hasta que está en `main`.

## Ramas activas ahora mismo

| Rama | Qué es | Estado |
|---|---|---|
| `main` | el sitio real | al día con `origin/main` |
| `corregir-aviso-productos-sellados-2026-09-16` | línea de trabajo paralela (Codex), viva en un worktree separado (`~/.codex/.chatgpt-projects/.../ameli-hotfix-aviso-alimentario`) | **no tocar** — en uso activo por otra sesión |
| `cierre-tecnico-menu` | 7 commits, "Fase C1: cierre técnico del menú" (seguridad, integridad, tests, docs) + carga diferida de openpyxl en `build.py` | **en revisión** — parte de esto (carga diferida de openpyxl) ya parece estar en `main` por otro camino; no confirmado si el resto sigue vigente o quedó obsoleto. No borrar sin decisión de Ignacio. |
| `integracion-web-menu` | los mismos 7 commits de arriba + "Unificar web institucional y menú en un solo artefacto de GitHub Pages" (11/09, cambio de arquitectura) | **en revisión** — anterior al Boceto Literal (15/09) que terminó siendo lo que se publicó; puede estar superada o puede tener algo que valga la pena rescatar. No borrar sin decisión de Ignacio. |

## Ramas cerradas el 2026-09-17 (ya no existen, ni local ni remoto)

Todas verificadas antes de borrar: o 0 commits propios respecto a `main`, o su
contenido ya llegó a `main` por otra vía (típicamente squash merge, por eso
`git` no las marcaba como "merged" aunque lo estaban).

| Rama borrada | Motivo |
|---|---|
| `diseno-visual-2026-09` | 0 commits propios; apuntaba a lo que ya es PR #8 en `main` |
| `docs-rotacion-pat-2026-09` | idéntica a la anterior, mismo commit |
| `instagram-links-2026-09-17` | rama de trabajo del PR #11, ya squasheada en `main` (`d7561ae`) |
| `web-integracion-boceto-literal-2026-09-15` | rama original del PR #9 (más el intento fallido que se resolvió con cherry-pick); contenido ya en `main` vía PR #9 y #11 |
| `feature/pipeline-hardening` (solo remota) | commit de julio, ya mergeado hace tiempo, 0 commits propios |
| `ocultar-servicios-no-confirmados` | borrador temprano (67 líneas) superado por la versión que sí se mergeó como PR #8 (878 líneas) |

## Cómo mantener esto al día

Antes de crear una rama nueva de larga duración, o de abandonar una sin
mergear, actualizar esta tabla. Si en el futuro `cierre-tecnico-menu` o
`integracion-web-menu` se confirman como vigentes o como descartadas, mover la
fila correspondiente a la sección que corresponda (activa / cerrada) con la
fecha y el motivo real, no solo borrar la rama y listo.
