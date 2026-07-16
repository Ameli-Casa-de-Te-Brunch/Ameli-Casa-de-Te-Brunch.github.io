#!/usr/bin/env python3
"""data.json + templates/menu.template.html -> dist/index.html"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_JSON = HERE.parent / "dist" / "data.json"
DEFAULT_TEMPLATE = HERE.parent / "templates" / "menu.template.html"
DEFAULT_OUT = HERE.parent / "dist" / "index.html"

PLACEHOLDER_WSP = "549XXXXXXXXXX"  # mismo placeholder que traía el HTML a mano


def _safe_json(obj) -> str:
    """json.dumps no escapa '</', así que un texto del Excel con '</script>' literal
    cerraría el <script> del template antes de tiempo e inyectaría HTML arbitrario."""
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def render(data: dict, template: str) -> str:
    cfg = data["config"]
    wsp_number = (cfg.get("whatsapp") or PLACEHOLDER_WSP).replace(" ", "").replace("+", "")
    ig_handle = (cfg.get("instagram") or "@ameli").lstrip("@")

    out = template
    out = out.replace("__CATS_JSON__", _safe_json(data["cats"]))
    out = out.replace("__PRODS_JSON__", _safe_json(data["prods"]))
    out = out.replace("__PRECIOS_JSON__", _safe_json(data["precios"]))
    out = out.replace("__WSP_NUMBER__", wsp_number)
    out = out.replace("__IG_URL__", f"https://instagram.com/{ig_handle}")
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
