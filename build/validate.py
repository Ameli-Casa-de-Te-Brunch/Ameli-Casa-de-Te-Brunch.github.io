#!/usr/bin/env python3
"""Valida el maestro antes de publicar.

Habla en castellano llano: qué pasa, en qué hoja, en qué fila. El dueño del
negocio no es programador, así que cada mensaje dice exactamente qué corregir
y dónde.

Errores -> bloquean el build (build.py corta y no genera dist/index.html).
Warnings -> se listan pero no bloquean (ej. todavía no hay precios cargados).
"""
import re
import sys
from pathlib import Path

import openpyxl
from openpyxl.utils import get_column_letter

import config_local
import extract

HERE = Path(__file__).resolve().parent

# Solo 3 idiomas exigidos por el validador — ver la misma nota en extract.py.
LANGS = ["es", "en", "pt"]
IDIOMA_NOMBRE = {"es": "español", "en": "inglés", "pt": "portugués"}
COL_NOMBRE = {"es": 4, "en": 5, "pt": 6}       # 01_Menú_Multilingüe, D-F
COL_DESC = {"es": 9, "en": 10, "pt": 11}       # 01_Menú_Multilingüe, I-K
COL_PRECIO_LOCAL = 4                                             # 04_Precios, D
COL_CATEGORIA_COD = 5                                             # 02_Productos_MASTER, E

ID_FORMATO = re.compile(r"^[A-Z]{3}\d{3}$")

CAMPOS_CONTACTO = {"WhatsApp de pedidos", "Instagram", "Dirección", "URL base del menú"}

# Si algún día extract.py empieza a leer 07_Alérgenos_Dietas, cualquiera de
# estas claves apareciendo en un producto público dispara el chequeo de abajo.
CAMPOS_ALERGENOS_PROHIBIDOS = {
    "alergenos", "alérgenos", "vegetariano", "vegano", "sin_tacc", "sintacc_real",
    "contiene_gluten", "contiene_leche", "contiene_huevo", "contiene_soja",
    "contiene_mani", "contiene_frutos_secos", "contiene_sesamo",
    "contiene_pescado", "contiene_mariscos",
}


def _hoja07_validada(wb):
    """True solo si TODAS las filas de 07_Alérgenos_Dietas dicen 'Validado'
    en la columna de estado. Hoy están todas en 'Pendiente' (o similar) a
    propósito, hasta que el dueño las revise con recetas/etiquetas reales."""
    try:
        ws = wb["07_Alérgenos_Dietas"]
    except KeyError:
        return False
    r = 5
    while True:
        idv = ws.cell(row=r, column=1).value
        if idv is None:
            break
        estado = ws.cell(row=r, column=17).value  # columna Q, "Estado de validación"
        if estado != "Validado":
            return False
        r += 1
    return True


def _col(n):
    return get_column_letter(n)


def _es_placeholder(valor):
    if valor in (None, ""):
        return False
    texto = str(valor).strip().lower()
    return "xxx" in texto or texto in ("ejemplo", "pendiente", "completar", "tbd", "n/a")


def _leer_ids_hoja02(wb):
    """Todas las filas de 02_Productos_MASTER, incluso con IDs repetidos o mal formados
    (a diferencia de extract.py, que ya los usa como clave de diccionario y pierde duplicados)."""
    ws = wb["02_Productos_MASTER"]
    filas = []
    r = 5
    while True:
        idv = ws.cell(row=r, column=1).value
        if idv is None:
            break
        filas.append((r, idv))
        r += 1
    return filas


def _leer_slugs(wb):
    ws = wb["10_Multimedia_SEO"]
    filas = []
    r = 5
    while True:
        idv = ws.cell(row=r, column=1).value
        if idv is None:
            break
        filas.append((r, idv, ws.cell(row=r, column=11).value, ws.cell(row=r, column=12).value))
        r += 1
    return filas


def _leer_config_crudo(wb):
    ws = wb["13_Configuración"]
    valores = {}
    r = 5
    while True:
        nombre = ws.cell(row=r, column=1).value
        if nombre is None:
            break
        valores[nombre] = (r, ws.cell(row=r, column=2).value)
        r += 1
    return valores


def validate(data: dict, xlsx_path: Path):
    errors, warnings = [], []
    if not xlsx_path.exists():
        errors.append(f"No encuentro el archivo {xlsx_path} — revisá la ruta.")
        return errors, warnings

    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    meta = data.get("_meta", {})
    cat_codes = {c["cod"] for c in data["cats"]}

    # --- alérgenos: mientras 07_Alérgenos_Dietas no esté 100% validada, no
    # puede publicarse NINGÚN dato de esa hoja. Esto es una traba de verdad,
    # no solo un aviso: afirmar mal un alérgeno es un problema de salud, no
    # un detalle estético. ---
    if not _hoja07_validada(wb):
        for p in data["prods"]:
            campos_encontrados = CAMPOS_ALERGENOS_PROHIBIDOS & set(p.keys())
            if campos_encontrados:
                errors.append(
                    f"{p['id']}: trae datos de alérgenos ({', '.join(sorted(campos_encontrados))}) "
                    f"pero la hoja 07_Alérgenos_Dietas todavía no está validada (columna Q, "
                    f"'Estado de validación', tiene que decir 'Validado' en TODAS las filas). "
                    f"No se puede publicar ningún dato de alérgenos hasta entonces."
                )

    # --- rangos con nombre rotos (ej. si se perdió la hoja oculta 99_Listas al
    # guardar desde Excel). El pipeline no depende de estos rangos para nada —
    # lee valores de celda directamente — pero rompen los desplegables del
    # Excel para quien lo edita, así que vale la pena avisar. ---
    for nombre, rango in wb.defined_names.items():
        destino = rango.value if hasattr(rango, "value") else str(rango)
        if "#REF!" in destino:
            warnings.append(
                f"El rango con nombre '{nombre}' está roto (#REF!) — probablemente se perdió "
                f"la hoja oculta 99_Listas al guardar. No afecta la publicación del menú, pero "
                f"puede haber roto algún desplegable en el Excel. Revisalo cuando puedas."
            )

    # --- IDs: formato y duplicados (sobre TODAS las filas de la hoja 02, activas o no) ---
    filas_hoja02 = _leer_ids_hoja02(wb)
    vistos = {}
    for fila, idv in filas_hoja02:
        idv_txt = str(idv).strip()
        if not ID_FORMATO.match(idv_txt):
            errors.append(
                f"Fila {fila} de 02_Productos_MASTER: el ID '{idv_txt}' no tiene el formato "
                f"esperado (3 letras + 3 números, ej. TYT004). Corregilo en la columna A."
            )
        if idv_txt in vistos:
            errors.append(
                f"El ID '{idv_txt}' está repetido en 02_Productos_MASTER: filas {vistos[idv_txt]} "
                f"y {fila}. Cada producto necesita un ID único — cambiá uno de los dos."
            )
        else:
            vistos[idv_txt] = fila

    # --- por producto activo: traducciones, categoría, precio ---
    for p in data["prods"]:
        pid = p["id"]
        info = meta.get(pid, {})
        nombre = info.get("nombre_es") or pid
        fila_01 = info.get("fila_01")
        fila_02 = info.get("fila_02")
        fila_04 = info.get("fila_04")

        if p["cat"] not in cat_codes:
            errors.append(
                f"Fila {fila_02} ({pid} · {nombre}): la categoría '{p['cat']}' (columna "
                f"{_col(COL_CATEGORIA_COD)}) no existe en 03_Categorías, o no está marcada "
                f"como visible ahí."
            )

        for lang in LANGS:
            if not p["n"].get(lang):
                errors.append(
                    f"Fila {fila_01} ({pid} · {nombre}): falta el nombre en {IDIOMA_NOMBRE[lang]}. "
                    f"Cargalo en la hoja 01_Menú_Multilingüe, columna {_col(COL_NOMBRE[lang])}."
                )
            if not p["d"].get(lang):
                errors.append(
                    f"Fila {fila_01} ({pid} · {nombre}): falta la descripción en {IDIOMA_NOMBRE[lang]}. "
                    f"Cargala en la hoja 01_Menú_Multilingüe, columna {_col(COL_DESC[lang])}."
                )

        if pid not in data["precios"]:
            warnings.append(
                f"Fila {fila_04} ({pid} · {nombre}): está activo pero sin precio cargado en "
                f"04_Precios, columna {_col(COL_PRECIO_LOCAL)} — se va a publicar sin precio visible."
            )

    # --- slugs duplicados (hoja 10, SEO) ---
    filas_slugs = _leer_slugs(wb)
    for idx_col, label in ((2, "ES"), (3, "EN")):
        vistos_slug = {}
        for fila, idv, slug_es, slug_en in filas_slugs:
            slug = slug_es if idx_col == 2 else slug_en
            if not slug:
                continue
            if slug in vistos_slug:
                fila_prev, id_prev = vistos_slug[slug]
                errors.append(
                    f"El slug {label} '{slug}' se repite en 10_Multimedia_SEO: fila {fila_prev} "
                    f"({id_prev}) y fila {fila} ({idv}). Cada producto necesita un slug único."
                )
            else:
                vistos_slug[slug] = (fila, idv)

    # --- datos de contacto: placeholders detectados directamente en la hoja 13 ---
    config_crudo = _leer_config_crudo(wb)
    for campo, (fila, valor) in config_crudo.items():
        if campo not in CAMPOS_CONTACTO:
            continue
        if valor in (None, ""):
            warnings.append(
                f"Hoja 13_Configuración, fila {fila} ('{campo}'): está vacío. El elemento "
                f"correspondiente no se va a mostrar en el sitio hasta que lo completes."
            )
        elif _es_placeholder(valor):
            warnings.append(
                f"Hoja 13_Configuración, fila {fila} ('{campo}'): el valor '{valor}' parece un "
                f"dato de ejemplo, no uno real — no se va a publicar hasta que lo reemplaces."
            )

    return errors, warnings


def main():
    xlsx_arg = sys.argv[1] if len(sys.argv) > 1 else None
    xlsx_path = config_local.resolver_ruta_xlsx(xlsx_arg)
    if not xlsx_path.exists():
        print(config_local.mensaje_no_encontrado(xlsx_path))
        sys.exit(1)
    data = extract.extract(xlsx_path)  # incluye _meta, necesario para las filas de los mensajes
    errors, warnings = validate(data, xlsx_path)

    for w in warnings:
        print(f"[AVISO]  {w}")
    for e in errors:
        print(f"[ERROR] {e}")

    print(f"\n{len(errors)} error(es), {len(warnings)} aviso(s).")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
