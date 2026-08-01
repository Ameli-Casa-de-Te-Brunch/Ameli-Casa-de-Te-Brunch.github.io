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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--xlsx", default=None, help="ruta al Excel maestro (si no, se resuelve solo)")
    ap.add_argument("--template", type=Path, default=ROOT / "templates" / "menu.template.html")
    ap.add_argument("--out", type=Path, default=ROOT / "dist" / "index.html")
    ap.add_argument("--dry-run", action="store_true", help="solo validar y reportar, no escribir nada")
    ap.add_argument("--publicar", action="store_true", help="al final, ofrecer publicar (con confirmación)")
    args = ap.parse_args()

    xlsx_path = config_local.resolver_ruta_xlsx(args.xlsx)
    if not xlsx_path.exists():
        print(config_local.mensaje_no_encontrado(xlsx_path))
        sys.exit(1)

    print(f"1/3 extract  ({xlsx_path.name})")
    data = extract.extract(xlsx_path)
    print(f"      {len(data['prods'])} productos activos, {len(data['cats'])} categorías")

    print("2/3 validate")
    errors, warnings = validate.validate(data, xlsx_path)
    for w in warnings:
        print(f"      [AVISO] {w}")
    for e in errors:
        print(f"      [ERROR] {e}")
    print(f"      {len(errors)} error(es), {len(warnings)} aviso(s)")
    if errors:
        print("\nBuild detenido: corregí los errores de arriba en el Excel maestro y volvé a correr")
        print("python build.py. Nada se generó ni se publicó.")
        sys.exit(1)

    if args.dry_run:
        print("\n--dry-run: no se generó ni publicó nada")
        return

    print("3/3 render")
    MENU_JSON.parent.mkdir(parents=True, exist_ok=True)
    MENU_JSON.write_text(json.dumps(extract.datos_publicos(data), ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"      {MENU_JSON} (solo campos públicos)")

    template = args.template.read_text(encoding="utf-8")
    html = render.render(data, template)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html, encoding="utf-8")
    print(f"      {args.out} ({len(html)} bytes)")
    render.copiar_assets(args.out.parent)
    print(f"      {args.out.parent / 'assets'} (fuentes)")

    if args.publicar:
        publicar()
    else:
        print("\nListo en tu PC. Para publicar de verdad: python build.py --publicar")


if __name__ == "__main__":
    main()
