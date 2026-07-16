#!/usr/bin/env python3
"""Valida data.json (+ el maestro original para chequeos que no viajan al JSON).

Errores -> bloquean el build. Warnings -> se listan pero no bloquean.
"""
import json
import sys
from pathlib import Path

import openpyxl

HERE = Path(__file__).resolve().parent
DEFAULT_XLSX = HERE.parent / "data" / "Ameli_Menu_Maestro_V2.1.xlsx"
DEFAULT_JSON = HERE.parent / "dist" / "data.json"
LANGS = ["es", "en", "pt", "fr", "it"]


def load_slugs(xlsx_path):
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb["10_Multimedia_SEO"]
    slugs_es, slugs_en = {}, {}
    r = 5
    while True:
        idv = ws.cell(row=r, column=1).value
        if idv is None:
            break
        slugs_es[idv] = ws.cell(row=r, column=11).value
        slugs_en[idv] = ws.cell(row=r, column=12).value
        r += 1
    return slugs_es, slugs_en


def validate(data: dict, xlsx_path: Path):
    errors, warnings = [], []
    cat_codes = {c["cod"] for c in data["cats"]}
    seen_ids = set()

    for p in data["prods"]:
        pid = p["id"]
        if pid in seen_ids:
            errors.append(f"ID duplicado: {pid}")
        seen_ids.add(pid)

        if p["cat"] not in cat_codes:
            errors.append(f"{pid}: categoría {p['cat']!r} no existe en 03_Categorías (o no está visible)")

        faltantes = [f"n.{l}" for l in LANGS if not p["n"].get(l)] + \
                    [f"d.{l}" for l in LANGS if not p["d"].get(l)]
        if faltantes:
            msg = f"{pid}: faltan traducciones {', '.join(faltantes)}"
            if p["dest"]:
                errors.append(msg + " (es producto destacado)")
            else:
                warnings.append(msg)

        if pid not in data["precios"]:
            warnings.append(f"{pid}: activo sin precio cargado en 04_Precios")

    if xlsx_path.exists():
        slugs_es, slugs_en = load_slugs(xlsx_path)
        for slugs, label in ((slugs_es, "ES"), (slugs_en, "EN")):
            vistos = {}
            for pid, slug in slugs.items():
                if not slug:
                    continue
                if slug in vistos:
                    errors.append(f"Slug {label} duplicado {slug!r}: {vistos[slug]} y {pid}")
                vistos[slug] = pid

    cfg = data["config"]
    if not cfg.get("whatsapp"):
        warnings.append("13_Configuración: falta 'WhatsApp de pedidos' (se usa el placeholder del template)")
    if not cfg.get("url_base"):
        warnings.append("13_Configuración: falta 'URL base del menú' (necesaria para el QR definitivo)")

    return errors, warnings


def main():
    json_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_JSON
    xlsx_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_XLSX
    data = json.loads(json_path.read_text(encoding="utf-8"))
    errors, warnings = validate(data, xlsx_path)

    for w in warnings:
        print(f"[WARN]  {w}")
    for e in errors:
        print(f"[ERROR] {e}")

    print(f"\n{len(errors)} error(es), {len(warnings)} warning(s).")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
