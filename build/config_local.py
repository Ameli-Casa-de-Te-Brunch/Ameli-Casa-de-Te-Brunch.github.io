"""Resuelve dónde vive el Excel maestro en esta máquina.

El maestro NO vive en el repo (es información de costos/negocio, y el repo
es público) — vive en la PC del dueño, respaldado por OneDrive. Este módulo
busca la ruta en este orden:

  1. Argumento --xlsx pasado por línea de comandos.
  2. Variable de entorno AMELI_XLSX_PATH.
  3. Archivo .env en la raíz del repo (gitignoreado), línea AMELI_XLSX_PATH=...
  4. Carpeta de OneDrive donde vive hoy: el archivo "Ameli_Menu_Maestro_V*.xlsx"
     con la fecha de modificación más reciente (a propósito, sin hardcodear
     un número de versión — cuando aparezca un V2.3 esto lo sigue encontrando
     solo, sin tocar código).
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
VAR = "AMELI_XLSX_PATH"

CARPETA_POR_DEFECTO = Path.home() / "OneDrive" / "Documentos" / "TRABAJO" / "AMELÍ"
PATRON_POR_DEFECTO = "Ameli_Menu_Maestro_V*.xlsx"


def _leer_env_file():
    if not ENV_FILE.exists():
        return {}
    valores = {}
    for linea in ENV_FILE.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, _, valor = linea.partition("=")
        valores[clave.strip()] = valor.strip().strip('"').strip("'")
    return valores


def _ruta_por_defecto() -> Path:
    """Entre todos los Ameli_Menu_Maestro_V*.xlsx de la carpeta, el modificado
    más recientemente — así no hay que tocar código cada vez que cambia la
    versión del maestro."""
    if not CARPETA_POR_DEFECTO.exists():
        return CARPETA_POR_DEFECTO / "Ameli_Menu_Maestro.xlsx"  # ruta "no encontrada" informativa
    candidatos = sorted(
        CARPETA_POR_DEFECTO.glob(PATRON_POR_DEFECTO),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if candidatos:
        return candidatos[0]
    return CARPETA_POR_DEFECTO / "Ameli_Menu_Maestro.xlsx"


def resolver_ruta_xlsx(desde_cli=None) -> Path:
    if desde_cli:
        return Path(desde_cli)

    if os.environ.get(VAR):
        return Path(os.environ[VAR])

    valores_env_file = _leer_env_file()
    if valores_env_file.get(VAR):
        return Path(valores_env_file[VAR])

    return _ruta_por_defecto()


def mensaje_no_encontrado(ruta: Path) -> str:
    return (
        f"No encuentro el Excel maestro en:\n  {ruta}\n\n"
        "El maestro vive fuera del repo (a propósito: tiene costos y márgenes,\n"
        "y el repo es público). Decile a build.py dónde está de alguna de estas formas:\n\n"
        f"  1. python build.py --xlsx \"C:\\ruta\\a\\tu\\archivo.xlsx\"\n"
        f"  2. Variable de entorno: set {VAR}=C:\\ruta\\a\\tu\\archivo.xlsx\n"
        f"  3. Archivo .env en la raíz del repo (no se sube a git), con esta línea:\n"
        f"     {VAR}=C:\\ruta\\a\\tu\\archivo.xlsx\n"
    )
