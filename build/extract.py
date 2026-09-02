#!/usr/bin/env python3
"""xlsx (Ameli_Menu_Maestro, fuera del repo) -> data/menu.json (solo campos públicos).

Desde el maestro V3.1 el archivo tiene 4 hojas: 'Resumen y Configuración',
'Categorías', 'Productos' (nombre, descripción, precio, alérgenos — lo
esencial del menú) y 'Productos - Backoffice' (ingredientes y
personalización, referencia interna que el sitio nunca lee).
"""
import json
import sys
from pathlib import Path

import openpyxl

import config_local
import extract_common as ec

# Re-exportados para que validate.py y build.py los sigan encontrando en
# extract.* sin cambios (compatibilidad hacia atrás).
LANGS = ec.LANGS
CATEGORIAS_VASO_JARRA = ec.CATEGORIAS_VASO_JARRA
ESTADOS_ALERGENOS_VALIDADOS = ec.ESTADOS_ALERGENOS_VALIDADOS
_MAPA_ALERGENOS = ec.MAPA_ALERGENOS
DISPONIBILIDAD_VALORES = ec.DISPONIBILIDAD_VALORES

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE.parent / "data" / "menu.json"
OVERRIDES_MOMENTOS = HERE / "overrides_momentos.json"

FILA_CONFIG_INICIO = 16  # ver hoja "Resumen y Configuración": el bloque de
FILA_CONFIG_FIN = 30     # config empieza después del resumen automático.

# Columnas de la hoja "Productos" (1-indexado). Definidas una sola vez acá
# porque validate.py las necesita también para armar sus mensajes.
COL = {
    "id": 1, "cat": 2, "orden": 3,
    "nombre": {"es": 4, "en": 5, "pt": 6, "fr": 7, "it": 8},
    "desc": {"es": 9, "en": 10, "pt": 11, "fr": 12, "it": 13},
    "activo": 14, "destacado": 15, "recomendado": 16, "mas_vendido": 17, "nuevo": 18,
    "edicion_limitada": 19, "etiqueta_inicial": 20,
    "precio_chico": 21, "precio_grande": 22, "moneda": 23,
    "temperatura": 24, "formato": 25,
    "img": 26,
    "slug": {"es": 27, "en": 28, "pt": 29, "fr": 30, "it": 31},
    "alergenos_inicio": 32, "alergenos_fin": 46,
    "estado_alergenos": 47, "obs_alergenos": 48, "observaciones": 49,
    "disponibilidad": 50,
    "alt": {"es": 51, "en": 52, "pt": 53, "fr": 54, "it": 55},
}


def _sheet(wb, name):
    for candidate in wb.sheetnames:
        if candidate == name:
            return wb[candidate]
    raise KeyError(f"No se encontró la hoja {name!r}")


def load_categorias(wb):
    ws = _sheet(wb, "Categorías")
    cats = []
    r = 5
    while True:
        cod = ws.cell(row=r, column=1).value
        if cod is None:
            break
        visible = ws.cell(row=r, column=15).value
        cats.append({
            "cod": cod,
            "orden": ws.cell(row=r, column=2).value,
            "visible": visible == "Sí",
            "nom": {
                "es": ws.cell(row=r, column=9).value,
                "en": ws.cell(row=r, column=10).value,
                "pt": ws.cell(row=r, column=11).value,
                "fr": ws.cell(row=r, column=12).value,
                "it": ws.cell(row=r, column=13).value,
            },
        })
        r += 1
    cats.sort(key=lambda c: c["orden"])
    return cats


def load_opciones_leche(wb):
    """ID -> lista de opciones de leche disponibles ("veg", "lac"), leídas de
    'Productos - Backoffice' (columnas 'Leche vegetal' / 'Leche sin lactosa').
    Esto reemplaza a los viejos productos ADI001/ADI002 ("Leche vegetal",
    "Leche sin lactosa"): no son productos que se pidan solos, son un
    agregado para las bebidas que ya llevan leche — se muestra en el
    detalle del producto correspondiente, no como su propia fila de menú."""
    try:
        ws = wb["Productos - Backoffice"]
    except KeyError:
        return {}
    COL_LECHE_VEGETAL, COL_LECHE_SIN_LACTOSA = 18, 19
    out = {}
    r = 5
    while True:
        idv = ws.cell(row=r, column=1).value
        if idv is None:
            break
        ops = []
        if ws.cell(row=r, column=COL_LECHE_VEGETAL).value == "Sí":
            ops.append("veg")
        if ws.cell(row=r, column=COL_LECHE_SIN_LACTOSA).value == "Sí":
            ops.append("lac")
        if ops:
            out[idv] = ops
        r += 1
    return out


def load_productos(wb):
    """ID -> todos los datos de producto que usa el pipeline, en un solo lugar."""
    ws = _sheet(wb, "Productos")
    opciones_leche = load_opciones_leche(wb)
    out = {}
    r = 5
    while True:
        idv = ws.cell(row=r, column=COL["id"]).value
        if idv is None:
            break
        cat_cod = ws.cell(row=r, column=COL["cat"]).value
        chico = ws.cell(row=r, column=COL["precio_chico"]).value
        grande = ws.cell(row=r, column=COL["precio_grande"]).value
        estado_alergenos = ws.cell(row=r, column=COL["estado_alergenos"]).value

        alergenos = None
        if estado_alergenos in ESTADOS_ALERGENOS_VALIDADOS:
            c = COL["alergenos_inicio"]
            alergenos = {}
            for clave, _nombre in _MAPA_ALERGENOS:
                alergenos[clave] = ws.cell(row=r, column=c).value == "Sí"
                c += 1

        out[idv] = {
            "cat": cat_cod,
            "orden": ws.cell(row=r, column=COL["orden"]).value,
            "n": {lang: ws.cell(row=r, column=c).value for lang, c in
                  ((l, COL["nombre"][l]) for l in LANGS)},
            "d": {lang: ws.cell(row=r, column=c).value for lang, c in
                  ((l, COL["desc"][l]) for l in LANGS)},
            "activo": ws.cell(row=r, column=COL["activo"]).value == "Sí",
            "destacado": ws.cell(row=r, column=COL["destacado"]).value == "Sí",
            "recomendado": ws.cell(row=r, column=COL["recomendado"]).value == "Sí",
            "mas_vendido": ws.cell(row=r, column=COL["mas_vendido"]).value == "Sí",
            "nuevo": ws.cell(row=r, column=COL["nuevo"]).value == "Sí",
            "precio": ec.formatear_precio(chico, grande, cat_cod),
            "precio_chico_ars": chico if chico not in (None, "") else grande,
            "temperatura": ws.cell(row=r, column=COL["temperatura"]).value or "",
            "formato": ws.cell(row=r, column=COL["formato"]).value or "",
            "img": ws.cell(row=r, column=COL["img"]).value or None,
            "alt": {lang: ws.cell(row=r, column=c).value for lang, c in
                    ((l, COL["alt"][l]) for l in LANGS)},
            "tag": ws.cell(row=r, column=COL["etiqueta_inicial"]).value or None,
            "disp": DISPONIBILIDAD_VALORES.get(ws.cell(row=r, column=COL["disponibilidad"]).value),
            "alerg": alergenos,
            "estado_alergenos": estado_alergenos,
            "leche": opciones_leche.get(idv, []),
            "_fila": r,
        }
        r += 1
    return out


def load_config(wb):
    ws = _sheet(wb, "Resumen y Configuración")
    params = {}
    for r in range(FILA_CONFIG_INICIO, FILA_CONFIG_FIN + 1):
        nombre = ws.cell(row=r, column=1).value
        if nombre is None:
            continue
        params[str(nombre).strip()] = ws.cell(row=r, column=2).value
    return ec.sanear_config(params)


# Re-exportados: moments_for/badges_for viven en extract_common (los
# necesita también extract_sheets.py), pero quedan accesibles como
# extract.moments_for/extract.badges_for por si algo los importa de acá.
moments_for = ec.moments_for
badges_for = ec.badges_for


def extract(xlsx_path: Path) -> dict:
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    cats = load_categorias(wb)
    productos = load_productos(wb)
    config = load_config(wb)
    overrides = json.loads(OVERRIDES_MOMENTOS.read_text(encoding="utf-8"))["extra"]
    return ec.ensamblar(productos, cats, config, overrides)


# Re-exportados por compatibilidad (ver extract_common.py).
_CAMPOS_PROD_PUBLICOS = ec.CAMPOS_PROD_PUBLICOS
_CAMPOS_CONFIG_PUBLICOS = ec.CAMPOS_CONFIG_PUBLICOS
datos_publicos = ec.datos_publicos


def main():
    xlsx_arg = sys.argv[1] if len(sys.argv) > 1 else None
    xlsx_path = config_local.resolver_ruta_xlsx(xlsx_arg)
    if not xlsx_path.exists():
        print(config_local.mensaje_no_encontrado(xlsx_path))
        sys.exit(1)
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUT
    data = extract(xlsx_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(datos_publicos(data), ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"OK: {len(data['prods'])} productos activos, {len(data['cats'])} categorías -> {out_path}")


if __name__ == "__main__":
    main()
