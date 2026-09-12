#!/usr/bin/env python3
"""site.config.json + templates/*.html -> dist/

Genera la salida pública en `dist/` — el único directorio que debería
servirse o publicarse. Nada fuera de `dist/` (código fuente, config,
docs, `.git`) debe llegar nunca a un hosting público.

Dos modos, siempre explícitos:

    python build_site.py                 # preview (por defecto)
    python build_site.py --production    # producción

`preview` nunca genera nada indexable por accidente: robots noindex
siempre, sin canonical, sin sitemap.xml. `--production` es la única
forma de obtener canonical + robots indexable + sitemap.xml, y exige
que `site_url` esté presente y sea válido en `site.config.json` — si
falta o es inválido, el build falla antes de escribir nada.

El build entero se arma primero en un directorio de staging temporal
(`.build-tmp-<pid>/`, ignorado por git) y solo reemplaza `dist/` si:
  1. la validación de `site.config.json` pasó completa, y
  2. el contenido armado pasa la allowlist de `dist/` (sin .py, sin
     .json, sin .md, sin `__pycache__`, sin `.git`, sin nada que no
     esté explícitamente permitido).
Si cualquiera de los dos falla, `dist/` (si ya existía) queda
exactamente como estaba, sin tocarlo.

El reemplazo en sí aparta primero el `dist/` anterior a un respaldo con
nombre único (nunca sobrescribe uno existente) antes de mover el
staging a `dist/`; si ese segundo paso falla, restaura el respaldo
automáticamente. Esto reduce la ventana en la que `dist/` podría quedar
ausente a los dos `rename()` en sí (normalmente casi instantáneos en el
mismo volumen) -- **no es una garantía de atomicidad frente a un corte
de energía exactamente entre esos dos pasos**; eso requeriría una capa
adicional (por ejemplo, un symlink que se reapunta) que este script no
implementa. Si hay un respaldo de una corrida anterior sin resolver
(`.dist-respaldo-*`), el build se niega a continuar hasta que se
revise a mano -- nunca lo pisa ni lo borra solo.

index.html es un archivo GENERADO -- no se edita a mano. Para cambiar
contenido: editar site.config.json (datos) o
templates/index.template.html (estructura/copy fija), y volver a
correr este script.
"""
import argparse
import html
import json
import os
import re
import shutil
import tempfile
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "site.config.json"
TEMPLATE_INDEX_PATH = HERE / "templates" / "index.template.html"
TEMPLATE_404_PATH = HERE / "templates" / "404.template.html"
ASSETS_SRC = HERE / "assets"
DIST_PATH = HERE / "dist"

# Dominios permitidos por campo -- hosts explícitos y completos (nunca
# fragmentos como "tripadvisor."). Esquema https obligatorio, y el host
# tiene que coincidir exactamente con alguno de estos o ser un
# subdominio real (ver _host_permitido).
DOMINIOS_MENU = ("ameli-casa-de-te-brunch.github.io",)
DOMINIOS_GOOGLE = ("google.com", "g.page")
DOMINIOS_TRIPADVISOR = ("tripadvisor.com", "tripadvisor.com.ar")

# Único dominio válido para site_url -- el que ya está verificado en
# GitHub para Pages. Política mucho más estricta que _url_https_valida,
# igual que url_base_valida() en build/extract_common.py del repo del
# menú: exige el origen exacto, sin path más allá de "/".
DOMINIO_SITIO = "amelicasadete.com.ar"

# Extensiones y rutas permitidas dentro de dist/. Cualquier archivo que
# no calce con esto hace fallar el build antes de reemplazar dist/ --
# ver _verificar_allowlist_dist().
ARCHIVOS_RAIZ_PERMITIDOS = {"index.html", "404.html", "robots.txt", "sitemap.xml"}
EXTENSIONES_ASSETS_PERMITIDAS = {
    "assets/css": {".css"},
    "assets/js": {".js"},
    "assets/fonts": {".woff2", ".txt"},  # .txt: licencias OFL, exigidas por la licencia de cada fuente
    "assets/img": {".png", ".webp", ".svg", ".ico"},
}

TRUNCADO_LIMITE = 60


def _truncar(valor) -> str:
    """No reproducir un valor completo y no confiable en un mensaje de
    error o log -- ver _url_https_valida más abajo. Se usa específicamente
    para valores tipo URL, nunca para texto de marca/copy (que es del
    dueño, no un dato potencialmente hostil)."""
    texto = str(valor)
    if len(texto) <= TRUNCADO_LIMITE:
        return repr(texto)
    return repr(texto[:TRUNCADO_LIMITE] + "...(truncado)")


def _host_permitido(host, dominios_permitidos):
    """True solo si `host` es exactamente uno de los dominios permitidos,
    o un subdominio real de alguno (termina en "." + dominio). Nunca una
    coincidencia parcial de texto: "google.com.ejemplo.com" o
    "tripadvisor.com.ar.ejemplo.com" contienen el nombre permitido como
    subcadena pero no son ese dominio ni un subdominio suyo, así que
    quedan afuera. Mismo criterio que build/extract_common.py del repo
    del menú (host_permitido)."""
    if not host:
        return False
    host = host.lower()
    for permitido in dominios_permitidos:
        permitido = permitido.lower()
        if host == permitido or host.endswith("." + permitido):
            return True
    return False


def _url_https_valida(valor, dominios_permitidos):
    """Misma política que build/extract_common.py::url_https_valida del
    repo del menú: solo https, sin usuario ni contraseña embebidos
    (nunca un "https://usuario:clave@host/..." ni "https://algo@host/...",
    ni siquiera para compararlos -- un navegador real interpreta esa
    porción como credenciales HTTP, una forma de colar texto arbitrario
    en una URL que de otro modo parece confiable), sin un puerto
    distinto del 443 (ausente o explícitamente 443 se acepta, cualquier
    otro se rechaza), y el host (no el netloc completo) tiene que
    coincidir exactamente o ser un subdominio real de alguno de los
    dominios permitidos. Paths y query strings siguen permitidos
    (TripAdvisor y Google Reseñas los necesitan)."""
    if valor in (None, ""):
        return False
    if not isinstance(valor, str):
        return False
    try:
        partes = urllib.parse.urlsplit(valor)
        puerto = partes.port
    except ValueError:
        # urlsplit() y el acceso a .port pueden levantar ValueError con
        # texto malformado (ej. un puerto no numérico) -- nunca se
        # reproduce `valor` completo en ningún mensaje.
        return False
    if partes.scheme != "https" or not partes.hostname:
        return False
    if partes.username is not None or partes.password is not None:
        return False
    if puerto is not None and puerto != 443:
        return False
    return _host_permitido(partes.hostname, dominios_permitidos)


def _site_url_valida(valor):
    """Política mucho más estricta que _url_https_valida, solo para
    site_url (el origen público real del sitio, usado en canonical,
    robots.txt y sitemap.xml): tiene que ser exactamente
    "https://amelicasadete.com.ar", opcionalmente con una "/" final, y
    nada más. Rechaza explícitamente: http, cualquier otro host (ni
    siquiera un subdominio real cuenta acá), usuario/contraseña
    embebidos, cualquier puerto que no sea 443, cualquier path que no
    sea "/", query string, fragmento, y esquemas peligrosos o URLs
    malformadas. Mismo criterio que url_base_valida() en
    build/extract_common.py del repo del menú."""
    if not isinstance(valor, str) or not valor:
        return False
    try:
        partes = urllib.parse.urlsplit(valor)
        puerto = partes.port
    except ValueError:
        return False
    if partes.scheme != "https":
        return False
    if (partes.hostname or "").lower() != DOMINIO_SITIO:
        return False
    if partes.username is not None or partes.password is not None:
        return False
    if puerto is not None and puerto != 443:
        return False
    if partes.path not in ("", "/"):
        return False
    if partes.query or partes.fragment:
        return False
    return True


def _site_url_normalizada(valor: str) -> str:
    """https://amelicasadete.com.ar -> https://amelicasadete.com.ar/ --
    para usar siempre con "/" final en canonical/sitemap/robots. Solo se
    llama con un valor ya validado por _site_url_valida."""
    return valor if valor.endswith("/") else valor + "/"


# Ruta interna permitida para menu_url -- desde la unificación en un
# único artefacto de GitHub Pages (ver build_unificado.py en la raíz
# del repo), el menú ya no es un dominio externo: vive bajo /menu/ del
# mismo origen. RUTA_MENU_INTERNA es la única ruta interna aceptada
# hoy -- no una allowlist abierta a cualquier ruta -- para no aceptar
# por accidente algo como "/admin/" si algún día ese literal cambiara
# de sentido.
RUTA_MENU_INTERNA = "/menu/"


def _ruta_interna_valida(valor) -> bool:
    """True solo para RUTA_MENU_INTERNA exacta: sin esquema, sin host,
    empieza y termina en "/", sin "..", sin query ni fragmento. Rechaza
    cualquier otra ruta relativa -- esto no es una allowlist general de
    rutas del sitio, es la validación de un único valor esperado."""
    return valor == RUTA_MENU_INTERNA


def _menu_url_valida(valor) -> bool:
    """menu_url acepta DOS formas válidas a propósito, durante la
    transición: la ruta interna nueva (/menu/, ver RUTA_MENU_INTERNA)
    o -- como red de seguridad para un rollback rápido sin tocar código,
    ver INFORME -- la URL externa del repo separado que se usaba antes
    de unificar (https://ameli-casa-de-te-brunch.github.io/). Cualquier
    otro valor se rechaza."""
    if _ruta_interna_valida(valor):
        return True
    return _url_https_valida(valor, DOMINIOS_MENU)


def _campo_texto_valido(config: dict, campo: str, maximo: int, obligatorio: bool = True) -> list:
    """Validación genérica de presencia/tipo/longitud para campos de
    texto plano (no URLs, no regex especiales). No trunca el valor en el
    mensaje -- son campos de copy del propio dueño, no datos externos ni
    potencialmente hostiles."""
    valor = config.get(campo)
    if valor in (None, "") and not obligatorio:
        return []
    if not isinstance(valor, str) or not valor.strip():
        return [f"{campo}: tiene que ser texto no vacío -- valor actual: {valor!r}"]
    if len(valor) > maximo:
        return [f"{campo}: no puede superar {maximo} caracteres (tiene {len(valor)})"]
    return []


def validar_config(config: dict, requiere_site_url: bool) -> list:
    """Devuelve una lista de errores (vacía si todo está bien). No
    depende únicamente de la CSP como defensa -- esto corre en el build,
    antes de que se escriba nada. `requiere_site_url`: True en modo
    producción (--production) -- ahí site_url es obligatorio y tiene que
    pasar _site_url_valida; en preview es opcional, pero si está
    presente igual tiene que ser válido (nunca se acepta basura ahí)."""
    errores = []

    errores += _campo_texto_valido(config, "marca", 80)
    errores += _campo_texto_valido(config, "categoria", 120)
    errores += _campo_texto_valido(config, "ubicacion_corta", 120)
    errores += _campo_texto_valido(config, "ubicacion_completa", 200)
    errores += _campo_texto_valido(config, "direccion_calle", 200)
    errores += _campo_texto_valido(config, "tagline", 200)
    errores += _campo_texto_valido(config, "descripcion_menu_confirmada", 300)
    errores += _campo_texto_valido(config, "horarios", 500, obligatorio=False)

    if not _menu_url_valida(config.get("menu_url")):
        errores.append(
            f"menu_url: tiene que ser exactamente la ruta interna {RUTA_MENU_INTERNA!r} "
            f"(arquitectura unificada) o, como rollback, una URL https a un dominio "
            f"permitido del menú {DOMINIOS_MENU} -- valor actual: "
            f"{_truncar(config.get('menu_url'))}"
        )
    if not _url_https_valida(config.get("google_reviews_url"), DOMINIOS_GOOGLE):
        errores.append(
            "google_reviews_url: tiene que ser https y un host de Google "
            f"{DOMINIOS_GOOGLE} -- valor actual: {_truncar(config.get('google_reviews_url'))}"
        )
    if not _url_https_valida(config.get("tripadvisor_url"), DOMINIOS_TRIPADVISOR):
        errores.append(
            "tripadvisor_url: tiene que ser https y un host de TripAdvisor -- "
            f"valor actual: {_truncar(config.get('tripadvisor_url'))}"
        )

    whatsapp = config.get("whatsapp_e164")
    if not isinstance(whatsapp, str) or not re.fullmatch(r"[0-9]{8,15}", whatsapp):
        errores.append(
            "whatsapp_e164: solo dígitos, entre 8 y 15 -- "
            f"valor actual: {whatsapp!r}"
        )

    instagram = config.get("instagram_handle")
    if not isinstance(instagram, str) or not re.fullmatch(r"[A-Za-z0-9._]{1,30}", instagram):
        errores.append(
            "instagram_handle: solo letras, números, punto o guion bajo, hasta "
            f"30 caracteres -- valor actual: {instagram!r}"
        )

    maps_query = config.get("maps_query")
    if not isinstance(maps_query, str) or not (1 <= len(maps_query) <= 200):
        errores.append("maps_query: tiene que ser texto no vacío, hasta 200 caracteres")

    sobre_ameli = config.get("presentacion_sobre_ameli")
    if sobre_ameli is not None:
        if not isinstance(sobre_ameli, str):
            errores.append("presentacion_sobre_ameli: tiene que ser texto o null")
        elif len(sobre_ameli) > 2000:
            errores.append("presentacion_sobre_ameli: no puede superar 2000 caracteres")

    # Datos legales del pie -- ver anexo de cumplimiento: publicarlos sin
    # confirmación de contador/asesor legal está desaconsejado, así que
    # ninguno tiene un valor por defecto y el build no obliga a
    # completarlos. Lo que sí exige: si se completa alguno de los tres
    # que forman la identidad fiscal (razón social/CUIT/domicilio), hay
    # que completar los tres -- un dato fiscal parcial en el pie es peor
    # que no mostrar nada.
    errores += _campo_texto_valido(config, "razon_social", 200, obligatorio=False)
    errores += _campo_texto_valido(config, "domicilio_comercial", 300, obligatorio=False)
    errores += _campo_texto_valido(config, "aviso_copyright", 300, obligatorio=False)
    errores += _campo_texto_valido(config, "informacion_servicio", 2000, obligatorio=False)
    errores += _campo_texto_valido(config, "pasteleria_pedidos_texto", 2000, obligatorio=False)
    errores += _campo_texto_valido(config, "la_experiencia_texto", 2000, obligatorio=False)
    errores += _campo_texto_valido(config, "preguntas_frecuentes_texto", 4000, obligatorio=False)

    cuit = config.get("cuit")
    if cuit is not None:
        if not isinstance(cuit, str) or not re.fullmatch(r"\d{2}-\d{8}-\d{1}", cuit):
            errores.append(
                "cuit: tiene que ser texto con formato XX-XXXXXXXX-X o null -- "
                f"valor actual: {cuit!r}"
            )

    campos_identidad_fiscal = ("razon_social", "cuit", "domicilio_comercial")
    presentes = [
        campo for campo in campos_identidad_fiscal
        if isinstance(config.get(campo), str) and config.get(campo).strip()
    ]
    if presentes and len(presentes) < len(campos_identidad_fiscal):
        faltantes = [c for c in campos_identidad_fiscal if c not in presentes]
        errores.append(
            "razon_social/cuit/domicilio_comercial: se completaron "
            f"{presentes} pero no {faltantes} -- si se publica uno de los "
            "tres hay que publicar los tres juntos, nunca un dato fiscal parcial"
        )

    site_url = config.get("site_url")
    if site_url not in (None, ""):
        if not _site_url_valida(site_url):
            errores.append(
                "site_url: tiene que ser exactamente https://" + DOMINIO_SITIO +
                " (con o sin '/' final, sin path/query/fragmento/usuario/puerto) -- "
                f"valor actual: {_truncar(site_url)}"
            )
    elif requiere_site_url:
        errores.append(
            "site_url: obligatorio en modo producción (--production) y falta en "
            "site.config.json"
        )

    return errores


def _bloque(texto: str, marcador: str, mantener: bool) -> str:
    """Un bloque delimitado por <!--X_START--> y <!--X_END--> se
    conserva (sacando solo los comentarios) si `mantener` es verdadero,
    o se elimina por completo (comentarios y contenido) si es falso.
    Mismo criterio que build/render.py del repo del menú."""
    patron = re.compile(
        r"<!--" + marcador + r"_START-->(.*?)<!--" + marcador + r"_END-->",
        re.S,
    )
    if mantener:
        return patron.sub(lambda m: m.group(1), texto)
    return patron.sub("", texto)


def _parrafos_html(texto: str, clase: str) -> str:
    """Texto plano de config.json con párrafos separados por una línea
    en blanco (\\n\\n) -> una etiqueta <p class="clase"> por párrafo,
    cada una con su propio html.escape(). Evita que un texto largo
    real (como "Sobre Amelí") termine como un único bloque gigante sin
    estructura semántica para un lector de pantalla -- cada idea
    completa es su propio párrafo, no una línea suelta dentro de uno
    solo. Párrafos vacíos (líneas en blanco de más) se descartan."""
    partes = [p.strip() for p in texto.split("\n\n")]
    partes = [p for p in partes if p]
    return "\n    ".join(f'<p class="{clase}">{html.escape(p)}</p>' for p in partes)


def _escanear_placeholders_restantes(html_generado: str) -> list:
    """Escaneo genérico -- no solo los marcadores que este script conoce
    de antemano. Si el template gana un __PLACEHOLDER__ nuevo y se
    olvida agregarlo al diccionario de reemplazos, esto tiene que hacer
    fallar el build, no publicar un "__ALGO__" literal."""
    return sorted(set(re.findall(r"__[A-Z_]+__", html_generado)))


def renderizar_index(config: dict, produccion: bool) -> str:
    plantilla = TEMPLATE_INDEX_PATH.read_text(encoding="utf-8")

    sobre_ameli = config.get("presentacion_sobre_ameli")
    tiene_sobre_ameli = isinstance(sobre_ameli, str) and sobre_ameli.strip() != ""
    plantilla = _bloque(plantilla, "SOBRE_AMELI", tiene_sobre_ameli)

    # "Servicios Amelí" -- BORRADOR de diseño/contenido (nombres, alcance
    # y textos todavía sin confirmar con Ignacio, ver comentario en el
    # propio template). Oculta por defecto: solo se muestra si
    # servicios_habilitado es exactamente true en site.config.json (no
    # "truthy" genérico), para que activarla sea una decisión explícita y
    # no un efecto secundario de cualquier valor no vacío. El HTML/CSS ya
    # preparado no se borra -- mismo mecanismo null-gated que los demás
    # bloques opcionales de esta función.
    tiene_servicios = config.get("servicios_habilitado") is True
    plantilla = _bloque(plantilla, "SERVICIOS", tiene_servicios)

    # Datos legales del pie -- ver comentario en validar_config(): solo
    # se genera si los tres campos de identidad fiscal están completos
    # a la vez (nunca un dato fiscal parcial).
    razon_social = config.get("razon_social")
    cuit = config.get("cuit")
    domicilio_comercial = config.get("domicilio_comercial")
    tiene_datos_legales = (
        isinstance(razon_social, str) and razon_social.strip()
        and isinstance(cuit, str) and cuit.strip()
        and isinstance(domicilio_comercial, str) and domicilio_comercial.strip()
    )
    plantilla = _bloque(plantilla, "DATOS_LEGALES", bool(tiene_datos_legales))

    aviso_copyright = config.get("aviso_copyright")
    tiene_copyright = isinstance(aviso_copyright, str) and aviso_copyright.strip() != ""
    plantilla = _bloque(plantilla, "COPYRIGHT", tiene_copyright)

    # "Información del servicio" (reglas de la casa) -- a propósito NO
    # "Términos y Condiciones" ni "derecho de admisión digital": el
    # anexo de cumplimiento dice que esto último no es una obligación
    # demostrada y pide encuadrarlo como información objetiva del
    # servicio, con redacción aprobada por Ignacio.
    informacion_servicio = config.get("informacion_servicio")
    tiene_info_servicio = isinstance(informacion_servicio, str) and informacion_servicio.strip() != ""
    plantilla = _bloque(plantilla, "INFO_SERVICIO", tiene_info_servicio)

    # Horario de atención -- confirmado por Ignacio para esta web
    # institucional específicamente (no toca la fuente del repo del
    # menú). Opcional/ausente igual que los bloques de arriba, por si
    # en el futuro hay que sacarlo temporalmente (por ejemplo, mientras
    # se actualiza) sin tocar el template.
    horarios = config.get("horarios")
    tiene_horarios = isinstance(horarios, str) and horarios.strip() != ""
    plantilla = _bloque(plantilla, "HORARIOS", tiene_horarios)

    # Tres secciones pedidas para el cierre de la etapa funcional
    # (2026-09-11) sin texto real todavía -- mismo mecanismo null-gated
    # que los bloques de arriba. Ver informe: no se inventó contenido.
    pasteleria_pedidos = config.get("pasteleria_pedidos_texto")
    tiene_pasteleria_pedidos = isinstance(pasteleria_pedidos, str) and pasteleria_pedidos.strip() != ""
    plantilla = _bloque(plantilla, "PASTELERIA_PEDIDOS", tiene_pasteleria_pedidos)

    la_experiencia = config.get("la_experiencia_texto")
    tiene_la_experiencia = isinstance(la_experiencia, str) and la_experiencia.strip() != ""
    plantilla = _bloque(plantilla, "LA_EXPERIENCIA", tiene_la_experiencia)

    preguntas_frecuentes = config.get("preguntas_frecuentes_texto")
    tiene_preguntas_frecuentes = isinstance(preguntas_frecuentes, str) and preguntas_frecuentes.strip() != ""
    plantilla = _bloque(plantilla, "PREGUNTAS_FRECUENTES", tiene_preguntas_frecuentes)

    if produccion:
        robots_tag = '<meta name="robots" content="index, follow">'
        site_url = _site_url_normalizada(config["site_url"])
        canonical_tag = f'<link rel="canonical" href="{html.escape(site_url)}">'
        titulo_social = html.escape(
            f'{config["marca"]} {config["categoria"]} — {config["ubicacion_corta"]}'
        )
        descripcion_social = html.escape(
            f'{config["marca"]} {config["categoria"]} en '
            f'{config["ubicacion_corta"]}. {config["descripcion_menu_confirmada"]}'
        )
        url_social = html.escape(site_url)
        # Metadatos de texto para compartir. No se declara og:image:
        # todavía no existe una pieza social aprobada y nunca se usa una
        # imagen genérica o improvisada como sustituto.
        social_meta_tags = (
            '<meta property="og:type" content="website">\n'
            '<meta property="og:locale" content="es_AR">\n'
            f'<meta property="og:title" content="{titulo_social}">\n'
            f'<meta property="og:description" content="{descripcion_social}">\n'
            f'<meta property="og:url" content="{url_social}">\n'
            '<meta name="twitter:card" content="summary">\n'
            f'<meta name="twitter:title" content="{titulo_social}">\n'
            f'<meta name="twitter:description" content="{descripcion_social}">'
        )
    else:
        robots_tag = '<meta name="robots" content="noindex, nofollow"><!-- preview: nunca indexable -->'
        canonical_tag = ""
        social_meta_tags = ""

    reemplazos = {
        "__MARCA__": config["marca"],
        "__CATEGORIA__": config["categoria"],
        "__UBICACION_CORTA__": config["ubicacion_corta"],
        "__UBICACION_COMPLETA__": config["ubicacion_completa"],
        "__DIRECCION_CALLE__": config["direccion_calle"],
        "__TAGLINE__": config["tagline"],
        "__DESCRIPCION_MENU__": config["descripcion_menu_confirmada"],
        "__MENU_URL__": config["menu_url"],
        "__WHATSAPP_E164__": config["whatsapp_e164"],
        "__INSTAGRAM_HANDLE__": config["instagram_handle"],
        "__GOOGLE_REVIEWS_URL__": config["google_reviews_url"],
        "__TRIPADVISOR_URL__": config["tripadvisor_url"],
        "__MAPS_URL__": (
            "https://www.google.com/maps/search/?api=1&query="
            + urllib.parse.quote(config["maps_query"])
        ),
    }
    if tiene_datos_legales:
        reemplazos["__RAZON_SOCIAL__"] = razon_social
        reemplazos["__CUIT__"] = cuit
        reemplazos["__DOMICILIO_COMERCIAL__"] = domicilio_comercial
    if tiene_copyright:
        reemplazos["__AVISO_COPYRIGHT__"] = aviso_copyright
    if tiene_info_servicio:
        reemplazos["__INFORMACION_SERVICIO__"] = informacion_servicio
    if tiene_horarios:
        # Sigue el loop genérico de html.escape() de abajo -- el propio
        # valor lleva saltos de línea reales (\n) que html.escape() no
        # toca (solo escapa <>&"'), y que site.css preserva como saltos
        # visuales con white-space:pre-line en .horario-detalle.
        reemplazos["__HORARIOS__"] = horarios
    if tiene_pasteleria_pedidos:
        reemplazos["__PASTELERIA_PEDIDOS_TEXTO__"] = pasteleria_pedidos
    if tiene_la_experiencia:
        reemplazos["__LA_EXPERIENCIA_TEXTO__"] = la_experiencia
    if tiene_preguntas_frecuentes:
        reemplazos["__PREGUNTAS_FRECUENTES_TEXTO__"] = preguntas_frecuentes

    salida = plantilla
    for marcador, valor in reemplazos.items():
        if marcador == "__MAPS_URL__":
            salida = salida.replace(marcador, valor)  # ya es una URL, no re-escapar
        else:
            salida = salida.replace(marcador, html.escape(str(valor)))

    # __ROBOTS_META_TAG__ / __CANONICAL_TAG__ / __SOCIAL_META_TAGS__ se
    # resuelven aparte -- no pasan por html.escape porque ya son HTML
    # armado acá arriba, no texto plano de config.
    salida = salida.replace("__ROBOTS_META_TAG__", robots_tag)
    salida = salida.replace("__CANONICAL_TAG__", canonical_tag)
    salida = salida.replace("__SOCIAL_META_TAGS__", social_meta_tags)

    # __SOBRE_AMELI_TEXTO__ también se resuelve aparte -- a diferencia
    # de los demás campos de texto, acá SÍ queremos un <p> por párrafo
    # real (separados por línea en blanco en config.json), así que
    # _parrafos_html() ya devuelve HTML armado (con su propio
    # html.escape() por párrafo adentro) en vez de una sola cadena para
    # el loop genérico de arriba.
    if tiene_sobre_ameli:
        salida = salida.replace(
            "__SOBRE_AMELI_TEXTO__", _parrafos_html(sobre_ameli, "texto-editorial"))

    quedan = _escanear_placeholders_restantes(salida)
    if quedan:
        raise SystemExit(f"Quedaron marcadores sin reemplazar en index.html: {quedan}")

    return salida


def renderizar_404(config: dict) -> str:
    """404 siempre noindex, sin importar el modo -- una página de error
    nunca debe indexarse. Usa la identidad visual ya existente (mismo
    site.css, mismo logo) y permite volver al inicio."""
    plantilla = TEMPLATE_404_PATH.read_text(encoding="utf-8")
    reemplazos = {
        "__MARCA__": config["marca"],
        "__CATEGORIA__": config["categoria"],
    }
    salida = plantilla
    for marcador, valor in reemplazos.items():
        salida = salida.replace(marcador, html.escape(str(valor)))

    quedan = _escanear_placeholders_restantes(salida)
    if quedan:
        raise SystemExit(f"Quedaron marcadores sin reemplazar en 404.html: {quedan}")

    return salida


def renderizar_robots_txt(produccion: bool, config: dict) -> str:
    if not produccion:
        return "User-agent: *\nDisallow: /\n"
    site_url = _site_url_normalizada(config["site_url"])
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "\n"
        f"Sitemap: {site_url}sitemap.xml\n"
    )


def renderizar_sitemap_xml(config: dict) -> str:
    """Solo se llama en modo producción (site_url ya validado). Un único
    URL: la portada -- este prototipo es una sola página."""
    site_url = _site_url_normalizada(config["site_url"])
    loc = html.escape(site_url)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        "  <url>\n"
        f"    <loc>{loc}</loc>\n"
        "  </url>\n"
        "</urlset>\n"
    )


def _copiar_assets(staging: Path) -> None:
    for subcarpeta in ("css", "js", "fonts", "img"):
        origen = ASSETS_SRC / subcarpeta
        if not origen.is_dir():
            continue
        destino = staging / "assets" / subcarpeta
        destino.mkdir(parents=True, exist_ok=True)
        for archivo in origen.iterdir():
            if archivo.is_file():
                shutil.copy2(archivo, destino / archivo.name)


def _verificar_allowlist_dist(staging: Path) -> list:
    """Recorre todo lo armado en el staging y confirma que cada archivo
    calza con la allowlist explícita -- nunca confía únicamente en que
    el código de arriba "debería" haber generado solo cosas seguras.
    Devuelve la lista de violaciones (vacía si todo bien)."""
    violaciones = []
    for ruta in sorted(staging.rglob("*")):
        if ruta.is_dir():
            continue
        relativa = ruta.relative_to(staging).as_posix()

        if relativa in ARCHIVOS_RAIZ_PERMITIDOS:
            continue

        permitido = False
        for prefijo, extensiones in EXTENSIONES_ASSETS_PERMITIDAS.items():
            if relativa.startswith(prefijo + "/") and ruta.suffix.lower() in extensiones:
                permitido = True
                break

        if not permitido:
            violaciones.append(relativa)

    return violaciones


def _respaldos_residuales() -> list:
    """Cualquier `.dist-respaldo-*` que haya quedado de una corrida
    anterior sin terminar de resolver. Si hay alguno, el build no debe
    ni empezar -- podría ser evidencia de un fallo previo que todavía no
    se revisó a mano."""
    return sorted(HERE.glob(".dist-respaldo-*"))


def _nombre_respaldo_libre() -> Path:
    """Nombre único para el respaldo de dist/ -- nunca reutiliza ni
    sobrescribe uno existente. Vive en HERE, el mismo volumen que
    dist/, para que renombrarlo sea una operación de metadatos y no una
    copia entre discos distintos."""
    pid = os.getpid()
    intento = 0
    while True:
        candidato = HERE / f".dist-respaldo-{pid}-{intento}"
        if not candidato.exists():
            return candidato
        intento += 1


def _renombrar(origen: Path, destino: Path) -> None:
    """Envoltorio fino sobre Path.rename(). Existe únicamente para que
    las pruebas puedan simular un fallo puntual en un rename específico
    de forma determinista -- forzar un fallo real de sistema de
    archivos (permisos, disco lleno) de manera portable y repetible no
    es práctico."""
    origen.rename(destino)


def construir(produccion: bool) -> dict:
    """Arma todo en un directorio de staging temporal, valida la
    allowlist, y solo entonces reemplaza dist/. Devuelve un resumen
    (nunca valores de config sensibles -- acá no hay ninguno, pero se
    mantiene el hábito).

    Si la validación o la allowlist fallan, dist/ (si ya existía) queda
    intacto y el staging se limpia. Si el swap sobre dist/ en sí falla,
    ver el docstring del módulo -- se intenta restaurar automáticamente
    el respaldo, y si eso también falla, no se borra nada: el mensaje de
    error deja las rutas exactas para resolver a mano."""
    residuales = _respaldos_residuales()
    if residuales:
        raise SystemExit(
            "Hay respaldo(s) de dist/ de una corrida anterior sin resolver -- no "
            "se construye nada hasta revisarlos a mano: "
            + ", ".join(str(p) for p in residuales)
        )

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    errores = validar_config(config, requiere_site_url=produccion)
    if errores:
        mensaje = "\n".join(f"  - {e}" for e in errores)
        raise SystemExit(f"site.config.json no pasó la validación, no se generó nada:\n{mensaje}")

    staging = Path(tempfile.mkdtemp(prefix=".build-tmp-", dir=str(HERE)))
    try:
        (staging / "index.html").write_text(renderizar_index(config, produccion), encoding="utf-8")
        (staging / "404.html").write_text(renderizar_404(config), encoding="utf-8")
        (staging / "robots.txt").write_text(renderizar_robots_txt(produccion, config), encoding="utf-8")
        if produccion:
            (staging / "sitemap.xml").write_text(renderizar_sitemap_xml(config), encoding="utf-8")

        _copiar_assets(staging)

        violaciones = _verificar_allowlist_dist(staging)
        if violaciones:
            raise SystemExit(
                "El contenido armado para dist/ tiene archivos no permitidos, no se "
                f"reemplazó nada: {violaciones}"
            )
    except SystemExit:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    # A partir de acá el contenido del staging ya está validado -- lo
    # único que puede fallar de acá en más es el swap en sí sobre el
    # sistema de archivos, no el contenido.
    respaldo = None
    if DIST_PATH.exists():
        respaldo = _nombre_respaldo_libre()
        try:
            _renombrar(DIST_PATH, respaldo)
        except OSError as e:
            # dist/ no debería haberse llegado a tocar (el rename no se
            # completó) -- el staging nuevo todavía no se usó para nada.
            shutil.rmtree(staging, ignore_errors=True)
            raise SystemExit(
                "No se pudo apartar el dist/ anterior para respaldarlo antes de "
                f"reemplazarlo -- dist/ real ({DIST_PATH}) no debería haber "
                f"cambiado. Error: {type(e).__name__}: {e}"
            )

    try:
        _renombrar(staging, DIST_PATH)
    except OSError as e:
        if respaldo is not None:
            try:
                _renombrar(respaldo, DIST_PATH)
            except OSError as e2:
                raise SystemExit(
                    "FALLO CRÍTICO: no se pudo mover el build nuevo a dist/ y "
                    "TAMPOCO se pudo restaurar el respaldo -- en este momento "
                    f"dist/ no existe. Rutas para resolver a mano -- respaldo "
                    f"(versión anterior válida): {respaldo} | staging (build "
                    f"nuevo que falló): {staging}. Error al mover: "
                    f"{type(e).__name__}: {e}. Error al restaurar: "
                    f"{type(e2).__name__}: {e2}"
                )
            raise SystemExit(
                "No se pudo mover el build nuevo a dist/ -- se restauró "
                f"automáticamente la versión anterior en {DIST_PATH}, sin "
                f"pérdida. El build nuevo que falló se conserva sin borrar en: "
                f"{staging}. Error original: {type(e).__name__}: {e}"
            )
        raise SystemExit(
            "No se pudo mover el build nuevo a dist/ (no había una versión "
            f"anterior que restaurar). Se conserva sin borrar en: {staging}. "
            f"Error: {type(e).__name__}: {e}"
        )

    # dist/ ya es el build nuevo y válido. El respaldo (si hubo) ya
    # cumplió su función -- se intenta borrar, pero si eso falla no se
    # pierde nada: dist/ sigue siendo el nuevo, correcto. Solo se avisa.
    if respaldo is not None:
        try:
            shutil.rmtree(respaldo)
        except OSError as e:
            print(
                f"[ADVERTENCIA] dist/ se actualizó correctamente a la versión "
                f"nueva, pero no se pudo borrar el respaldo temporal en "
                f"{respaldo} -- queda ahí, revisalo y borralo a mano cuando "
                f"quieras. Error: {type(e).__name__}: {e}"
            )

    archivos_generados = sorted(
        p.relative_to(DIST_PATH).as_posix() for p in DIST_PATH.rglob("*") if p.is_file()
    )
    return {
        "modo": "produccion" if produccion else "preview",
        "dist": str(DIST_PATH),
        "archivos": archivos_generados,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--production", action="store_true",
        help="Genera para producción (canonical + robots indexable + sitemap.xml). "
             "Sin esta opción, siempre genera preview (noindex, nunca indexable).",
    )
    args = parser.parse_args()

    resumen = construir(produccion=args.production)
    print(f"Generado en {resumen['dist']} (modo: {resumen['modo']})")
    for archivo in resumen["archivos"]:
        print(f"  - {archivo}")


if __name__ == "__main__":
    main()
