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
import validate_json_publico  # noqa: E402

ROOT = Path(__file__).resolve().parent
MENU_JSON = ROOT / "data" / "menu.json"


class DocumentoPublicoInvalido(Exception):
    """Se levanta cuando el documento que armaría data/menu.json (el
    resultado de extract.datos_publicos(data)) no pasa su propio control
    independiente (validate_json_publico.validate_menu_json) -- el mismo
    que corre en CI antes de renderizar. El mensaje nunca reproduce
    valores no confiables (ver validate_json_publico.py: esa garantía
    vive ahí, no acá)."""


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


def preparar_en_memoria(data: dict, disponibilidad_estricta: bool, consultar_disponibilidad: bool) -> str:
    """Hace, en memoria y sin tocar disco, todo lo que hace falta antes de
    poder decidir si se escribe algo:

    1. arma el documento público exacto (extract.datos_publicos(data)) que
       iría a data/menu.json;
    2. lo valida con validate_json_publico.validate_menu_json -- el mismo
       control independiente que corre en CI antes de renderizar. Un
       error acá (ERROR, no AVISO) levanta DocumentoPublicoInvalido SIN
       haber escrito nada todavía;
    3. si consultar_disponibilidad=True, aplica/valida la disponibilidad
       en vivo -- ver el parámetro más abajo;
    4. serializa a texto EXACTAMENTE el documento ya validado en el paso 2
       (nunca uno recalculado después) -- así el JSON versionado nunca
       incorpora la disponibilidad efímera aplicada en memoria sobre
       data["prods"] para el render (esa mutación pasa DESPUÉS de
       serializar). El commiteado refleja el Excel; la hoja lo pisa recién
       al renderizar, y de nuevo en cada rebuild que dispare el Apps
       Script vía GitHub Actions (ver aplicar_disponibilidad.py).

    consultar_disponibilidad: si False, ni siquiera se mira si hay una URL
    configurada -- no se hace ninguna llamada de red ni a
    aplicar_a_prods. Lo usa "--dry-run" sin "--disponibilidad-estricta":
    ese modo valida el Excel y el JSON público, pero no tiene por qué
    consultar la hoja en vivo para poder decir "esto pasaría". Cuando es
    True: si disponibilidad_estricta=True, una URL ausente es en sí misma
    un error (se exige, no es opcional en modo estricto); si hay URL, se
    aplica (estricta u no, según disponibilidad_estricta) y un problema en
    modo estricto propaga aplicar_disponibilidad.DisponibilidadInvalida
    SIN haber escrito nada todavía -- es responsabilidad del llamador no
    escribir ningún archivo si cualquiera de estas dos excepciones
    levanta."""
    documento_publico = extract.datos_publicos(data)

    print("      validando documento público (data/menu.json)")
    errores_json, avisos_json = validate_json_publico.validate_menu_json(documento_publico)
    for w in avisos_json:
        print("      [AVISO] " + w)
    for e in errores_json:
        print("      [ERROR] " + e)
    if errores_json:
        raise DocumentoPublicoInvalido(
            str(len(errores_json)) + " error(es) en el documento público -- ver arriba."
        )

    if consultar_disponibilidad:
        url_disponibilidad = data["config"].get("disponibilidad_csv_url")
        if disponibilidad_estricta and not url_disponibilidad:
            raise aplicar_disponibilidad.DisponibilidadInvalida(
                "DISPONIBILIDAD_CSV_URL no está configurada -- en modo estricto es obligatoria, "
                "no se continúa sin ella."
            )
        if url_disponibilidad:
            aplicar_disponibilidad.aplicar_a_prods(
                data["prods"], url_disponibilidad, estricto=disponibilidad_estricta
            )

    return json.dumps(documento_publico, ensure_ascii=False, indent=1)


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

    # Todo esto (extracción, validación del JSON público y, según el modo,
    # validación estricta de disponibilidad en vivo) ocurre en memoria,
    # ANTES de escribir cualquier archivo. Cuatro modos, según
    # --dry-run/--disponibilidad-estricta:
    #   - "--dry-run" solo: valida el Excel y el JSON público, pero NUNCA
    #     consulta la hoja (ni siquiera en modo no estricto) -- no hace
    #     falta red para poder decir "esto pasaría".
    #   - "--dry-run --disponibilidad-estricta": exige URL y hace la
    #     consulta/validación estricta real -- sirve para probar de
    #     verdad si la hoja real pasaría el modo estricto, sin escribir
    #     nada.
    #   - normal sin --disponibilidad-estricta: comportamiento de siempre
    #     -- aplica disponibilidad en modo NO estricto si hay URL
    #     configurada, sigue sin aplicarla si no la hay.
    #   - normal con --disponibilidad-estricta: exige URL (una URL
    #     ausente es en sí misma un error acá) y valida en modo estricto.
    # Un fallo en cualquiera de los dos controles (JSON público o
    # disponibilidad) nunca deja data/menu.json, dist/index.html ni ningún
    # otro output tocado -- el mensaje "no se generó ni publicó nada"
    # sigue siendo cierto en los cuatro modos.
    consultar_disponibilidad = args.disponibilidad_estricta or not args.dry_run
    try:
        menu_json_texto = preparar_en_memoria(data, args.disponibilidad_estricta, consultar_disponibilidad)
    except DocumentoPublicoInvalido as e:
        print()
        print("[ERROR] El documento público (data/menu.json) no pasa su propia validación: " + str(e))
        print("Build detenido. No se generó ni publicó nada.")
        sys.exit(1)
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
