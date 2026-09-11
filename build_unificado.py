#!/usr/bin/env python3
"""Orquesta el build de la web institucional (web/) + el menú
(build/render.py) en un único dist/ -- el artefacto que sube a GitHub
Pages (ver .github/workflows/deploy.yml).

    python build_unificado.py                  # preview
    python build_unificado.py --production      # producción

No modifica ni web/build_site.py ni build/render.py -- cada uno sigue
siendo un proyecto self-contained, con su propia suite de tests, su
propia validación y su propio modo de generar (o no) canonical/robots/
sitemap. Este script solo decide DÓNDE queda cada salida dentro de un
único dist/:

    dist/index.html                <- web institucional (raíz)
    dist/404.html
    dist/assets/...                <- assets de la web
    dist/robots.txt, sitemap.xml   <- de la web (según su propio modo)
    dist/menu/index.html           <- menú, sin tocar build/render.py
    dist/menu/assets/...           <- assets propios del menú (independientes)
    dist/menu/robots.txt, sitemap.xml  <- del menú (según su propio config.url_base)
    dist/CNAME                     <- solo en --production, ver _escribir_cname()

build/render.py YA aceptaba (desde antes de esta unificación) una ruta
de salida por argumento -- por eso alcanza con pedirle
"dist/menu/index.html" en vez de tocar una sola línea de su código.

Todo se arma primero en un directorio de staging temporal y solo se
mueve a dist/ si CADA build (web y menú) terminó sin error -- mismo
criterio de "todo o nada, nunca pisar dist/ a medias" que
web/build_site.py ya aplica para su propio staging interno, llevado acá
al nivel del repo completo.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
WEB_DIR = HERE / "web"
DIST_PATH = HERE / "dist"

# Dominio final confirmado por Ignacio (arquitectura unificada). Solo se
# escribe dist/CNAME en modo --production -- un preview no debe dejar
# artefactos que sugieran que algo ya está listo para servirse en ese
# dominio real.
DOMINIO_PROPIO = "amelicasadete.com.ar"


def _ejecutar(cmd: list, cwd: Path) -> str:
    resultado = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    if resultado.returncode != 0:
        raise SystemExit(
            f"Falló: {' '.join(str(c) for c in cmd)} (cwd={cwd})\n"
            f"--- stdout ---\n{resultado.stdout}\n--- stderr ---\n{resultado.stderr}"
        )
    return resultado.stdout


def _escribir_cname(staging: Path) -> None:
    (staging / "CNAME").write_text(DOMINIO_PROPIO + "\n", encoding="utf-8")


def construir(produccion: bool) -> dict:
    residuales = sorted(HERE.glob(".dist-unificado-respaldo-*"))
    if residuales:
        raise SystemExit(
            "Hay respaldo(s) de dist/ de una corrida anterior de "
            "build_unificado.py sin resolver -- revisalos a mano antes de "
            "seguir: " + ", ".join(str(p) for p in residuales)
        )

    staging = Path(tempfile.mkdtemp(prefix=".build-unificado-tmp-", dir=str(HERE)))
    try:
        # 1) Web institucional -- corre su propio build_site.py tal cual,
        #    en su propio directorio (produce web/dist/), y ese
        #    resultado ya validado se copia entero al staging unificado.
        cmd_web = [sys.executable, "build_site.py"]
        if produccion:
            cmd_web.append("--production")
        _ejecutar(cmd_web, cwd=WEB_DIR)
        web_dist = WEB_DIR / "dist"
        if not web_dist.is_dir():
            raise SystemExit(f"web/build_site.py no generó {web_dist}")
        shutil.copytree(web_dist, staging, dirs_exist_ok=True)

        # 2) Menú -- build/render.py ya acepta ruta de salida por
        #    argumento, así que se le pide directamente
        #    <staging>/menu/index.html. Nada de su código cambia; sigue
        #    generando (o no) canonical/robots/sitemap/JSON-LD según
        #    config.url_base de data/menu.json, exactamente como cuando
        #    corre solo.
        menu_out = staging / "menu" / "index.html"
        _ejecutar([
            sys.executable, "build/render.py",
            "data/menu.json", "templates/menu.template.html", str(menu_out),
        ], cwd=HERE)
        if not menu_out.is_file():
            raise SystemExit(f"build/render.py no generó {menu_out}")

        if produccion:
            _escribir_cname(staging)
    except SystemExit:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    # Reemplazo del dist/ unificado -- aparta el anterior a un respaldo
    # antes de mover el staging nuevo, y restaura automáticamente si el
    # segundo paso falla. Mismo patrón que web/build_site.py usa para su
    # propio dist/, acá al nivel del repo completo.
    respaldo = None
    if DIST_PATH.exists():
        respaldo = HERE / f".dist-unificado-respaldo-{os.getpid()}"
        try:
            DIST_PATH.rename(respaldo)
        except OSError as e:
            shutil.rmtree(staging, ignore_errors=True)
            raise SystemExit(
                f"No se pudo apartar el dist/ anterior para respaldarlo -- "
                f"dist/ real no debería haber cambiado. Error: {e}"
            )

    try:
        staging.rename(DIST_PATH)
    except OSError as e:
        if respaldo is not None:
            try:
                respaldo.rename(DIST_PATH)
            except OSError as e2:
                raise SystemExit(
                    "FALLO CRÍTICO: no se pudo mover el build nuevo a dist/ y "
                    "TAMPOCO se pudo restaurar el respaldo. Rutas para resolver "
                    f"a mano -- respaldo: {respaldo} | staging fallido: {staging}. "
                    f"Error al mover: {e}. Error al restaurar: {e2}"
                )
            raise SystemExit(
                f"No se pudo mover el build nuevo a dist/ -- se restauró la "
                f"versión anterior automáticamente. Build nuevo (fallido) sin "
                f"borrar en: {staging}. Error original: {e}"
            )
        raise SystemExit(
            f"No se pudo mover el build nuevo a dist/ (no había versión "
            f"anterior que restaurar). Se conserva sin borrar en: {staging}. "
            f"Error: {e}"
        )

    if respaldo is not None:
        shutil.rmtree(respaldo, ignore_errors=True)

    return {"dist": str(DIST_PATH), "modo": "produccion" if produccion else "preview"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--production", action="store_true",
        help="Build de producción: la web genera canonical/robots indexable/"
             "sitemap/CNAME. El menú sigue su propia lógica de config.url_base, "
             "sin relación con esta bandera.",
    )
    args = parser.parse_args()

    resumen = construir(produccion=args.production)
    print(f"Generado {resumen['dist']} (modo: {resumen['modo']})")
    archivos = sorted(
        p.relative_to(DIST_PATH).as_posix() for p in DIST_PATH.rglob("*") if p.is_file()
    )
    for a in archivos:
        print(f"  - {a}")


if __name__ == "__main__":
    main()
