#!/usr/bin/env python3
"""Google Sheets (publicado en la web como CSV) -> el mismo `data` que
produce extract.py desde el Excel. Pensado para correr en GitHub Actions,
disparado por el botón "Publicar cambios" del Sheet (ver Apps Script en
el README, sección "Consolidación en Sheets").

El Sheet tiene que replicar el layout del Excel maestro: mismas filas de
inicio, mismas columnas (ver extract.COL, extract.FILA_CONFIG_INICIO/FIN,
y las columnas de Categorías más abajo). Esto es deliberado: reescribe
extract.COL una sola vez y todo el resto del pipeline (render.py,
validate) no necesita saber de dónde salieron los datos.

Tres hojas, publicadas cada una como su propio CSV (Archivo > Compartir >
Publicar en la web > esa hoja > CSV), igual que ya se hace hoy con la
hoja de disponibilidad:
  - Productos
  - Categorías
  - Config (equivalente a "Resumen y Configuración" del Excel, pero sin
    las filas de resumen automático -- solo el bloque de parámetros)
"""
import csv
import io
import json
import urllib.request
from pathlib import Path

import extract as ex
import extract_common as ec

HERE = Path(__file__).resolve().parent
OVERRIDES_MOMENTOS = HERE / "overrides_momentos.json"

# Columnas de la hoja "Categorías" -- mismas posiciones que
# extract.load_categorias() usa en el Excel (no hay un COL dict allá
# porque son pocas; se replican acá literalmente por la misma razón).
COL_CAT = {"cod": 1, "orden": 2, "visible": 15, "nom": {"es": 9, "en": 10, "pt": 11, "fr": 12, "it": 13}}

# En el Excel, "Config" es un rango de filas (FILA_CONFIG_INICIO..FIN)
# dentro de la hoja "Resumen y Configuración", que además tiene un bloque
# de resumen automático arriba (fórmulas). En Sheets, la hoja "Config"
# publicada es SOLO ese rango de parámetros -- fila 1 = encabezado,
# fila 2 en adelante = "Parámetro,Valor". Evita depender de fórmulas de
# resumen (que Sheets no siempre recalcula igual que Excel) para algo
# que el pipeline ni siquiera lee.
FILA_CONFIG_DESDE = 2


def _leer_csv(fuente: str) -> list:
    """fuente: URL https publicada de Google Sheets, o ruta a un archivo
    local (para pruebas). Devuelve una lista de filas (cada fila, una
    lista de strings) -- igual forma que csv.reader.

    Toda URL se valida contra el mismo allowlist de dominio que ya usa
    disponibilidad_csv_url en extract_common.sanear_config() -- si algún
    día esta fuente viene de una variable de repo mal configurada, el
    runner de CI no le hace un GET a un host arbitrario (ver auditoría
    de seguridad, hallazgo H-01)."""
    if fuente.startswith("http://") or fuente.startswith("https://"):
        if not ec.url_https_valida(fuente, ("docs.google.com",)):
            raise ValueError(
                f"La URL de origen no es de docs.google.com, no la voy a buscar: {fuente}"
            )
        with urllib.request.urlopen(fuente, timeout=15) as resp:
            contenido = resp.read().decode("utf-8-sig")
    else:
        contenido = Path(fuente).read_text(encoding="utf-8-sig")
    return list(csv.reader(io.StringIO(contenido)))


def _celda(filas, fila, col):
    """1-indexado, como extract.py. Fuera de rango o vacío -> None (igual
    que una celda vacía de Excel)."""
    if fila - 1 >= len(filas):
        return None
    linea = filas[fila - 1]
    if col - 1 >= len(linea):
        return None
    v = linea[col - 1]
    return v if v != "" else None


def _numero(valor):
    """CSV no tiene tipos -- todo llega como texto. Los campos que
    extract.py espera como número (precios, orden, tasas de cambio)
    necesitan esta conversión explícita, que openpyxl hacía sola."""
    if valor in (None, ""):
        return None
    try:
        f = float(str(valor).replace(",", "."))
    except ValueError:
        return None
    return int(f) if f.is_integer() else f


def load_categorias(filas: list) -> list:
    cats = []
    r = 5
    while _celda(filas, r, COL_CAT["cod"]) is not None:
        cats.append({
            "cod": _celda(filas, r, COL_CAT["cod"]),
            "orden": _numero(_celda(filas, r, COL_CAT["orden"])),
            "visible": _celda(filas, r, COL_CAT["visible"]) == "Sí",
            "nom": {lang: _celda(filas, r, c) for lang, c in COL_CAT["nom"].items()},
        })
        r += 1
    cats.sort(key=lambda c: c["orden"])
    return cats


def load_opciones_leche(filas_backoffice: list | None) -> dict:
    """Igual que extract.load_opciones_leche, pero desde un CSV opcional
    de 'Productos - Backoffice'. Si no se publicó esa hoja (es interna,
    no hace falta para el sitio), se sigue publicando sin datos de leche
    -- no bloquea nada, igual que en el Excel si esa hoja faltara."""
    if not filas_backoffice:
        return {}
    COL_LECHE_VEGETAL, COL_LECHE_SIN_LACTOSA = 18, 19
    out = {}
    r = 5
    while _celda(filas_backoffice, r, 1) is not None:
        idv = _celda(filas_backoffice, r, 1)
        ops = []
        if _celda(filas_backoffice, r, COL_LECHE_VEGETAL) == "Sí":
            ops.append("veg")
        if _celda(filas_backoffice, r, COL_LECHE_SIN_LACTOSA) == "Sí":
            ops.append("lac")
        if ops:
            out[idv] = ops
        r += 1
    return out


def load_productos(filas: list, filas_backoffice: list | None = None) -> dict:
    """Misma forma que extract.load_productos(), leyendo de filas de CSV
    en vez de celdas de openpyxl. Usa extract.COL -- una sola definición
    de columnas para las dos fuentes."""
    COL = ex.COL
    opciones_leche = load_opciones_leche(filas_backoffice)
    out = {}
    r = 5
    while _celda(filas, r, COL["id"]) is not None:
        idv = _celda(filas, r, COL["id"])
        cat_cod = _celda(filas, r, COL["cat"])
        chico = _numero(_celda(filas, r, COL["precio_chico"]))
        grande = _numero(_celda(filas, r, COL["precio_grande"]))
        estado_alergenos = _celda(filas, r, COL["estado_alergenos"])

        alergenos = None
        if estado_alergenos in ec.ESTADOS_ALERGENOS_VALIDADOS:
            c = COL["alergenos_inicio"]
            alergenos = {}
            for clave, _nombre in ec.MAPA_ALERGENOS:
                alergenos[clave] = _celda(filas, r, c) == "Sí"
                c += 1

        out[idv] = {
            "cat": cat_cod,
            "orden": _numero(_celda(filas, r, COL["orden"])),
            "n": {lang: _celda(filas, r, c) for lang, c in COL["nombre"].items()},
            "d": {lang: _celda(filas, r, c) for lang, c in COL["desc"].items()},
            "activo": _celda(filas, r, COL["activo"]) == "Sí",
            "destacado": _celda(filas, r, COL["destacado"]) == "Sí",
            "recomendado": _celda(filas, r, COL["recomendado"]) == "Sí",
            "mas_vendido": _celda(filas, r, COL["mas_vendido"]) == "Sí",
            "nuevo": _celda(filas, r, COL["nuevo"]) == "Sí",
            "precio": ec.formatear_precio(chico, grande, cat_cod),
            "precio_chico_ars": chico if chico not in (None, "") else grande,
            "temperatura": _celda(filas, r, COL["temperatura"]) or "",
            "formato": _celda(filas, r, COL["formato"]) or "",
            "img": _celda(filas, r, COL["img"]) or None,
            "alt": {lang: _celda(filas, r, c) for lang, c in COL["alt"].items()},
            "tag": _celda(filas, r, COL["etiqueta_inicial"]) or None,
            "disp": ec.DISPONIBILIDAD_VALORES.get(_celda(filas, r, COL["disponibilidad"])),
            "alerg": alergenos,
            "estado_alergenos": estado_alergenos,
            "leche": opciones_leche.get(idv, []),
            "_fila": r,
        }
        r += 1
    return out


def load_config(filas: list) -> dict:
    params = {}
    r = FILA_CONFIG_DESDE
    while _celda(filas, r, 1) is not None:
        nombre = _celda(filas, r, 1)
        params[str(nombre).strip()] = _celda(filas, r, 2)
        r += 1
    # Las tasas de cambio sí necesitan ser número (sanear_config las usa
    # como número para dividir) -- el resto de sanear_config ya maneja
    # bien los strings vacíos/None que vienen de CSV.
    for campo in ("Tipo de cambio ARS/USD", "Tipo de cambio ARS/EUR", "Real"):
        if campo in params:
            params[campo] = _numero(params[campo])
    return ec.sanear_config(params)


def extract(fuente_productos: str, fuente_categorias: str, fuente_config: str,
            fuente_backoffice: str | None = None) -> dict:
    filas_prod = _leer_csv(fuente_productos)
    filas_cat = _leer_csv(fuente_categorias)
    filas_cfg = _leer_csv(fuente_config)
    filas_back = _leer_csv(fuente_backoffice) if fuente_backoffice else None

    cats = load_categorias(filas_cat)
    productos = load_productos(filas_prod, filas_back)
    config = load_config(filas_cfg)
    overrides = json.loads(OVERRIDES_MOMENTOS.read_text(encoding="utf-8"))["extra"]
    return ec.ensamblar(productos, cats, config, overrides)
