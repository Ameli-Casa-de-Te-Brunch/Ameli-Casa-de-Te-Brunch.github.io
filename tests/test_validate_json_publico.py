"""Pruebas de build/validate_json_publico.py: estructura, campos públicos,
IDs, categorías, disponibilidad, URLs/handles, marcadores sin reemplazar --
y una corrida contra el data/menu.json real committeado, que tiene que dar
cero errores (si esto falla, algo en el JSON público real está roto).
Solo biblioteca estándar."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build"))
import validate_json_publico as vjp  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MENU_JSON_REAL = ROOT / "data" / "menu.json"


def _doc_valido():
    return {
        "cats": [{"cod": "BEB", "orden": 1, "nom": {"es": "Bebidas"}}],
        "prods": [{
            "id": "BEB001", "cat": "BEB", "orden": 1, "dest": False,
            "n": {"es": "Café", "en": "Coffee", "pt": "Café", "fr": "Café", "it": "Caffè"},
            "d": {"es": "d", "en": "d", "pt": "d", "fr": "d", "it": "d"},
            "m": [], "b": [], "img": None,
        }],
        "precios": {"BEB001": {"ars": 1000}},
        "config": {
            "moneda": "ARS", "whatsapp": "5492604106653", "instagram": "ameli.casadete",
            "direccion": "Malargüe, Mendoza, Argentina",
            "url_base": "https://ameli-casa-de-te-brunch.github.io",
            "tripadvisor": None, "google_resenas": None,
        },
    }


class TestDocumentoValido(unittest.TestCase):
    def test_documento_minimo_valido_no_tiene_errores(self):
        errors, _warnings = vjp.validate_menu_json(_doc_valido())
        self.assertEqual(errors, [])


class TestCamposYTipos(unittest.TestCase):
    def test_campo_no_publico_en_producto_es_error(self):
        doc = _doc_valido()
        doc["prods"][0]["_fila"] = 12
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("_fila" in e for e in errors))

    def test_campo_interno_en_config_es_error(self):
        doc = _doc_valido()
        doc["config"]["disponibilidad_csv_url"] = "https://docs.google.com/x"
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("disponibilidad_csv_url" in e for e in errors))

    def test_falta_clave_de_primer_nivel(self):
        doc = _doc_valido()
        del doc["precios"]
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("precios" in e for e in errors))


class TestIdsYReferencias(unittest.TestCase):
    def test_id_duplicado(self):
        doc = _doc_valido()
        doc["prods"].append(dict(doc["prods"][0]))
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("duplicado" in e for e in errors))

    def test_categoria_inexistente(self):
        doc = _doc_valido()
        doc["prods"][0]["cat"] = "ZZZ"
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("ZZZ" in e for e in errors))

    def test_precio_huerfano(self):
        doc = _doc_valido()
        doc["precios"]["NOEXISTE"] = {"ars": 1}
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("huérfana" in e for e in errors))


class TestDisponibilidad(unittest.TestCase):
    def test_codigo_valido_no_es_error(self):
        doc = _doc_valido()
        doc["prods"][0]["disp"] = "agotado"
        errors, _ = vjp.validate_menu_json(doc)
        self.assertEqual(errors, [])

    def test_codigo_invalido_es_error(self):
        doc = _doc_valido()
        doc["prods"][0]["disp"] = "en_camino"
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("en_camino" in e for e in errors))


class TestConfigValidacion(unittest.TestCase):
    def test_whatsapp_invalido(self):
        doc = _doc_valido()
        doc["config"]["whatsapp"] = "123"
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("whatsapp" in e for e in errors))

    def test_instagram_invalido(self):
        doc = _doc_valido()
        doc["config"]["instagram"] = "<script>"
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("instagram" in e for e in errors))

    def test_url_base_dominio_no_permitido(self):
        doc = _doc_valido()
        doc["config"]["url_base"] = "https://ejemplo-no-permitido.com"
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("url_base" in e for e in errors))


class TestMarcadoresSinReemplazar(unittest.TestCase):
    def test_marcador_suelto_es_error(self):
        doc = _doc_valido()
        doc["prods"][0]["n"]["es"] = "__ALGO__"
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("__ALGO__" in e for e in errors))


class TestJsonPublicoReal(unittest.TestCase):
    """El JSON público committeado hoy tiene que pasar este validador con
    cero errores -- si esto falla, algo real está roto, no la prueba."""

    def test_menu_json_real_sin_errores(self):
        if not MENU_JSON_REAL.exists():
            self.skipTest(f"no existe {MENU_JSON_REAL} en este checkout")
        data = json.loads(MENU_JSON_REAL.read_text(encoding="utf-8"))
        errors, _warnings = vjp.validate_menu_json(data)
        self.assertEqual(errors, [], f"data/menu.json real tiene errores: {errors}")


if __name__ == "__main__":
    unittest.main()
