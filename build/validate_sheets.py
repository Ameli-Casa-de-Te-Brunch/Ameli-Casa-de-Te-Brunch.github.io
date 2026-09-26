#!/usr/bin/env python3
"""Igual que validate.py, pero para el maestro publicado en Google Sheets
en vez del Excel. Mismos chequeos, mismos mensajes -- las columnas se
referencian con la misma letra porque el Sheet replica el layout del
Excel (ver extract_sheets.py). Pensado para correr en GitHub Actions:
errores bloquean la publicación, avisos no.
"""
import re

import extract_common as ec
import extract_sheets as es

IDIOMA_NOMBRE = {"es": "español", "en": "inglés", "pt": "portugués", "fr": "francés", "it": "italiano"}
ID_FORMATO = re.compile(r"^[A-Z]{3}\d{3}$")
CAMPOS_CONTACTO = {"WhatsApp de pedidos", "Instagram", "Dirección", "URL base del menú", "TripAdvisor", "Google (reseñas)"}


def _letra_columna(n: int) -> str:
    """Número de columna (1-indexado) -> letra estilo Excel/Sheets (1->A,
    27->AA). Reimplementado acá (en vez de openpyxl.utils.get_column_letter)
    a propósito: este módulo no puede depender de openpyxl -- es el único
    validador que sí corre en CI sin ese paquete instalado."""
    letras = ""
    while n > 0:
        n, resto = divmod(n - 1, 26)
        letras = chr(65 + resto) + letras
    return letras


def _col(nombre_campo, lang=None):
    c = ec.COL[nombre_campo]
    if lang:
        c = c[lang]
    return _letra_columna(c)


def _leer_ids_productos(filas):
    """Todas las filas de Productos, incluso con IDs repetidos o mal
    formados (a diferencia de extract_sheets.load_productos, que ya los
    usa como clave de diccionario y pierde duplicados)."""
    out = []
    r = 5
    while es._celda(filas, r, ec.COL["id"]) is not None:
        out.append((r, es._celda(filas, r, ec.COL["id"])))
        r += 1
    return out


def _leer_slugs(filas):
    out = []
    r = 5
    while es._celda(filas, r, ec.COL["id"]) is not None:
        idv = es._celda(filas, r, ec.COL["id"])
        out.append((r, idv, es._celda(filas, r, ec.COL["slug"]["es"]), es._celda(filas, r, ec.COL["slug"]["en"])))
        r += 1
    return out


def _leer_config_crudo(filas_config):
    """fila, valor por nombre de parámetro -- desde la hoja Config
    publicada (fila 1 = encabezado, ver extract_sheets.FILA_CONFIG_DESDE)."""
    valores = {}
    r = es.FILA_CONFIG_DESDE
    while es._celda(filas_config, r, 1) is not None:
        nombre = es._celda(filas_config, r, 1)
        valores[str(nombre).strip()] = (r, es._celda(filas_config, r, 2))
        r += 1
    return valores


def validate(data: dict, filas_productos: list, filas_config: list):
    """Misma firma conceptual que validate.validate(data, xlsx_path), pero
    recibe las filas de CSV ya leídas en vez de un path. El llamador actual
    es build.py en el camino local --sheets-productos; CI no importa estas
    hojas directamente."""
    errors, warnings = [], []
    meta = data.get("_meta", {})
    cat_codes = {c["cod"] for c in data["cats"]}

    # --- IDs: formato y duplicados (sobre TODAS las filas de Productos, activas o no) ---
    filas_ids = _leer_ids_productos(filas_productos)
    vistos = {}
    for fila, idv in filas_ids:
        idv_txt = str(idv).strip()
        if not ID_FORMATO.match(idv_txt):
            errors.append(
                f"Fila {fila} de Productos: el ID '{idv_txt}' no tiene el formato "
                f"esperado (3 letras + 3 números, ej. TYT004). Corregilo en la columna A."
            )
        if idv_txt in vistos:
            errors.append(
                f"El ID '{idv_txt}' está repetido en Productos: filas {vistos[idv_txt]} "
                f"y {fila}. Cada producto necesita un ID único — cambiá uno de los dos."
            )
        else:
            vistos[idv_txt] = fila

    # --- por producto activo: traducciones, categoría, precio, alérgenos ---
    for p in data["prods"]:
        pid = p["id"]
        info = meta.get(pid, {})
        nombre = info.get("nombre_es") or pid
        fila = info.get("fila")

        if p["cat"] not in cat_codes:
            errors.append(
                f"Fila {fila} ({pid} · {nombre}): la categoría '{p['cat']}' (columna "
                f"{_col('cat')}) no existe en la hoja Categorías, o no está marcada "
                f"como visible ahí."
            )

        for lang in ec.LANGS:
            if not p["n"].get(lang):
                errors.append(
                    f"Fila {fila} ({pid} · {nombre}): falta el nombre en {IDIOMA_NOMBRE[lang]}. "
                    f"Cargalo en la hoja Productos, columna {_col('nombre', lang)}."
                )
            if not p["d"].get(lang):
                errors.append(
                    f"Fila {fila} ({pid} · {nombre}): falta la descripción en {IDIOMA_NOMBRE[lang]}. "
                    f"Cargala en la hoja Productos, columna {_col('desc', lang)}."
                )

        if pid not in data["precios"]:
            warnings.append(
                f"Fila {fila} ({pid} · {nombre}): está activo pero sin precio cargado en "
                f"la hoja Productos, columna {_col('precio_chico')} (o su columna de precio "
                f"grande) — se va a publicar sin precio visible."
            )

        if "alerg" not in p:
            warnings.append(
                f"Fila {fila} ({pid} · {nombre}): sus alérgenos todavía no están validados "
                f"(columna {_col('estado_alergenos')} de Productos tiene que decir 'Validado "
                f"por cocina' o 'Validado por proveedor') — se va a publicar sin esa "
                f"información hasta entonces."
            )

        disp_crudo = es._celda(filas_productos, fila, ec.COL["disponibilidad"])
        if disp_crudo and disp_crudo not in ec.DISPONIBILIDAD_VALORES:
            valores_validos = "', '".join(ec.DISPONIBILIDAD_VALORES)
            warnings.append(
                f"Fila {fila} ({pid} · {nombre}): la columna {_col('disponibilidad')} "
                f"('Disponibilidad hoy') tiene '{disp_crudo}', que no es un valor reconocido. "
                f"Dejala vacía (= disponible) o usá exactamente '{valores_validos}'."
            )

    # --- slugs duplicados ---
    filas_slugs = _leer_slugs(filas_productos)
    for idx_col, label in (("es", "ES"), ("en", "EN")):
        vistos_slug = {}
        for fila, idv, slug_es, slug_en in filas_slugs:
            slug = slug_es if idx_col == "es" else slug_en
            if not slug:
                continue
            if slug in vistos_slug:
                fila_prev, id_prev = vistos_slug[slug]
                errors.append(
                    f"El slug {label} '{slug}' se repite en Productos: fila {fila_prev} "
                    f"({id_prev}) y fila {fila} ({idv}). Cada producto necesita un slug único."
                )
            else:
                vistos_slug[slug] = (fila, idv)

    # --- datos de contacto: placeholders detectados directamente en el bloque de config ---
    config_crudo = _leer_config_crudo(filas_config)
    for campo, (fila, valor) in config_crudo.items():
        if campo not in CAMPOS_CONTACTO:
            continue
        if valor in (None, ""):
            warnings.append(
                f"Hoja Config, fila {fila} ('{campo}'): está vacío. El elemento "
                f"correspondiente no se va a mostrar en el sitio hasta que lo completes."
            )
        elif ec.es_placeholder(valor):
            warnings.append(
                f"Hoja Config, fila {fila} ('{campo}'): el valor '{valor}' parece un "
                f"dato de ejemplo, no uno real — no se va a publicar hasta que lo reemplaces."
            )

    return errors, warnings
