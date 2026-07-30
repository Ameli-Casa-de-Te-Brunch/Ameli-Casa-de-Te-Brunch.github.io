#!/usr/bin/env python3
"""Un solo comando: extract -> validate -> render -> publicar (git commit + push).

Uso:
  python build.py              # valida, genera el sitio y lo publica (commit + push)
  python build.py --dry-run    # solo valida y reporta, no genera ni publica nada
  python build.py --no-push    # valida y genera dist/ localmente, pero no publica
  python build.py --xlsx ruta/al/maestro.xlsx
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "build"))
import extract  # noqa: E402
import render  # noqa: E402
import validate  # noqa: E402

ROOT = Path(__file__).resolve().parent
XLSX_POR_DEFECTO = ROOT / "data" / "Ameli_Menu_Maestro_V2.1.xlsx"


def _git(*args):
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8"
    )


def publicar(xlsx_path: Path):
    """Commitea el Excel maestro (si cambió) y pushea a origin/main.
    No toca dist/ (no está versionado: lo regenera GitHub Actions en cada push)."""
    print("4/4 publicar")

    rev_parse = _git("rev-parse", "--abbrev-ref", "HEAD")
    if rev_parse.returncode != 0:
        print("      No pude detectar la rama actual (¿esto es un repo git?). No se publicó.")
        print("      Corré 'git add', 'git commit' y 'git push' a mano si hace falta.")
        return
    rama = rev_parse.stdout.strip()
    if rama != "main":
        print(f"      Estás en la rama '{rama}', no en 'main'. Por seguridad no publico solo:")
        print(f"      corré 'git checkout main' y volvé a ejecutar esto, o pedile ayuda a quien te armó el sitio.")
        return

    try:
        xlsx_rel = xlsx_path.resolve().relative_to(ROOT)
    except ValueError:
        print("      El Excel no está dentro de este repo, así que no hay nada para commitear.")
        return

    xlsx_rel_str = str(xlsx_rel).replace("\\", "/")
    _git("add", "--", xlsx_rel_str)
    # el diff se limita al xlsx: si hay OTROS cambios ya staged por separado
    # (de otro trabajo en curso), no queremos arrastrarlos a este commit.
    diff = _git("diff", "--cached", "--quiet", "--", xlsx_rel_str)
    if diff.returncode == 0:
        print("      El Excel no tiene cambios respecto al último commit — nada para publicar.")
        return

    commit = _git("commit", "-m", "Actualizar menú desde el Excel maestro", "--", xlsx_rel_str)
    if commit.returncode != 0:
        print("      No pude hacer el commit:")
        print("      " + commit.stderr.strip().replace("\n", "\n      "))
        return
    print(f"      commit creado: {commit.stdout.strip().splitlines()[0] if commit.stdout else 'ok'}")

    push = _git("push", "origin", "main")
    if push.returncode != 0:
        print("      El commit se hizo pero el push falló (revisá tu conexión o permisos):")
        print("      " + push.stderr.strip().replace("\n", "\n      "))
        print("      Corré 'git push' a mano cuando se resuelva.")
        return
    print("      publicado. GitHub Actions va a reconstruir el sitio en un par de minutos:")
    print("      https://ameli-casa-de-te-brunch.github.io/")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--xlsx", type=Path, default=XLSX_POR_DEFECTO)
    ap.add_argument("--template", type=Path, default=ROOT / "templates" / "menu.template.html")
    ap.add_argument("--out", type=Path, default=ROOT / "dist" / "index.html")
    ap.add_argument("--dry-run", action="store_true", help="solo validar y reportar, no generar ni publicar nada")
    ap.add_argument("--no-push", action="store_true", help="generar dist/ localmente, pero no commitear ni pushear")
    args = ap.parse_args()

    print(f"1/4 extract  ({args.xlsx.name})")
    data = extract.extract(args.xlsx)
    (ROOT / "dist").mkdir(parents=True, exist_ok=True)
    (ROOT / "dist" / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"      {len(data['prods'])} productos activos, {len(data['cats'])} categorías")

    print("2/4 validate")
    errors, warnings = validate.validate(data, args.xlsx)
    for w in warnings:
        print(f"      [AVISO] {w}")
    for e in errors:
        print(f"      [ERROR] {e}")
    print(f"      {len(errors)} error(es), {len(warnings)} aviso(s)")
    if errors:
        print("\nBuild detenido: corregí los errores de arriba en el Excel maestro y volvé a correr")
        print("python build.py (o menu.bat). Nada se publicó.")
        sys.exit(1)

    if args.dry_run:
        print("\n--dry-run: no se generó ni publicó nada")
        return

    print("3/4 render")
    template = args.template.read_text(encoding="utf-8")
    html = render.render(data, template)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html, encoding="utf-8")
    print(f"      {args.out} ({len(html)} bytes)")

    local_config = ROOT / "config.js"
    dist_config = args.out.parent / "config.js"
    if local_config.exists():
        dist_config.write_text(local_config.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"      {dist_config} (copiado de config.js local)")
    elif not dist_config.exists():
        dist_config.write_text('window.AMELI_CONFIG = { votosEndpoint: "" };\n', encoding="utf-8")
        print(f"      {dist_config} (sin backend de votos configurado — ver backend/apps-script/README.md)")

    if args.no_push:
        print("\n--no-push: el sitio se generó en dist/ pero no se publicó")
        return

    publicar(args.xlsx)


if __name__ == "__main__":
    main()
