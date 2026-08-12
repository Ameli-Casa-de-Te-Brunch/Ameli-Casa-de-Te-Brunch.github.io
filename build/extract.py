#!/usr/bin/env python3
"""xlsx (Ameli_Menu_Maestro, fuera del repo) -> data/menu.json (solo campos públicos).

Desde el maestro V3.0 el archivo tiene 4 hojas (antes eran 14):
'Resumen y Configuración', 'Categorías', 'Productos' y 'Productos - Backoffice'.
Este módulo solo lee las primeras tres — Backoffice es información interna
(costos, márgenes, ingredientes, alérgenos sin validar, canales futuros) que
el sitio público nunca necesita y por lo tanto nunca se lee acá.
"""
import json
import re
import sys
from pathlib import Path

import openpyxl

import config_local

# Solo 3 idiomas activos (turismo real de Malargüe). Francés e italiano
# quedan escritos en las columnas F/G (nombre) y L/M (descripción) de la
# hoja Productos para el futuro, pero ni se extraen ni el validador los exige.
LANGS = ["es", "en", "pt"]

# Categorías cuyo segundo precio (cuando existe) se etiqueta "Vaso/Jarra" en
# vez de "Chico/Grande" — así lo pide el menú físico (batidos y jugos).
CATEGORIAS_VASO_JARRA = {"BYJ"}

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE.parent / "data" / "menu.json"
OVERRIDES_MOMENTOS = HERE / "overrides_momentos.json"

FILA_CONFIG_INICIO = 18  # ver hoja "Resumen y Configuración": el bloque de
FILA_CONFIG_FIN = 27     # config empieza después del resumen automático.


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
                # columnas J/K (FR/IT) existen pero no se leen — ver LANGS.
            },
        })
        r += 1
    cats.sort(key=lambda c: c["orden"])
    return cats


def _formatear_precio(chico, grande, cat_cod):
    """Un solo precio -> "$ X". Dos precios -> "Chico $ X · Grande $ Y"
    (o "Vaso/Jarra" para batidos y jugos), según lo que haya cargado."""
    if chico in (None, "") and grande in (None, ""):
        return None
    et1, et2 = ("Vaso", "Jarra") if cat_cod in CATEGORIAS_VASO_JARRA else ("Chico", "Grande")
    fmt = lambda v: f"$ {v:,.0f}".replace(",", ".")
    if grande in (None, ""):
        return fmt(chico)
    if chico in (None, ""):
        return f"{et2} {fmt(grande)}"
    return f"{et1} {fmt(chico)} · {et2} {fmt(grande)}"


def load_productos(wb):
    """ID -> todos los datos de producto que usa el pipeline, en un solo lugar
    (antes vivían repartidos en 5 hojas distintas; ahora es una sola fila)."""
    ws = _sheet(wb, "Productos")
    out = {}
    r = 5
    while True:
        idv = ws.cell(row=r, column=1).value
        if idv is None:
            break
        cat_cod = ws.cell(row=r, column=2).value
        chico = ws.cell(row=r, column=22).value
        grande = ws.cell(row=r, column=23).value
        out[idv] = {
            "cat": cat_cod,
            "orden": ws.cell(row=r, column=3).value,
            "n": {
                "es": ws.cell(row=r, column=4).value,
                "en": ws.cell(row=r, column=5).value,
                "pt": ws.cell(row=r, column=6).value,
                # columnas G/H (FR/IT) existen pero no se leen — ver LANGS.
            },
            "d": {
                "es": ws.cell(row=r, column=9).value,
                "en": ws.cell(row=r, column=10).value,
                "pt": ws.cell(row=r, column=11).value,
                # columnas L/M (FR/IT) existen pero no se leen — ver LANGS.
            },
            "estado_traduccion": ws.cell(row=r, column=14).value,
            "activo": ws.cell(row=r, column=15).value == "Sí",
            "destacado": ws.cell(row=r, column=16).value == "Sí",
            "recomendado": ws.cell(row=r, column=17).value == "Sí",
            "mas_vendido": ws.cell(row=r, column=18).value == "Sí",
            "nuevo": ws.cell(row=r, column=19).value == "Sí",
            "precio": _formatear_precio(chico, grande, cat_cod),
            "tiene_precio": chico not in (None, "") or grande not in (None, ""),
            "temperatura": ws.cell(row=r, column=25).value or "",
            "formato": ws.cell(row=r, column=26).value or "",
            "img": ws.cell(row=r, column=27).value or None,
            "_fila": r,
        }
        r += 1
    return out


def _normalizar_whatsapp(valor):
    """La celda puede venir como número (Excel la interpreta así si son solo dígitos)
    o como texto con espacios/guiones. Siempre devolvemos solo dígitos, o None."""
    if valor in (None, ""):
        return None
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    solo_digitos = re.sub(r"\D", "", str(valor))
    return solo_digitos or None


def _es_placeholder(valor):
    """Detecta placeholders obvios tipo 'XXXXXXXX' o 'ejemplo' que no deberían publicarse."""
    if valor in (None, ""):
        return False
    texto = str(valor).strip().lower()
    return "xxx" in texto or texto in ("ejemplo", "pendiente", "completar", "tbd", "n/a")


def load_config(wb):
    ws = _sheet(wb, "Resumen y Configuración")
    params = {}
    for r in range(FILA_CONFIG_INICIO, FILA_CONFIG_FIN + 1):
        nombre = ws.cell(row=r, column=1).value
        if nombre is None:
            continue
        params[nombre] = ws.cell(row=r, column=2).value

    whatsapp = _normalizar_whatsapp(params.get("WhatsApp de pedidos"))
    instagram = params.get("Instagram")
    direccion = params.get("Dirección")
    url_base = params.get("URL base del menú")

    if _es_placeholder(whatsapp) or _es_placeholder(params.get("WhatsApp de pedidos")):
        whatsapp = None
    if _es_placeholder(instagram):
        instagram = None
    if _es_placeholder(direccion):
        direccion = None
    if _es_placeholder(url_base):
        url_base = None

    return {
        "moneda": params.get("Moneda local") or "ARS",
        "whatsapp": whatsapp,
        "instagram": instagram,
        "direccion": direccion,
        "url_base": url_base,
    }


def moments_for(prod, overrides):
    temp = prod["temperatura"]
    formato = prod["formato"]
    cat_cod = prod["cat"]
    prod_id = None  # se completa afuera si hace falta (overrides usa el id, no el dict)
    m = []
    if "Caliente" in temp:
        m.append("calentito")
    if "Fría" in temp:
        m.append("fresco")
    if "jarra" in formato or cat_cod == "TYT":
        m.append("compartir")
    if "Unidad" in formato or cat_cod == "STC":
        m.append("llevar")
    return m


def badges_for(prod):
    b = []
    if prod["destacado"]:
        b.append("fav")
    elif prod["recomendado"]:
        b.append("reco")
    elif prod["mas_vendido"]:
        b.append("pedido")
    elif prod["nuevo"]:
        b.append("nuevo")
    if prod["cat"] == "STC":
        b.append("sintacc")
    return b


def extract(xlsx_path: Path) -> dict:
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    cats = load_categorias(wb)
    productos = load_productos(wb)
    config = load_config(wb)
    overrides = json.loads(OVERRIDES_MOMENTOS.read_text(encoding="utf-8"))["extra"]

    prods = []
    precios = {}
    meta = {}
    # metadata de TODOS los productos (activos o no), para que el validador
    # pueda señalar filas concretas incluso en productos inactivos
    for prod_id, prod in productos.items():
        meta[prod_id] = {
            "fila": prod["_fila"],
            "cat": prod["cat"],
            "activo": prod["activo"],
            "destacado": prod["destacado"],
            "nombre_es": prod["n"]["es"] or prod_id,
        }

    for prod_id, prod in productos.items():
        if not prod["activo"]:
            continue
        m = moments_for(prod, overrides)
        for extra in overrides.get(prod_id, []):
            if extra not in m:
                m.append(extra)
        if prod["precio"]:
            precios[prod_id] = prod["precio"]
        prods.append({
            "id": prod_id,
            "cat": prod["cat"],
            "orden": prod["orden"],
            "dest": prod["destacado"],
            "n": prod["n"],
            "d": prod["d"],
            "m": m,
            "b": badges_for(prod),
            "img": prod["img"],
        })
    prods.sort(key=lambda p: (next(c["orden"] for c in cats if c["cod"] == p["cat"]), p["orden"]))

    cats_out = [{"cod": c["cod"], "orden": c["orden"], "nom": c["nom"]} for c in cats if c["visible"]]

    return {
        "cats": cats_out,
        "prods": prods,
        "precios": precios,
        "config": config,
        "_meta": meta,
    }


# Campos que SÍ salen al sitio público. Todo lo demás (costos, márgenes,
# proveedores, ingredientes internos, notas operativas, estadísticas,
# fila/columna de origen) se queda afuera de lo que se versiona y se publica.
_CAMPOS_PROD_PUBLICOS = ("id", "cat", "orden", "dest", "n", "d", "m", "b", "img")
_CAMPOS_CONFIG_PUBLICOS = ("moneda", "whatsapp", "instagram", "direccion", "url_base")


def datos_publicos(data: dict) -> dict:
    """Proyección de extract() con solo lo que un visitante del menú necesita ver.
    Esto es lo que se escribe a disco y se versiona — nunca el dict completo
    (que trae _meta: filas de origen, flags internos, etc. útiles solo para
    que validate.py arme sus mensajes en el mismo proceso)."""
    return {
        "cats": data["cats"],
        "prods": [{k: p[k] for k in _CAMPOS_PROD_PUBLICOS} for p in data["prods"]],
        "precios": data["precios"],
        "config": {k: data["config"].get(k) for k in _CAMPOS_CONFIG_PUBLICOS},
    }


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
