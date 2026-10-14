#!/usr/bin/env python3
"""Calendario de temas estacionales (Halloween, Navidad, etc.).

Fuente única: data/calendario.json. La leen los dos builds (la web
institucional y el menú) y la embeben en el HTML como un bloque JSON de
datos (<script type="application/json" id="ameli-calendario">). Un script
chico (assets/js/tema.js) decide en el navegador, con la fecha de
Mendoza, qué tema está activo -- por eso un tema empieza y termina solo,
sin republicar nada, y fuera de sus fechas el sitio es el diseño original.

Validación estricta (mismo criterio que validate_json_publico.py): un
dato mal cargado hace fallar el build en vez de publicarse a medias.
Solo biblioteca estándar.
"""
import datetime
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_CALENDARIO = HERE.parent / "data" / "calendario.json"

ZONA_HORARIA = "America/Argentina/Mendoza"

# Temas que existen de verdad en el CSS (assets/css/temas.css de cada
# sitio). Un evento no puede apuntar a un tema que no esté acá: se agrega
# primero el CSS del tema y después se lo agrega a esta lista.
TEMAS_CONOCIDOS = ("encantada",)

# Tipos de evento:
#   tema              cambia colores/adornos (ver assets/js/tema.js)
#   cierre            el local no abre en esas fechas
#   horario_especial  horario distinto al habitual en esas fechas
#   aviso             un mensaje visible en esas fechas
#   campana           un bloque destacado (título + texto + botón de pedido por
#                     WhatsApp) en la portada y en el menú durante esas fechas
# Los cuatro últimos los lee assets/js/agenda.js (cartel "Abierto/Cerrado",
# aviso del día y campaña).
TIPOS_CONOCIDOS = ("tema", "cierre", "horario_especial", "aviso", "campana")

CAMPOS_RAIZ_PERMITIDOS = ("version", "zona_horaria", "activo", "eventos")
CAMPOS_COMUNES = ("id", "tipo", "desde", "hasta", "prioridad")
# Campos propios de cada tipo: lo que no corresponde al tipo es un error (una
# fila de cierre con un tema cargado casi siempre es una fila mal copiada).
CAMPOS_PROPIOS = {
    "tema": ("tema",),
    "cierre": ("mensaje", "mensaje_en"),
    "horario_especial": ("horario", "mensaje", "mensaje_en"),
    "aviso": ("mensaje", "mensaje_en"),
    "campana": ("titulo", "titulo_en", "mensaje", "mensaje_en"),
}
CAMPOS_OBLIGATORIOS_PROPIOS = {
    "tema": ("tema",),
    "cierre": (),
    "horario_especial": ("horario",),
    "aviso": ("mensaje",),
    "campana": ("titulo",),
}
CAMPOS_EVENTO_PERMITIDOS = CAMPOS_COMUNES + ("tema", "horario", "mensaje", "mensaje_en", "titulo", "titulo_en")
CAMPOS_EVENTO_OBLIGATORIOS = ("id", "tipo", "desde", "hasta")

MAX_MENSAJE = 140
MAX_TITULO = 40
MAX_FRANJAS = 3
MAX_EVENTOS = 200
_RE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
_RE_FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_RE_FRANJA = re.compile(r"^(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})$")


def _fecha_valida(valor) -> bool:
    if not isinstance(valor, str) or not _RE_FECHA.match(valor):
        return False
    try:
        datetime.date.fromisoformat(valor)
    except ValueError:
        return False
    return True


def franjas_de_horario(texto):
    """'10:00-14:00; 18:00-21:00' -> [[10,0,14,0],[18,0,21,0]]; None si el
    texto no es un horario válido (1 a 3 franjas separadas por ';', cada una
    HH:MM-HH:MM del mismo día, en orden y sin superponerse)."""
    if not isinstance(texto, str):
        return None
    partes = [p.strip() for p in texto.split(";")]
    if not 1 <= len(partes) <= MAX_FRANJAS:
        return None
    franjas, fin_anterior = [], -1
    for p in partes:
        m = _RE_FRANJA.match(p)
        if not m:
            return None
        h1, m1, h2, m2 = (int(x) for x in m.groups())
        if h1 > 23 or h2 > 23 or m1 > 59 or m2 > 59:
            return None
        ini, fin = h1 * 60 + m1, h2 * 60 + m2
        if fin <= ini or ini < fin_anterior:
            return None
        fin_anterior = fin
        franjas.append([h1, m1, h2, m2])
    return franjas


def horario_canonico(franjas) -> str:
    return "; ".join(f"{a:02d}:{b:02d}-{c:02d}:{d:02d}" for a, b, c, d in franjas)


def mensaje_valido(texto, maximo=MAX_MENSAJE) -> bool:
    """Texto corto, imprimible, sin HTML ni enlaces. Se muestra siempre con
    textContent (nunca como HTML), pero igual se rechaza lo que podría usarse
    para engañar: etiquetas, URLs."""
    if not isinstance(texto, str) or not texto.strip() or len(texto) > maximo:
        return False
    if texto != texto.strip() or not texto.isprintable():
        return False
    bajo = texto.lower()
    return not any(x in texto for x in "<>") and "://" not in bajo and "www." not in bajo


def validar(doc) -> list:
    """Devuelve la lista de errores (vacía si el calendario es válido)."""
    errores = []
    if not isinstance(doc, dict):
        return ["El calendario tiene que ser un objeto JSON."]

    desconocidos = set(doc.keys()) - set(CAMPOS_RAIZ_PERMITIDOS)
    if desconocidos:
        errores.append(f"Campos no permitidos en la raíz: {len(desconocidos)}. Solo {list(CAMPOS_RAIZ_PERMITIDOS)}.")

    if doc.get("version") != 1:
        errores.append("'version' tiene que ser 1.")
    if doc.get("zona_horaria") != ZONA_HORARIA:
        errores.append(f"'zona_horaria' tiene que ser exactamente {ZONA_HORARIA!r}.")
    if not isinstance(doc.get("activo"), bool):
        errores.append("'activo' tiene que ser true o false (interruptor general: false apaga todos los temas).")

    eventos = doc.get("eventos")
    if not isinstance(eventos, list):
        errores.append("'eventos' tiene que ser una lista.")
        return errores
    if len(eventos) > MAX_EVENTOS:
        errores.append(f"Demasiados eventos ({len(eventos)}); el máximo es {MAX_EVENTOS}.")
        return errores

    ids_vistos = set()
    for i, ev in enumerate(eventos):
        etiqueta = f"eventos[{i}]"
        if not isinstance(ev, dict):
            errores.append(f"{etiqueta}: tiene que ser un objeto.")
            continue
        ev_id = ev.get("id")
        if isinstance(ev_id, str) and _RE_ID.match(ev_id):
            etiqueta = f"evento {ev_id!r}"
        tipo = ev.get("tipo")
        faltan = [c for c in CAMPOS_EVENTO_OBLIGATORIOS if c not in ev]
        if tipo in TIPOS_CONOCIDOS:
            faltan += [c for c in CAMPOS_OBLIGATORIOS_PROPIOS[tipo] if c not in ev]
        if faltan:
            errores.append(f"{etiqueta}: faltan campos obligatorios {faltan}.")
        extra = set(ev.keys()) - set(CAMPOS_EVENTO_PERMITIDOS)
        if extra:
            errores.append(f"{etiqueta}: {len(extra)} campo(s) no permitido(s). Solo {list(CAMPOS_EVENTO_PERMITIDOS)}.")
        if tipo in TIPOS_CONOCIDOS:
            ajenos = [c for c in ev if c in CAMPOS_EVENTO_PERMITIDOS and c not in CAMPOS_COMUNES
                      and c not in CAMPOS_PROPIOS[tipo]]
            if ajenos:
                errores.append(f"{etiqueta}: {ajenos} no corresponde(n) a un evento de tipo '{tipo}'.")

        if "id" in ev:
            if not (isinstance(ev_id, str) and _RE_ID.match(ev_id)):
                errores.append(f"{etiqueta}: 'id' tiene que ser minúsculas, números y guiones (máx. 40).")
            elif ev_id in ids_vistos:
                errores.append(f"{etiqueta}: 'id' repetido.")
            else:
                ids_vistos.add(ev_id)
        if "tipo" in ev and tipo not in TIPOS_CONOCIDOS:
            errores.append(f"{etiqueta}: 'tipo' tiene que ser uno de {list(TIPOS_CONOCIDOS)}.")
        if "tema" in ev and ev["tema"] not in TEMAS_CONOCIDOS:
            errores.append(f"{etiqueta}: 'tema' tiene que ser uno de {list(TEMAS_CONOCIDOS)}.")
        if "horario" in ev and franjas_de_horario(ev["horario"]) is None:
            errores.append(f"{etiqueta}: 'horario' tiene que ser de 1 a {MAX_FRANJAS} franjas HH:MM-HH:MM separadas por ';', "
                           "en orden y sin superponerse (ej. 10:00-14:00; 18:00-21:00).")
        for campo in ("mensaje", "mensaje_en"):
            if campo in ev and not mensaje_valido(ev[campo]):
                errores.append(f"{etiqueta}: '{campo}' tiene que ser un texto de hasta {MAX_MENSAJE} caracteres, "
                               "sin < >, sin enlaces y sin espacios al principio o al final.")
        for campo in ("titulo", "titulo_en"):
            if campo in ev and not mensaje_valido(ev[campo], MAX_TITULO):
                errores.append(f"{etiqueta}: '{campo}' tiene que ser un texto de hasta {MAX_TITULO} caracteres, "
                               "sin < >, sin enlaces y sin espacios al principio o al final.")
        fechas_ok = True
        for campo in ("desde", "hasta"):
            if campo in ev and not _fecha_valida(ev[campo]):
                errores.append(f"{etiqueta}: '{campo}' tiene que ser una fecha real en formato AAAA-MM-DD.")
                fechas_ok = False
        if fechas_ok and "desde" in ev and "hasta" in ev and ev["desde"] > ev["hasta"]:
            errores.append(f"{etiqueta}: 'desde' no puede ser posterior a 'hasta'.")
        if "prioridad" in ev:
            p = ev["prioridad"]
            if isinstance(p, bool) or not isinstance(p, int) or not 0 <= p <= 100:
                errores.append(f"{etiqueta}: 'prioridad' tiene que ser un número entero entre 0 y 100.")
    return errores


def cargar(ruta: Path = DEFAULT_CALENDARIO) -> dict:
    """Lee y valida el calendario. Levanta ValueError con todos los errores
    juntos si algo está mal (el build falla antes de publicar nada)."""
    try:
        doc = json.loads(Path(ruta).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"No existe el calendario: {ruta}")
    except json.JSONDecodeError as e:
        raise ValueError(f"El calendario no es un JSON válido ({e.msg}, línea {e.lineno}).")
    errores = validar(doc)
    if errores:
        raise ValueError("Calendario inválido:\n  - " + "\n  - ".join(errores))
    return doc


def json_embebido(doc: dict) -> str:
    """JSON compacto para el bloque de datos del HTML. Escapa <, > y & (y
    los separadores de línea Unicode) para que nada pueda cerrar el
    <script> ni inyectar HTML. Incluye 'temas' (los ids con CSS real) para
    que tema.js pueda validar el parámetro ?tema= de la previsualización."""
    eventos = []
    for e in doc["eventos"]:
        item = {"tipo": e["tipo"], "desde": e["desde"], "hasta": e["hasta"], "prioridad": e.get("prioridad", 0)}
        if e["tipo"] == "tema":
            item["tema"] = e["tema"]
        if "horario" in e:
            item["franjas"] = franjas_de_horario(e["horario"])
        for campo in ("titulo", "titulo_en", "mensaje", "mensaje_en"):
            if campo in e:
                item[campo] = e[campo]
        eventos.append(item)
    salida = json.dumps(
        {"activo": doc["activo"], "zona": doc["zona_horaria"],
         "temas": list(TEMAS_CONOCIDOS), "eventos": eventos},
        ensure_ascii=True, separators=(",", ":"),
    )
    return (salida.replace("<", "\\u003c").replace(">", "\\u003e")
            .replace("&", "\\u0026").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def json_embebido_default() -> str:
    return json_embebido(cargar())
