#!/usr/bin/env python3
"""Un solo comando: extract -> validate -> render.

Uso:
  python build.py              # valida y publica dist/index.html
  python build.py --dry-run    # solo extrae y valida, no escribe dist/index.html
  python build.py --xlsx ruta/al/maestro.xlsx
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "build"))
import extract  # noqa: E402
import render  # noqa: E402
import validate  # noqa: E402

ROOT = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--xlsx", type=Path, default=ROOT / "data" / "Ameli_Menu_Maestro_V2.1.xlsx")
    ap.add_argument("--template", type=Path, default=ROOT / "templates" / "menu.template.html")
    ap.add_argument("--out", type=Path, default=ROOT / "dist" / "index.html")
    ap.add_argument("--dry-run", action="store_true", help="solo extraer y validar, no publicar")
    args = ap.parse_args()

    print(f"1/3 extract  ({args.xlsx.name})")
    data = extract.extract(args.xlsx)
    (ROOT / "dist").mkdir(parents=True, exist_ok=True)
    (ROOT / "dist" / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"      {len(data['prods'])} productos activos, {len(data['cats'])} categorías")

    print("2/3 validate")
    errors, warnings = validate.validate(data, args.xlsx)
    for w in warnings:
        print(f"      [WARN]  {w}")
    for e in errors:
        print(f"      [ERROR] {e}")
    print(f"      {len(errors)} error(es), {len(warnings)} warning(s)")
    if errors:
        print("\nBuild detenido: corregí los errores en el maestro antes de publicar.")
        sys.exit(1)

    if args.dry_run:
        print("\n--dry-run: no se generó dist/index.html")
        return

    print("3/3 render")
    template = args.template.read_text(encoding="utf-8")
    html = render.render(data, template)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html, encoding="utf-8")
    print(f"      {args.out} ({len(html)} bytes)")


if __name__ == "__main__":
    main()
