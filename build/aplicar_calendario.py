#!/usr/bin/env python3
"""Lee el calendario de temas desde una pestaña de Google Sheets "publicada
en la web" (CSV) y reescribe data/calendario.json con lo que diga -- sin
que nadie tenga que tocar el repo para mover una fecha.

Mismo circuito que la hoja de disponibilidad (build/aplicar_disponibilidad.py):
una URL https de docs.google.com guardada en una repo variable (no un
secreto: es pública por diseño de Google al publicar la hoja), descarga con
redirecciones restringidas, tope de tamaño, validación estricta y mensajes
que nunca reproducen el contenido crudo de las celdas.

Diferencia deliberada con disponibilidad (que es fail-closed): si el
calendario de la hoja tiene un error, este paso NO frena el deploy. Un
calendario roto no puede impedir que se publique "agotado por hoy". En
cambio: (1) no pisa nada -- queda el data/calendario.json commiteado, el
último válido; (2) avisa a la salida del paso (calendario_ok=false) y el
workflow marca la corrida en rojo DESPUÉS de publicar (ver el job
avisar-calendario de deploy.yml), así llega el mail de GitHub y alguien lo
corrige, en vez de quedar un cambio "aplicado" que no se aplicó.

Columnas de la pestaña (primera fila = encabezado, en cualquier orden):
  tipo, tema, desde, hasta            obligatorias
  id, prioridad, activo, nota         opcionales
  - desde/hasta: AAAA-MM-DD (formato de columna "texto sin formato" o
    personalizado aaaa-mm-dd; el CSV publicado exporta lo que se VE).
  - activo: vacío o "Sí" = vale; "No" = la fila se ignora (sirve para apagar
    un evento sin borrarlo).
  - id vacío: se arma "fila-N" (N = número de fila de la hoja).
  - nota: texto libre para las personas; nunca se publica ni se lee.
Solo biblioteca estándar.
"""
import csv
import io
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import aplicar_disponibilidad as ad  # noqa: E402  (mismo allowlist de Google y tope de tamaño)
import calendario  # noqa: E402
import extract_common as ec  # noqa: E402

ENCABEZADOS_PERMITIDOS = ("id", "tipo", "tema", "desde", "hasta", "prioridad", "activo", "nota")
ENCABEZADOS_OBLIGATORIOS = ("tipo", "tema", "desde", "hasta")
MAX_FILAS = 500
TAMANO_MAXIMO_BYTES = ad.TAMANO_MAXIMO_BYTES
VALORES_ACTIVO_SI = {"", "si", "sí"}
VALORES_ACTIVO_NO = {"no"}


class CalendarioInvalido(Exception):
    """Calendario de la hoja que no se puede confiar. El mensaje nunca incluye
    la URL ni el texto crudo de ninguna celda."""


class _RedirectHandlerRestringido(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not ec.url_https_valida(newurl, ad.DOMINIOS_REDIRECCION_PERMITIDOS):
            raise CalendarioInvalido("La hoja del calendario redirigió a un destino no permitido -- corto acá.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _descargar(url: str, timeout: int = 10) -> str:
    if not ec.url_https_valida(url, ec.DOMINIOS_DISPONIBILIDAD):
        raise CalendarioInvalido("La URL del calendario configurada no es https de docs.google.com -- no se descarga.")
    opener = urllib.request.build_opener(_RedirectHandlerRestringido)
    try:
        with opener.open(url, timeout=timeout) as resp:
            crudo = resp.read(TAMANO_MAXIMO_BYTES + 1)
    except CalendarioInvalido:
        raise
    except Exception as e:
        # Nunca str(e): algunos errores de urllib incluyen la URL completa.
        raise CalendarioInvalido(f"No se pudo descargar la hoja del calendario ({type(e).__name__}).") from None
    if len(crudo) > TAMANO_MAXIMO_BYTES:
        raise CalendarioInvalido(f"La hoja del calendario supera el máximo permitido ({TAMANO_MAXIMO_BYTES} bytes).")
    try:
        return crudo.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise CalendarioInvalido("La hoja del calendario no es un CSV de texto en una codificación válida.") from None


def parsear_csv(contenido: str) -> tuple:
    """Devuelve (doc, problemas). Nunca levanta: el llamador decide. 'doc' es
    el calendario armado (formato de data/calendario.json) o None si hay
    problemas. Los mensajes citan solo números de fila y valores permitidos,
    nunca el texto de una celda."""
    filas = list(csv.reader(io.StringIO(contenido)))
    if not filas:
        return None, ["La hoja del calendario está vacía (ni encabezado)."]

    encabezado = [c.strip().lower() for c in filas[0]]
    problemas = []
    desconocidos = [c for c in encabezado if c and c not in ENCABEZADOS_PERMITIDOS]
    if desconocidos:
        problemas.append(f"El encabezado tiene {len(desconocidos)} columna(s) que no existen. "
                         f"Solo se permiten: {', '.join(ENCABEZADOS_PERMITIDOS)}.")
    if len(set(c for c in encabezado if c)) != len([c for c in encabezado if c]):
        problemas.append("El encabezado tiene columnas repetidas.")
    faltan = [c for c in ENCABEZADOS_OBLIGATORIOS if c not in encabezado]
    if faltan:
        problemas.append(f"Faltan columnas obligatorias en el encabezado: {', '.join(faltan)}.")
    if problemas:
        return None, problemas

    if len(filas) - 1 > MAX_FILAS:
        return None, [f"Demasiadas filas ({len(filas) - 1}); el máximo es {MAX_FILAS}."]

    indice = {c: i for i, c in enumerate(encabezado) if c}

    def celda(fila, nombre):
        i = indice.get(nombre)
        return fila[i].strip() if i is not None and i < len(fila) else ""

    eventos = []
    for numero, fila in enumerate(filas[1:], start=2):
        if not any(c.strip() for c in fila):
            continue
        if any(c.strip() for c in fila[len(encabezado):]):
            problemas.append(f"Fila {numero}: tiene datos fuera de las columnas del encabezado.")
            continue
        activo = celda(fila, "activo").lower()
        if activo in VALORES_ACTIVO_NO:
            continue
        if activo not in VALORES_ACTIVO_SI:
            problemas.append(f"Fila {numero}: 'activo' tiene que estar vacío, 'Sí' o 'No'.")
            continue

        ev = {
            "id": celda(fila, "id").lower() or f"fila-{numero}",
            "tipo": celda(fila, "tipo").lower(),
            "tema": celda(fila, "tema").lower(),
            "desde": celda(fila, "desde"),
            "hasta": celda(fila, "hasta"),
        }
        prioridad = celda(fila, "prioridad")
        if prioridad:
            if not prioridad.isdigit():
                problemas.append(f"Fila {numero}: 'prioridad' tiene que ser un número entero entre 0 y 100.")
                continue
            ev["prioridad"] = int(prioridad)

        # Validación por fila (para poder citar el número de fila)...
        errores = calendario.validar(_doc_con([ev]))
        if errores:
            for e in errores:
                problemas.append(f"Fila {numero}: " + e.replace("eventos[0]", "esta fila"))
            continue
        eventos.append(ev)

    if problemas:
        return None, problemas

    # ...y del conjunto (ids repetidos entre filas).
    doc = _doc_con(eventos)
    errores = calendario.validar(doc)
    if errores:
        return None, errores
    return doc, []


def _doc_con(eventos: list) -> dict:
    return {"version": 1, "zona_horaria": calendario.ZONA_HORARIA, "activo": True, "eventos": eventos}


def aplicar_a_archivo(url: str, ruta: Path = calendario.DEFAULT_CALENDARIO, timeout: int = 10) -> int:
    """Descarga, valida y reescribe el calendario. Devuelve la cantidad de
    eventos. Levanta CalendarioInvalido ante cualquier problema, SIN haber
    tocado el archivo (se escribe a un temporal y se reemplaza al final)."""
    contenido = _descargar(url, timeout)
    doc, problemas = parsear_csv(contenido)
    if problemas:
        raise CalendarioInvalido("El calendario de la hoja tiene datos que no se pueden confiar:\n  - "
                                 + "\n  - ".join(problemas))
    ruta = Path(ruta)
    temporal = ruta.with_suffix(".json.tmp")
    temporal.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporal.replace(ruta)
    return len(doc["eventos"])


def _salida(clave: str, valor: str) -> None:
    ruta = os.environ.get("GITHUB_OUTPUT")
    if ruta:
        with open(ruta, "a", encoding="utf-8") as f:
            f.write(f"{clave}={valor}\n")


def main() -> int:
    url = os.environ.get("CALENDARIO_CSV_URL", "").strip()
    if not url:
        print("Calendario: no hay CALENDARIO_CSV_URL configurada -- se usa data/calendario.json del repositorio.")
        _salida("calendario_ok", "true")
        return 0
    try:
        cantidad = aplicar_a_archivo(url)
    except CalendarioInvalido as e:
        print("::warning::Calendario de la hoja NO aplicado -- se conserva el último calendario válido del repo.")
        print(e)
        _salida("calendario_ok", "false")
        return 0
    except Exception as e:  # un bug acá no puede frenar la publicación del menú
        print(f"::warning::Calendario de la hoja NO aplicado ({type(e).__name__}) -- se conserva el del repo.")
        _salida("calendario_ok", "false")
        return 0
    print(f"Calendario: {cantidad} evento(s) aplicados desde la hoja.")
    _salida("calendario_ok", "true")
    return 0


if __name__ == "__main__":
    sys.exit(main())
