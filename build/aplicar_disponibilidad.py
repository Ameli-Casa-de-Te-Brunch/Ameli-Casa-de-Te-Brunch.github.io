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
    return crudo.decode("utf-8-sig")


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
            if disp_crudo:
                problemas.append(
                    f"Fila {numero_fila}: tiene un estado de disponibilidad ('{disp_crudo}') "
                    "pero no tiene ID -- no se sabe a qué producto corresponde."
                )
            continue

        if idv in vistos:
            problemas.append(
                f"El ID '{idv}' está repetido en la hoja de disponibilidad: filas {vistos[idv]} y {numero_fila}."
            )
            continue
        vistos[idv] = numero_fila

        if ids_activos_esperados is not None and idv not in ids_activos_esperados:
            problemas.append(
                f"Fila {numero_fila}: el ID '{idv}' no corresponde a ningún producto activo publicado."
            )
            continue

        if disp_crudo not in ESTADOS_VALIDOS:
            valores_validos = "', '".join(v for v in ESTADOS_VALIDOS if v)
            problemas.append(
                f"Fila {numero_fila} (ID '{idv}'): '{disp_crudo}' no es un valor reconocido. "
                f"Tiene que estar vacío, 'Disponible', o exactamente uno de '{valores_validos}'."
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
             timeout: int = 10) -> dict:
    """ID de producto -> código de disponibilidad ('agotado'/'no_disp'/'ultimas'),
    o ausente si la fila dice 'Disponible' o está vacía.

    ids_activos_esperados: set opcional de IDs de productos activos. Si se
    pasa, en modo estricto TODOS tienen que aparecer como fila (una fila
    ausente es un error, nunca "disponible por omisión"), y cualquier ID de
    fila que no esté en ese conjunto es un error (fila de un producto
    desconocido).

    estricto=True (el default, y el único modo del camino de CI): cualquier
    problema de integridad hace levantar DisponibilidadInvalida, sin
    devolver nada aplicable.
    estricto=False (uso local, opt-in vía build.py): los problemas se
    devuelven como avisos impresos por el llamador; se sigue con lo que se
    pudo interpretar."""
    contenido = _descargar(url, timeout)
    disponibilidad, problemas = _parsear_y_validar(contenido, ids_activos_esperados)
    if problemas and estricto:
        raise DisponibilidadInvalida(
            "La hoja de disponibilidad tiene datos que no se pueden confiar:\n  - "
            + "\n  - ".join(problemas)
        )
    if problemas:
        for p in problemas:
            print(f"[AVISO] Disponibilidad en vivo: {p}")
    return disponibilidad


def aplicar_a_prods(prods: list, url: str, estricto: bool = False) -> int:
    """Parchea en el lugar una lista de productos (dicts con 'id' y 'disp'
    opcional) en memoria. Devuelve la cantidad de cambios, o -1 si no se
    pudo aplicar (sin URL, o -- solo si estricto=False -- la hoja no
    respondió o tenía problemas). En estricto=True, un problema levanta
    DisponibilidadInvalida en vez de devolver -1."""
    if not url:
        return -1
    if not estricto:
        print("Disponibilidad en vivo: modo NO estricto (uso local) -- nunca usar así en producción.")
    ids_activos = {p["id"] for p in prods}
    try:
        disponibilidad = leer_csv(url, ids_activos_esperados=ids_activos, estricto=estricto)
    except DisponibilidadInvalida as e:
        if estricto:
            raise
        print(f"Disponibilidad en vivo: no pude aplicarla ({e}) -- sigo con lo que había.")
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


def aplicar_a_archivo(url: str, menu_json_path: Path = MENU_JSON, estricto: bool = True) -> int:
    """Igual que aplicar_a_prods, pero leyendo y reescribiendo un
    data/menu.json en disco -- para el caso CI, que no tiene el dict en
    memoria porque nunca corre extract.py. estricto=True por defecto: es el
    camino de producción."""
    if not url:
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
        aplicar_a_archivo(url, estricto=True)
    except DisponibilidadInvalida as e:
        print(f"[ERROR] Disponibilidad en vivo: {e}")
        print("[ERROR] Build detenido -- no se publica con datos de disponibilidad no confiables.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
