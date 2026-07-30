#!/usr/bin/env python3
"""data.json + templates/menu.template.html -> dist/index.html"""
import html as html_mod
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
DEFAULT_JSON = HERE.parent / "dist" / "data.json"
DEFAULT_TEMPLATE = HERE.parent / "templates" / "menu.template.html"
DEFAULT_OUT = HERE.parent / "dist" / "index.html"


def _safe_json(obj) -> str:
    """json.dumps no escapa '</', así que un texto del Excel con '</script>' literal
    cerraría el <script> del template antes de tiempo e inyectaría HTML arbitrario."""
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def _bloque(texto: str, nombre: str, mantener: bool) -> str:
    """Quita <!--NOMBRE_START-->...<!--NOMBRE_END--> por completo si mantener=False,
    o solo los comentarios marcadores (dejando el contenido) si mantener=True.
    Un dato de contacto ausente en el maestro nunca debe publicarse como link roto."""
    patron = re.compile(
        rf"<!--{nombre}_START-->(.*?)<!--{nombre}_END-->", re.S
    )
    if mantener:
        return patron.sub(lambda m: m.group(1), texto)
    return patron.sub("", texto)


def render(data: dict, template: str) -> str:
    cfg = data["config"]
    wsp_number = cfg.get("whatsapp")
    ig_handle = cfg.get("instagram")
    direccion = cfg.get("direccion")

    out = template
    out = out.replace("__CATS_JSON__", _safe_json(data["cats"]))
    out = out.replace("__PRODS_JSON__", _safe_json(data["prods"]))
    out = out.replace("__PRECIOS_JSON__", _safe_json(data["precios"]))

    out = _bloque(out, "WSP", bool(wsp_number))
    out = out.replace("__WSP_NUMBER__", wsp_number or "")

    out = _bloque(out, "IG", bool(ig_handle))
    if ig_handle:
        out = out.replace("__IG_URL__", f"https://instagram.com/{ig_handle.lstrip('@')}")

    out = _bloque(out, "MAPS", bool(direccion))
    out = _bloque(out, "DIRECCION", bool(direccion))
    if direccion:
        out = out.replace("__MAPS_URL__", f"https://maps.google.com/?q={quote(direccion)}")
        out = out.replace("__DIRECCION__", html_mod.escape(direccion))

    return out


def main():
    json_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_JSON
    template_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_TEMPLATE
    out_path = Path(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_OUT

    data = json.loads(json_path.read_text(encoding="utf-8"))
    template = template_path.read_text(encoding="utf-8")
    html = render(data, template)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"OK: {out_path} ({len(html)} bytes)")


if __name__ == "__main__":
    main()
