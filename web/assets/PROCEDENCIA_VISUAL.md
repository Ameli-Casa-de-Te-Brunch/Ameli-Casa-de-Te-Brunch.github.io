# Procedencia de logo, fotografías, íconos y fuentes

Registro de lo que se sabe hoy sobre cada activo visual publicado.
Ningún dato de autoría, licencia o autorización se inventa acá: donde
no existe una confirmación por escrito, el campo "Estado" queda
explícitamente `PENDIENTE`, no se asume ni se marca como resuelto.

Los hashes SHA-256 son del archivo tal como está hoy en `assets/` (no
de lo que termine copiado a `dist/`, que es una copia byte a byte del
mismo archivo — ver `build_site.py::_copiar_assets`).

## Logo

| Campo | Valor |
|---|---|
| Ruta | `assets/img/logo.svg` |
| SHA-256 | `2322a6d0ba25a91ee1d8dfb3064ce888329b234c7bc0d76987d87d8773de2bde` |
| Tipo de activo | Logo / isotipo (vectorial) |
| Autor o proveedor | Desconocido (no registrado) |
| Procedencia | Según `README.md`, sección "Logo y fotografía real": "isotipo oficial de Amelí... copiado tal cual del archivo fuente entregado" — afirmación del dueño, no verificada independientemente |
| Fecha de recepción | Desconocida — no quedó registrada al preparar este repositorio |
| Fundamento de uso | Propio (afirmado en README, sin confirmación escrita) |
| Ubicación de la evidencia | `README.md` (prosa) — no existe un archivo de cesión o licencia separado |
| Estado | `PENDIENTE` |
| Observaciones | Reutilizado dentro del sitio (header + footer, dos tratamientos CSS distintos) a partir de este mismo archivo — no se generó ninguna copia nueva |

## Fotografías

| Ruta | SHA-256 | Autor o proveedor | Procedencia | Fecha de recepción | Fundamento de uso | Ubicación de la evidencia | Estado | Observaciones |
|---|---|---|---|---|---|---|---|---|
| `assets/img/hero-tostada.webp` | `56786a62c9904963e863e70abe416509b42f65caefbe246dac68e79e8df19bd1` | Desconocido | Según README: foto real del negocio, provista para este uso | Desconocida | Propio (afirmado, sin confirmación escrita) | `README.md` (prosa) | `PENDIENTE` | Optimizada a WebP calidad 82, sin metadatos EXIF (según README) |
| `assets/img/menu-smoothies.webp` | `55808169d4e936b06a0d26c9932a69336ec4614abf2033184ae57c64bcb11aa7` | Desconocido | ídem | Desconocida | ídem | `README.md` (prosa) | `PENDIENTE` | ídem |
| `assets/img/sabor-torta.webp` | `53c691018ec41dc59311a4d45f7feb165baeb420dfc20713679a319891af6808` | Desconocido | ídem | Desconocida | ídem | `README.md` (prosa) | `PENDIENTE` | ídem |
| `assets/img/sabor-tarta.webp` | `8dbbf7f5a4ae96459952c57af77e5ae62dc825cebaeb25737a9b272cec35ee9c` | Desconocido | ídem | Desconocida | ídem | `README.md` (prosa) | `PENDIENTE` | ídem |
| `assets/img/sabor-sandwich.webp` | `7bf7bb6b52c2a3e25e0b39ac992fa7b9773f0e82e2b3a92a01f53b6eb4b98a55` | Desconocido | ídem | Desconocida | ídem | `README.md` (prosa) | `PENDIENTE` | ídem |

## Íconos (derivados del logo)

| Ruta | SHA-256 | Autor o proveedor | Procedencia | Fecha de recepción | Fundamento de uso | Ubicación de la evidencia | Estado | Observaciones |
|---|---|---|---|---|---|---|---|---|
| `assets/img/favicon-16.png` | `b4491b448c4fb22cdf5b4d096096ef3b86203699555a69d7a0c2035756497938` | Desconocido | Derivado del logo (ver arriba) | Desconocida | Propio (afirmado, sin confirmación escrita) | `README.md` (prosa) | `PENDIENTE` | Mismo estado que el logo del que se derivan |
| `assets/img/favicon-32.png` | `153ea10d655dec74eeadb1c0874f29ec4696caf11a4c30fedd74a954ad62ea1b` | Desconocido | ídem | Desconocida | ídem | `README.md` (prosa) | `PENDIENTE` | ídem |
| `assets/img/apple-touch-icon.png` | `599cf2ea0ad0f3a656da62790b97280f23a2c1fd4f1abf9e12ea33d46cc31ac1` | Desconocido | ídem | Desconocida | ídem | `README.md` (prosa) | `PENDIENTE` | ídem |

## Fuentes tipográficas

A diferencia del logo y las fotos, estas sí tienen licencia real,
completa y verificable — el archivo de licencia viaja con la fuente
hasta `dist/`.

| Ruta | SHA-256 | Autor o proveedor | Procedencia | Fecha de recepción | Fundamento de uso | Ubicación de la evidencia | Estado | Observaciones |
|---|---|---|---|---|---|---|---|---|
| `assets/fonts/cormorant-garamond.woff2` | `d80df8ff5aecd299a61549f9e29ab1ed0b9b05f4ea71d50fe978e07d5240b235` | The Cormorant Project Authors | SIL Open Font License 1.1 | Año de copyright de la fuente según su licencia: **2015** (no es la fecha en que este proyecto la recibió, ese dato no está registrado) | Licencia (SIL OFL 1.1) | `assets/fonts/OFL-CormorantGaramond.txt` | `CONFIRMADO` | Licencia libre para uso e incrustación en la web |
| `assets/fonts/cormorant-garamond-italic.woff2` | `6f2f5c3b1abc3d0bb035a927f66a90ca873f94fc31c4966c8d024142c2036e55` | The Cormorant Project Authors | ídem | ídem (2015) | Licencia (SIL OFL 1.1) | `assets/fonts/OFL-CormorantGaramond.txt` | `CONFIRMADO` | ídem |
| `assets/fonts/karla.woff2` | `3b1eb09a53fd7b26c107b099b3da5fb2ac90b77297cb3ad713a7b40438ae718b` | The Karla Project Authors | SIL Open Font License 1.1 | Año de copyright según licencia: **2019** | Licencia (SIL OFL 1.1) | `assets/fonts/OFL-Karla.txt` | `CONFIRMADO` | ídem |
| `assets/fonts/montserrat-light.woff2` | `a04fdaaec9f3cd46b0cb3adc3d3e35a15264664330d22c7ba688ef6ea7d02010` | The Montserrat.Git Project Authors | SIL Open Font License 1.1 | Año de copyright según licencia: **2024** | Licencia (SIL OFL 1.1) | `assets/fonts/OFL-Montserrat.txt` | `CONFIRMADO` | ídem |

## Qué falta para cerrar el logo y las fotografías

Una confirmación explícita y por escrito del dueño (alcanza una línea
por activo, o una sola línea general si aplica a todos por igual) de:

- titularidad de los derechos sobre el logo y las 5 fotografías, **o**
- de quién las tomó/diseñó y bajo qué términos, si fueron encargadas a
  un tercero.

Hasta que eso exista, estos activos permanecen `PENDIENTE` en este
documento — no se marcan como `CONFIRMADO` por inferencia ni por uso
continuado.
