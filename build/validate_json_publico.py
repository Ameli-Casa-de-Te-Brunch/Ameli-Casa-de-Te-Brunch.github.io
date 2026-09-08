#!/usr/bin/env python3
"""Valida data/menu.json de forma independiente del Excel/Sheets -- el único
control de integridad que corre en GitHub Actions antes de renderizar y
publicar (CI nunca ve el maestro, así que validate.py/validate_sheets.py no
alcanzan ahí). Habla en los mismos términos que validate.py: errores
bloquean, avisos no.

Allowlist estricta y real: cualquier clave -- de primer nivel, de una
categoría, de un producto, de una entrada de precios o de config -- que no
esté en la lista explícita correspondiente es un ERROR, no se deja pasar
en silencio. Las traducciones en los 5 idiomas son obligatorias (error, no
aviso) porque el maestro ya las exige así (ver validate.py).

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
LANGS = ec.LANGS

CAMPOS_RAIZ_PERMITIDOS = ("cats", "prods", "precios", "config")
CAMPOS_CATEGORIA_PERMITIDOS = ("cod", "orden", "nom")
CAMPOS_PROD_OBLIGATORIOS = ("id", "cat", "orden", "dest", "n", "d", "m", "b", "img")
CAMPOS_PROD_OPCIONALES = tuple(c for c in ec.CAMPOS_PROD_PUBLICOS if c not in CAMPOS_PROD_OBLIGATORIOS)
CAMPOS_PRECIO_PERMITIDOS = ("ars", "usd", "eur", "brl")

# Mismos valores que efectivamente consume assets/js/menu.js (BADGES,
# ALERG_TXT, los chips de "momentos", y las opciones de leche del
# detalle) -- un valor fuera de esta lista no es solo un dato sucio: en
# el sitio real produce un BADGES[k].c o ALERG_TXT[k][lang] con `k`
# indefinida, que puede romper ese producto en el navegador.
BADGES_VALIDOS = {"fav", "reco", "pedido", "nuevo", "sintacc"}
# "dulce" no sale de extract_common.moments_for() (ver
# build/overrides_momentos.json: no tiene columna propia en el maestro,
# se agrega a mano por excepción) -- pero sí es un chip real del array
# CHIPS en assets/js/menu.js, así que es un valor válido acá también.
MOMENTOS_VALIDOS = {"dulce", "fresco", "compartir", "calentito", "llevar"}
ALERGENOS_VALIDOS = {clave for clave, _nombre in ec.MAPA_ALERGENOS}
LECHE_VALIDA = {"veg", "lac"}

# Mismo formato que ID_FORMATO en validate.py (3 letras + 3 números) --
# los códigos de categoría son siempre las mismas 3 letras que prefijan
# sus productos (ej. categoría "TYT", productos "TYT001".."TYT00N").
ID_PRODUCTO_FORMATO = re.compile(r"^[A-Z]{3}[0-9]{3}$")
ID_CATEGORIA_FORMATO = re.compile(r"^[A-Z]{3}$")

# Detecta __ALGO__ y también __ALGO2__ / __ALGO_123__ -- la versión
# anterior ([A-Z_]+) no reconocía dígitos en el marcador.
MARCADOR_PLANTILLA = re.compile(r"__[A-Z0-9_]+__")


def _es_num(valor) -> bool:
    """int/float, pero no bool -- bool es subclase de int en Python y un
    'True' donde se espera un precio sería un tipo incorrecto igual."""
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def _img_valida(valor: str) -> bool:
    """Única política sostenible dada la CSP real (img-src 'self',
    ver render.py): una ruta relativa propia bajo assets/img/, nunca una
    URL externa -- el navegador la bloquearía igual, mejor rechazarla acá
    con un mensaje claro que confiar en que la CSP la tape en silencio.
    Sin esquema (bloquea http:, https:, data:, javascript:, //host), sin
    ruta absoluta, sin "..": tres formas distintas de escapar de
    assets/img/."""
    if not valor:
        return False
    if ":" in valor or valor.startswith("//"):
        return False
    if valor.startswith("/"):
        return False
    if ".." in valor:
        return False
    return valor.startswith("assets/img/")


def validate_menu_json(data) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    # --- estructura de primer nivel: objeto, claves permitidas, tipos ---
    if not isinstance(data, dict):
        return ["El JSON público no es un objeto en la raíz."], []

    campos_raiz_desconocidos = set(data.keys()) - set(CAMPOS_RAIZ_PERMITIDOS)
    if campos_raiz_desconocidos:
        errors.append(
            f"El JSON tiene clave(s) de primer nivel no permitidas: {sorted(campos_raiz_desconocidos)}. "
            f"Solo se permiten {list(CAMPOS_RAIZ_PERMITIDOS)}."
        )

    for clave, tipos in (("cats", list), ("prods", list), ("precios", dict), ("config", dict)):
        if clave not in data:
            errors.append(f"Falta la clave de primer nivel '{clave}'.")
        elif not isinstance(data[clave], tipos):
            errors.append(f"'{clave}' tiene que ser {tipos.__name__}, encontré {type(data[clave]).__name__}.")
    if errors:
        return errors, warnings  # sin esto no se puede seguir validando nada más

    cats, prods, precios, config = data["cats"], data["prods"], data["precios"], data["config"]

    # --- categorías: solo campos permitidos, tipos, códigos únicos ---
    cat_codes = set()
    for i, c in enumerate(cats):
        if not isinstance(c, dict):
            errors.append(f"Categoría en posición {i}: no es un objeto.")
            continue

        campos_desconocidos = set(c.keys()) - set(CAMPOS_CATEGORIA_PERMITIDOS)
        if campos_desconocidos:
            errors.append(
                f"Categoría en posición {i} ({c.get('cod', '?')}): tiene campo(s) no permitidos "
                f"{sorted(campos_desconocidos)}. Solo se permiten {list(CAMPOS_CATEGORIA_PERMITIDOS)}."
            )
        faltantes_cat = [c2 for c2 in CAMPOS_CATEGORIA_PERMITIDOS if c2 not in c]
        if faltantes_cat:
            errors.append(f"Categoría en posición {i}: faltan campos obligatorios {faltantes_cat}.")
            continue

        if not isinstance(c["cod"], str) or not c["cod"]:
            errors.append(f"Categoría en posición {i}: 'cod' tiene que ser un string no vacío.")
            continue
        if not ID_CATEGORIA_FORMATO.match(c["cod"]):
            errors.append(
                f"Categoría '{c['cod']}': el código no tiene el formato esperado (3 letras mayúsculas)."
            )
        if not _es_num(c["orden"]):
            errors.append(f"Categoría '{c['cod']}': 'orden' tiene que ser numérico.")
        if c["cod"] in cat_codes:
            errors.append(f"Código de categoría duplicado: '{c['cod']}'.")
        cat_codes.add(c["cod"])

        nom = c["nom"]
        if not isinstance(nom, dict):
            errors.append(f"Categoría '{c['cod']}': 'nom' tiene que ser un objeto por idioma.")
        else:
            campos_nom_desconocidos = set(nom.keys()) - set(LANGS)
            if campos_nom_desconocidos:
                errors.append(
                    f"Categoría '{c['cod']}': 'nom' tiene idioma(s) no permitido(s) "
                    f"{sorted(campos_nom_desconocidos)}. Solo se permiten {LANGS}."
                )
            for lang in LANGS:
                if not isinstance(nom.get(lang), str) or not nom.get(lang):
                    errors.append(f"Categoría '{c['cod']}': falta o es inválido 'nom.{lang}'.")

    # --- productos: campos permitidos, tipos, IDs únicos, categoría existente,
    #     código de disponibilidad válido ---
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
        if not ID_PRODUCTO_FORMATO.match(pid):
            errors.append(
                f"Producto '{pid}': el ID no tiene el formato esperado (3 letras + 3 números, ej. TYT004)."
            )
        if pid in ids_vistos:
            errors.append(f"ID de producto duplicado: '{pid}' (posiciones {ids_vistos[pid]} y {i}).")
        else:
            ids_vistos[pid] = i
        ids_activos.add(pid)

        if not isinstance(p["cat"], str):
            errors.append(f"Producto '{pid}': 'cat' tiene que ser un string.")
        elif p["cat"] not in cat_codes:
            errors.append(f"Producto '{pid}': la categoría '{p['cat']}' no existe entre las categorías publicadas.")

        if not _es_num(p["orden"]):
            errors.append(f"Producto '{pid}': 'orden' tiene que ser numérico.")
        if not isinstance(p["dest"], bool):
            errors.append(f"Producto '{pid}': 'dest' tiene que ser booleano.")
        if p["img"] is not None:
            if not isinstance(p["img"], str):
                errors.append(f"Producto '{pid}': 'img' tiene que ser un string o null.")
            elif not _img_valida(p["img"]):
                errors.append(
                    f"Producto '{pid}': 'img' tiene que ser una ruta relativa propia bajo 'assets/img/' "
                    "-- no una URL externa, ruta absoluta, ni contener '..' (la CSP solo permite img-src 'self')."
                )

        # Traducciones en los 5 idiomas: obligatorias -- el maestro ya las
        # exige así (ver validate.py), un faltante acá es tan error como
        # allá, no un aviso. Solo esos 5 idiomas -- ni uno más.
        for campo_texto in ("n", "d"):
            valor = p.get(campo_texto)
            if not isinstance(valor, dict):
                errors.append(f"Producto '{pid}': '{campo_texto}' tiene que ser un objeto por idioma.")
                continue
            campos_idioma_desconocidos = set(valor.keys()) - set(LANGS)
            if campos_idioma_desconocidos:
                errors.append(
                    f"Producto '{pid}': '{campo_texto}' tiene idioma(s) no permitido(s) "
                    f"{sorted(campos_idioma_desconocidos)}. Solo se permiten {LANGS}."
                )
            for lang in LANGS:
                if not isinstance(valor.get(lang), str) or not valor.get(lang):
                    errors.append(f"Producto '{pid}': falta o es inválida '{campo_texto}.{lang}'.")

        if not isinstance(p.get("m"), list):
            errors.append(f"Producto '{pid}': 'm' tiene que ser una lista.")
        else:
            desconocidos_m = sorted(set(p["m"]) - MOMENTOS_VALIDOS)
            if desconocidos_m:
                errors.append(
                    f"Producto '{pid}': 'm' tiene valor(es) no reconocido(s) {desconocidos_m} "
                    f"(válidos: {sorted(MOMENTOS_VALIDOS)})."
                )
        if not isinstance(p.get("b"), list):
            errors.append(f"Producto '{pid}': 'b' tiene que ser una lista.")
        else:
            desconocidos_b = sorted(set(p["b"]) - BADGES_VALIDOS)
            if desconocidos_b:
                errors.append(
                    f"Producto '{pid}': 'b' tiene valor(es) no reconocido(s) {desconocidos_b} "
                    f"(válidos: {sorted(BADGES_VALIDOS)})."
                )

        if "disp" in p and p["disp"] not in CODIGOS_DISPONIBILIDAD_VALIDOS:
            errors.append(
                f"Producto '{pid}': código de disponibilidad '{p['disp']}' no reconocido "
                f"(válidos: {sorted(CODIGOS_DISPONIBILIDAD_VALIDOS)})."
            )

        # "alt" es opcional a propósito: si falta (entero o por idioma),
        # assets/js/menu.js ya usa el nombre del producto (p.n[lang])
        # como alternativa -- ver altProducto() en menu.js. Cuando SÍ
        # está, solo puede traer estos 5 idiomas.
        if "alt" in p:
            if not isinstance(p["alt"], dict):
                errors.append(f"Producto '{pid}': 'alt' tiene que ser un objeto por idioma.")
            else:
                campos_alt_desconocidos = set(p["alt"].keys()) - set(LANGS)
                if campos_alt_desconocidos:
                    errors.append(
                        f"Producto '{pid}': 'alt' tiene idioma(s) no permitido(s) "
                        f"{sorted(campos_alt_desconocidos)}. Solo se permiten {LANGS}."
                    )
                for lang, valor_alt in p["alt"].items():
                    if valor_alt is not None and (not isinstance(valor_alt, str) or not valor_alt.strip()):
                        errors.append(f"Producto '{pid}': 'alt.{lang}' tiene que ser un string no vacío o null.")

        if "alerg" in p:
            if not isinstance(p["alerg"], dict):
                errors.append(f"Producto '{pid}': 'alerg' tiene que ser un objeto.")
            else:
                desconocidos_alerg = sorted(set(p["alerg"].keys()) - ALERGENOS_VALIDOS)
                if desconocidos_alerg:
                    errors.append(
                        f"Producto '{pid}': 'alerg' tiene clave(s) no reconocida(s) {desconocidos_alerg} "
                        f"(válidas: {sorted(ALERGENOS_VALIDOS)})."
                    )
                for clave, valor_alerg in p["alerg"].items():
                    if not isinstance(valor_alerg, bool):
                        errors.append(f"Producto '{pid}': 'alerg.{clave}' tiene que ser booleano.")

        if "tag" in p and not isinstance(p["tag"], str):
            errors.append(f"Producto '{pid}': 'tag' tiene que ser un string.")

        if "leche" in p:
            if not isinstance(p["leche"], list):
                errors.append(f"Producto '{pid}': 'leche' tiene que ser una lista.")
            else:
                if any(not isinstance(x, str) for x in p["leche"]):
                    errors.append(f"Producto '{pid}': 'leche' tiene que ser una lista de strings.")
                else:
                    desconocidos_leche = sorted(set(p["leche"]) - LECHE_VALIDA)
                    if desconocidos_leche:
                        errors.append(
                            f"Producto '{pid}': 'leche' tiene valor(es) no reconocido(s) {desconocidos_leche} "
                            f"(válidos: {sorted(LECHE_VALIDA)})."
                        )
                    if len(p["leche"]) != len(set(p["leche"])):
                        errors.append(f"Producto '{pid}': 'leche' tiene valores duplicados.")

        if pid not in precios:
            warnings.append(f"Producto '{pid}': no tiene precio en 'precios' -- se publica sin precio visible.")

    # --- precios: solo campos permitidos, tipos correctos, ninguna entrada
    #     huérfana (un ID que ya no exista en prods) ---
    for pid, entrada in precios.items():
        if pid not in ids_activos:
            errors.append(f"'precios' tiene una entrada para '{pid}', que no existe en 'prods' (referencia huérfana).")
            continue
        if not isinstance(entrada, dict):
            errors.append(f"'precios.{pid}' tiene que ser un objeto.")
            continue
        campos_desconocidos = set(entrada.keys()) - set(CAMPOS_PRECIO_PERMITIDOS)
        if campos_desconocidos:
            errors.append(
                f"'precios.{pid}' tiene campo(s) no permitidos {sorted(campos_desconocidos)}. "
                f"Solo se permiten {list(CAMPOS_PRECIO_PERMITIDOS)}."
            )
        if "ars" not in entrada:
            errors.append(f"'precios.{pid}' tiene que tener al menos la clave 'ars'.")
        elif not isinstance(entrada["ars"], str) or not entrada["ars"]:
            # "ars" ya viene formateado como string de display (ej. "$
            # 6.000" o "Vaso $ 7.500 · Jarra $ 16.000") -- ver
            # extract_common.formatear_precio(); no es un número crudo.
            errors.append(f"'precios.{pid}.ars' tiene que ser un string no vacío (ya viene formateado).")
        for campo in ("usd", "eur", "brl"):
            if campo in entrada and not isinstance(entrada[campo], str):
                errors.append(f"'precios.{pid}.{campo}' tiene que ser un string (ya viene formateado).")

    # --- config: solo campos públicos, y válidos si están presentes ---
    campos_config_desconocidos = set(config.keys()) - set(ec.CAMPOS_CONFIG_PUBLICOS)
    if campos_config_desconocidos:
        errors.append(
            f"'config' tiene campo(s) no públicos o internos: {sorted(campos_config_desconocidos)} "
            f"-- nunca deberían llegar al JSON público (ver CAMPOS_CONFIG_PUBLICOS)."
        )

    whatsapp = config.get("whatsapp")
    if whatsapp is not None:
        # isinstance(x, str) primero y aparte: un número JSON como 12345678
        # coincidiría con la regex si se lo pasara por str(), pero no es
        # un string -- el tipo importa, no solo el contenido.
        if not isinstance(whatsapp, str):
            errors.append(f"'config.whatsapp' tiene que ser un string, no {type(whatsapp).__name__}.")
        elif not ec.WHATSAPP_LONGITUD.match(whatsapp):
            errors.append(f"'config.whatsapp' ('{whatsapp}') no son 8 a 15 dígitos.")

    moneda = config.get("moneda")
    if moneda is not None and (not isinstance(moneda, str) or not moneda):
        errors.append("'config.moneda' tiene que ser un string no vacío.")

    direccion = config.get("direccion")
    if direccion is not None and (not isinstance(direccion, str) or not direccion):
        errors.append("'config.direccion' tiene que ser un string no vacío o null.")

    instagram = config.get("instagram")
    if instagram is not None and (not isinstance(instagram, str) or not re.fullmatch(r"[A-Za-z0-9._]{1,30}", instagram)):
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
    marcadores = sorted(set(MARCADOR_PLANTILLA.findall(texto_completo)))
    if marcadores:
        errors.append(f"Quedaron marcadores de plantilla sin reemplazar en el JSON: {marcadores}.")

    return errors, warnings


def main():
    json_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_JSON
    if not json_path.exists():
        print(f"[ERROR] No encuentro {json_path}.")
        sys.exit(1)

    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"[ERROR] {json_path} no es JSON válido: {e}")
        sys.exit(1)
    except UnicodeDecodeError:
        print(f"[ERROR] {json_path} no es UTF-8 válido.")
        sys.exit(1)

    errors, warnings = validate_menu_json(data)

    n_prods = len(data.get("prods", [])) if isinstance(data, dict) and isinstance(data.get("prods"), list) else 0
    n_cats = len(data.get("cats", [])) if isinstance(data, dict) and isinstance(data.get("cats"), list) else 0
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
