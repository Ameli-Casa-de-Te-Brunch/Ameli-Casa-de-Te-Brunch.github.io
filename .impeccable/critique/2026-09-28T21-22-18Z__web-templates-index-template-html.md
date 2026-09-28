---
target: Amelí homepage (web/templates/index.template.html)
total_score: 19
max_score: 32
na_heuristics: 7,10
p0_count: 0
p1_count: 3
target_identity: "file:C:\\Users\\nacho\\ameli-menu\\web\\templates\\index.template.html"
target_fingerprint: "sha256:19fb637798db32244f66b4c9138351381efba4c02bbffedb10e55c5e4a0598fe"
target_path: "C:\\Users\\nacho\\ameli-menu\\web\\templates\\index.template.html"
timestamp: 2026-09-28T21-22-18Z
slug: web-templates-index-template-html
---
# Critique — Amelí homepage (web/templates/index.template.html)

## Design Health Score (19/32 — Flexibility y Help and Documentation marcados n/a, superficie Persuade)

| # | Heuristic | Score | Key Issue |
|---|---|---|---|
| 1 | Visibility of System Status | 2 | Horario recién visible ~6900px abajo en mobile, o dentro de un FAQ colapsado |
| 2 | Match System / Real World | 3 | Voseo natural; pero "Una sola consulta, distintas posibilidades" describe el proceso del negocio, no la necesidad del visitante |
| 3 | User Control and Freedom | 3 | `<dialog>` nativo cierra con Escape, skip-link presente |
| 4 | Consistency and Standards | 2 | Bug confirmado: clase `visitanos` en el HTML vs `.visitarnos` en el CSS — ninguna regla de esa sección aplica |
| 5 | Error Prevention | 2 | CTAs de WhatsApp sin horario al lado; FAQ de alérgenos no menciona celiaquía/TACC explícitamente |
| 6 | Recognition Rather Than Recall | 2 | Nav detrás de hamburguesa incluso en desktop; botón flotante sin etiqueta |
| 7 | Flexibility and Efficiency | n/a | Página de marketing |
| 8 | Aesthetic and Minimalist Design | 3 | Calma y contenida, pero el placeholder "ESPACIO PARA MAPA" y 6 links de WhatsApp repetidos suman ruido |
| 9 | Error Recovery | 2 | Sin alternativa clara si wa.me falla en desktop sin WhatsApp instalado |
| 10 | Help and Documentation | n/a | Página de marketing (el FAQ en sí está bien resuelto) |
| **Total** | | **19/32 (59%) — Aceptable** | |

## Veredicto de especificidad de diseño

Parcialmente propio. La tipografía (Cormorant + Karla, 3 niveles) y la voz ("las meriendas que se extienden más de lo planeado") sí son de Amelí. Pero la estructura es la secuencia genérica de café boutique (hero con foto, historia centrada, 3 tarjetas numeradas, bloque oscuro partido, FAQ, mapa, directorio) y Malargüe solo aparece como nombre de lugar, nunca como contexto (nada sobre turismo, Las Leñas, la Caverna de las Brujas). No hay té en las fotos de una "Casa de Té", no aparece Amelio (la mascota que sí usan en vouchers), y el emblema del hero es un ✻ genérico. Cambiando el nombre y las fotos, funcionaría igual para cualquier café.

## Impresión general

La base tipográfica y el tono de la copy son sólidos y ya distinguen a Amelí de un template genérico. El problema no es "hace falta más diseño" — es que hay **contenido real faltante o roto** en los momentos de mayor decisión (horario, ubicación, fotos con comida) y **un bug de CSS confirmado** que deja toda la sección de ubicación sin el layout que se diseñó para ella.

## Qué funciona

1. **Sistema tipográfico de 3 niveles** (Cormorant display / Karla eyebrows trackeados / Karla body) — disciplinado, con voz editorial familiar en vez de SaaS.
2. **Bloque "Carta y pedidos"** — el mejor compuesto de la página: verde oscuro, jerarquía clara, y el dato de "48 horas de anticipación" es exactamente el tipo de reaseguro concreto que falta en el resto.
3. **Copy honesta** — "No trabajamos con reservas" dicho directo, sin esconderlo.

## Problemas prioritarios

**[P1] Bug confirmado — sección "Visitarnos" sin sus estilos.** El HTML tiene `class="ubicacion visitanos"` (typo, falta la "r"), pero TODO el CSS de esa sección apunta a `.visitarnos` — ninguna de esas reglas matchea nunca (verificado línea por línea: `site.css:1439-1445, 1527-1529, 1551-1554` vs. `index.template.html:236`). La sección cae al layout genérico anterior en vez del diseño de 2 columnas pensado para ella, y el placeholder "ESPACIO PARA MAPA" queda visible en producción. Fix: corregir el typo a `visitarnos` en el template (1 palabra).

**[P1] Horario y "abierto ahora" enterrados.** Solo aparecen dentro de un FAQ colapsado o en Visitarnos (muy abajo). Es el primer dato que un visitante nuevo necesita para decidir "hoy sí o no". Fix: línea de horario compacta debajo de los CTA del hero.

**[P1] Las fotos contradicen la marca.** Cero té visible en la home de una "Casa de Té". El hero es un salón vacío, sin gente ni mesa servida — el propio slogan habla de "momentos" y ninguno se ve. Fix: reemplazar la foto de "Carta y pedidos" por una de té/brunch real; considerar una segunda foto con mesa servida.

**[P2] Roturas de word-wrap confirmadas.** A 375px la primera tarjeta de servicio corta "Experiencia/s y eventos" a mitad de palabra (`.servicio-ruta h3{max-width:10ch}` + `overflow-wrap:anywhere` a ≤620px). En desktop el email corta "contacto@amelicas/adete.com.ar" (confirmado visualmente). Fix: sacar el `max-width:10ch` o agregar `hyphens:auto`; dar más ancho a la ficha de email.

**[P2] "Origen y compromiso" es contenido de relleno.** Media pantalla de foto junto a dos frases que prometen contenido futuro. Fix: sumar 2-3 hechos concretos y verdaderos, o achicar la sección.

**[P2] Jerarquía de CTA invertida y sobrecarga.** El botón secundario ("Pedir por WhatsApp", relleno crema) llama más la atención que el primario ("Ver el menú", verde) sobre la foto oscura del hero. 6 links a WhatsApp repartidos por la página. Botón flotante sin etiqueta visible. Fix: invertir el peso visual del hero; etiquetar el botón flotante.

## Persona red flags

- **Jordan (primera vez):** el hero pasa la prueba de 5 segundos, pero no dice qué se sirve ni el horario. "Boxes" y "Coworking" aparecen sin explicación. "Turismo y empresas: consultas para grupos" contradice más abajo "No trabajamos con reservas".
- **Riley (estrés):** confirmado el corte de "Experiencia/s" y del email. La tarjeta de Coworking pasa a una segunda línea en desktop, desalineando el separador de la tarjeta 1.
- **Casey (mobile, una mano):** CTAs del hero bien puestos. Links a reseñas de Google/TripAdvisor miden ~26px de alto (mínimo recomendado: 44px), y el link "Privacidad" del footer es casi invisible por contraste.

## Observaciones menores

- El HTML compilado incluye comentarios de desarrollo visibles en "ver código fuente" — limpiar en el build.
- No hay link a Instagram pese a que `instagram_handle` ya está en `site.config.json`.

## Preguntas provocadoras

- ¿Y si el hero mostrara un momento real en la mesa (té, una porción de torta, manos) en vez de un salón vacío?
- ¿Y si Amelio apareciera como anfitrión silencioso de la página, igual que en los vouchers?
- ¿Y si el texto le hablara directo al turista de Malargüe en vez de genérico?
