#!/usr/bin/env python3
"""data/menu.json + templates/menu.template.html -> dist/index.html (+ assets/)"""
import base64
import hashlib
import html as html_mod
import json
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
DEFAULT_JSON = HERE.parent / "data" / "menu.json"
DEFAULT_TEMPLATE = HERE.parent / "templates" / "menu.template.html"
DEFAULT_OUT = HERE.parent / "dist" / "index.html"
ASSETS_DIR = HERE.parent / "assets"


def copiar_assets(destino_dir: Path):
    """Copia assets/ (fuentes self-hosteadas) junto al index.html generado —
    tienen que viajar con el HTML para que las rutas relativas del CSS funcionen."""
    if not ASSETS_DIR.exists():
        return
    shutil.copytree(ASSETS_DIR, destino_dir / "assets", dirs_exist_ok=True)


def _safe_json(obj) -> str:
    """json.dumps no escapa '</', así que un texto del Excel con '</script>' literal
    cerraría el <script> del template antes de tiempo e inyectaría HTML arbitrario."""
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def _hash_script_csp(contenido: str) -> str:
    """CSP permite un <script> inline puntual si declarás el hash exacto de su
    contenido (script-src 'sha256-...'), en vez de abrir la puerta con
    'unsafe-inline'. El contenido cambia en cada build (trae los datos del
    Excel), así que el hash se recalcula acá, no se hardcodea."""
    digest = hashlib.sha256(contenido.encode("utf-8")).digest()
    return "sha256-" + base64.b64encode(digest).decode("ascii")


def _csp_meta(hash_script: str) -> str:
    """Restrictiva a propósito: el sitio no carga nada de terceros (ver README,
    sección 'Cabeceras de seguridad'). GitHub Pages no permite mandar cabeceras
    HTTP, así que esto va como <meta>, que es lo único disponible en ese caso."""
    politica = "; ".join([
        "default-src 'none'",
        f"script-src 'self' '{hash_script}'",
        "style-src 'self'",
        "font-src 'self'",
        "img-src 'self'",
        "connect-src 'none'",
        "frame-ancestors 'none'",
        "base-uri 'none'",
        "form-action 'none'",
    ])
    return f'<meta http-equiv="Content-Security-Policy" content="{politica}">'


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

    match = re.search(r"<script>(.*?)</script>", out, re.S)
    if not match:
        raise RuntimeError(
            "No encontré el <script> inline con los datos — no puedo calcular "
            "el hash para la Content-Security-Policy."
        )
    out = out.replace("__CSP_META__", _csp_meta(_hash_script_csp(match.group(1))))

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
    copiar_assets(out_path.parent)
    print(f"OK: {out_path} ({len(html)} bytes)")


if __name__ == "__main__":
    main()
