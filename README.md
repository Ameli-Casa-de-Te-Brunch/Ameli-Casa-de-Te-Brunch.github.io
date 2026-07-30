# Menú digital Amelí

Pipeline que genera `dist/index.html` a partir de `data/Ameli_Menu_Maestro_V2.1.xlsx`.
Publicado en https://ameli-casa-de-te-brunch.github.io/

## Estado de los datos de contacto (hoja `13_Configuración`)

| Campo | Estado | Efecto si falta |
|---|---|---|
| WhatsApp de pedidos | ✅ cargado | — |
| Instagram | ✅ cargado | — |
| Dirección | ✅ cargado | — |
| URL base del menú | ⚠️ pendiente | No afecta lo publicado hoy (no se usa como link en la página); hace falta para configurar el QR físico definitivo con una URL propia en vez de `github.io`. |

Si cualquiera de estos campos queda vacío en el maestro, el build **oculta el
botón o enlace correspondiente en vez de publicar un link roto** (ver
`build/render.py`). No hay fallback a datos de ejemplo.

*(Documentación completa del pipeline — instalación, comando de publicación,
qué hoja editar para cada cosa — pendiente en una próxima entrega.)*
