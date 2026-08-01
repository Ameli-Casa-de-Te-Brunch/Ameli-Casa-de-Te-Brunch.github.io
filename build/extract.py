#!/usr/bin/env python3
"""xlsx (Ameli_Menu_Maestro, fuera del repo) -> data/menu.json (solo campos públicos)."""
import json
import re
import sys
from pathlib import Path

import openpyxl

import config_local

# Solo 3 idiomas activos (turismo real de Malargüe). Francés e italiano
# quedan escritos en las columnas G/H (nombre) y L/M (descripción) del
# maestro para el futuro, pero ni se extraen ni el validador los exige.
LANGS = ["es", "en", "pt"]

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE.parent / "data" / "menu.json"
OVERRIDES_MOMENTOS = HERE / "overrides_momentos.json"


def _sheet(wb, name):
    for candidate in wb.sheetnames:
        if candidate.split("_", 1)[-1] == name or candidate == name:
            return wb[candidate]
    # tolerate encoding mismatches on the accented part, match by numeric prefix
    prefix = name.split("_", 1)[0]
    for candidate in wb.sheetnames:
        if candidate.startswith(prefix + "_"):
            return wb[candidate]
    raise KeyError(f"No se encontró la hoja {name!r}")


def load_categorias(wb):
    ws = _sheet(wb, "03_Categorías")
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
                "es": ws.cell(row=r, column=8).value,
                "en": ws.cell(row=r, column=9).value,
                "pt": ws.cell(row=r, column=10).value,
                # K/L (fr/it) existen en el maestro pero no se leen — ver LANGS.
            },
        })
        r += 1
    cats.sort(key=lambda c: c["orden"])
    return cats


def load_menu_multilingue(wb):
    """ID -> {n:{lang}, d:{lang}, estado_traduccion, _fila}"""
    ws = _sheet(wb, "01_Menú_Multilingüe")
    out = {}
    r = 5
    while True:
        idv = ws.cell(row=r, column=1).value
        if idv is None:
            break
        out[idv] = {
            "n": {
                "es": ws.cell(row=r, column=4).value,
                "en": ws.cell(row=r, column=5).value,
                "pt": ws.cell(row=r, column=6).value,
                # G/H (fr/it) existen en el maestro pero no se leen — ver LANGS.
            },
            "d": {
                "es": ws.cell(row=r, column=9).value,
                "en": ws.cell(row=r, column=10).value,
                "pt": ws.cell(row=r, column=11).value,
                # L/M (fr/it) existen en el maestro pero no se leen — ver LANGS.
            },
            "estado_traduccion": ws.cell(row=r, column=14).value,
            "_fila": r,
        }
        r += 1
    return out


def load_productos_master(wb):
    """ID -> flags/orden dict"""
    ws = _sheet(wb, "02_Productos_MASTER")
    out = {}
    r = 5
    while True:
        idv = ws.cell(row=r, column=1).value
        if idv is None:
            break
        out[idv] = {
            "cat": ws.cell(row=r, column=5).value,
            "orden_cat": ws.cell(row=r, column=6).value,
            "orden_prod": ws.cell(row=r, column=7).value,
            "activo": ws.cell(row=r, column=10).value == "Sí",
            "destacado": ws.cell(row=r, column=11).value == "Sí",
            "recomendado": ws.cell(row=r, column=12).value == "Sí",
            "mas_vendido": ws.cell(row=r, column=13).value == "Sí",
            "nuevo": ws.cell(row=r, column=14).value == "Sí",
            "_fila": r,
        }
        r += 1
    return out


def load_gastronomia(wb):
    """ID -> {temperatura, formato}"""
    ws = _sheet(wb, "05_Gastronomía")
    out = {}
    r = 5
    while True:
        idv = ws.cell(row=r, column=1).value
        if idv is None:
            break
        out[idv] = {
            "temperatura": ws.cell(row=r, column=4).value or "",
            "formato": ws.cell(row=r, column=5).value or "",
        }
        r += 1
    return out


def load_multimedia(wb):
    """ID -> URL de imagen principal (o None si la hoja todavía no la tiene cargada)."""
    ws = _sheet(wb, "10_Multimedia_SEO")
    out = {}
    r = 5
    while True:
        idv = ws.cell(row=r, column=1).value
        if idv is None:
            break
        url = ws.cell(row=r, column=3).value
        out[idv] = url or None
        r += 1
    return out


def load_precios(wb):
    """ID -> precio local formateado (solo si está cargado)."""
    ws = _sheet(wb, "04_Precios")
    out = {}
    r = 5
    while True:
        idv = ws.cell(row=r, column=1).value
        if idv is None:
            break
        precio = ws.cell(row=r, column=4).value
        if precio not in (None, ""):
            out[idv] = f"$ {precio:,.0f}".replace(",", ".")
        r += 1
    return out


def load_filas_precios(wb):
    """ID -> número de fila en 04_Precios (para mensajes de validación)."""
    ws = _sheet(wb, "04_Precios")
    out = {}
    r = 5
    while True:
        idv = ws.cell(row=r, column=1).value
        if idv is None:
            break
        out[idv] = r
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
    ws = _sheet(wb, "13_Configuración")
    params = {}
    r = 5
    while True:
        nombre = ws.cell(row=r, column=1).value
        if nombre is None:
            break
        params[nombre] = ws.cell(row=r, column=2).value
        r += 1

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


def moments_for(prod_id, cat_cod, gastro, overrides):
    temp = gastro.get(prod_id, {}).get("temperatura", "")
    formato = gastro.get(prod_id, {}).get("formato", "")
    m = []
    if "Caliente" in temp:
        m.append("calentito")
    if "Fría" in temp:
        m.append("fresco")
    if "jarra" in formato or cat_cod == "TYT":
        m.append("compartir")
    if "Unidad" in formato or cat_cod == "STC":
        m.append("llevar")
    for extra in overrides.get(prod_id, []):
        if extra not in m:
            m.append(extra)
    return m


def badges_for(flags, cat_cod):
    b = []
    if flags["destacado"]:
        b.append("fav")
    elif flags["recomendado"]:
        b.append("reco")
    elif flags["mas_vendido"]:
        b.append("pedido")
    elif flags["nuevo"]:
        b.append("nuevo")
    if cat_cod == "STC":
        b.append("sintacc")
    return b


def extract(xlsx_path: Path) -> dict:
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    cats = load_categorias(wb)
    menu = load_menu_multilingue(wb)
    master = load_productos_master(wb)
    gastro = load_gastronomia(wb)
    precios = load_precios(wb)
    filas_precios = load_filas_precios(wb)
    multimedia = load_multimedia(wb)
    config = load_config(wb)
    overrides = json.loads(OVERRIDES_MOMENTOS.read_text(encoding="utf-8"))["extra"]

    prods = []
    meta = {}
    # metadata de TODOS los productos de la hoja 02 (activos o no), para que el
    # validador pueda señalar filas concretas incluso en productos inactivos
    for prod_id, flags in master.items():
        traducciones = menu.get(prod_id)
        meta[prod_id] = {
            "fila_02": flags["_fila"],
            "fila_01": traducciones["_fila"] if traducciones else None,
            "fila_04": filas_precios.get(prod_id),
            "cat": flags["cat"],
            "activo": flags["activo"],
            "destacado": flags["destacado"],
            "nombre_es": (traducciones["n"]["es"] if traducciones else None) or prod_id,
        }

    for prod_id, flags in master.items():
        if not flags["activo"]:
            continue
        traducciones = menu.get(prod_id)
        if traducciones is None:
            continue
        prods.append({
            "id": prod_id,
            "cat": flags["cat"],
            "orden": flags["orden_prod"],
            "dest": flags["destacado"],
            "n": traducciones["n"],
            "d": traducciones["d"],
            "m": moments_for(prod_id, flags["cat"], gastro, overrides),
            "b": badges_for(flags, flags["cat"]),
            "img": multimedia.get(prod_id),
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
