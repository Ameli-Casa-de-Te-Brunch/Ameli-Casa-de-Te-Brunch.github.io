#!/usr/bin/env python3
"""Sobrescribe el campo 'disp' (disponibilidad) con lo que diga la hoja de
Google Sheets publicada que usa el personal para marcar "agotado por hoy"
desde el celular -- sin tocar el Excel maestro, sin volver a correr
extract.py, sin que el CI necesite ver el Excel.

Se usa de dos formas:
  - Localmente, vía build.py: aplicar_a_prods(data["prods"], url) parchea la
    lista de productos en memoria, con la URL que venga del Excel ("URL de
    disponibilidad (Google Sheets)" en Resumen y Configuración) si está
    cargada. Por defecto corre en modo NO estricto (estricto=False): un
    problema en la hoja se avisa por consola y se sigue con lo que había --
    conveniente para previsualizar en la PC del dueño sin que la hoja de
    prueba tenga que estar perfecta. build.py expone --disponibilidad-estricta
    para probar el modo estricto localmente antes de confiar en él.
  - En GitHub Actions: standalone (este archivo ejecutado directo), leyendo
    la URL de la variable de entorno DISPONIBILIDAD_CSV_URL (repo variable,
    no secreto -- ver README) y parcheando data/menu.json en disco, porque
    ahí no existe un `data` en memoria (CI nunca corre extract.py). Este
    camino SIEMPRE es estricto (estricto=True, no hay forma de desactivarlo
    desde afuera) -- ver la sección "Fallo seguro" más abajo.

Si no hay ninguna URL configurada (el campo está vacío), no es un error: la
disponibilidad en vivo es una función opcional que simplemente no está
activada todavía, y el build sigue con los datos del Excel/último build tal
cual estaban.

Fallo seguro (modo estricto, el que usa CI): si la URL configurada no
responde, redirige a un destino no permitido, entrega más de
TAMANO_MAXIMO_BYTES, o el contenido no pasa la integridad de filas (valor
desconocido, ID duplicado, fila sin ID con un estado, ID desconocido,
producto activo ausente, hoja vacía o truncada) -- se levanta
DisponibilidadInvalida. En el workflow eso hace fallar el job de build, que
nunca llega a publicar: el deploy (needs: build) no corre, y GitHub Pages
conserva la última versión publicada con éxito. Nunca se imprime la URL
completa ni el contenido de la hoja en los logs.
"""
import csv
import io
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

import extract_common as ec

HERE = Path(__file__).resolve().parent
MENU_JSON = HERE.parent / "data" / "menu.json"

# Mismo mapeo de textos que build/extract_common.py (DISPONIBILIDAD_VALORES)
# -- la hoja de Sheets tiene que usar exactamente estos textos en la columna
# "Disponibilidad", o "" / "Disponible" (ambos = disponible, sin código).
ESTADOS_VALIDOS = {
    "": None,
    "Disponible": None,
    "Agotado por hoy": "agotado",
    "No disponible temporalmente": "no_disp",
    "Últimas porciones": "ultimas",
}

# Nunca más de esto por la red -- una hoja "publicada en la web" que de
# pronto entrega varios MB (mal configurada, o algo la reemplazó) no
# debería poder inflar la memoria del runner ni tardar de más.
TAMANO_MAXIMO_BYTES = 1 * 1024 * 1024  # 1 MB

# Google, al servir un CSV "publicado en la web", redirige (307) desde
# docs.google.com hacia un host de contenido dinámico bajo
# googleusercontent.com (comprobado en vivo: ej.
# doc-00-2k-sheets.googleusercontent.com) -- es el comportamiento real y
# esperado de esa función de Sheets, no un tercero. La URL que se
# configura en el maestro sigue teniendo que ser docs.google.com (ver
# ec.DOMINIOS_DISPONIBILIDAD, usado para validar la URL de origen); acá
# se permite además que la REDIRECCIÓN aterrice en el host de contenido
# real de Google, y en ningún otro lado.
DOMINIOS_REDIRECCION_PERMITIDOS = ec.DOMINIOS_DISPONIBILIDAD + ("googleusercontent.com",)


class DisponibilidadInvalida(Exception):
    """Se levanta en modo estricto ante cualquier dato de disponibilidad que
    no se pueda confiar. El mensaje nunca incluye la URL completa ni el
    contenido de la hoja -- ver leer_csv() y _descargar()."""


class _RedirectHandlerRestringido(urllib.request.HTTPRedirectHandler):
    """Sin esto, urllib sigue cualquier redirección que la respuesta pida,
    a cualquier host. Acá se valida el destino de la redirección contra
    DOMINIOS_REDIRECCION_PERMITIDOS (docs.google.com + el host real de
    contenido de Sheets bajo googleusercontent.com), antes de seguirla."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not ec.url_https_valida(newurl, DOMINIOS_REDIRECCION_PERMITIDOS):
            raise DisponibilidadInvalida(
                "La hoja de disponibilidad redirigió a un destino no permitido -- corto acá."
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _verificar_tamano(crudo: bytes) -> None:
    """Separado de _descargar() para poder probarlo sin red."""
    if len(crudo) > TAMANO_MAXIMO_BYTES:
        raise DisponibilidadInvalida(
            f"La hoja de disponibilidad supera el máximo permitido ({TAMANO_MAXIMO_BYTES} bytes) -- se corta."
        )


def _descargar(url: str, timeout: int) -> str:
    """Descarga el CSV con: esquema/host validados, redirecciones
    restringidas al mismo allowlist, y un tope de tamaño. Nunca imprime la
    URL ni el contenido -- solo puede propagar DisponibilidadInvalida con un
    mensaje genérico."""
    if not ec.url_https_valida(url, ec.DOMINIOS_DISPONIBILIDAD):
        raise DisponibilidadInvalida(
            "La URL de disponibilidad configurada no es https de docs.google.com -- no se descarga."
        )
    opener = urllib.request.build_opener(_RedirectHandlerRestringido)
    try:
        with opener.open(url, timeout=timeout) as resp:
            crudo = resp.read(TAMANO_MAXIMO_BYTES + 1)
    except DisponibilidadInvalida:
        raise
    except Exception as e:
        # Nunca str(e): algunos errores de urllib incluyen la URL completa
        # en su mensaje. Solo el tipo de excepción es seguro de loguear.
        raise DisponibilidadInvalida(
            f"No se pudo descargar la hoja de disponibilidad ({type(e).__name__})."
        ) from None
    _verificar_tamano(crudo)
    try:
        return crudo.decode("utf-8-sig")
    except UnicodeDecodeError:
        # Nunca los bytes crudos ni el contenido en el mensaje -- ni
        # siquiera parcialmente, por si el problema es justo en un punto
        # que dejaría ver algo sensible por casualidad.
        raise DisponibilidadInvalida(
            "La hoja de disponibilidad no es un CSV de texto en una codificación válida."
        ) from None


def _parsear_y_validar(contenido: str, ids_activos_esperados: set | None) -> tuple[dict, list[str]]:
    """Devuelve (disponibilidad {id: código o None}, problemas). Nunca
    levanta -- el llamador decide, según el modo, si los problemas frenan
    todo (estricto) o solo se avisan (no estricto)."""
    problemas: list[str] = []
    filas = list(csv.reader(io.StringIO(contenido)))
    if not filas:
        return {}, ["La hoja de disponibilidad está vacía (ni encabezado)."]

    encabezado = [c.strip().lower() for c in filas[0]]
    try:
        col_id = encabezado.index("id")
        col_disp = encabezado.index("disponibilidad")
    except ValueError:
        return {}, ["La hoja no tiene columnas 'ID' y 'Disponibilidad' en la primera fila."]

    filas_datos = filas[1:]
    if ids_activos_esperados and not filas_datos:
        return {}, ["La hoja de disponibilidad no tiene ninguna fila de datos (vacía o truncada)."]

    disponibilidad: dict[str, str | None] = {}
    vistos: dict[str, int] = {}
    for numero_fila, fila in enumerate(filas_datos, start=2):
        idv = fila[col_id].strip() if len(fila) > col_id else ""
        disp_crudo = fila[col_disp].strip() if len(fila) > col_disp else ""

        if not idv:
            # Nunca disp_crudo acá: es texto de celda no confiable, podría
            # llevar cualquier cosa pegada por error (hasta una
            # credencial) -- alcanza con el número de fila.
            if disp_crudo:
                problemas.append(
                    f"Fila {numero_fila}: tiene un valor de disponibilidad pero no tiene ID -- "
                    "no se sabe a qué producto corresponde."
                )
            continue

        # A partir de acá, "idv" solo es seguro de reproducir en un
        # mensaje si es uno de los IDs públicos ya conocidos (nuestros
        # propios códigos de producto, ej. "TYT004") -- nunca el texto
        # crudo de la celda tal cual llegó, que podría no serlo.
        id_conocido = ids_activos_esperados is not None and idv in ids_activos_esperados

        if idv in vistos:
            if id_conocido:
                problemas.append(
                    f"El ID '{idv}' está repetido en la hoja de disponibilidad: filas {vistos[idv]} y {numero_fila}."
                )
            else:
                problemas.append(
                    f"Fila {numero_fila}: repite el mismo ID que la fila {vistos[idv]} (ID no reconocido)."
                )
            continue
        vistos[idv] = numero_fila

        if ids_activos_esperados is not None and not id_conocido:
            # Nunca idv acá: no es uno de nuestros IDs conocidos, así que
            # no hay garantía de qué contiene esa celda.
            problemas.append(
                f"Fila {numero_fila}: contiene un ID que no corresponde a ningún producto activo publicado."
            )
            continue

        if disp_crudo not in ESTADOS_VALIDOS:
            # Nunca disp_crudo (el valor recibido) -- solo la fila y, si
            # ya se confirmó que es un ID público conocido, ese ID. La
            # lista de valores no vacíos ya incluye "Disponible" una sola
            # vez -- "vacío" se menciona aparte porque "" no es un valor
            # que tenga sentido citar entre comillas en la lista.
            valores_no_vacios = "', '".join(v for v in ESTADOS_VALIDOS if v)
            identificacion = f" (ID '{idv}')" if id_conocido else ""
            problemas.append(
                f"Fila {numero_fila}{identificacion}: el valor de disponibilidad no es reconocido. "
                f"Tiene que estar vacío o ser exactamente uno de: '{valores_no_vacios}'."
            )
            continue

        codigo = ESTADOS_VALIDOS[disp_crudo]
        if codigo is not None:
            disponibilidad[idv] = codigo

    if ids_activos_esperados is not None:
        ausentes = sorted(ids_activos_esperados - vistos.keys())
        for idv in ausentes:
            problemas.append(
                f"El producto activo '{idv}' no tiene ninguna fila en la hoja de disponibilidad "
                "(una fila ausente no se interpreta como disponible: tiene que estar presente, "
                "aunque sea vacía)."
            )

    return disponibilidad, problemas


def leer_csv(url: str, ids_activos_esperados: set | None = None, estricto: bool = True,
             timeout: int = 10) -> tuple[dict, list[str]]:
    """Devuelve siempre (disponibilidad, problemas):
    - disponibilidad: {id: código ('agotado'/'no_disp'/'ultimas')}, ausente
      si la fila dice 'Disponible' o está vacía.
    - problemas: lista de mensajes de integridad (vacía si todo está bien).

    ids_activos_esperados: set opcional de IDs de productos activos. Si se
    pasa, TODOS tienen que aparecer como fila (una fila ausente es un
    problema, nunca "disponible por omisión"), y cualquier ID de fila que
    no esté en ese conjunto es un problema (fila de un producto
    desconocido).

    estricto=True (el default, y el único modo del camino de CI): si
    `problemas` no está vacía, levanta DisponibilidadInvalida en vez de
    devolver nada -- no hay forma de que el llamador reciba un resultado
    parcial en este modo.
    estricto=False (uso local, opt-in vía build.py): nunca levanta por
    problemas de integridad (sí puede levantar por una descarga fallida,
    ver _descargar) -- devuelve la tupla completa para que el llamador
    decida qué hacer (ver aplicar_a_prods: por atomicidad, no aplica nada
    si hay problemas)."""
    contenido = _descargar(url, timeout)
    disponibilidad, problemas = _parsear_y_validar(contenido, ids_activos_esperados)
    if problemas and estricto:
        raise DisponibilidadInvalida(
            "La hoja de disponibilidad tiene datos que no se pueden confiar:\n  - "
            + "\n  - ".join(problemas)
        )
    return disponibilidad, problemas


def aplicar_a_prods(prods: list, url: str, estricto: bool = False) -> int:
    """Parchea en el lugar una lista de productos (dicts con 'id' y 'disp'
    opcional) en memoria. Devuelve la cantidad de cambios, o -1 si no se
    aplicó nada (sin URL; o -- solo si estricto=False -- la descarga
    falló, o la hoja tenía cualquier problema de integridad).

    Atomicidad: si hay algún problema (aunque sea en una sola fila), no se
    modifica NINGÚN producto -- nunca se aplica parcialmente lo que sí se
    pudo interpretar. En estricto=True, un problema levanta
    DisponibilidadInvalida en vez de devolver -1."""
    if not url:
        return -1
    if not estricto:
        print("Disponibilidad en vivo: modo NO estricto (uso local) -- nunca usar así en producción.")
    ids_activos = {p["id"] for p in prods}
    try:
        disponibilidad, problemas = leer_csv(url, ids_activos_esperados=ids_activos, estricto=estricto)
    except DisponibilidadInvalida as e:
        if estricto:
            raise
        print(f"Disponibilidad en vivo: no pude aplicarla ({e}) -- no se modifica ningún producto.")
        return -1

    if problemas:
        # Solo posible acá en modo no estricto (estricto ya habría
        # levantado dentro de leer_csv). Se avisa, pero no se toca nada:
        # todo o nada, nunca una mezcla de productos actualizados y otros
        # con el estado viejo por una fila mala en el medio.
        for p in problemas:
            print(f"[AVISO] Disponibilidad en vivo: {p}")
        print("Disponibilidad en vivo: hay problemas de integridad en la hoja -- no se modifica ningún producto.")
        return -1

    cambios = 0
    for p in prods:
        nuevo = disponibilidad.get(p["id"])
        if nuevo != p.get("disp"):
            cambios += 1
        if nuevo:
            p["disp"] = nuevo
        else:
            p.pop("disp", None)
    if cambios:
        print(f"Disponibilidad en vivo: {cambios} producto(s) actualizados desde la hoja.")
    return cambios


def aplicar_a_archivo(url: str, menu_json_path: Path = MENU_JSON, estricto: bool = True,
                       url_obligatoria: bool = False) -> int:
    """Igual que aplicar_a_prods, pero leyendo y reescribiendo un
    data/menu.json en disco -- para el caso CI, que no tiene el dict en
    memoria porque nunca corre extract.py. estricto=True por defecto: es el
    camino de producción.

    url_obligatoria=True (usado por main(), el camino de CI/producción):
    una URL vacía/faltante es en sí misma un problema -- levanta
    DisponibilidadInvalida en vez de seguir de largo sin aplicar nada. Sin
    esto, si la repo variable DISPONIBILIDAD_CSV_URL se borra o queda mal
    configurada por error, el build podía terminar "exitosamente" sin
    ningún dato de disponibilidad aplicado -- publicando todo como
    disponible sin que nadie se entere. url_obligatoria=False (el default,
    usado por build.py en la PC del dueño) conserva el comportamiento
    anterior: sin URL configurada, la función es simplemente opcional."""
    if not url:
        if url_obligatoria:
            raise DisponibilidadInvalida(
                "DISPONIBILIDAD_CSV_URL no está configurada -- en este camino es obligatoria, no se publica sin ella."
            )
        print("Disponibilidad en vivo: no hay URL configurada, no se aplica nada.")
        return -1
    if not menu_json_path.exists():
        if estricto:
            raise DisponibilidadInvalida(f"No encuentro {menu_json_path}.")
        print(f"Disponibilidad en vivo: no encuentro {menu_json_path}.")
        return -1
    data = json.loads(menu_json_path.read_text(encoding="utf-8"))
    cambios = aplicar_a_prods(data["prods"], url, estricto=estricto)
    if cambios >= 0:
        menu_json_path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return cambios


def main():
    url = os.environ.get("DISPONIBILIDAD_CSV_URL", "").strip()
    try:
        aplicar_a_archivo(url, estricto=True, url_obligatoria=True)
    except DisponibilidadInvalida as e:
        print(f"[ERROR] Disponibilidad en vivo: {e}")
        print("[ERROR] Build detenido -- no se publica con datos de disponibilidad no confiables.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
