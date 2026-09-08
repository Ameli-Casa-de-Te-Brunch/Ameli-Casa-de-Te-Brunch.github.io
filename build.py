#!/usr/bin/env python3
"""extract -> validate -> render, con la publicación (git) como paso aparte y explícito.

Uso:
  python build.py                 # valida y arma dist/ en tu PC. No toca git.
  python build.py --dry-run       # solo valida y reporta, no escribe nada.
  python build.py --publicar      # además de lo anterior, ofrece publicar: te
                                   # muestra exactamente qué va a subir y pide
                                   # que escribas "si" para confirmar.
  python build.py --xlsx ruta.xlsx
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "build"))
import aplicar_disponibilidad  # noqa: E402
import config_local  # noqa: E402
import extract  # noqa: E402
import render  # noqa: E402
import validate  # noqa: E402

ROOT = Path(__file__).resolve().parent
MENU_JSON = ROOT / "data" / "menu.json"


def _git(*args):
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8"
    )


def publicar():
    """Muestra EXACTAMENTE qué archivo cambiaría y pide confirmación explícita
    antes de commitear y pushear. Nunca commitea nada que no haya listado antes."""
    print("\n--publicar")

    rev_parse = _git("rev-parse", "--abbrev-ref", "HEAD")
    if rev_parse.returncode != 0:
        print("No pude detectar la rama actual (¿esto es un repo git?). No se publicó.")
        return
    rama = rev_parse.stdout.strip()
    if rama != "main":
        print(f"Estás en la rama '{rama}', no en 'main'. Por seguridad no publico desde acá:")
        print("corré 'git checkout main' y volvé a intentar, o pedile ayuda a quien te armó el sitio.")
        return

    ruta_rel = str(MENU_JSON.relative_to(ROOT)).replace("\\", "/")
    diff = _git("diff", "--stat", "--", ruta_rel)
    diff_cached = _git("diff", "--cached", "--stat", "--", ruta_rel)
    sin_cambios = not diff.stdout.strip() and not diff_cached.stdout.strip()
    untracked = _git("status", "--porcelain", "--", ruta_rel).stdout.strip()

    if sin_cambios and not untracked:
        print(f"'{ruta_rel}' no tiene cambios respecto al último commit — nada para publicar.")
        return

    print("Esto es exactamente lo que se va a subir (y nada más):")
    print(f"  {ruta_rel}")
    resumen = diff.stdout.strip() or diff_cached.stdout.strip() or untracked
    if resumen:
        print("  " + resumen.replace("\n", "\n  "))

    respuesta = input('\n¿Confirmás? Escribí "si" para publicar, cualquier otra cosa cancela: ').strip().lower()
    if respuesta not in ("si", "sí"):
        print("Cancelado. No se publicó nada.")
        return

    _git("add", "--", ruta_rel)
    commit = _git("commit", "-m", "Actualizar menú publicado (data/menu.json)", "--", ruta_rel)
    if commit.returncode != 0:
        print("No pude hacer el commit:")
        print(commit.stderr.strip())
        return
    print(f"commit creado: {commit.stdout.strip().splitlines()[0] if commit.stdout else 'ok'}")

    push = _git("push", "origin", "main")
    if push.returncode != 0:
        print("El commit se hizo pero el push falló (revisá tu conexión o permisos):")
        print(push.stderr.strip())
        print("Corré 'git push' a mano cuando se resuelva.")
        return
    print("Publicado. GitHub Actions va a reconstruir el sitio en un par de minutos:")
    print("https://ameli-casa-de-te-brunch.github.io/")


def preparar_en_memoria(data: dict, disponibilidad_estricta: bool) -> str:
    """Hace, en memoria y sin tocar disco, todo lo que hace falta antes de
    poder decidir si se escribe algo: arma el texto exacto que iría a
    data/menu.json y aplica/valida la disponibilidad en vivo.

    El texto de data/menu.json se serializa ACÁ, antes de aplicar
    disponibilidad -- así el JSON versionado nunca incorpora la
    disponibilidad efímera de la hoja (cambia varias veces por día), sin
    importar que aplicar_a_prods más abajo mute data["prods"] para el
    render. El commiteado refleja el Excel; la hoja lo pisa recién al
    renderizar, en memoria, y de nuevo en cada rebuild que dispare el Apps
    Script vía GitHub Actions (ver aplicar_disponibilidad.py).

    Si disponibilidad_estricta=True y la hoja no es confiable, propaga
    aplicar_disponibilidad.DisponibilidadInvalida SIN haber escrito nada
    todavía -- es responsabilidad del llamador no escribir ningún archivo
    si esto levanta.
    """
    menu_json_texto = json.dumps(extract.datos_publicos(data), ensure_ascii=False, indent=1)

    url_disponibilidad = data["config"].get("disponibilidad_csv_url")
    if url_disponibilidad:
        aplicar_disponibilidad.aplicar_a_prods(
            data["prods"], url_disponibilidad, estricto=disponibilidad_estricta
        )

    return menu_json_texto


def ejecutar(args, xlsx_path: Path) -> None:
    print("1/3 extract  (" + xlsx_path.name + ")")
    data = extract.extract(xlsx_path)
    print("      " + str(len(data["prods"])) + " productos activos, " + str(len(data["cats"])) + " categorías")

    print("2/3 validate")
    errors, warnings = validate.validate(data, xlsx_path)
    for w in warnings:
        print("      [AVISO] " + w)
    for e in errors:
        print("      [ERROR] " + e)
    print("      " + str(len(errors)) + " error(es), " + str(len(warnings)) + " aviso(s)")
    if errors:
        print()
        print("Build detenido: corregí los errores de arriba en el Excel maestro y volvé a correr")
        print("python build.py. Nada se generó ni se publicó.")
        sys.exit(1)

    # Todo esto (extracción, validación del JSON y validación estricta de
    # disponibilidad en vivo) ocurre en memoria, ANTES de escribir cualquier
    # archivo -- inclusive en --dry-run, que antes salía sin siquiera
    # intentar la descarga/validación de la hoja. Así
    # "--dry-run --disponibilidad-estricta" prueba de verdad si la hoja
    # real pasaría el modo estricto, y un fallo (con o sin --dry-run) nunca
    # deja data/menu.json, dist/index.html ni ningún otro output tocado --
    # el mensaje "no se generó ni publicó nada" sigue siendo cierto.
    try:
        menu_json_texto = preparar_en_memoria(data, args.disponibilidad_estricta)
    except aplicar_disponibilidad.DisponibilidadInvalida as e:
        print()
        print("[ERROR] Disponibilidad en vivo (modo estricto): " + str(e))
        print("Build detenido. Corregí la hoja de disponibilidad o corré sin --disponibilidad-estricta.")
        print("No se generó ni publicó nada.")
        sys.exit(1)

    if args.dry_run:
        print()
        print("--dry-run: no se generó ni publicó nada")
        return

    print("3/3 render")
    MENU_JSON.parent.mkdir(parents=True, exist_ok=True)
    MENU_JSON.write_text(menu_json_texto, encoding="utf-8")
    print("      " + str(MENU_JSON) + " (solo campos públicos)")

    template = args.template.read_text(encoding="utf-8")
    html = render.render(data, template)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html, encoding="utf-8")
    print("      " + str(args.out) + " (" + str(len(html)) + " bytes)")
    render.copiar_assets(args.out.parent)
    print("      " + str(args.out.parent / "assets") + " (fuentes)")
    render._escribir_seo_estatico(args.out.parent, data["config"].get("url_base"))

    if args.publicar:
        publicar()
    else:
        print()
        print("Listo en tu PC. Para publicar de verdad: python build.py --publicar")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--xlsx", default=None, help="ruta al Excel maestro (si no, se resuelve solo)")
    ap.add_argument("--template", type=Path, default=ROOT / "templates" / "menu.template.html")
    ap.add_argument("--out", type=Path, default=ROOT / "dist" / "index.html")
    ap.add_argument("--dry-run", action="store_true", help="solo validar y reportar, no escribir nada")
    ap.add_argument("--publicar", action="store_true", help="al final, ofrecer publicar (con confirmación)")
    ap.add_argument(
        "--disponibilidad-estricta", action="store_true",
        help="probar localmente el modo estricto de disponibilidad en vivo (el mismo que usa "
             "CI en producción) -- por defecto la corrida local es NO estricta: un problema en "
             "la hoja se avisa por consola y se sigue con lo que había.",
    )
    args = ap.parse_args()

    xlsx_path = config_local.resolver_ruta_xlsx(args.xlsx)
    if not xlsx_path.exists():
        print(config_local.mensaje_no_encontrado(xlsx_path))
        sys.exit(1)

    ejecutar(args, xlsx_path)


if __name__ == "__main__":
    main()
