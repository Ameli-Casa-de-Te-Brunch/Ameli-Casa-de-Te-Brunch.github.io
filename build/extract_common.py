#!/usr/bin/env python3
"""Lógica de transformación compartida entre las dos fuentes del maestro:
el Excel (extract.py, "PC del dueño") y Google Sheets (extract_sheets.py,
"publicar desde el celular"). Nada acá lee un archivo directamente -- solo
transforma datos ya leídos (dicts/listas planas), sea cual sea su origen.

Separar esto evitó duplicar la lógica de negocio (formato de precio,
badges, moments, saneo de config) en dos lugares que se irían desalineando
con el tiempo -- ambas fuentes terminan en el mismo data/menu.json.
"""
import re
from urllib.parse import urlsplit

# Los 5 idiomas trabajados en el maestro.
LANGS = ["es", "en", "pt", "fr", "it"]

# Categorías cuyo segundo precio (cuando existe) se etiqueta "Vaso/Jarra" en
# vez de "Chico/Grande" — así lo pide el menú físico (batidos y jugos).
CATEGORIAS_VASO_JARRA = {"BYJ"}

# Estados de la columna "Estado de validación (alérgenos)" que habilitan
# publicar los datos de alérgenos de ESE producto puntual. Ver la nota legal
# en validate.py: mientras un producto diga otra cosa (por defecto,
# "Pendiente"), sus alérgenos nunca salen en el JSON público.
ESTADOS_ALERGENOS_VALIDADOS = {"Validado por cocina", "Validado por proveedor"}

# Columnas de la hoja "Productos" (1-indexado), Excel y Sheets por igual --
# definidas acá (no en extract.py) para que extract_sheets.py las pueda usar
# sin arrastrar la dependencia de openpyxl que trae importar extract.py.
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

# Claves cortas del alérgeno público <- columna del Excel/Sheets.
MAPA_ALERGENOS = [
    ("veg", "Vegetariano"), ("vgn", "Vegano"), ("tacc", "Sin TACC"), ("lac", "Sin lactosa"),
    ("glu", "Contiene gluten"), ("lech", "Contiene leche"), ("huev", "Contiene huevo"),
    ("soja", "Contiene soja"), ("mani", "Contiene maní"), ("fsec", "Contiene frutos secos"),
    ("ses", "Contiene sésamo"), ("pesc", "Contiene pescado"), ("mar", "Contiene mariscos"),
    ("alc", "Contiene alcohol"), ("caf", "Contiene cafeína"),
]

# Valores de la columna "Disponibilidad hoy" -> código corto publicado.
# Ausente o "Disponible" (el default) no se publica -- un producto sin
# esta columna cargada se sigue mostrando normal, sin badge. "Inactivo"
# ya lo cubre la columna "Producto activo" (el producto ni aparece), así
# que acá solo hacen falta los estados intermedios. "Últimas porciones" es
# el único que no bloquea el pedido por WhatsApp -- el producto sigue
# disponible, solo avisa que queda poco (ver menu.js, dispBadge y el
# chequeo antes de mostrar el botón de WhatsApp).
DISPONIBILIDAD_VALORES = {
    "Agotado por hoy": "agotado",
    "No disponible temporalmente": "no_disp",
    "Últimas porciones": "ultimas",
}


def formatear_precio(chico, grande, cat_cod):
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


def equivalente(precio_ars, tasa, simbolo):
    """Convierte el precio de referencia (el chico/único, nunca el grande —
    para no saturar la tarjeta con cuatro números) a otra moneda, usando la
    tasa manual del maestro. Ninguna llamada externa: es la conversión fija
    del día que se publicó, no una cotización en vivo (ver README, sección
    de cabeceras de seguridad, para la razón: no queríamos abrir connect-src
    a un tercero por esto)."""
    if precio_ars in (None, "") or tasa in (None, "") or tasa == 0:
        return None
    valor = precio_ars / tasa
    return f"≈ {simbolo} {valor:,.0f}".replace(",", ".")


def moments_for(prod, overrides):
    temp = prod["temperatura"]
    formato = prod["formato"]
    cat_cod = prod["cat"]
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


def es_placeholder(valor):
    """Detecta placeholders obvios tipo 'XXXXXXXX' o 'ejemplo' que no deberían publicarse."""
    if valor in (None, ""):
        return False
    texto = str(valor).strip().lower()
    return "xxx" in texto or texto in ("ejemplo", "pendiente", "completar", "tbd", "n/a")


def host_permitido(host, dominios_permitidos):
    """True solo si `host` es exactamente uno de los dominios permitidos, o
    un subdominio real de alguno (termina en "." + dominio). Nunca una
    coincidencia parcial de texto: "google.com.ejemplo.com" o
    "tripadvisor.com.ar.ejemplo.com" contienen el nombre permitido como
    subcadena pero no son ese dominio ni un subdominio suyo, así que
    quedan afuera. Mismo criterio que build_site.py del prototipo
    institucional (_host_permitido)."""
    if not host:
        return False
    host = host.lower()
    for permitido in dominios_permitidos:
        permitido = permitido.lower()
        if host == permitido or host.endswith("." + permitido):
            return True
    return False


def url_https_valida(valor, dominios_permitidos=None):
    """Antes de publicar un link que viene del maestro como texto libre (no un
    handle ni un teléfono que ya sanitizamos con regex), lo validamos: solo
    https, sin usuario ni contraseña embebidos (nunca un
    "https://usuario:clave@host/..." ni un "https://algo@host/..." -- ni
    siquiera para compararlo, ver el motivo más abajo), sin un puerto
    distinto del 443 (ausente o explícitamente 443, cualquier otro se
    rechaza), y si se pasa una lista de dominios, el host (no el netloc
    completo) tiene que coincidir exactamente o ser un subdominio real de
    alguno de los permitidos -- nunca una coincidencia parcial de texto.
    Paths y query strings siguen totalmente permitidos (TripAdvisor y
    Google Reseñas los necesitan) -- esta función no los toca ni los
    valida, solo el esquema/host/usuario/puerto.

    Por qué rechazar usuario/contraseña en vez de solo ignorarlos como
    antes: aceptar "https://algo@host/..." como válido (mirando solo
    partes.hostname, que ya ignora esa parte) dejaba pasar una URL que un
    navegador real interpreta con esa porción como credenciales HTTP
    embebidas -- una forma de colar texto arbitrario (hasta un secreto)
    en una URL que de otro modo parece apuntar a un host confiable. Mejor
    rechazarla directamente que solo evitar que engañe al chequeo de host.

    Esto es una segunda capa además del escapado HTML en render.py — no
    confiamos en que la celda siempre tenga lo que se espera (podría
    pegarse mal, quedar a medio escribir, etc.), y un esquema no-https
    (`javascript:`, `data:`, ...) nunca debería llegar a un href
    publicado, más allá de que el CSP también lo bloquee."""
    if valor in (None, ""):
        return False
    texto = str(valor).strip()
    try:
        partes = urlsplit(texto)
        puerto = partes.port
    except ValueError:
        # urlsplit() y el acceso a .port pueden levantar ValueError con
        # texto malformado (ej. un puerto no numérico) -- nunca se
        # reproduce `texto` en la excepción ni en ningún lado de acá.
        return False
    if partes.scheme != "https" or not partes.hostname:
        return False
    if partes.username is not None or partes.password is not None:
        return False
    if puerto is not None and puerto != 443:
        return False
    if dominios_permitidos and not host_permitido(partes.hostname, dominios_permitidos):
        return False
    return True


def handle_instagram_sano(valor):
    """Los handles de Instagram son solo letras, números, punto y guion bajo.
    Cualquier otra cosa (comillas, ángulos, espacios) no es un handle válido
    y no debería terminar pegada sin escapar dentro de un href — se
    descarta en vez de intentar 'arreglarla'."""
    if valor in (None, ""):
        return None
    texto = str(valor).strip().lstrip("@")
    if not texto or not re.fullmatch(r"[A-Za-z0-9._]{1,30}", texto):
        return None
    return texto


def normalizar_whatsapp(valor):
    """La celda puede venir como número (Excel/Sheets la interpreta así si son
    solo dígitos) o como texto con espacios/guiones. Siempre devolvemos solo
    dígitos, o None."""
    if valor in (None, ""):
        return None
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    solo_digitos = re.sub(r"\D", "", str(valor))
    return solo_digitos or None


WHATSAPP_LONGITUD = re.compile(r"^[0-9]{8,15}$")


def whatsapp_valido(valor):
    """Normaliza y además exige 8 a 15 dígitos -- un número más corto o más
    largo no es un WhatsApp real utilizable y generaría un link wa.me roto;
    mejor publicarlo ausente que roto (mismo criterio que el resto de los
    campos de contacto acá)."""
    normalizado = normalizar_whatsapp(valor)
    if normalizado is None or not WHATSAPP_LONGITUD.match(normalizado):
        return None
    return normalizado


# Dominios explícitos y completos por campo -- nunca fragmentos como
# "tripadvisor." (ver host_permitido: exige coincidencia exacta o
# subdominio real, así que un fragmento sería además inútil acá).
DOMINIOS_MENU = ("ameli-casa-de-te-brunch.github.io",)
DOMINIOS_GOOGLE = ("google.com", "g.page")
DOMINIOS_TRIPADVISOR = ("tripadvisor.com", "tripadvisor.com.ar")
DOMINIOS_DISPONIBILIDAD = ("docs.google.com",)

# Dos orígenes válidos para "config.url_base" durante la transición a
# la arquitectura unificada (web + menú en un único artefacto de
# GitHub Pages, ver build_unificado.py en la raíz del repo):
#   - el nuevo, real: dominio propio con el menú bajo /menu/.
#   - el viejo: el repo separado de antes, como rollback rápido sin
#     depender de que la celda de Sheets ya esté actualizada.
# url_base_valida() más abajo exige coincidencia EXACTA de host (nunca
# un subdominio), a diferencia de host_permitido()/url_https_valida()
# (pensadas para permitir subdominios reales de TripAdvisor/Google).
DOMINIO_URL_BASE_NUEVO = "amelicasadete.com.ar"
RUTA_URL_BASE_NUEVO = "/menu"
DOMINIO_URL_BASE_VIEJO = "ameli-casa-de-te-brunch.github.io"


def url_base_valida(valor) -> bool:
    """Único campo que se usa como origen público del sitio (JSON-LD,
    canonical, sitemap, robots.txt -- ver render.py). Acepta EXACTAMENTE
    una de dos formas (con o sin "/" final): "https://amelicasadete.com.ar/menu"
    -- la arquitectura unificada real -- o "https://ameli-casa-de-te-brunch.github.io"
    -- rollback al repo separado. Rechaza explícitamente: http, cualquier
    otro host o path (ni siquiera un subdominio real cuenta acá),
    usuario/contraseña embebidos, cualquier puerto que no sea el 443
    (default de https), query string, fragmento, y esquemas peligrosos
    (javascript:, data:) o URLs malformadas -- estas últimas ya quedan
    afuera por el chequeo de esquema/por el try/except de más abajo."""
    if not isinstance(valor, str) or not valor:
        return False
    try:
        partes = urlsplit(valor)
        puerto = partes.port
    except ValueError:
        # urlsplit() y el acceso a .port pueden levantar ValueError con
        # texto malformado (ej. un puerto no numérico) -- eso ya es, en sí
        # mismo, una URL inválida para esta política.
        return False
    if partes.scheme != "https":
        return False
    if partes.username is not None or partes.password is not None:
        return False
    if puerto is not None and puerto != 443:
        return False
    if partes.query or partes.fragment:
        return False
    host = (partes.hostname or "").lower()
    if host == DOMINIO_URL_BASE_NUEVO:
        return partes.path in (RUTA_URL_BASE_NUEVO, RUTA_URL_BASE_NUEVO + "/")
    if host == DOMINIO_URL_BASE_VIEJO:
        return partes.path in ("", "/")
    return False


def sanear_config(params: dict) -> dict:
    """params: nombre de campo -> valor crudo (ya sea de la hoja Resumen y
    Configuración del Excel, o de la fila equivalente en Sheets). Aplica el
    mismo saneo/validación de links y handles sea cual sea el origen."""
    whatsapp = whatsapp_valido(params.get("WhatsApp de pedidos"))
    instagram = params.get("Instagram")
    direccion = params.get("Dirección")
    url_base = params.get("URL base del menú")
    tripadvisor = params.get("TripAdvisor")
    google_resenas = params.get("Google (reseñas)")
    disponibilidad_csv_url = params.get("URL de disponibilidad (Google Sheets)")

    if es_placeholder(whatsapp) or es_placeholder(params.get("WhatsApp de pedidos")):
        whatsapp = None
    if es_placeholder(instagram):
        instagram = None
    if es_placeholder(direccion):
        direccion = None
    if es_placeholder(url_base):
        url_base = None
    if es_placeholder(tripadvisor):
        tripadvisor = None
    if es_placeholder(google_resenas):
        google_resenas = None
    if es_placeholder(disponibilidad_csv_url):
        disponibilidad_csv_url = None

    instagram = handle_instagram_sano(instagram)
    if not url_base_valida(url_base):
        url_base = None
    if not url_https_valida(tripadvisor, DOMINIOS_TRIPADVISOR):
        tripadvisor = None
    if not url_https_valida(google_resenas, DOMINIOS_GOOGLE):
        google_resenas = None
    if not url_https_valida(disponibilidad_csv_url, DOMINIOS_DISPONIBILIDAD):
        disponibilidad_csv_url = None

    tasa_usd = params.get("Tipo de cambio ARS/USD")
    tasa_eur = params.get("Tipo de cambio ARS/EUR")
    tasa_brl = params.get("Real")

    return {
        "moneda": params.get("Moneda local") or "ARS",
        "whatsapp": whatsapp,
        "instagram": instagram,
        "direccion": direccion,
        "url_base": url_base,
        "tripadvisor": tripadvisor,
        "google_resenas": google_resenas,
        # Solo para build.py (aplicar_disponibilidad.py) -- nunca sale al
        # HTML/JSON público, no está en CAMPOS_CONFIG_PUBLICOS.
        "disponibilidad_csv_url": disponibilidad_csv_url,
        "tasa_usd": tasa_usd if isinstance(tasa_usd, (int, float)) else None,
        "tasa_eur": tasa_eur if isinstance(tasa_eur, (int, float)) else None,
        "tasa_brl": tasa_brl if isinstance(tasa_brl, (int, float)) else None,
    }


def ensamblar(productos: dict, cats: list, config: dict, overrides: dict) -> dict:
    """productos: id -> dict crudo (misma forma que arma load_productos() en
    extract.py y extract_sheets.py). cats: lista de dicts (cod/orden/visible/nom).
    config: dict ya saneado (sanear_config()). overrides: {"extra": {...}} de
    overrides_momentos.json. Arma el mismo `data` que consume render.py,
    sin importar si productos/cats vinieron del Excel o de Sheets."""
    prods = []
    precios = {}
    meta = {}
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
            entrada = {"ars": prod["precio"]}
            usd = equivalente(prod["precio_chico_ars"], config["tasa_usd"], "USD")
            eur = equivalente(prod["precio_chico_ars"], config["tasa_eur"], "EUR")
            brl = equivalente(prod["precio_chico_ars"], config["tasa_brl"], "R$")
            if usd:
                entrada["usd"] = usd
            if eur:
                entrada["eur"] = eur
            if brl:
                entrada["brl"] = brl
            precios[prod_id] = entrada
        item = {
            "id": prod_id,
            "cat": prod["cat"],
            "orden": prod["orden"],
            "dest": prod["destacado"],
            "n": prod["n"],
            "d": prod["d"],
            "m": m,
            "b": badges_for(prod),
            "img": prod["img"],
        }
        if any(prod["alt"].values()):
            item["alt"] = prod["alt"]
        if prod["alerg"] is not None:
            item["alerg"] = prod["alerg"]
        if prod["tag"]:
            item["tag"] = prod["tag"]
        if prod["leche"]:
            item["leche"] = prod["leche"]
        if prod["disp"]:
            item["disp"] = prod["disp"]
        prods.append(item)
    prods.sort(key=lambda p: (next(c["orden"] for c in cats if c["cod"] == p["cat"]), p["orden"]))

    cats_out = [{"cod": c["cod"], "orden": c["orden"], "nom": c["nom"]} for c in cats if c["visible"]]

    return {
        "cats": cats_out,
        "prods": prods,
        "precios": precios,
        "config": config,
        "_meta": meta,
    }


# Campos que SÍ salen al sitio público. "alerg" solo aparece en un producto
# si su fila individual está validada — el resto (costos, ingredientes,
# personalización, notas operativas, fila de origen) se queda afuera de lo
# que se versiona y se publica.
CAMPOS_PROD_PUBLICOS = ("id", "cat", "orden", "dest", "n", "d", "m", "b", "img", "alt", "alerg", "tag", "leche", "disp")
CAMPOS_CONFIG_PUBLICOS = ("moneda", "whatsapp", "instagram", "direccion", "url_base", "tripadvisor", "google_resenas")


def datos_publicos(data: dict) -> dict:
    """Proyección de ensamblar() con solo lo que un visitante del menú necesita
    ver. Esto es lo que se escribe a disco y se versiona — nunca el dict
    completo (que trae _meta: filas de origen, útiles solo para que
    validate.py arme sus mensajes en el mismo proceso)."""
    return {
        "cats": data["cats"],
        "prods": [{k: p[k] for k in CAMPOS_PROD_PUBLICOS if k in p} for p in data["prods"]],
        "precios": data["precios"],
        "config": {k: data["config"].get(k) for k in CAMPOS_CONFIG_PUBLICOS},
    }
