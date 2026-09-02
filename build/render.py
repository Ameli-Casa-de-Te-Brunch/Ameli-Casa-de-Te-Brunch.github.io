#!/usr/bin/env python3
"""data/menu.json + templates/menu.template.html -> dist/index.html (+ assets/)"""
import base64
import datetime
import hashlib
import html as html_mod
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_JSON = HERE.parent / "data" / "menu.json"
DEFAULT_TEMPLATE = HERE.parent / "templates" / "menu.template.html"
DEFAULT_OUT = HERE.parent / "dist" / "index.html"
ASSETS_DIR = HERE.parent / "assets"

# Horario actual del local -- se repite acá porque el Excel todavía no lo
# tiene como dato estructurado (solo existe como texto de display en
# assets/js/menu.js, UI.datos + HORARIO). Si cambian el horario, hay que
# actualizar los dos lugares hasta que esto se mueva a la hoja de config.
HORARIO_JSONLD = [
    {"dayOfWeek": ["Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
     "opens": "09:00", "closes": "13:00"},
    {"dayOfWeek": ["Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
     "opens": "17:30", "closes": "21:00"},
]


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


def _jsonld(data: dict, url_base_limpia: str) -> str:
    """Restaurant + Menu (Schema.org) para resultados enriquecidos de Google.
    Se arma con los mismos datos que ya alimentan el sitio (una sola fuente),
    salvo el horario (ver HORARIO_JSONLD arriba)."""
    cfg = data["config"]
    direccion = cfg.get("direccion") or ""
    # "Malargüe, Mendoza, Argentina" -> separar en partes para PostalAddress.
    partes_dir = [p.strip() for p in direccion.split(",")]
    localidad = partes_dir[1] if len(partes_dir) > 1 else "Malargüe"

    secciones = []
    for cat in data["cats"]:
        items = [p for p in data["prods"] if p["cat"] == cat["cod"]]
        if not items:
            continue
        secciones.append({
            "@type": "MenuSection",
            "name": cat["nom"].get("es"),
            "hasMenuItem": [
                {
                    "@type": "MenuItem",
                    "name": p["n"].get("es"),
                    "description": p["d"].get("es"),
                }
                for p in items
            ],
        })

    obj = {
        "@context": "https://schema.org",
        "@type": "Restaurant",
        "name": "Amelí Casa de Té & Brunch",
        "url": f"{url_base_limpia}/",
        "image": f"{url_base_limpia}/assets/img/og-image.jpg",
        "servesCuisine": ["Café", "Té", "Brunch", "Pastelería"],
        "priceRange": "$$",
        "address": {
            "@type": "PostalAddress",
            "streetAddress": partes_dir[0] if partes_dir else direccion,
            "addressLocality": localidad,
            "addressRegion": "Mendoza",
            "addressCountry": "AR",
        },
        "openingHoursSpecification": [
            {"@type": "OpeningHoursSpecification", **h} for h in HORARIO_JSONLD
        ],
        "hasMenu": {
            "@type": "Menu",
            "hasMenuSection": secciones,
        },
    }
    if cfg.get("whatsapp"):
        obj["telephone"] = f"+{cfg['whatsapp']}"
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def render(data: dict, template: str) -> str:
    cfg = data["config"]
    wsp_number = cfg.get("whatsapp")
    ig_handle = cfg.get("instagram")
    direccion = cfg.get("direccion")
    url_base = cfg.get("url_base")

    out = template
    out = out.replace("__CATS_JSON__", _safe_json(data["cats"]))
    out = out.replace("__PRODS_JSON__", _safe_json(data["prods"]))
    out = out.replace("__PRECIOS_JSON__", _safe_json(data["precios"]))

    # og:url y og:image necesitan URL absoluta para que WhatsApp/Instagram
    # puedan armar la vista previa al compartir el link — sin "URL base del
    # menú" cargada en la config no hay forma de saber el dominio, así que
    # esas etiquetas directamente no se publican (mejor ausentes que rotas).
    url_base_limpia = url_base.rstrip("/") if url_base else None
    out = _bloque(out, "OG_URL", bool(url_base_limpia))
    if url_base_limpia:
        out = out.replace("__OG_URL__", html_mod.escape(f"{url_base_limpia}/"))
    out = _bloque(out, "OG_IMAGE", bool(url_base_limpia))
    if url_base_limpia:
        out = out.replace("__OG_IMAGE_URL__", html_mod.escape(f"{url_base_limpia}/assets/img/og-image.jpg"))

    out = _bloque(out, "CANONICAL", bool(url_base_limpia))
    if url_base_limpia:
        out = out.replace("__CANONICAL_URL__", html_mod.escape(f"{url_base_limpia}/"))

    out = _bloque(out, "JSONLD", bool(url_base_limpia))
    if url_base_limpia:
        out = out.replace("__JSONLD__", _jsonld(data, url_base_limpia))

    out = _bloque(out, "WSP", bool(wsp_number))
    out = out.replace("__WSP_NUMBER__", wsp_number or "")

    out = _bloque(out, "IG", bool(ig_handle))
    if ig_handle:
        out = out.replace("__IG_URL__", html_mod.escape(f"https://instagram.com/{ig_handle}"))

    out = _bloque(out, "DIRECCION", bool(direccion))
    if direccion:
        out = out.replace("__DIRECCION__", html_mod.escape(direccion))

    tripadvisor_url = cfg.get("tripadvisor")
    out = _bloque(out, "TA", bool(tripadvisor_url))
    if tripadvisor_url:
        out = out.replace("__TRIPADVISOR_URL__", html_mod.escape(tripadvisor_url))

    google_url = cfg.get("google_resenas")
    out = _bloque(out, "GOOGLE", bool(google_url))
    if google_url:
        out = out.replace("__GOOGLE_URL__", html_mod.escape(google_url))

    match = re.search(r"<script>(.*?)</script>", out, re.S)
    if not match:
        raise RuntimeError(
            "No encontré el <script> inline con los datos — no puedo calcular "
            "el hash para la Content-Security-Policy."
        )
    out = out.replace("__CSP_META__", _csp_meta(_hash_script_csp(match.group(1))))

    return out


def _escribir_seo_estatico(destino_dir: Path, url_base: str | None):
    """robots.txt y sitemap.xml -- sitemap.xml necesita URL absoluta, así
    que sin 'URL base del menú' cargada solo se escribe un robots.txt
    mínimo (sin línea Sitemap) y no se genera sitemap.xml."""
    url_base_limpia = url_base.rstrip("/") if url_base else None
    lineas_robots = ["User-agent: *", "Allow: /"]
    if url_base_limpia:
        lineas_robots += ["", f"Sitemap: {url_base_limpia}/sitemap.xml"]
    (destino_dir / "robots.txt").write_text("\n".join(lineas_robots) + "\n", encoding="utf-8")

    if url_base_limpia:
        hoy = datetime.date.today().isoformat()
        sitemap = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            "  <url>\n"
            f"    <loc>{html_mod.escape(url_base_limpia)}/</loc>\n"
            f"    <lastmod>{hoy}</lastmod>\n"
            "    <changefreq>weekly</changefreq>\n"
            "    <priority>1.0</priority>\n"
            "  </url>\n"
            "</urlset>\n"
        )
        (destino_dir / "sitemap.xml").write_text(sitemap, encoding="utf-8")


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
    _escribir_seo_estatico(out_path.parent, data["config"].get("url_base"))
    print(f"OK: {out_path} ({len(html)} bytes)")


if __name__ == "__main__":
    main()
