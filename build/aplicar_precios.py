#!/usr/bin/env python3
"""Lee los precios (y los tipos de cambio) desde una pestaña de Google Sheets
"publicada en la web" (CSV) y los aplica sobre data/menu.json, para poder
cambiar un precio desde la computadora del local sin correr el build en la PC
del dueño.

Mismo circuito que disponibilidad y calendario: una URL https de
docs.google.com en una repo variable (PRECIOS_CSV_URL, no es un secreto: los
precios del menú son públicos), descarga restringida a Google, validación
estricta y mensajes que nunca reproducen el contenido de una celda.

Un precio mal cargado es peor que un precio viejo, así que la validación es
más dura que en el calendario:
  - TODOS los productos con precio tienen que estar en la hoja, y ninguno
    desconocido (una fila ausente nunca significa "dejar como estaba").
  - Cada precio es un número entero de pesos razonable (500 a 200.000).
  - No se puede agregar ni quitar un tamaño (Chico/Grande, Vaso/Jarra) desde
    la hoja: eso cambia la estructura del menú y se hace desde el Excel maestro.
  - Ningún precio puede cambiar más de MAX_CAMBIO (60 %) de una vez: un cero
    de más o de menos se frena acá. Un ajuste real tan grande se hace desde el
    Excel maestro.
Cada fila es independiente (desde 2026-10-14): una fila mala NO frena a las
demás. Esa fila se omite (el producto conserva el precio que ya tenía en
data/menu.json), se aplican las filas válidas y el paso marca precios_ok=false
para que el workflow ponga la corrida en rojo DESPUÉS de publicar (job
avisar-hojas) y avise qué fila corregir. Lo único que sigue siendo todo o nada
es lo estructural: encabezado, hoja vacía o demasiado grande y las tres filas
de tipo de cambio (si una tasa falla, todos los equivalentes en otras monedas
quedarían mal). Un error de precios no frena un "agotado por hoy".

Columnas de la pestaña (primera fila = encabezado, en cualquier orden):
  id, precio_chico, precio_grande     obligatorias (precio_grande puede quedar
                                      vacía en los productos de un solo precio)
  nombre, categoria, nota             opcionales, solo para las personas (nunca
                                      se leen ni se publican)
Tres filas especiales con id TASA_USD, TASA_EUR y TASA_BRL llevan, en
precio_chico, cuántos pesos vale una unidad (se usan para los equivalentes
"≈ USD 3" que muestra el menú; son orientativos, no una cotización en vivo).
Los números pueden venir como 4800, 4.800 o $ 4.800.

    python build/aplicar_precios.py                 # CI: lee PRECIOS_CSV_URL
    python build/aplicar_precios.py --comparar      # solo lectura: qué cambiaría
    python build/aplicar_precios.py --plantilla 1485 1715 289   # CSV inicial

Solo biblioteca estándar.
"""
import csv
import io
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import extract_common as ec  # noqa: E402
import hoja_publica  # noqa: E402

MENU_JSON = HERE.parent / "data" / "menu.json"

ENCABEZADOS_PERMITIDOS = ("id", "nombre", "categoria", "precio_chico", "precio_grande", "nota")
ENCABEZADOS_OBLIGATORIOS = ("id", "precio_chico", "precio_grande")
FILAS_DE_TASAS = {"TASA_USD": "usd", "TASA_EUR": "eur", "TASA_BRL": "brl"}
RANGO_TASAS = {"usd": (100, 20000), "eur": (100, 20000), "brl": (20, 5000)}
PRECIO_MIN, PRECIO_MAX = 500, 200000
MAX_CAMBIO = 0.60
MAX_FILAS = 500

_RE_ENTERO = re.compile(r"^\d+$")
_RE_MILES = re.compile(r"^\d{1,3}(\.\d{3})+$")
_RE_TASA = re.compile(r"^(\d+|\d{1,3}(\.\d{3})+)(,\d{1,2})?$")


class PreciosInvalidos(Exception):
    """Hoja de precios que no se puede confiar. El mensaje nunca incluye la URL
    ni el texto crudo de una celda (sí números de fila e IDs de productos que
    ya existen en data/menu.json)."""


_RedirectHandlerRestringido = hoja_publica.manejador_de_redirecciones(PreciosInvalidos, "de precios")


def _descargar(url: str, timeout: int = 10) -> str:
    return hoja_publica.descargar_csv(url, "de precios", PreciosInvalidos, timeout)


# ----------------------------------------------------------------------------
# Números
# ----------------------------------------------------------------------------
def _limpiar(texto: str) -> str:
    return texto.replace("$", "").replace(" ", "").replace(" ", "").strip()


def parsear_pesos(texto):
    """'4800' / '4.800' / '$ 4.800' -> 4800. '' -> None (celda vacía).
    Cualquier otra cosa (decimales, comas, letras) -> False."""
    t = _limpiar(texto)
    if t == "":
        return None
    if _RE_ENTERO.match(t):
        return int(t)
    if _RE_MILES.match(t):
        return int(t.replace(".", ""))
    return False


def parsear_tasa(texto):
    t = _limpiar(texto)
    if t == "" or not _RE_TASA.match(t):
        return False
    v = float(t.replace(".", "").replace(",", "."))
    return int(v) if v == int(v) else v


# ----------------------------------------------------------------------------
# Estado actual (data/menu.json) -> (chico, grande) por producto
# ----------------------------------------------------------------------------
def _pesos_de_texto_publicado(ars: str):
    m = re.fullmatch(r"\$ (\d{1,3}(?:\.\d{3})*|\d+)", ars)
    return int(m.group(1).replace(".", "")) if m else None


def desarmar_precio(entrada: dict):
    """(chico, grande|None) de una entrada de data/menu.json, o None si tiene un
    formato que la hoja no sabe manejar."""
    niveles = entrada.get("niveles")
    if niveles:
        chico = _pesos_de_texto_publicado(niveles[0]["ars"])
        grande = _pesos_de_texto_publicado(niveles[1]["ars"])
        return (chico, grande) if chico is not None and grande is not None else None
    chico = _pesos_de_texto_publicado(entrada["ars"])
    return (chico, None) if chico is not None else None


def precios_actuales(data: dict) -> dict:
    """{id: (chico, grande|None)} de todos los productos con precio editable."""
    salida = {}
    for pid, entrada in data["precios"].items():
        par = desarmar_precio(entrada)
        if par is not None:
            salida[pid] = par
    return salida


# ----------------------------------------------------------------------------
# Lectura y validación de la hoja
# ----------------------------------------------------------------------------
def parsear_csv(contenido: str, data: dict) -> tuple:
    """Modo estricto: devuelve (tasas, precios, problemas) y, si hay CUALQUIER
    problema (de estructura o de una fila), (None, None, problemas). Es lo que
    verifica que la plantilla leída de vuelta reproduce los precios publicados;
    la publicación usa parsear_csv_por_fila()."""
    tasas, precios, bloqueantes, omitidos = parsear_csv_por_fila(contenido, data)
    problemas = list(bloqueantes) + list(omitidos)
    if problemas:
        return None, None, problemas
    return tasas, precios, []


def parsear_csv_por_fila(contenido: str, data: dict) -> tuple:
    """Devuelve (tasas, precios, bloqueantes, omitidos).
    tasas = {'usd':..,'eur':..,'brl':..}; precios = {id: (chico, grande|None)}
    SOLO con las filas válidas. bloqueantes: problemas de estructura o de las
    filas de tipo de cambio (no se puede aplicar nada; precios y tasas vienen en
    None). omitidos: filas de producto con problemas, que se saltean (el producto
    conserva su precio). Nunca levanta: el llamador decide."""
    filas = list(csv.reader(io.StringIO(contenido)))
    if not filas:
        return None, None, ["La hoja de precios está vacía (ni encabezado)."], []

    encabezado = [c.strip().lower() for c in filas[0]]
    problemas = []
    desconocidos = [c for c in encabezado if c and c not in ENCABEZADOS_PERMITIDOS]
    if desconocidos:
        problemas.append(f"El encabezado tiene {len(desconocidos)} columna(s) que no existen. "
                         f"Solo se permiten: {', '.join(ENCABEZADOS_PERMITIDOS)}.")
    no_vacios = [c for c in encabezado if c]
    if len(set(no_vacios)) != len(no_vacios):
        problemas.append("El encabezado tiene columnas repetidas.")
    faltan = [c for c in ENCABEZADOS_OBLIGATORIOS if c not in encabezado]
    if faltan:
        problemas.append(f"Faltan columnas obligatorias en el encabezado: {', '.join(faltan)}.")
    if problemas:
        return None, None, problemas, []
    if len(filas) - 1 > MAX_FILAS:
        return None, None, [f"Demasiadas filas ({len(filas) - 1}); el máximo es {MAX_FILAS}."], []

    indice = {c: i for i, c in enumerate(encabezado) if c}

    def celda(fila, nombre):
        i = indice.get(nombre)
        return fila[i].strip() if i is not None and i < len(fila) else ""

    actuales = precios_actuales(data)
    tasas, precios, vistos_fila = {}, {}, {}
    omitidos = []
    for numero, fila in enumerate(filas[1:], start=2):
        if not any(c.strip() for c in fila):
            continue
        pid = celda(fila, "id")
        if not pid:
            omitidos.append(f"Fila {numero}: tiene datos pero no tiene ID.")
            continue

        if pid in FILAS_DE_TASAS:
            clave = FILAS_DE_TASAS[pid]
            if clave in tasas:
                problemas.append(f"Fila {numero}: repite la fila {pid} (ya está en la fila {vistos_fila[pid]}).")
                continue
            vistos_fila[pid] = numero
            valor = parsear_tasa(celda(fila, "precio_chico"))
            lo, hi = RANGO_TASAS[clave]
            if valor is False or not lo <= valor <= hi:
                problemas.append(f"Fila {numero}: {pid} tiene que ser un número entre {lo} y {hi} "
                                 "(cuántos pesos vale una unidad).")
                continue
            if celda(fila, "precio_grande"):
                problemas.append(f"Fila {numero}: {pid} solo lleva valor en precio_chico.")
                continue
            tasas[clave] = valor
            continue

        if pid not in actuales:
            # Nunca el texto de la celda: puede no ser un ID.
            omitidos.append(f"Fila {numero}: el ID no corresponde a ningún producto con precio publicado.")
            continue
        if pid in vistos_fila:
            omitidos.append(f"El producto '{pid}' está repetido en la hoja de precios: filas {vistos_fila[pid]} y {numero}. "
                            "No se aplica ninguna de las dos.")
            precios.pop(pid, None)
            continue
        vistos_fila[pid] = numero

        chico = parsear_pesos(celda(fila, "precio_chico"))
        grande = parsear_pesos(celda(fila, "precio_grande"))
        if chico is None or chico is False:
            omitidos.append(f"Fila {numero} ('{pid}'): precio_chico tiene que ser un número entero de pesos (ej. 4800 o 4.800).")
            continue
        if grande is False:
            omitidos.append(f"Fila {numero} ('{pid}'): precio_grande tiene que estar vacío o ser un número entero de pesos.")
            continue
        if not PRECIO_MIN <= chico <= PRECIO_MAX or (grande is not None and not PRECIO_MIN <= grande <= PRECIO_MAX):
            omitidos.append(f"Fila {numero} ('{pid}'): los precios tienen que estar entre {PRECIO_MIN} y {PRECIO_MAX}.")
            continue

        viejo_chico, viejo_grande = actuales[pid]
        if (viejo_grande is None) != (grande is None):
            omitidos.append(f"Fila {numero} ('{pid}'): no se puede agregar ni quitar un tamaño desde la hoja "
                             "(Chico/Grande o Vaso/Jarra): eso se cambia desde el Excel maestro.")
            continue
        if grande is not None and grande < chico:
            omitidos.append(f"Fila {numero} ('{pid}'): el precio grande no puede ser menor que el chico.")
            continue
        for nuevo, viejo in ((chico, viejo_chico), (grande, viejo_grande)):
            if nuevo is not None and abs(nuevo - viejo) / viejo > MAX_CAMBIO:
                omitidos.append(f"Fila {numero} ('{pid}'): el cambio supera el {int(MAX_CAMBIO * 100)} % del precio "
                                 "publicado (¿un cero de más o de menos?). Un ajuste así de grande se hace desde el Excel maestro.")
                break
        else:
            precios[pid] = (chico, grande)

    for clave in ("usd", "eur", "brl"):
        if f"TASA_{clave.upper()}" not in vistos_fila:
            problemas.append(f"Falta la fila TASA_{clave.upper()} (cuántos pesos vale una unidad).")
    ausentes = sorted(set(actuales) - set(vistos_fila))
    for pid in ausentes:
        omitidos.append(f"El producto '{pid}' no tiene fila en la hoja de precios: conserva el precio publicado "
                        "(una fila ausente nunca se interpreta como un cambio).")
    if problemas:
        return None, None, problemas, omitidos
    return tasas, precios, [], omitidos


# ----------------------------------------------------------------------------
# Armado de las entradas (las mismas funciones que usa el extractor)
# ----------------------------------------------------------------------------
def armar_entrada(cat_cod: str, chico: int, grande, tasas: dict) -> dict:
    """Misma estructura que extract_common.armar_datos_publicos():
    ars (+ usd/eur/brl del precio chico) y, con dos tamaños, niveles."""
    entrada = {"ars": ec.formatear_precio(chico, grande, cat_cod)}
    for clave, simbolo in (("usd", "USD"), ("eur", "EUR"), ("brl", "R$")):
        texto = ec.equivalente(chico, tasas[clave], simbolo)
        if texto:
            entrada[clave] = texto
    niveles = ec.niveles_precio(chico, grande, cat_cod, tasas["usd"], tasas["eur"], tasas["brl"])
    if niveles:
        entrada["niveles"] = niveles
    return entrada


def nuevos_precios(data: dict, tasas: dict, precios: dict) -> dict:
    cat_de = {p["id"]: p["cat"] for p in data["prods"]}
    resultado = dict(data["precios"])
    for pid, (chico, grande) in precios.items():
        resultado[pid] = armar_entrada(cat_de[pid], chico, grande, tasas)
    return resultado


def aplicar_a_archivo(url: str, menu_json_path: Path = MENU_JSON, timeout: int = 10) -> tuple:
    """Descarga, valida y parchea data/menu.json. Devuelve (cambiados, omitidos):
    cuántos productos cambiaron de precio (0 = sin cambios, no se reescribe el
    archivo) y la lista de filas que se saltearon por tener problemas (esas
    conservan su precio). Levanta PreciosInvalidos, SIN haber tocado nada, solo
    ante un problema estructural o de tipo de cambio."""
    data = json.loads(Path(menu_json_path).read_text(encoding="utf-8"))
    tasas, precios, bloqueantes, omitidos = parsear_csv_por_fila(_descargar(url, timeout), data)
    if bloqueantes:
        raise PreciosInvalidos("La hoja de precios tiene datos que no se pueden confiar:\n  - "
                               + "\n  - ".join(bloqueantes + omitidos))
    nuevos = nuevos_precios(data, tasas, precios)
    cambiados = [pid for pid in nuevos if nuevos[pid] != data["precios"][pid]]
    if cambiados:
        data["precios"] = nuevos
        ruta = Path(menu_json_path)
        temporal = ruta.with_suffix(".json.tmp")
        temporal.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        temporal.replace(ruta)
    return len(cambiados), omitidos


def comparar(url: str, menu_json_path: Path = MENU_JSON) -> list:
    """Solo lectura: líneas legibles con lo que cambiaría. No escribe nada."""
    data = json.loads(Path(menu_json_path).read_text(encoding="utf-8"))
    tasas, precios, bloqueantes, omitidos = parsear_csv_por_fila(_descargar(url), data)
    if bloqueantes:
        raise PreciosInvalidos("La hoja de precios tiene datos que no se pueden confiar:\n  - "
                               + "\n  - ".join(bloqueantes + omitidos))
    nombre = {p["id"]: p["n"]["es"] for p in data["prods"]}
    nuevos = nuevos_precios(data, tasas, precios)
    lineas = [f"{pid} {nombre[pid]}: {data['precios'][pid]['ars']}  ->  {nuevos[pid]['ars']}"
              for pid in nuevos if nuevos[pid] != data["precios"][pid]]
    return lineas + [f"SE OMITE: {o}" for o in omitidos]


# ----------------------------------------------------------------------------
# Plantilla inicial de la pestaña
# ----------------------------------------------------------------------------
def plantilla_csv(data: dict, tasa_usd, tasa_eur, tasa_brl) -> str:
    """CSV para pegar en una pestaña nueva: una fila por producto (en el orden
    del menú) con sus precios de hoy, más las tres filas de tipo de cambio."""
    cat_nombre = {c["cod"]: c["nom"]["es"] for c in data["cats"]}
    cat_orden = {c["cod"]: c["orden"] for c in data["cats"]}
    salida = io.StringIO()
    w = csv.writer(salida, lineterminator="\n")
    w.writerow(["id", "nombre", "categoria", "precio_chico", "precio_grande", "nota"])
    for pid, nombre, valor in (("TASA_USD", "Tipo de cambio: pesos por 1 dólar", tasa_usd),
                               ("TASA_EUR", "Tipo de cambio: pesos por 1 euro", tasa_eur),
                               ("TASA_BRL", "Tipo de cambio: pesos por 1 real", tasa_brl)):
        w.writerow([pid, nombre, "", valor, "", "Orientativo: se usa para los equivalentes en otras monedas"])
    actuales = precios_actuales(data)
    for p in sorted(data["prods"], key=lambda p: (cat_orden.get(p["cat"], 999), p["orden"], p["id"])):
        if p["id"] not in actuales:
            continue
        chico, grande = actuales[p["id"]]
        w.writerow([p["id"], p["n"]["es"], cat_nombre.get(p["cat"], p["cat"]), chico,
                    "" if grande is None else grande, ""])
    return salida.getvalue()


# ----------------------------------------------------------------------------
def _salida(clave: str, valor: str) -> None:
    ruta = os.environ.get("GITHUB_OUTPUT")
    if ruta:
        with open(ruta, "a", encoding="utf-8") as f:
            f.write(f"{clave}={valor}\n")


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["--plantilla"]:
        if len(argv) != 4:
            print("Uso: python build/aplicar_precios.py --plantilla TASA_USD TASA_EUR TASA_BRL")
            return 2
        data = json.loads(MENU_JSON.read_text(encoding="utf-8"))
        sys.stdout.write(plantilla_csv(data, *argv[1:4]))
        return 0
    url = os.environ.get("PRECIOS_CSV_URL", "").strip()
    if argv[:1] == ["--comparar"]:
        if not url:
            print("Falta la variable de entorno PRECIOS_CSV_URL.")
            return 2
        try:
            lineas = comparar(url)
        except PreciosInvalidos as e:
            print(e)
            return 1
        print("\n".join(lineas) if lineas else "Sin diferencias: la hoja coincide con data/menu.json.")
        return 0

    if not url:
        print("Precios: no hay PRECIOS_CSV_URL configurada -- se usan los precios de data/menu.json.")
        _salida("precios_ok", "true")
        return 0
    try:
        n, omitidos = aplicar_a_archivo(url)
    except PreciosInvalidos as e:
        print("::warning::Precios de la hoja NO aplicados -- se conservan los de data/menu.json.")
        print(e)
        _salida("precios_ok", "false")
        return 0
    except Exception as e:  # un bug acá no puede frenar la publicación del menú
        print(f"::warning::Precios de la hoja NO aplicados ({type(e).__name__}) -- se conservan los de data/menu.json.")
        _salida("precios_ok", "false")
        return 0
    print(f"Precios: {n} producto(s) con precio actualizado desde la hoja." if n else
          "Precios: la hoja coincide con data/menu.json, sin cambios.")
    if omitidos:
        # Las filas válidas ya se aplicaron; la corrida se marca en rojo para que alguien corrija estas.
        print(f"::warning::Precios: {len(omitidos)} fila(s) de la hoja NO se aplicaron (esos productos "
              "conservan el precio publicado):")
        print("  - " + "\n  - ".join(omitidos))
        _salida("precios_ok", "false")
        return 0
    _salida("precios_ok", "true")
    return 0


if __name__ == "__main__":
    sys.exit(main())
