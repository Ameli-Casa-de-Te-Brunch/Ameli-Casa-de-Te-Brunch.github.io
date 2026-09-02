#!/usr/bin/env python3
"""Sobrescribe el campo 'disp' (disponibilidad) con lo que diga la hoja de
Google Sheets publicada que usa el personal para marcar "agotado por hoy"
desde el celular -- sin tocar el Excel maestro, sin volver a correr
extract.py, sin que el CI necesite ver el Excel.

Se usa de dos formas:
  - Localmente, vía build.py: aplicar_a_prods(data["prods"], url) parchea la
    lista de productos en memoria, con la URL que venga del Excel ("URL de
    disponibilidad (Google Sheets)" en Resumen y Configuración) si está cargada.
  - En GitHub Actions: standalone (este archivo ejecutado directo), leyendo
    la URL de la variable de entorno DISPONIBILIDAD_CSV_URL (repo variable,
    no secreto -- ver README) y parcheando data/menu.json en disco, porque
    ahí no existe un `data` en memoria (CI nunca corre extract.py).

Nunca corta el build si la hoja no está configurada o no responde -- en ese
caso los datos quedan como estaban (lo del Excel/último build), y listo.
Esto es a propósito: la disponibilidad en vivo es una mejora, no algo de lo
que dependa poder publicar el sitio.
"""
import csv
import io
import json
import os
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
MENU_JSON = HERE.parent / "data" / "menu.json"

# Mismo mapeo de textos que build/extract.py (DISPONIBILIDAD_VALORES) --
# la hoja de Sheets tiene que usar exactamente estos textos en la columna
# "Disponibilidad", o queda vacía = disponible.
VALORES = {
    "Agotado por hoy": "agotado",
    "No disponible temporalmente": "no_disp",
    "Últimas porciones": "ultimas",
}


def leer_csv(url: str, timeout: int = 10) -> dict:
    """ID de producto -> código de disponibilidad ('agotado'/'no_disp'/'ultimas'),
    o ausente si la fila dice 'Disponible' o está vacía."""
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        contenido = resp.read().decode("utf-8-sig")
    filas = list(csv.reader(io.StringIO(contenido)))
    if not filas:
        return {}
    encabezado = [c.strip().lower() for c in filas[0]]
    try:
        col_id = encabezado.index("id")
        col_disp = encabezado.index("disponibilidad")
    except ValueError:
        raise RuntimeError(
            "la hoja no tiene columnas 'ID' y 'Disponibilidad' en la primera fila"
        )
    resultado = {}
    for fila in filas[1:]:
        if len(fila) <= max(col_id, col_disp):
            continue
        idv = fila[col_id].strip()
        if not idv:
            continue
        resultado[idv] = VALORES.get(fila[col_disp].strip())
    return resultado


def aplicar_a_prods(prods: list, url: str) -> int:
    """Parchea en el lugar una lista de productos (dicts con 'id' y 'disp'
    opcional) en memoria. Devuelve la cantidad de cambios, o -1 si no se
    pudo aplicar (sin URL, o la hoja no respondió) -- nunca levanta una
    excepción hacia quien la llama."""
    if not url:
        return -1
    try:
        disponibilidad = leer_csv(url)
    except Exception as e:
        print(f"Disponibilidad en vivo: no pude leer la hoja ({e}) -- sigo con lo que había.")
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


def aplicar_a_archivo(url: str, menu_json_path: Path = MENU_JSON) -> int:
    """Igual que aplicar_a_prods, pero leyendo y reescribiendo un
    data/menu.json en disco -- para el caso CI, que no tiene el dict en
    memoria porque nunca corre extract.py."""
    if not url:
        print("Disponibilidad en vivo: no hay URL configurada, no se aplica nada.")
        return -1
    if not menu_json_path.exists():
        print(f"Disponibilidad en vivo: no encuentro {menu_json_path}.")
        return -1
    data = json.loads(menu_json_path.read_text(encoding="utf-8"))
    cambios = aplicar_a_prods(data["prods"], url)
    if cambios >= 0:
        menu_json_path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return cambios


def main():
    aplicar_a_archivo(os.environ.get("DISPONIBILIDAD_CSV_URL", "").strip())


if __name__ == "__main__":
    main()
