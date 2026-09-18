#!/usr/bin/env python3
"""extract -> validate -> render, con la publicación (git) como paso aparte y explícito.

Uso:
  python build.py                 # valida y arma dist/ en tu PC. No toca git.
  python build.py --dry-run       # solo valida y reporta, no escribe nada.
  python build.py --publicar      # además de lo anterior, ofrece publicar: te
                                   # muestra exactamente qué va a subir y pide
                                   # que escribas "si" para confirmar.
  python build.py --xlsx ruta.xlsx
  python build.py --sheets-productos URL --sheets-categorias URL --sheets-config URL
                                   # usa Google Sheets como fuente en vez del Excel (las tres
                                   # URLs son obligatorias juntas; --sheets-backoffice es
                                   # opcional). No se puede combinar con --xlsx.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "build"))
# aplicar_disponibilidad, config_local, extract_common, render y
# validate_json_publico son stdlib puro (ver requirements.txt) -- seguros
# de importar acá, a nivel de módulo. extract.py y validate.py son
# DELIBERADAMENTE la excepción: ambos importan openpyxl (la única
# dependencia de terceros de todo el pipeline), y los runners de CI nunca
# la instalan. Importarlos remoto (import build) no puede arrastrar esa
# dependencia -- por eso se cargan recién al ejecutar de verdad el flujo
# que abre el Excel, nunca al cargar este módulo (ver
# _cargar_dependencias_xlsx()/ejecutar() más abajo).
import aplicar_disponibilidad  # noqa: E402
import config_local  # noqa: E402
import extract_common  # noqa: E402
import render  # noqa: E402
import validate_json_publico  # noqa: E402

ROOT = Path(__file__).resolve().parent
MENU_JSON = ROOT / "data" / "menu.json"


class DocumentoPublicoInvalido(Exception):
    """Se levanta cuando el documento que armaría data/menu.json (el
    resultado de extract_common.datos_publicos(data)) no pasa su propio
    control independiente (validate_json_publico.validate_menu_json) --
    el mismo que corre en CI antes de renderizar. El mensaje nunca
    reproduce valores no confiables (ver validate_json_publico.py: esa
    garantía vive ahí, no acá)."""


class OpenpyxlNoInstalado(Exception):
    """Se levanta cuando hace falta leer el Excel maestro real (vía
    extract.py o validate.py) pero el paquete 'openpyxl' no está
    instalado. Nunca se levanta por el simple hecho de importar build.py
    -- solo al ejecutar de verdad el flujo local que abre un .xlsx (ver
    _cargar_dependencias_xlsx())."""


def _cargar_dependencias_xlsx():
    """Importa extract.py y validate.py recién ACÁ -- nunca a nivel de
    módulo -- porque son los dos únicos módulos de build/ que requieren
    openpyxl (para leer el Excel maestro real). Así "import build" (lo
    que hacen los tests, y cualquier otra herramienta que solo necesite
    -por ejemplo- preparar_en_memoria) nunca arrastra esa dependencia de
    terceros: ni los runners de CI (que corren sin pip install, solo
    stdlib) ni nadie que solo quiera importar este módulo la necesitan,
    con tal de no ejecutar el flujo real.

    Si openpyxl no está instalado, levanta OpenpyxlNoInstalado con un
    mensaje claro y accionable en vez de dejar que un
    ModuleNotFoundError crudo (con traceback) llegue hasta quien corre
    build.py."""
    try:
        import extract
        import validate
    except ModuleNotFoundError as e:
        if e.name != "openpyxl":
            raise
        raise OpenpyxlNoInstalado(
            "Falta el paquete 'openpyxl' (necesario para leer el Excel maestro real). "
            "Instalalo con: pip install -r requirements.txt"
        ) from None
    return extract, validate


def _git(*args):
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8"
    )


def _mensaje_url_publicada(url_base: str | None) -> str:
    """Arma la línea final de publicar() a partir de config.url_base --
    separada en su propia función, sin tocar git ni pedir confirmación,
    para poder probarla sola (ver tests/test_build.py). Nunca un dominio
    hardcodeado acá: sea cual sea el origen real vigente
    (amelicasadete.com.ar/menu/, el repo separado de antes como
    rollback, o cualquier otro que se configure en el futuro), el
    mensaje siempre refleja ese mismo dato, no un texto fijo que pueda
    quedar desactualizado."""
    if url_base:
        return url_base if url_base.endswith("/") else url_base + "/"
    return ("(config.url_base no está configurada -- revisá GitHub Pages, "
            "Settings, para la URL publicada real).")


def publicar(url_base: str | None = None):
    """Muestra EXACTAMENTE qué archivo cambiaría y pide confirmación explícita
    antes de commitear y pushear. Nunca commitea nada que no haya listado antes.

    url_base: el mismo config.url_base ya extraído del Excel/Sheets en esta
    corrida (ver ejecutar() más abajo) -- ver _mensaje_url_publicada()."""
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
    print(_mensaje_url_publicada(url_base))


def preparar_en_memoria(data: dict, disponibilidad_estricta: bool, consultar_disponibilidad: bool) -> str:
    """Hace, en memoria y sin tocar disco, todo lo que hace falta antes de
    poder decidir si se escribe algo:

    1. arma el documento público exacto (extract_common.datos_publicos(data),
       la misma función que extract.py re-exporta como extract.datos_publicos
       -- se usa acá directo porque extract_common no necesita openpyxl,
       así esta función nunca depende de que el Excel real sea legible)
       que iría a data/menu.json;
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
    documento_publico = extract_common.datos_publicos(data)

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


def _preparar_o_abortar(args, data) -> str:
    """Envoltorio de preparar_en_memoria() compartido por ejecutar() (Excel)
    y ejecutar_sheets() (Google Sheets) -- la validación del documento
    público y de disponibilidad en vivo no depende de la fuente, solo de
    `data` (ya en la forma común que arma extract_common.ensamblar()).

    Todo esto ocurre en memoria, ANTES de escribir cualquier archivo.
    Cuatro modos, según --dry-run/--disponibilidad-estricta:
      - "--dry-run" solo: valida el documento público, pero NUNCA consulta
        la hoja de disponibilidad (ni siquiera en modo no estricto) -- no
        hace falta red para poder decir "esto pasaría".
      - "--dry-run --disponibilidad-estricta": exige URL y hace la
        consulta/validación estricta real -- sirve para probar de verdad
        si la hoja real pasaría el modo estricto, sin escribir nada.
      - normal sin --disponibilidad-estricta: comportamiento de siempre --
        aplica disponibilidad en modo NO estricto si hay URL configurada,
        sigue sin aplicarla si no la hay.
      - normal con --disponibilidad-estricta: exige URL (una URL ausente
        es en sí misma un error acá) y valida en modo estricto.
    Un fallo en cualquiera de los dos controles (JSON público o
    disponibilidad) nunca deja data/menu.json, dist/index.html ni ningún
    otro output tocado -- el mensaje "no se generó ni publicó nada" sigue
    siendo cierto en los cuatro modos."""
    consultar_disponibilidad = args.disponibilidad_estricta or not args.dry_run
    try:
        return preparar_en_memoria(data, args.disponibilidad_estricta, consultar_disponibilidad)
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


def _generar_y_publicar(args, data, menu_json_texto: str) -> None:
    """Paso 3/3 compartido por ejecutar() y ejecutar_sheets(): escribir
    data/menu.json y dist/index.html, y opcionalmente ofrecer publicar.
    Nunca se llama si _preparar_o_abortar ya cortó con sys.exit(1), ni en
    --dry-run (ambos llamadores retornan antes)."""
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
        publicar(data["config"].get("url_base"))
    else:
        print()
        print("Listo en tu PC. Para publicar de verdad: python build.py --publicar")


def ejecutar(args, xlsx_path: Path, extract_mod=None, validate_mod=None) -> None:
    """extract_mod/validate_mod: inyección explícita de los módulos
    extract.py/validate.py (los dos únicos que requieren openpyxl) --
    los tests SIEMPRE los pasan (dobles simples, nunca el openpyxl real
    ni un mock global en sys.modules), así nunca necesitan que openpyxl
    esté instalado. Si se omite alguno, se cargan de verdad acá mismo,
    recién ahora, vía _cargar_dependencias_xlsx() -- el camino que usa
    main() en una corrida real."""
    if extract_mod is None or validate_mod is None:
        try:
            extract_cargado, validate_cargado = _cargar_dependencias_xlsx()
        except OpenpyxlNoInstalado as e:
            print("[ERROR] " + str(e))
            print("Build detenido. No se generó ni publicó nada.")
            sys.exit(1)
        extract_mod = extract_mod or extract_cargado
        validate_mod = validate_mod or validate_cargado

    print("1/3 extract  (" + xlsx_path.name + ")")
    data = extract_mod.extract(xlsx_path)
    print("      " + str(len(data["prods"])) + " productos activos, " + str(len(data["cats"])) + " categorías")

    print("2/3 validate")
    errors, warnings = validate_mod.validate(data, xlsx_path)
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

    menu_json_texto = _preparar_o_abortar(args, data)

    if args.dry_run:
        print()
        print("--dry-run: no se generó ni publicó nada")
        return

    _generar_y_publicar(args, data, menu_json_texto)


def ejecutar_sheets(args, urls: dict, extract_mod=None, validate_mod=None) -> None:
    """Mismo flujo de tres pasos que ejecutar(), pero leyendo el maestro
    desde Google Sheets (CSVs publicados) en vez del Excel. `urls` trae
    'productos'/'categorias'/'config' (obligatorias) y 'backoffice'
    (opcional, ver extract_sheets.extract()).

    extract_mod/validate_mod: misma inyección explícita que ejecutar() --
    pensada para que los tests puedan pasar dobles, aunque acá ninguno de
    los dos módulos reales (extract_sheets.py/validate_sheets.py) depende
    de openpyxl, así que no hace falta un _cargar_dependencias_xlsx()
    equivalente: importarlos de verdad es seguro incluso en un runner de
    CI sin ese paquete instalado."""
    if extract_mod is None:
        import extract_sheets as extract_mod
    if validate_mod is None:
        import validate_sheets as validate_mod

    print("1/3 extract  (Google Sheets)")
    data = extract_mod.extract(
        urls["productos"], urls["categorias"], urls["config"], urls.get("backoffice")
    )
    print("      " + str(len(data["prods"])) + " productos activos, " + str(len(data["cats"])) + " categorías")

    print("2/3 validate")
    filas_productos = extract_mod._leer_csv(urls["productos"])
    filas_config = extract_mod._leer_csv(urls["config"])
    errors, warnings = validate_mod.validate(data, filas_productos, filas_config)
    for w in warnings:
        print("      [AVISO] " + w)
    for e in errors:
        print("      [ERROR] " + e)
    print("      " + str(len(errors)) + " error(es), " + str(len(warnings)) + " aviso(s)")
    if errors:
        print()
        print("Build detenido: corregí los errores de arriba en el Sheet y volvé a correr")
        print("python build.py --sheets-productos ... Nada se generó ni se publicó.")
        sys.exit(1)

    menu_json_texto = _preparar_o_abortar(args, data)

    if args.dry_run:
        print()
        print("--dry-run: no se generó ni publicó nada")
        return

    _generar_y_publicar(args, data, menu_json_texto)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--xlsx", default=None, help="ruta al Excel maestro (si no, se resuelve solo)")
    ap.add_argument("--sheets-productos", default=None,
                     help="URL CSV publicada de la hoja Productos -- si se pasa, se usa Google "
                          "Sheets como fuente en vez del Excel (requiere también --sheets-categorias "
                          "y --sheets-config).")
    ap.add_argument("--sheets-categorias", default=None, help="URL CSV publicada de la hoja Categorías")
    ap.add_argument("--sheets-config", default=None, help="URL CSV publicada de la hoja Config")
    ap.add_argument("--sheets-backoffice", default=None,
                     help="URL CSV publicada de 'Productos - Backoffice' (opcional -- sin esto, "
                          "se publica igual pero sin datos de leche vegetal/sin lactosa)")
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

    urls_sheets = {
        "productos": args.sheets_productos,
        "categorias": args.sheets_categorias,
        "config": args.sheets_config,
    }
    algun_sheets_arg = any(urls_sheets.values()) or args.sheets_backoffice
    if algun_sheets_arg:
        faltantes = [nombre for nombre, url in urls_sheets.items() if not url]
        if faltantes:
            print(
                "Faltan URLs para usar Google Sheets como fuente: --sheets-"
                + ", --sheets-".join(faltantes)
                + ". Las tres (productos, categorías, config) son obligatorias juntas -- "
                  "--sheets-backoffice es la única opcional."
            )
            sys.exit(1)
        if args.sheets_backoffice:
            urls_sheets["backoffice"] = args.sheets_backoffice
        if args.xlsx:
            print("No se puede pasar --xlsx junto con --sheets-*: elegí una sola fuente.")
            sys.exit(1)
        ejecutar_sheets(args, urls_sheets)
        return

    xlsx_path = config_local.resolver_ruta_xlsx(args.xlsx)
    if not xlsx_path.exists():
        print(config_local.mensaje_no_encontrado(xlsx_path))
        sys.exit(1)

    ejecutar(args, xlsx_path)


if __name__ == "__main__":
    main()
