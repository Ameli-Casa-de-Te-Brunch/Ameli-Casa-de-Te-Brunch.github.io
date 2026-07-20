#!/usr/bin/env python3
"""xlsx (Ameli_Menu_Maestro) -> data.json (CATS/PRODS/PRECIOS/CONFIG)."""
import json
import sys
from pathlib import Path

import openpyxl

LANGS = ["es", "en", "pt", "fr", "it"]
LANG_COLS = {"es": 0, "en": 1, "pt": 2, "fr": 3, "it": 4}  # offset from first name/desc column

HERE = Path(__file__).resolve().parent
DEFAULT_XLSX = HERE.parent / "data" / "Ameli_Menu_Maestro_V2.1.xlsx"
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


def _row_dict(ws, header_row=4, id_col=1, first_data_row=5):
    """Yield {id: {col_letter_index: value}} keyed by row, stopping at first empty ID."""
    rows = {}
    r = first_data_row
    while True:
        idv = ws.cell(row=r, column=id_col).value
        if idv is None:
            if r - first_data_row > 200:  # safety valve, sheet is capped at row ~60
                break
            r += 1
            if ws.cell(row=r, column=id_col).value is None and r > first_data_row + 5:
                break
            continue
        rows[idv] = r
        r += 1
    return rows


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
                "fr": ws.cell(row=r, column=11).value,
                "it": ws.cell(row=r, column=12).value,
            },
        })
        r += 1
    cats.sort(key=lambda c: c["orden"])
    return cats


def load_menu_multilingue(wb):
    """ID -> {n:{lang}, d:{lang}, estado_traduccion}"""
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
                "fr": ws.cell(row=r, column=7).value,
                "it": ws.cell(row=r, column=8).value,
            },
            "d": {
                "es": ws.cell(row=r, column=9).value,
                "en": ws.cell(row=r, column=10).value,
                "pt": ws.cell(row=r, column=11).value,
                "fr": ws.cell(row=r, column=12).value,
                "it": ws.cell(row=r, column=13).value,
            },
            "estado_traduccion": ws.cell(row=r, column=14).value,
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
    return {
        "moneda": params.get("Moneda local") or "ARS",
        "whatsapp": params.get("WhatsApp de pedidos"),
        "instagram": params.get("Instagram"),
        "direccion": params.get("Dirección"),
        "url_base": params.get("URL base del menú"),
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
    multimedia = load_multimedia(wb)
    config = load_config(wb)
    overrides = json.loads(OVERRIDES_MOMENTOS.read_text(encoding="utf-8"))["extra"]

    prods = []
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
    }


def main():
    xlsx_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_XLSX
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE.parent / "dist" / "data.json"
    data = extract(xlsx_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"OK: {len(data['prods'])} productos activos, {len(data['cats'])} categorías -> {out_path}")


if __name__ == "__main__":
    main()
