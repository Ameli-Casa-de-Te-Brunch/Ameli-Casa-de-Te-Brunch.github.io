#!/usr/bin/env python3
"""Valida data/menu.json de forma independiente del Excel/Sheets -- el único
control de integridad que corre en GitHub Actions antes de renderizar y
publicar (CI nunca ve el maestro, así que validate.py/validate_sheets.py no
alcanzan ahí). Habla en los mismos términos que validate.py: errores
bloquean, avisos no.

No fija en ningún lado que "tienen que ser 51 productos" -- reporta el
conteo actual y valida coherencia de referencias (categorías, precios),
para que agregar o sacar productos nunca rompa este control por un número
hardcodeado.
"""
import json
import re
import sys
from pathlib import Path

import extract_common as ec

HERE = Path(__file__).resolve().parent
DEFAULT_JSON = HERE.parent / "data" / "menu.json"

CODIGOS_DISPONIBILIDAD_VALIDOS = set(ec.DISPONIBILIDAD_VALORES.values())
CAMPOS_PROD_OBLIGATORIOS = ("id", "cat", "orden", "dest", "n", "d", "m", "b", "img")
CAMPOS_PROD_OPCIONALES = tuple(c for c in ec.CAMPOS_PROD_PUBLICOS if c not in CAMPOS_PROD_OBLIGATORIOS)
LANGS = ec.LANGS


def _tipo_ok(valor, tipos):
    return isinstance(valor, tipos)


def validate_menu_json(data: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    # --- estructura de primer nivel ---
    if not isinstance(data, dict):
        return ["El JSON público no es un objeto en la raíz."], []
    for clave, tipos in (("cats", list), ("prods", list), ("precios", dict), ("config", dict)):
        if clave not in data:
            errors.append(f"Falta la clave de primer nivel '{clave}'.")
        elif not _tipo_ok(data[clave], tipos):
            errors.append(f"'{clave}' tiene que ser {tipos.__name__}, encontré {type(data[clave]).__name__}.")
    if errors:
        return errors, warnings  # sin esto no se puede seguir validando nada más

    cats, prods, precios, config = data["cats"], data["prods"], data["precios"], data["config"]

    # --- categorías: forma y códigos únicos ---
    cat_codes = set()
    for i, c in enumerate(cats):
        if not isinstance(c, dict) or "cod" not in c or "nom" not in c:
            errors.append(f"Categoría en posición {i}: le falta 'cod' o 'nom', o no es un objeto.")
            continue
        if c["cod"] in cat_codes:
            errors.append(f"Código de categoría duplicado: '{c['cod']}'.")
        cat_codes.add(c["cod"])
        if not isinstance(c.get("nom"), dict) or not c["nom"].get("es"):
            errors.append(f"Categoría '{c['cod']}': falta el nombre en español ('nom.es').")

    # --- productos: campos permitidos, tipos, IDs únicos, categoría existente,
    #     código de disponibilidad válido, URLs/handles válidos si vienen embebidos ---
    ids_vistos: dict[str, int] = {}
    ids_activos: set[str] = set()
    for i, p in enumerate(prods):
        if not isinstance(p, dict):
            errors.append(f"Producto en posición {i}: no es un objeto.")
            continue

        campos_desconocidos = set(p.keys()) - set(ec.CAMPOS_PROD_PUBLICOS)
        if campos_desconocidos:
            errors.append(
                f"Producto en posición {i} ({p.get('id', '?')}): tiene campo(s) no públicos "
                f"o desconocidos: {sorted(campos_desconocidos)}. Solo se permiten "
                f"{list(ec.CAMPOS_PROD_PUBLICOS)}."
            )
        faltantes = [c for c in CAMPOS_PROD_OBLIGATORIOS if c not in p]
        if faltantes:
            errors.append(f"Producto en posición {i} ({p.get('id', '?')}): faltan campos obligatorios {faltantes}.")
            continue

        pid = p["id"]
        if not isinstance(pid, str) or not pid:
            errors.append(f"Producto en posición {i}: 'id' tiene que ser un string no vacío.")
            continue
        if pid in ids_vistos:
            errors.append(f"ID de producto duplicado: '{pid}' (posiciones {ids_vistos[pid]} y {i}).")
        else:
            ids_vistos[pid] = i
        ids_activos.add(pid)

        if p["cat"] not in cat_codes:
            errors.append(f"Producto '{pid}': la categoría '{p['cat']}' no existe entre las categorías publicadas.")

        for campo_texto, tipo_ok in (("n", dict), ("d", dict)):
            valor = p.get(campo_texto)
            if not isinstance(valor, tipo_ok):
                errors.append(f"Producto '{pid}': '{campo_texto}' tiene que ser un objeto por idioma.")
                continue
            for lang in LANGS:
                if not valor.get(lang):
                    warnings.append(f"Producto '{pid}': falta '{campo_texto}.{lang}'.")

        if not isinstance(p.get("m"), list) or not isinstance(p.get("b"), list):
            errors.append(f"Producto '{pid}': 'm' y 'b' tienen que ser listas.")

        if "disp" in p and p["disp"] not in CODIGOS_DISPONIBILIDAD_VALIDOS:
            errors.append(
                f"Producto '{pid}': código de disponibilidad '{p['disp']}' no reconocido "
                f"(válidos: {sorted(CODIGOS_DISPONIBILIDAD_VALIDOS)})."
            )

        if pid not in precios:
            warnings.append(f"Producto '{pid}': no tiene precio en 'precios' -- se publica sin precio visible.")

    # --- precios: ninguna entrada huérfana (un ID que ya no exista en prods) ---
    for pid in precios:
        if pid not in ids_activos:
            errors.append(f"'precios' tiene una entrada para '{pid}', que no existe en 'prods' (referencia huérfana).")
        elif not isinstance(precios[pid], dict) or "ars" not in precios[pid]:
            errors.append(f"'precios.{pid}' tiene que ser un objeto con al menos la clave 'ars'.")

    # --- config: solo campos públicos, y válidos si están presentes ---
    campos_config_desconocidos = set(config.keys()) - set(ec.CAMPOS_CONFIG_PUBLICOS)
    if campos_config_desconocidos:
        errors.append(
            f"'config' tiene campo(s) no públicos o internos: {sorted(campos_config_desconocidos)} "
            f"-- nunca deberían llegar al JSON público (ver CAMPOS_CONFIG_PUBLICOS)."
        )

    whatsapp = config.get("whatsapp")
    if whatsapp is not None and not ec.WHATSAPP_LONGITUD.match(str(whatsapp)):
        errors.append(f"'config.whatsapp' ('{whatsapp}') no son 8 a 15 dígitos.")

    instagram = config.get("instagram")
    if instagram is not None and not re.fullmatch(r"[A-Za-z0-9._]{1,30}", instagram):
        errors.append(f"'config.instagram' ('{instagram}') no es un handle válido.")

    for campo, dominios in (
        ("url_base", ec.DOMINIOS_MENU),
        ("tripadvisor", ec.DOMINIOS_TRIPADVISOR),
        ("google_resenas", ec.DOMINIOS_GOOGLE),
    ):
        valor = config.get(campo)
        if valor is not None and not ec.url_https_valida(valor, dominios):
            errors.append(f"'config.{campo}' ('{valor}') no pasa la validación de URL (https + dominio permitido).")

    # --- ningún marcador de plantilla sin reemplazar, en ningún string del JSON ---
    texto_completo = json.dumps(data, ensure_ascii=False)
    marcadores = sorted(set(re.findall(r"__[A-Z_]+__", texto_completo)))
    if marcadores:
        errors.append(f"Quedaron marcadores de plantilla sin reemplazar en el JSON: {marcadores}.")

    return errors, warnings


def main():
    json_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_JSON
    if not json_path.exists():
        print(f"[ERROR] No encuentro {json_path}.")
        sys.exit(1)

    data = json.loads(json_path.read_text(encoding="utf-8"))
    errors, warnings = validate_menu_json(data)

    n_prods = len(data.get("prods", [])) if isinstance(data.get("prods"), list) else 0
    n_cats = len(data.get("cats", [])) if isinstance(data.get("cats"), list) else 0
    print(f"[INFO] {n_prods} producto(s), {n_cats} categoría(s) en {json_path}.")

    for w in warnings:
        print(f"[AVISO] {w}")
    for e in errors:
        print(f"[ERROR] {e}")

    print(f"\n{len(errors)} error(es), {len(warnings)} aviso(s).")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
