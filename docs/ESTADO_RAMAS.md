# Estado de ramas — ameli-menu

Última revisión: 2026-09-21. Objetivo: que nadie (yo, Ignacio, u otra línea de
trabajo tipo Codex) tenga que reconstruir esto de cero para saber qué rama es
"la buena" antes de tocar el repo.

## La única fuente de verdad

**`main`** (rastrea `origin/main`) es lo único que cuenta como estado real del
sitio publicado en `amelicasadete.com.ar`. Cualquier otra rama es, como mucho,
trabajo en curso — nunca se asume publicado hasta que está en `main`.

## Ramas todavía presentes fuera de `main`

| Rama | Qué es | Estado |
|---|---|---|
| `estado-ramas-cierre-2026-09-21` | actualización de este documento | pendiente de PR; no cambia código ni contenido público |
| `corregir-aviso-alimentario-2026-09-21` | rama de trabajo del aviso alimentario | **absorbida por PR #15** (`30b6b3e`); puede borrarse cuando se autorice la limpieza |
| `corregir-aviso-productos-sellados-2026-09-16` | borrador anterior en un worktree separado (`~/.codex/.chatgpt-projects/.../ameli-hotfix-aviso-alimentario`) | **superado por PR #15**; conserva dos cambios sin commit equivalentes a una versión anterior, revisar y limpiar solo con autorización |

`main` y `origin/main` apuntan a `30b6b3e`, el squash merge del PR #15. El
despliegue #71 terminó correctamente y el aviso actualizado fue comprobado en
el dominio público.

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

## Ramas cerradas el 2026-09-21 (ya no existen, ni local ni remoto)

Antes figuraban "en revisión". Se comprobó que el árbol de archivos de cada una
es **idéntico** al del squash merge que ya las absorbió en `main` (`git diff`
entre la rama y el commit del squash: vacío) -- no tenían nada único.

| Rama borrada | Absorbida en | SHA final (por si hiciera falta recuperarla) |
|---|---|---|
| `cierre-tecnico-menu` | PR #5 (`92a3d56`, "Fase C1: cierre técnico y de seguridad del menú") | `9733d49342c71599cf9e5768666d32f337795dc1` |
| `integracion-web-menu` | PR #7 (`360dc9f`, "Integracion web menu") | `2061a0dde4c7fab3eab133ccb92762a2cf6594d4` |

## Cómo mantener esto al día

Antes de crear una rama nueva de larga duración, o de abandonar una sin
mergear, actualizar esta tabla. Al cerrar una rama, moverla a la sección de cerradas con la fecha y el motivo
real (idealmente con la prueba de que su contenido ya está en `main`), no solo
borrarla.
