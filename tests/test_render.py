"""Pruebas de build/render.py: JSON-LD (dirección real, sin inventar calle),
render sin placeholders, CSP presente, y que un campo interno de config
nunca aparezca en el HTML publicado. Solo biblioteca estándar."""
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build"))
import render  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_REAL = ROOT / "templates" / "menu.template.html"


def _data_minima(**overrides):
    data = {
        "cats": [{"cod": "BEB", "orden": 1, "nom": {"es": "Bebidas"}}],
        "prods": [{
            "id": "BEB001", "cat": "BEB", "orden": 1, "dest": False,
            "n": {"es": "Café"}, "d": {"es": "Café de especialidad"},
            "m": [], "b": [], "img": None,
        }],
        "precios": {"BEB001": {"ars": 1000}},
        "config": {
            "moneda": "ARS",
            "whatsapp": "5492604106653",
            "instagram": "ameli.casadete",
            "direccion": "Malargüe, Mendoza, Argentina",
            "url_base": "https://ameli-casa-de-te-brunch.github.io",
            "tripadvisor": None,
            "google_resenas": None,
        },
    }
    data.update(overrides)
    return data


class TestJsonLdDireccion(unittest.TestCase):
    def test_no_inventa_calle_y_usa_localidad_region_correctas(self):
        data = _data_minima()
        bruto = render._jsonld(data, "https://ameli-casa-de-te-brunch.github.io")
        obj = json.loads(bruto)
        direccion = obj["address"]
        self.assertNotIn("streetAddress", direccion)
        self.assertEqual(direccion["addressLocality"], "Malargüe")
        self.assertEqual(direccion["addressRegion"], "Mendoza")
        self.assertEqual(direccion["addressCountry"], "AR")

    def test_dos_partes_sin_pais_tambien_funciona(self):
        data = _data_minima(config={**_data_minima()["config"], "direccion": "Malargüe, Mendoza"})
        obj = json.loads(render._jsonld(data, "https://x.github.io"))
        self.assertNotIn("streetAddress", obj["address"])
        self.assertEqual(obj["address"]["addressLocality"], "Malargüe")
        self.assertEqual(obj["address"]["addressRegion"], "Mendoza")


class TestRenderSinPlaceholders(unittest.TestCase):
    def test_render_real_no_deja_marcadores_sin_reemplazar(self):
        template = TEMPLATE_REAL.read_text(encoding="utf-8")
        data = _data_minima()
        html = render.render(data, template)
        marcadores = re.findall(r"__[A-Z_]+__", html)
        self.assertEqual(marcadores, [], f"quedaron marcadores sin reemplazar: {marcadores}")

    def test_csp_presente_sin_unsafe_inline(self):
        template = TEMPLATE_REAL.read_text(encoding="utf-8")
        html = render.render(_data_minima(), template)
        self.assertIn("Content-Security-Policy", html)
        self.assertNotIn("unsafe-inline", html)
        self.assertIn("frame-ancestors 'none'", html)

    def test_campo_interno_de_config_nunca_aparece_en_el_html(self):
        template = TEMPLATE_REAL.read_text(encoding="utf-8")
        secreto = "https://docs.google.com/spreadsheets/d/deberia-quedar-afuera/pub?output=csv"
        data = _data_minima()
        data["config"]["disponibilidad_csv_url"] = secreto
        data["config"]["tasa_usd"] = 1234.5
        html = render.render(data, template)
        self.assertNotIn(secreto, html)
        self.assertNotIn("deberia-quedar-afuera", html)


class TestEnlacesExternosSeguros(unittest.TestCase):
    def test_todo_target_blank_tiene_noopener_noreferrer(self):
        template = TEMPLATE_REAL.read_text(encoding="utf-8")
        for match in re.finditer(r'<a\b[^>]*target="_blank"[^>]*>', template):
            etiqueta = match.group(0)
            self.assertIn('rel="noopener noreferrer"', etiqueta, f"falta rel seguro en: {etiqueta}")

    def test_referrer_no_referrer(self):
        template = TEMPLATE_REAL.read_text(encoding="utf-8")
        self.assertIn('<meta name="referrer" content="no-referrer">', template)


if __name__ == "__main__":
    unittest.main()
