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

Este archivo trata TODO el contenido de data/menu.json como no confiable
(no solo la disponibilidad en vivo de la hoja): nunca reproduce en un
mensaje de error un valor recibido que no haya sido confirmado antes
contra un conjunto o formato conocido -- ni una clave desconocida, ni un
ID sin validar, ni un valor de enumeración rechazado, ni una URL, ni un
teléfono/handle inválido. Cuando hace falta identificar dónde está el
problema sin reproducir el contenido, se usa la posición, el campo o un
conteo. Ver tests/test_validate_json_publico.py (centinela
SECRETO_NO_DEBE_APARECER_123) para la prueba de que esto se cumple en
todos los casos.

Tampoco asume que las listas/objetos anidados (m, b, leche, alerg, etc.)
tengan el tipo esperado en cada elemento: un elemento no-string, no
hasheable o de tipo mixto en una de esas listas nunca debe producir un
traceback (TypeError al armar un set() o al ordenar) -- se reporta como
error controlado."""
import json
import re
import sys
from pathlib import Path

import extract_common as ec

HERE = Path(__file__).resolve().parent
DEFAULT_JSON = HERE.parent / "data" / "menu.json"

CODIGOS_DISPONIBILIDAD_VALIDOS = {v for v in ec.DISPONIBILIDAD_VALORES.values() if v}
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
# sus productos (ej. categoría "TYT", productos "TYT001".."TYT00N"). Un
# ID/código que matchea este formato tiene un alfabeto tan chico que no
# puede llevar pegado nada sensible -- por eso es el único caso en que
# este archivo reproduce un identificador recibido en un mensaje de
# error: recién DESPUÉS de confirmar que matchea. Antes de eso (o si
# nunca matchea), los mensajes identifican por posición.
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


def _id_seguro_de_mostrar(valor, patron) -> bool:
    """True si `valor` es un string que matchea `patron` (ID_PRODUCTO_FORMATO
    o ID_CATEGORIA_FORMATO) -- el único caso en que es seguro reproducirlo
    tal cual en un mensaje de error (ver comentario junto a esos
    patrones)."""
    return isinstance(valor, str) and bool(patron.match(valor))


def _validar_enumeracion(errors, etiqueta, campo, valores, validos, exigir_sin_duplicados=False):
    """Valida una lista de strings (m, b, leche) contra un conjunto fijo de
    valores válidos, sin nunca reproducir ninguno de los valores recibidos
    en un mensaje de error, y sin nunca lanzar TypeError sin importar qué
    haya adentro de la lista (dicts, listas anidadas, números, None, tipos
    mixtos -- nada de eso es hasheable/ordenable de forma uniforme con
    set()/sorted() directo). Devuelve la sublista de elementos que sí son
    strings (por si el llamador la necesita)."""
    if not isinstance(valores, list):
        errors.append(f"{etiqueta}: '{campo}' tiene que ser una lista.")
        return []

    no_strings = sum(1 for x in valores if not isinstance(x, str))
    if no_strings:
        errors.append(f"{etiqueta}: '{campo}' tiene {no_strings} elemento(s) que no son texto.")

    strings = [x for x in valores if isinstance(x, str)]
    desconocidos = sorted(set(strings) - validos)
    if desconocidos:
        errors.append(
            f"{etiqueta}: '{campo}' tiene {len(desconocidos)} valor(es) no reconocido(s) "
            f"(válidos: {sorted(validos)})."
        )
    if exigir_sin_duplicados and len(strings) != len(set(strings)):
        errors.append(f"{etiqueta}: '{campo}' tiene valores duplicados.")
    return strings


def validate_menu_json(data) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    # --- estructura de primer nivel: objeto, claves permitidas, tipos ---
    if not isinstance(data, dict):
        return ["El JSON público no es un objeto en la raíz."], []

    campos_raiz_desconocidos = set(data.keys()) - set(CAMPOS_RAIZ_PERMITIDOS)
    if campos_raiz_desconocidos:
        errors.append(
            f"El JSON tiene {len(campos_raiz_desconocidos)} clave(s) de primer nivel no permitida(s). "
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
                f"Categoría en posición {i}: tiene {len(campos_desconocidos)} campo(s) no permitido(s). "
                f"Solo se permiten {list(CAMPOS_CATEGORIA_PERMITIDOS)}."
            )
        faltantes_cat = [c2 for c2 in CAMPOS_CATEGORIA_PERMITIDOS if c2 not in c]
        if faltantes_cat:
            errors.append(f"Categoría en posición {i}: faltan campos obligatorios {faltantes_cat}.")
            continue

        cod = c["cod"]
        cod_seguro = _id_seguro_de_mostrar(cod, ID_CATEGORIA_FORMATO)
        etiqueta_cat = f"Categoría '{cod}'" if cod_seguro else f"Categoría en posición {i}"

        if not isinstance(cod, str) or not cod:
            errors.append(f"{etiqueta_cat}: 'cod' tiene que ser un string no vacío.")
            continue
        if not cod_seguro:
            errors.append(f"{etiqueta_cat}: el código no tiene el formato esperado (3 letras mayúsculas).")
        if not _es_num(c["orden"]):
            errors.append(f"{etiqueta_cat}: 'orden' tiene que ser numérico.")
        if cod in cat_codes:
            errors.append(f"{etiqueta_cat}: código de categoría duplicado.")
        cat_codes.add(cod)

        nom = c["nom"]
        if not isinstance(nom, dict):
            errors.append(f"{etiqueta_cat}: 'nom' tiene que ser un objeto por idioma.")
        else:
            campos_nom_desconocidos = set(nom.keys()) - set(LANGS)
            if campos_nom_desconocidos:
                errors.append(
                    f"{etiqueta_cat}: 'nom' tiene {len(campos_nom_desconocidos)} idioma(s) no permitido(s). "
                    f"Solo se permiten {LANGS}."
                )
            for lang in LANGS:
                if not isinstance(nom.get(lang), str) or not nom.get(lang):
                    errors.append(f"{etiqueta_cat}: falta o es inválido 'nom.{lang}'.")

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
                f"Producto en posición {i}: tiene {len(campos_desconocidos)} campo(s) no público(s) "
                f"o desconocido(s). Solo se permiten {list(ec.CAMPOS_PROD_PUBLICOS)}."
            )
        faltantes = [c for c in CAMPOS_PROD_OBLIGATORIOS if c not in p]
        if faltantes:
            errors.append(f"Producto en posición {i}: faltan campos obligatorios {faltantes}.")
            continue

        pid = p["id"]
        pid_seguro = _id_seguro_de_mostrar(pid, ID_PRODUCTO_FORMATO)
        etiqueta = f"Producto '{pid}'" if pid_seguro else f"Producto en posición {i}"

        if not isinstance(pid, str) or not pid:
            errors.append(f"{etiqueta}: 'id' tiene que ser un string no vacío.")
            continue
        if not pid_seguro:
            errors.append(f"{etiqueta}: el ID no tiene el formato esperado (3 letras + 3 números, ej. TYT004).")
        if pid in ids_vistos:
            errors.append(f"{etiqueta}: ID de producto duplicado (también en posición {ids_vistos[pid]}).")
        else:
            ids_vistos[pid] = i
        ids_activos.add(pid)

        if not isinstance(p["cat"], str):
            errors.append(f"{etiqueta}: 'cat' tiene que ser un string.")
        elif p["cat"] not in cat_codes:
            errors.append(f"{etiqueta}: la categoría indicada no existe entre las categorías publicadas.")

        if not _es_num(p["orden"]):
            errors.append(f"{etiqueta}: 'orden' tiene que ser numérico.")
        if not isinstance(p["dest"], bool):
            errors.append(f"{etiqueta}: 'dest' tiene que ser booleano.")
        if p["img"] is not None:
            if not isinstance(p["img"], str):
                errors.append(f"{etiqueta}: 'img' tiene que ser un string o null.")
            elif not _img_valida(p["img"]):
                errors.append(
                    f"{etiqueta}: 'img' tiene que ser una ruta relativa propia bajo 'assets/img/' "
                    "-- no una URL externa, ruta absoluta, ni contener '..' (la CSP solo permite img-src 'self')."
                )

        # Traducciones en los 5 idiomas: obligatorias -- el maestro ya las
        # exige así (ver validate.py), un faltante acá es tan error como
        # allá, no un aviso. Solo esos 5 idiomas -- ni uno más. Se itera
        # sobre LANGS (fijo), nunca sobre valor.items(): así una clave de
        # idioma desconocida/inyectada nunca llega a formar parte de un
        # mensaje de error.
        for campo_texto in ("n", "d"):
            valor = p.get(campo_texto)
            if not isinstance(valor, dict):
                errors.append(f"{etiqueta}: '{campo_texto}' tiene que ser un objeto por idioma.")
                continue
            campos_idioma_desconocidos = set(valor.keys()) - set(LANGS)
            if campos_idioma_desconocidos:
                errors.append(
                    f"{etiqueta}: '{campo_texto}' tiene {len(campos_idioma_desconocidos)} idioma(s) "
                    f"no permitido(s). Solo se permiten {LANGS}."
                )
            for lang in LANGS:
                if not isinstance(valor.get(lang), str) or not valor.get(lang):
                    errors.append(f"{etiqueta}: falta o es inválida '{campo_texto}.{lang}'.")

        _validar_enumeracion(errors, etiqueta, "m", p.get("m"), MOMENTOS_VALIDOS)
        _validar_enumeracion(errors, etiqueta, "b", p.get("b"), BADGES_VALIDOS)

        if "disp" in p:
            disp_valor = p["disp"]
            # isinstance primero: p["disp"] podría no ser hasheable (una
            # lista, un dict) y el "in" de más abajo levantaría TypeError
            # si se evaluara sobre un valor así.
            if not isinstance(disp_valor, str) or disp_valor not in CODIGOS_DISPONIBILIDAD_VALIDOS:
                errors.append(
                    f"{etiqueta}: código de disponibilidad no reconocido "
                    f"(válidos: {sorted(CODIGOS_DISPONIBILIDAD_VALIDOS)})."
                )

        # "alt" es opcional a propósito: si falta (entero o por idioma),
        # assets/js/menu.js ya usa el nombre del producto (p.n[lang])
        # como alternativa -- ver altProducto() en menu.js. Cuando SÍ
        # está, solo puede traer estos 5 idiomas -- se itera sobre LANGS
        # (fijo), nunca sobre p["alt"].items().
        if "alt" in p:
            if not isinstance(p["alt"], dict):
                errors.append(f"{etiqueta}: 'alt' tiene que ser un objeto por idioma.")
            else:
                campos_alt_desconocidos = set(p["alt"].keys()) - set(LANGS)
                if campos_alt_desconocidos:
                    errors.append(
                        f"{etiqueta}: 'alt' tiene {len(campos_alt_desconocidos)} idioma(s) no permitido(s). "
                        f"Solo se permiten {LANGS}."
                    )
                for lang in LANGS:
                    if lang not in p["alt"]:
                        continue
                    valor_alt = p["alt"][lang]
                    if valor_alt is not None and (not isinstance(valor_alt, str) or not valor_alt.strip()):
                        errors.append(f"{etiqueta}: 'alt.{lang}' tiene que ser un string no vacío o null.")

        if "alerg" in p:
            if not isinstance(p["alerg"], dict):
                errors.append(f"{etiqueta}: 'alerg' tiene que ser un objeto.")
            else:
                desconocidos_alerg = set(p["alerg"].keys()) - ALERGENOS_VALIDOS
                if desconocidos_alerg:
                    errors.append(
                        f"{etiqueta}: 'alerg' tiene {len(desconocidos_alerg)} clave(s) no reconocida(s) "
                        f"(válidas: {sorted(ALERGENOS_VALIDOS)})."
                    )
                # Se recorren solo las claves ya confirmadas como
                # alérgenos reales (ALERGENOS_VALIDOS es un vocabulario
                # fijo, acotado y propio) -- nunca una clave inyectada
                # desconocida, que ya quedó reportada arriba sin
                # reproducirla.
                for clave in ALERGENOS_VALIDOS:
                    if clave not in p["alerg"]:
                        continue
                    if not isinstance(p["alerg"][clave], bool):
                        errors.append(f"{etiqueta}: 'alerg.{clave}' tiene que ser booleano.")

        if "tag" in p and not isinstance(p["tag"], str):
            errors.append(f"{etiqueta}: 'tag' tiene que ser un string.")

        if "leche" in p:
            _validar_enumeracion(errors, etiqueta, "leche", p.get("leche"), LECHE_VALIDA,
                                  exigir_sin_duplicados=True)

        if pid_seguro and pid not in precios:
            warnings.append(f"{etiqueta}: no tiene precio en 'precios' -- se publica sin precio visible.")

    # --- precios: solo campos permitidos, tipos correctos, ninguna entrada
    #     huérfana (un ID que ya no exista en prods) ---
    for pid, entrada in precios.items():
        # Las claves de un objeto JSON son siempre strings (json.loads
        # nunca produce claves de otro tipo), así que "pid" acá siempre es
        # un string -- pero puede no tener el formato de ID de producto
        # (una clave inyectada/con basura), en cuyo caso no se reproduce.
        pid_seguro = _id_seguro_de_mostrar(pid, ID_PRODUCTO_FORMATO)
        etiqueta_precio = f"'precios.{pid}'" if pid_seguro else "una entrada de 'precios' con clave inválida"

        if pid not in ids_activos:
            errors.append(f"{etiqueta_precio}: no existe en 'prods' (referencia huérfana).")
            continue
        if not isinstance(entrada, dict):
            errors.append(f"{etiqueta_precio}: tiene que ser un objeto.")
            continue
        campos_desconocidos = set(entrada.keys()) - set(CAMPOS_PRECIO_PERMITIDOS)
        if campos_desconocidos:
            errors.append(
                f"{etiqueta_precio}: tiene {len(campos_desconocidos)} campo(s) no permitido(s). "
                f"Solo se permiten {list(CAMPOS_PRECIO_PERMITIDOS)}."
            )
        if "ars" not in entrada:
            errors.append(f"{etiqueta_precio}: tiene que tener al menos la clave 'ars'.")
        elif not isinstance(entrada["ars"], str) or not entrada["ars"]:
            # "ars" ya viene formateado como string de display (ej. "$
            # 6.000" o "Vaso $ 7.500 · Jarra $ 16.000") -- ver
            # extract_common.formatear_precio(); no es un número crudo.
            errors.append(f"{etiqueta_precio}.ars: tiene que ser un string no vacío (ya viene formateado).")
        for campo in ("usd", "eur", "brl"):
            if campo in entrada and not isinstance(entrada[campo], str):
                errors.append(f"{etiqueta_precio}.{campo}: tiene que ser un string (ya viene formateado).")

    # --- config: solo campos públicos, y válidos si están presentes ---
    campos_config_desconocidos = set(config.keys()) - set(ec.CAMPOS_CONFIG_PUBLICOS)
    if campos_config_desconocidos:
        errors.append(
            f"'config' tiene {len(campos_config_desconocidos)} campo(s) no público(s) o interno(s) "
            "-- nunca deberían llegar al JSON público (ver CAMPOS_CONFIG_PUBLICOS)."
        )

    whatsapp = config.get("whatsapp")
    if whatsapp is not None:
        # isinstance(x, str) primero y aparte: un número JSON como 12345678
        # coincidiría con la regex si se lo pasara por str(), pero no es
        # un string -- el tipo importa, no solo el contenido.
        if not isinstance(whatsapp, str):
            errors.append(f"'config.whatsapp' tiene que ser un string, no {type(whatsapp).__name__}.")
        elif not ec.WHATSAPP_LONGITUD.match(whatsapp):
            errors.append("'config.whatsapp' no son 8 a 15 dígitos.")

    moneda = config.get("moneda")
    if moneda is not None and (not isinstance(moneda, str) or not moneda):
        errors.append("'config.moneda' tiene que ser un string no vacío.")

    direccion = config.get("direccion")
    if direccion is not None and (not isinstance(direccion, str) or not direccion):
        errors.append("'config.direccion' tiene que ser un string no vacío o null.")

    instagram = config.get("instagram")
    if instagram is not None and (not isinstance(instagram, str) or not re.fullmatch(r"[A-Za-z0-9._]{1,30}", instagram)):
        errors.append("'config.instagram' no es un handle válido.")

    # url_base tiene una política propia y más estricta (ver
    # extract_common.url_base_valida): un origen https limpio, exacto, sin
    # path/query/fragmento/usuario/puerto -- nunca se valida con la misma
    # función "genérica" que TripAdvisor/Google Reseñas, que sí pueden
    # necesitar paths.
    url_base = config.get("url_base")
    if url_base is not None and not ec.url_base_valida(url_base):
        errors.append("'config.url_base' no pasa la validación de origen público (https, host exacto, sin path/query/fragmento).")

    for campo, dominios in (
        ("tripadvisor", ec.DOMINIOS_TRIPADVISOR),
        ("google_resenas", ec.DOMINIOS_GOOGLE),
    ):
        valor = config.get(campo)
        if valor is not None and not ec.url_https_valida(valor, dominios):
            errors.append(f"'config.{campo}' no pasa la validación de URL (https + dominio permitido).")

    # --- ningún marcador de plantilla sin reemplazar, en ningún string del JSON ---
    texto_completo = json.dumps(data, ensure_ascii=False)
    marcadores = MARCADOR_PLANTILLA.findall(texto_completo)
    if marcadores:
        errors.append(f"Quedaron {len(set(marcadores))} marcador(es) de plantilla sin reemplazar en el JSON.")

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

    try:
        errors, warnings = validate_menu_json(data)
    except Exception as e:
        # Red de seguridad final: pase lo que pase adentro de
        # validate_menu_json (que ya está escrita para nunca necesitar
        # esto), un fallo inesperado nunca debe salir como traceback ni
        # reproducir el valor que lo causó -- solo el tipo de excepción.
        print(f"[ERROR] Fallo inesperado validando el JSON ({type(e).__name__}).")
        sys.exit(1)

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
